"""
Processor Module for Yamlr Engine.

Why: To handle high-concurrency batch healing operations and global semantic analysis
using multiprocessing workers.
"""
from __future__ import annotations
import logging
import os
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING, TextIO, Generator
from joblib import Parallel, delayed
if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from yamlr.core.entrypoints.base import get_console
from yamlr.models import HealFileResult

from yamlr.core.engine import crawler
from yamlr.parsers.hcl_parser import parse_tf_files
from yamlr.analyzers.ref_resolver import ReferenceResolver
from yamlr.healers.semantic.missing_target import MissingTargetHealer

from yamlr.core.engine.processor_helpers import (
    prepare_batch_context, check_batch_quota, 
    run_global_analysis, record_batch_telemetry
)

logger = logging.getLogger("yamlr.engine.processor")

__all__ = ["batch_heal", "apply_semantic_fixes"]

def batch_heal(
    engine: "YamlrEngine",
    root_path: str,
    extensions: List[str],
    max_depth: int = 10,
    dry_run: bool = True,
    force_write: bool = False,
    identity_mode: str = "infer",
    stub_healing: bool = False,
    allow_unsafe: bool = False,
    enforce_limits: bool = False,
    fix_tags: bool = False,
    harden: bool = False,
    enforce_probes: bool = False,
    strict_validation: bool = False,
    compact: bool = False,
    skip_backup: bool = False,
    enforce_namespace: bool = False,
    fast: bool = False,
    sovereign: bool = False,
    stream_to: Optional[str] = None,
    check_deprecations: bool = False,
    task_label: str = "Healing",
    evidence_dir: Optional[str] = None,
    adapters_dir: Optional[str] = None,
    generate_receipts: bool = False,
    use_rust: bool = False,
    from_report_path: Optional[str] = None,
    pro_preview: bool = False,
) -> List[HealFileResult]:
    """Crawls the filesystem starting at root_path to find and heal manifests.

    Why: High-performance batch coordinator using multiprocessing and global analysis.
    """
    start_time = time.time()
    roots = [root_path] if isinstance(root_path, str) else root_path
    
    # 1. Preparation
    params = locals().copy()
    params.pop("engine", None)
    engine_context = prepare_batch_context(engine, params)

    files_to_process = crawler.crawl_manifests(
        workspace_root=engine.workspace,
        root_path=root_path,
        extensions=extensions,
        max_depth=max_depth,
        engine_context=engine_context,
        use_rust=use_rust
    )

    # Cross-Domain Discovery
    tf_identities = []
    for r in roots:
        try:
            root_p = Path(r).resolve()
            if root_p.exists():
                tf_identities.extend(parse_tf_files(root_p))
        except (OSError, ValueError):
            continue

    if tf_identities:
        logger.info(f"🌐 [Cross-Domain] Discovered {len(tf_identities)} Terraform resources")

    # 2. Quota Check
    if not check_batch_quota(dry_run, len(files_to_process)):
        return []

    # [HARDENING] Redirect artifacts to .yamlr_runtime if receipts requested
    if generate_receipts and not stream_to:
        runtime_dir = engine.config.runtime_dir
        runtime_dir.mkdir(parents=True, exist_ok=True)
        stream_to = str(runtime_dir / f"audit_{int(time.time())}.jsonl")

    # [PERF] Define Ultra-Scale Threshold (5000 manifests)
    is_ultra_scale = len(files_to_process) > 5000

    # 3. Execution (Pass 1)
    results_gen = _execute_batch_execution(
        engine, files_to_process, dry_run, stream_to, task_label, from_report_path, is_ultra_scale, engine_context
    )

    summary_results: List[HealFileResult] = []
    
    if is_ultra_scale:
        # [ULTRA-SCALE] Zero-List Master Process
        # Why: Exhausting RAM with 1M+ result objects is the primary OOM cause.
        # We consume the generator, populate DiskIndex, and keep only hollow summary results.
        for res in results_gen:
            if hasattr(res, "identities") and res.identities and engine.disk_index:
                # Convert dict to ManifestIdentity if necessary
                from yamlr.models import ManifestIdentity
                idents = []
                for id_data in res.identities:
                    if isinstance(id_data, dict):
                        ident = ManifestIdentity.from_dict(id_data)
                    else:
                        ident = id_data
                    ident.file_path = res.full_path or res.file_path
                    idents.append(ident)
                engine.disk_index.add_all(idents)
            
            # Keep a hollow summary for telemetry/summary reporting
            res.healed_content, res.raw_content = None, None
            res.logic_logs, res.findings = [], [] # [Zero-RAM]
            summary_results.append(res)
        
        # 4. Global Analysis (Pass 1.5) - Index-First
        run_global_analysis(None, tf_identities, None, index=engine.disk_index)
        
        # 5. Semantic Fixes (Pass 2) - Targeted parallelization
        apply_semantic_fixes(engine, None, stub_healing, allow_unsafe, dry_run, index=engine.disk_index)
        
        # Record final telemetry from hollow summaries
        record_batch_telemetry(engine, summary_results, dry_run, start_time)
        return summary_results
    
    # Standard path: collect results for small/medium batches
    results = list(results_gen)

    # 4. Global Analysis phase
    file_map = { (res.full_path or res.file_path): res for res in results }
    run_global_analysis(results, tf_identities, file_map)

    concurrency = getattr(engine, "concurrency", os.cpu_count() or 1)
    apply_semantic_fixes(engine, results, stub_healing, allow_unsafe, dry_run, concurrency=concurrency)
    
    # 5. Telemetry
    record_batch_telemetry(engine, results, dry_run, start_time)
    
    results.sort(key=lambda x: getattr(x, "full_path", getattr(x, "file_path", "")))
    return results

