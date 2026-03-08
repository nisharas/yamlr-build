"""
Processor Module for Yamlr Engine.

Why: To handle high-concurrency batch healing operations and global semantic analysis
using multiprocessing workers.
"""
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn

from yamlr.analyzers.cross_resource import CrossResourceAnalyzer
from yamlr.analyzers.ref_resolver import ReferenceResolver
from yamlr.core.engine import crawler
from yamlr.core.utils import construct_file_error, derive_status
from yamlr.healers.semantic.missing_target import MissingTargetHealer
from yamlr.models import Shard, ManifestIdentity, HealFileResult

logger = logging.getLogger("yamlr.engine.processor")

from yamlr.core.engine.worker import _init_worker, _execute_healing_chunk

def batch_heal(
    engine,
    root_path: str,
    extensions: List[str],
    max_depth: int = 10,
    dry_run: bool = True,
    force_write: bool = False,
    identity_mode: str = "infer",
    stub_healing: Any = False,
    allow_unsafe: Any = False,
    enforce_limits: bool = False,
    fix_tags: bool = False,
    harden: bool = False,
    enforce_probes: bool = False,
    strict_validation: bool = False,
    compact: bool = False,
    skip_backup: bool = False,
    enforce_namespace: bool = False,
    fast: bool = False,
    stream_to: Optional[str] = None,
    check_deprecations: bool = False,
    task_label: str = "Healing",
    evidence_dir: Optional[str] = None,
    adapters_dir: Optional[str] = None,
) -> List[HealFileResult]:
    """Crawls the filesystem starting at root_path to find and heal manifests."""
    start_time = time.time()
    results = []
    search_root = Path(root_path).resolve()

    if not search_root.exists():
        logger.error(f"Batch path does not exist: {root_path}")
        return results

    # 1. Crawl File System for Manifests
    engine_context = {
        "strict_validation": strict_validation,
        "compact": compact,
        "version": engine.cluster_version,
        "identity_mode": identity_mode,
        "threshold": engine.health_threshold,
        "enforce_limits": enforce_limits,
        "fix_tags": fix_tags,
        "harden": harden,
        "enforce_probes": enforce_probes,
        "dry_run": dry_run,
        "force_write": force_write,
        "skip_backup": skip_backup,
        "enforce_namespace": enforce_namespace,
        "fast": fast,
        "check_deprecations": check_deprecations,
        "fix_refs": stub_healing or allow_unsafe, # Derived or direct
        "evidence_dir": evidence_dir,
        "adapters_dir": adapters_dir,
        "quota_checked": True,
    }

    files_to_process = crawler.crawl_manifests(
        workspace_root=engine.workspace,
        root_path=root_path,
        extensions=extensions,
        max_depth=max_depth,
        engine_context=engine_context
    )

    # --- [MONETIZATION] FREE TIER HABIT GATE & BULK GUARDRAIL ---
    if not dry_run and len(files_to_process) > 0:
        from yamlr.core.license_manager import LicenseManager
        from rich.console import Console
        from rich.panel import Panel
        
        is_allowed, remaining, msg = LicenseManager.is_healing_allowed(len(files_to_process))
        if not is_allowed:
            LicenseManager.notify_quota_exceeded(msg)
            # Abort the process peacefully by returning empty results
            return results
    # ------------------------------------------------------------

    concurrency = getattr(engine, "concurrency", os.cpu_count() or 1)
    is_ultra_scale = len(files_to_process) > 5000
    
    # NDJSON Streaming Setup
    stream_fh = None
    if stream_to:
        try:
            stream_fh = open(stream_to, "w", encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to open stream file: {e}")

    if len(files_to_process) > 1 and concurrency > 1:
        # 2. Chunking: Use crawler for optimized work unit distribution
        chunk_size = 100 if is_ultra_scale else 20
        chunks = crawler.chunk_tasks(files_to_process, chunk_size)
        
        logger.info(f"🚀 Starting { 'ULTRA-SCALE' if is_ultra_scale else 'parallel' } surgery on {len(files_to_process)} manifest(s)...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            expand=True
        ) as progress:
            active_label = f"{task_label} manifests..."
            heal_task = progress.add_task(f"[cyan]{active_label}", total=len(files_to_process))
            
            with ProcessPoolExecutor(
                max_workers=concurrency,
                initializer=_init_worker,
                initargs=(
                    engine.catalog,
                    engine.cpu_limit,
                    engine.mem_limit,
                    engine.default_namespace,
                    engine.app_name,
                    engine.cluster_version,
                    str(engine.workspace),
                    logging.getLogger("yamlr").getEffectiveLevel(),
                ),
            ) as executor:
                futures = {executor.submit(_execute_healing_chunk, {"files": c}): c for c in chunks}
                for future in as_completed(futures):
                    try:
                        chunk_results = future.result()
                        for res in chunk_results:
                            # Stream to NDJSON if requested
                            if stream_fh:
                                stream_fh.write(json.dumps(res.to_dict()) + "\n")
                                stream_fh.flush()

                            # Ultra-Aggressive Memory PRUNING for Master Process
                            # We keep ONLY identities (for global analysis) and status/path
                            if is_ultra_scale and res.success and res.status == "CLEAN":
                                res.logic_logs = []
                                res.findings = []
                                res.healed_content = None
                                res.raw_content = None
                            
                            # Standard pruning
                            if not dry_run and getattr(res, "written", False):
                                res.healed_content = None

                            results.append(res)
                            progress.update(heal_task, advance=1)
                    except Exception as e:
                        logger.error(f"Worker chunk failed: {e}")
            
            # Update label to past tense on completion
            progress.update(heal_task, description=f"[green]{task_label.replace('ing', 'ed')} manifests")
    else:
        # Sequential (Small batch or fallback)
        for f in files_to_process:
            # Clean f for kwargs
            f_kwargs = f.copy()
            target_path = f_kwargs.pop("path")
            # Remove only engine-internal keys that the auditor DOES NOT take.
            for key in ["full_path", "version", "threshold", "task_label"]:
                f_kwargs.pop(key, None)
            
            # [MONETIZATION] Signal that batch already performed the quota check
            f_kwargs["quota_checked"] = True
            
            res = engine.audit_and_heal_file(target_path, **f_kwargs)
            if stream_fh:
                stream_fh.write(json.dumps(res.to_dict()) + "\n")
            results.append(res)

    if stream_fh: stream_fh.close()

    # Global Analysis phase (Remains in-memory but results are pruned)
    all_identities = []
    file_map = {}
    for res in results:
        path = res.full_path or res.file_path
        file_map[path] = res
        raw_ids = getattr(res, "_raw_identities", [])
        for ident in raw_ids:
            ident.file_path = path
            all_identities.append(ident)

    try:
        analyzer = CrossResourceAnalyzer()
        cross_findings = analyzer.analyze(all_identities)
        for finding in cross_findings:
            target_res = file_map.get(finding.file_path)
            if not target_res: continue
            
            # Re-inflate logs/findings if they were pruned (since this is an issue)
            if target_res.logic_logs is None: target_res.logic_logs = []
            if target_res.findings is None: target_res.findings = []
            
            msg = f"Graph Analysis: {finding.message} ({finding.suggestion})"
            target_res.logic_logs.append(msg)
            target_res.findings.append({
                "message": finding.message,
                "severity": finding.severity.lower(),
                "resource": f"{finding.resource_kind}/{finding.resource_name}",
                "suggestion": finding.suggestion,
                "analyzer": "cross-resource",
                "rule_id": finding.rule_id
            })
            if finding.severity.upper() == "ERROR":
                target_res.success = False
                target_res.status = "FAILED"
            
            # Update SEM status after global analysis
            target_res.sem_status = "⚠️ FAIL"
    except Exception as e:
        logger.warning(f"Global Graph Analysis failed: {e}")

    apply_semantic_fixes(engine, results, stub_healing, allow_unsafe, dry_run)
    
    # --- RECORD TELEMETRY ---
    total_breakdown = {
        "lexer_repairs": 0, "lexer_typos": 0, "semantic_repairs": 0,
        "security_hardens": 0, "migrator_changes": 0
    }
    total_score = 0.0
    total_fixed = 0
    for res in results:
        total_score += getattr(res, "health_score", 0) or 0
        s = getattr(res, "processing_stats", None) or {}
        for key in total_breakdown:
            total_breakdown[key] += s.get(key, 0)
        total_fixed += (s.get("lexer_repairs", 0) + s.get("lexer_typos", 0) + 
                        s.get("semantic_repairs", 0) + s.get("security_hardens", 0) + 
                        s.get("migrator_changes", 0))
    
    avg_score = total_score / len(results) if results else 0.0
    
    # Calculate Max Severity & Risk for CI Gating
    severity_rank = {"error": 100, "warning": 50, "info": 10, "none": 0}
    risk_rank = {"high": 100, "medium": 50, "low": 10, "none": 0}
    max_sev_rank = 0
    max_sev_label = "info"
    max_risk_rank = 0
    max_risk_label = "low"
    for res in results:
        for f in res.findings:
            sev = f.get("severity", "info").lower()
            rank = severity_rank.get(sev, 10)
            if rank > max_sev_rank:
                max_sev_rank = rank
                max_sev_label = sev
            
            risk = f.get("risk_level", "low").lower()
            rrank = risk_rank.get(risk, 10)
            if rrank > max_risk_rank:
                max_risk_rank = rrank
                max_risk_label = risk

    duration = time.time() - start_time
    total_bytes = 0
    for res in results:
        # We need a way to track input bytes. If not available in res, estimate from healed content
        # or just assume 0 for now if it's too expensive to re-read. 
        # Better: worker should return it. For now, estimate or use 0.
        pass

    engine.telemetry.record_session(
        files_count=len(results),
        fixed_issues=total_fixed,
        avg_health_score=avg_score,
        is_heal=not dry_run,
        max_severity=max_sev_label,
        max_risk=max_risk_label,
        breakdown=total_breakdown,
        duration_seconds=duration,
        bytes_processed=total_bytes # Placeholder until worker returns it
    )
    
    results.sort(key=lambda x: getattr(x, "full_path", getattr(x, "file_path", "")))
    return results

def apply_semantic_fixes(
    engine,
    results: List[HealFileResult],
    stub_healing: Any,
    allow_unsafe: Any,
    dry_run: bool,
) -> int:
    """Runs RefResolver -> Healer pipeline on results."""
    if not results or not stub_healing:
        return 0

    from io import StringIO
    import yaml

    all_identities = []
    file_map = {}
    for res in results:
        path = res.full_path
        file_map[path] = res
        raw_ids = getattr(res, "_raw_identities", [])
        for ident in raw_ids:
            ident.file_path = path
            all_identities.append(ident)

    files_modified_count = 0
    try:
        resolver = ReferenceResolver()
        candidates = resolver.resolve_references(all_identities)
        if candidates:
            logger.info(f"Found {len(candidates)} reference issues. Checking healing rules...")
            healer = MissingTargetHealer()
            cli_flags = {"stub_refs": stub_healing, "unsafe": allow_unsafe}
            pending_changes = {}

            for issue in candidates:
                mini_batch = [issue]
                new_stubs, suggestions = healer.heal(mini_batch, cli_flags)
                if suggestions:
                    source_ident = issue.get("source")
                    if source_ident and source_ident.file_path:
                        target_res = file_map.get(source_ident.file_path)
                        if target_res:
                            if target_res.logic_logs is None: target_res.logic_logs = []
                            target_res.logic_logs.extend([f"Warning - {s}" for s in suggestions])

                if new_stubs:
                    stub_doc = new_stubs[0]
                    source_ident = issue.get("source")
                    if source_ident and source_ident.file_path:
                        pending_changes.setdefault(source_ident.file_path, []).append(stub_doc)

            for target_file, stubs in pending_changes.items():
                target_res = file_map.get(target_file)
                if not target_res: continue
                try:
                    full_p = Path(target_res.full_path)
                    # For dry-run, we might not have touched the file yet, read raw
                    if not target_res.healed_content:
                         target_res.healed_content = full_p.read_text(encoding="utf-8") if full_p.exists() else ""

                    final_content = target_res.healed_content
                    if final_content and not final_content.endswith("\n"): final_content += "\n"

                    for stub_doc in stubs:
                        stream = StringIO()
                        yaml.dump(stub_doc, stream)
                        stub_yaml = stream.getvalue()
                        is_unsafe = stub_doc.get("metadata", {}).get("annotations", {}).get("yamlr.dev/safety") == "UNSAFE"
                        log_msg = f"  [+] Appending stub {stub_doc['kind']}/{stub_doc['metadata']['name']}"
                        if is_unsafe: log_msg += " ⚠️ (UNSAFE)"
                        if target_res.logic_logs is None: target_res.logic_logs = []
                        target_res.logic_logs.append(log_msg)
                        if target_res.findings is None: target_res.findings = []
                        target_res.findings.append({
                            "message": f"Generated missing {stub_doc['kind']}" + (" (UNSAFE)" if is_unsafe else ""),
                            "severity": "warning" if is_unsafe else "info",
                            "resource": f"{stub_doc['kind']}/{stub_doc['metadata']['name']}",
                            "analyzer": "semantic-healer",
                        })
                        header = "---\n# [Yamlr] Auto-Generated Stub\n"
                        if is_unsafe:
                            header += "# ⚠️  SAFETY WARNING: This resource is sensitive.\n# Generic values have been injected. Verify manually before use.\n"
                        final_content += header + stub_yaml
                    
                    # CRITICAL FIX: Update the result object so DiffEngine can show the stubs!
                    target_res.healed_content = final_content

                    if not dry_run:
                        engine.fs.atomic_write(full_p, final_content)
                        files_modified_count += 1
                        target_res.written = True
                        
                except Exception as write_err:
                    logger.error(f"Failed to apply stubs to {target_file}: {write_err}")

            if files_modified_count > 0 or (dry_run and pending_changes):
                logger.info(f"✨ Semantic Healer generated {sum(len(v) for v in pending_changes.values())} resource stubs.")
    except Exception as e:
        logger.error(f"Semantic Healing Pass failed: {e}", exc_info=True)

    return files_modified_count