def _execute_batch_execution(
    engine: "YamlrEngine", files_to_process: List[Dict[str, Any]], dry_run: bool, 
    stream_to: Optional[str], task_label: str, from_report_path: Optional[str],
    is_ultra_scale: bool = False, engine_context: Optional[Dict[str, Any]] = None
) -> Generator[HealFileResult, None, None]:
    """Handles the selection between parallel and sequential execution.
    """
    concurrency = getattr(engine, "concurrency", os.cpu_count() or 1)
    
    stream_fh = None
    if stream_to:
        try:
            stream_fh = open(stream_to, "w", encoding="utf-8")
        except OSError as e:
            logger.error(f"Failed to open stream file: {e}")

    try:
        if len(files_to_process) > 1 and concurrency > 1:
            results_gen = _execute_parallel_batch(
                engine, files_to_process, concurrency, dry_run, stream_fh, task_label, is_ultra_scale, engine_context
            )
            for res in results_gen:
                yield res
        else:
            results_gen = _execute_sequential_batch(engine, files_to_process, stream_fh, from_report_path)
            for res in results_gen:
                yield res
    finally:
        if stream_fh:
            stream_fh.close()

def _execute_parallel_batch(
    engine: "YamlrEngine", files_to_process: List[Dict[str, Any]], concurrency: int, 
    dry_run: bool, stream_fh: Optional[TextIO], task_label: str, is_ultra_scale: bool = False,
    engine_context: Optional[Dict[str, Any]] = None
) -> Generator[HealFileResult, None, None]:
    """Runs healing in parallel using a process pool.
    
    Why: To leverage multi-core systems for 'Ultra-Scale' repositories, 
         significantly reducing total processing time.
    """
    is_fast = engine_context and engine_context.get("fast")
    # [VAL-02-6] Optimized chunking for native acceleration
    # 100 files per chunk balances IPC overhead and worker utilization
    chunk_size = 100 if is_fast else (200 if is_ultra_scale else 20)
    chunks = crawler.chunk_tasks(files_to_process, chunk_size)
    
    logger.info(f"🚀 Starting { 'FAST-PATH' if is_fast else ('ULTRA-SCALE' if is_ultra_scale else 'parallel') } surgery on {len(files_to_process)} manifest(s)...")
    
    from yamlr.core.engine.processor_helpers import run_parallel_surgery_pool
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=get_console()
    ) as progress:
        active_label = f"{task_label} manifests..."
        heal_task = progress.add_task(f"[cyan]{active_label}", total=len(files_to_process))
        
        yield from run_parallel_surgery_pool(
            engine, chunks, concurrency, 
            stream_fh, is_ultra_scale, engine_context, 
            progress, heal_task
        )
        
        progress.update(heal_task, description=f"[green]{task_label.replace('ing', 'ed')} manifests")

def _execute_sequential_batch(
    engine: "YamlrEngine", files_to_process: List[Dict[str, Any]], stream_fh: Optional[TextIO], from_report_path: Optional[str]
) -> Generator[HealFileResult, None, None]:
    """Runs healing sequentially for small batches or fallback.
    
    Why: To avoid the overhead of process creation for small file sets, 
         optimizing for developer 'Habit' loops.
    """
    for f in files_to_process:
        f_kwargs = f.copy()
        target_path = f_kwargs.pop("path")
        for key in ["full_path", "version", "threshold", "task_label"]:
            f_kwargs.pop(key, None)
        
        f_kwargs["quota_checked"] = True
        f_kwargs["from_report_path"] = from_report_path
        
        res = engine.audit_and_heal_file(target_path, **f_kwargs)
        if stream_fh:
            stream_fh.write(json.dumps(res.to_dict()) + "\n")
        yield res

def apply_semantic_fixes(
    engine: "YamlrEngine",
    results: Optional[List[HealFileResult]],
    stub_healing: bool,
    allow_unsafe: bool,
    dry_run: bool,
    concurrency: int = 1,
    index: Optional["DiskIndex"] = None,
) -> int:
    """Runs RefResolver -> Healer pipeline on results with parallel I/O."""
    # [ULTRA-SCALE] Pass 2 optimization: Only process affected files.
    if index and results is None:
        return _apply_semantic_fixes_disk_index(engine, index, stub_healing, dry_run, concurrency)

    if not results:
        return 0
    
    file_map = { res.full_path: res for res in results }
    is_scale = len(results) > 5000 # Threshold matches is_ultra_scale in batch_heal
    
    try:
        # 1. Acquire Index
        global_index = _get_global_index(results, is_scale)
        
        # 2. Resolve References
        resolver = ReferenceResolver()
        candidates = _resolve_all_references(results, global_index, resolver, is_scale, concurrency)

        if not candidates:
            return 0

        # 3. Generate Stubs
        logger.info(f"Found {len(candidates)} reference issues. Checking healing rules...")
        pending_changes = _generate_healer_stubs(candidates, file_map, stub_healing, allow_unsafe)

        # 4. Parallel Apply
        if not pending_changes:
            return 0
            
        return _apply_all_healer_changes(engine, pending_changes, file_map, dry_run, concurrency)
            
    except (RuntimeError, ValueError, AttributeError, KeyError) as e:
        logger.error(f"Semantic Healing Pass failed: {e}", exc_info=True)
        return 0
    finally:
        if 'global_index' in locals() and hasattr(global_index, 'close'):
            global_index.close()

def _get_global_index(results: List[HealFileResult], is_scale: bool) -> Any:
    """Builds or retrieves the resource index."""
    if is_scale:
        return _build_disk_index(results)
    return _build_memory_index(results)

def _build_disk_index(results: List[HealFileResult]) -> Any:
    """Builds a DiskIndex for hyperscale processing."""
    from yamlr.analyzers.detectors.disk_index import DiskIndex
    logger.info(f"💾 Hyperscale detected ({len(results)} files). Initializing DiskIndex...")
    disk_index = DiskIndex()
    for res in results:
        for ident in (getattr(res, "_raw_identities", []) or []):
            if ident and ident.kind and ident.name:
                disk_index.add_all([ident])
    disk_index.commit()
    return disk_index

def _build_memory_index(results: List[HealFileResult]) -> Any:
    """Builds an in-memory index for standard processing."""
    all_identities = []
    for res in results:
        for ident in (getattr(res, "_raw_identities", []) or []):
            if ident:
                ident.file_path = res.full_path
                all_identities.append(ident)
    from yamlr.analyzers.detectors import CrossResourceDetectors
    return CrossResourceDetectors.build_index(all_identities)

def _resolve_all_references(results, index, resolver, is_scale, concurrency) -> List:
    """Orchestrates reference resolution across results."""
    if is_scale:
        from yamlr.models import ManifestIdentity
        typed_idents = (ManifestIdentity.from_dict(d) for d in index.get_all())
        return resolver.resolve_references(typed_idents, index=index)
    
    all_identities = []
    for res in results:
        for ident in (getattr(res, "_raw_identities", []) or []):
            if ident:
                ident.file_path = res.full_path
                all_identities.append(ident)
    
    if len(all_identities) > 100 and concurrency > 1:
        from yamlr.core.engine.worker import _execute_global_resolution_task
        parallel_executor = Parallel(n_jobs=concurrency, prefer="processes")
        tasks = [{"identities": [id.to_dict() for id in all_identities[i:i+500]], "index": index} 
                 for i in range(0, len(all_identities), 500)]
        results_list = parallel_executor(delayed(_execute_global_resolution_task)(t) for t in tasks)
        return [item for sublist in results_list for item in sublist]
    
    return resolver.resolve_references(all_identities, index=index)

def _generate_healer_stubs(candidates, file_map, stub_healing, allow_unsafe) -> Dict[str, List]:
    """Generates stubs for identified issues and updates result logs."""
    healer = MissingTargetHealer()
    cli_flags = {"stub_refs": stub_healing, "unsafe": allow_unsafe}
    pending_changes = {}

    for issue in candidates:
        new_stubs, suggestions = healer.heal([issue], cli_flags)
        source_path = issue.get("file_path") if isinstance(issue, dict) else getattr(issue, "file_path", None)
        
        if source_path and (target_res := file_map.get(source_path)):
            if target_res.logic_logs is None: target_res.logic_logs = []
            target_res.logic_logs.extend([f"Warning - {s}" for s in suggestions])
            if new_stubs:
                pending_changes.setdefault(source_path, []).extend(new_stubs)
    return pending_changes

def _apply_all_healer_changes(engine, pending_changes, file_map, dry_run, concurrency) -> int:
    """Applies generated stubs to files in parallel."""
    target_tasks = []
    for target_file, stubs in pending_changes.items():
        if target_res := file_map.get(target_file):
            _enrich_result_with_stubs(target_res, stubs)
            target_tasks.append({
                "full_path": target_file, "stubs": stubs, "dry_run": dry_run,
                "current_content": target_res.healed_content,
                "catalog_data": engine.catalog, "cpu_limit": engine.cpu_limit,
                "mem_limit": engine.mem_limit, "default_namespace": engine.default_namespace,
                "app_name": engine.app_name, "k8s_version": engine.cluster_version,
                "workspace_path": str(engine.workspace),
                "log_level": logging.getLogger("yamlr").getEffectiveLevel(),
            })

    logger.info(f"🚀 Global Healing: Applying stubs to {len(target_tasks)} files in parallel...")
    from yamlr.core.engine.worker import _apply_semantic_stubs_task
    parallel_executor = Parallel(n_jobs=min(concurrency, len(target_tasks)), prefer="processes")
    results_list = parallel_executor(delayed(_apply_semantic_stubs_task)(task) for task in target_tasks)
    
    fixed_count = 0
    for success, target_p, err in results_list:
        if success:
            fixed_count += 1
            if res := file_map.get(target_p): res.written = True
        elif err:
            logger.error(f"Failed to apply stubs to {target_p}: {err}")
    return fixed_count

def _enrich_result_with_stubs(res, stubs):
    """Updates result metadata with stub information."""
    if res.logic_logs is None: res.logic_logs = []
    if res.findings is None: res.findings = []
    for stub in stubs:
        is_unsafe = stub.get("metadata", {}).get("annotations", {}).get("yamlr.dev/safety") == "UNSAFE"
        res.logic_logs.append(f"  [+] Appending stub {stub['kind']}/{stub['metadata']['name']}" + (" ⚠️ (UNSAFE)" if is_unsafe else ""))
        res.findings.append({
            "message": f"Generated missing {stub['kind']}" + (" (UNSAFE)" if is_unsafe else ""),
            "severity": "warning" if is_unsafe else "info",
            "resource": f"{stub['kind']}/{stub['metadata']['name']}",
            "analyzer": "semantic-healer",
        })

def _apply_semantic_fixes_disk_index(engine, index, stub_healing, dry_run, concurrency):
    """targeted semantic healing using direct DiskIndex lookup."""
    logger.info("📐 Pass 2: Resolving broken references via DiskIndex...")
    from yamlr.analyzers.ref_resolver import ReferenceResolver
    from yamlr.models import ManifestIdentity
    resolver = ReferenceResolver()
    typed_idents = (ManifestIdentity.from_dict(d) for d in index.get_all())
    analysis_results = resolver.resolve_references(typed_idents, index=index)
    
    to_fix = {}
    for ar in analysis_results:
        if ar.needs_stub:
            to_fix.setdefault(ar.file_path, []).append(ar.to_dict())
    
    if not to_fix: return 0
    logger.info(f"✨ Pass 2: Applying semantic stubs to {len(to_fix)} affected files...")
    tasks = [{
        "full_path": p, "stubs": s, "dry_run": dry_run,
        "catalog_data": engine.catalog, "workspace_path": str(engine.workspace)
    } for p, s in to_fix.items()]
    
    from yamlr.core.engine.worker import _apply_semantic_stubs_task
    parallel_executor = Parallel(n_jobs=concurrency, prefer="processes")
    results_list = parallel_executor(delayed(_apply_semantic_stubs_task)(t) for t in tasks)
    return sum(1 for s, _, _ in results_list if s)
