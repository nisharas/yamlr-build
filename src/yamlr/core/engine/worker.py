"""
Worker Module for Yamlr Engine.

Why: Extracted from processor.py to ensure 100% modularity and compliance 
     with the <500 lines per module guardrail. Handles the actual 
     healing execution for single files within multiprocessing workers.
"""
from __future__ import annotations
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    pass
import json
from dataclasses import asdict

from yamlr.core.utils import construct_file_error
from yamlr.models import HealFileResult
from yamlr.core.engine.auditor_helpers import (
    build_heal_config,
    detect_manifest_version
)
from yamlr.core.engine.result_factory import ResultFactory
from yamlr.core.engine.adapter_handler import apply_enterprise_pro_adapters

__all__ = ["_init_worker", "_execute_healing_task", "_execute_healing_chunk", "_apply_semantic_stubs_task", "_execute_global_resolution_task", "_execute_global_analysis_task"]

# --- MULTIPROCESSING WORKER GLOBALS ---
# These are per-process globals initialized once per worker
_worker_pipeline = None
_worker_fs = None

def _init_worker(
    catalog_data: Dict,
    cpu_limit: str,
    mem_limit: str,
    default_namespace: str,
    app_name: str,
    k8s_version: str,
    workspace_path: str,
    log_level: int = logging.INFO,
):
    """Initializes the pipeline once per worker process to save memory."""
    global _worker_pipeline, _worker_fs
    from yamlr.core.pipeline import HealingPipeline
    from yamlr.core.io import FileSystemManager

    # Synchronize logging level with main process
    logging.getLogger().setLevel(log_level)
    logging.getLogger("yamlr").setLevel(log_level)

    _worker_pipeline = HealingPipeline(
        catalog=catalog_data,
        cpu_limit=cpu_limit,
        mem_limit=mem_limit,
        default_namespace=default_namespace,
        app_name=app_name,
        k8s_version=k8s_version,
    )
    _worker_fs = FileSystemManager(Path(workspace_path), app_name=app_name)

def _execute_healing_task(file_info: Dict[str, Any]) -> Any:
    """Serialized worker task to heal a single file."""
    start_time = time.time()
    global _worker_pipeline, _worker_fs
    if _worker_pipeline is None or _worker_fs is None:
        return construct_file_error(
            file_info["path"], 
            "WORKER_ERROR", 
            "Worker components not initialized",
            full_path=file_info["full_path"]
        )

    try:
        full_path = Path(file_info["full_path"])
        dry_run = file_info.get("dry_run", True)
        force_write = file_info.get("force_write", False)
        skip_backup = file_info.get("skip_backup", False)

        raw_text = full_path.read_text(encoding="utf-8-sig")

        active_version = detect_manifest_version(raw_text, _worker_pipeline.k8s_version)
        config = build_heal_config(
            dry_run=dry_run,
            strict_mode=file_info.get("strict_validation", False),
            strict_validation=file_info.get("strict_validation", False),
            compact=file_info.get("compact", False),
            identity_mode=file_info.get("identity_mode", "infer"),
            enforce_limits=file_info.get("enforce_limits", False),
            fix_tags=file_info.get("fix_tags", False),
            harden=file_info.get("harden", False),
            enforce_probes=file_info.get("enforce_probes", False),
            enforce_namespace=file_info.get("enforce_namespace", False),
            fast=file_info.get("fast", False),
            sovereign=file_info.get("sovereign", False),
            check_deprecations=file_info.get("check_deprecations", False),
            kind=file_info.get("kind"),
            api_version=file_info.get("api_version"),
            fix_refs=file_info.get("fix_refs", False),
            pro_preview=file_info.get("pro_preview", False),
            file_path=str(file_info["path"]),
            cluster_version=file_info.get("version") or active_version,
            cpu_limit=_worker_pipeline.cpu_limit,
            mem_limit=_worker_pipeline.mem_limit,
            default_namespace=_worker_pipeline.default_namespace,
            evidence_dir=file_info.get("evidence_dir")
        )

        result = _worker_pipeline.heal(raw_text, config=config)

        healed_text = result.content

        # [PRO-14-21-5] Execute Enterprise Custom Remediation Adapters (Unified Handler)
        adapters_dir = file_info.get("adapters_dir")
        if adapters_dir:
            from dataclasses import asdict
            finding_dicts = [asdict(f) for f in result.findings]
            shadow = file_info.get("adapter_shadow_mode", False)
            break_glass = file_info.get("allow_break_glass_adapters", False)
            healed_text = apply_enterprise_pro_adapters(
                healed_text, finding_dicts, result.logs, adapters_dir,
                shadow_mode=shadow, allow_break_glass=break_glass
            )


        written = False
        backup_created = None
        evidence_receipt = None
        logic_logs = result.logs
        
        if not dry_run or force_write:
            try:
                if not skip_backup:
                    backup_path = _worker_fs.create_backup(full_path)
                    try:
                        backup_created = str(backup_path.relative_to(_worker_fs.workspace))
                    except ValueError:
                        backup_created = str(backup_path)

                evidence_dir = file_info.get("evidence_dir")
                if evidence_dir:
                    try:
                        from yamlr.pro.compliance.evidence import EvidenceEngine
                        receipt = EvidenceEngine().generate_receipt(
                            file_path=str(full_path),
                            original_content=raw_text,
                            healed_content=healed_text,
                            findings=[asdict(f) for f in result.findings],
                            identities=[id.to_dict() for id in result.identities]
                        )
                        evidence_path = Path(evidence_dir) / f"evidence-{full_path.name}-{int(time.time())}.json"
                        evidence_path.parent.mkdir(parents=True, exist_ok=True)
                        evidence_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
                        evidence_receipt = str(evidence_path)
                        logic_logs.append(f"🛡️ Compliance: Generated DNA-signed evidence -> {evidence_path.name}")
                    except (AttributeError, KeyError, TypeError, ValueError, OSError, IOError) as e:
                        logic_logs.append(f"⚠️ Evidence Generation Failed: {e}")

                _worker_fs.atomic_write(full_path, healed_text)
                written = True
            except OSError as e:
                return construct_file_error(file_info["path"], "WRITE_ERROR", str(e))

        # 4. Final Result Building (Unified Factory)
        res_obj = ResultFactory.build(
            file_path=str(file_info["path"]),
            full_path=str(file_info["full_path"]),
            raw_text=raw_text,
            healed_text=healed_text,
            result=result,
            processing_time=time.time() - start_time,
            dry_run=dry_run,
            force_write=force_write,
            written=written,
            backup_path=backup_created,
            evidence_receipt=evidence_receipt,
            threshold=file_info.get("threshold", 70)
        )
        return res_obj
    except Exception as e:
        return construct_file_error(file_info["path"], "PIPELINE_ERROR", str(e), full_path=file_info["full_path"])

def _execute_healing_chunk(chunk_info: Dict[str, Any]) -> List[HealFileResult]:
    """Processes a chunk of files in a single worker call to minimize IPC.
    
    Why: Joblib workers may need on-demand initialization if not using 
         a persistent process pool initializer. Supports memmapped catalog.
    """
    global _worker_pipeline
    
    # [PHASE-3-FAST-PATH] Bypassing full pipeline initialization for speed (VAL-02-6)
    is_fast = chunk_info.get("fast", False)
    files = chunk_info.get("files", [])
    
    if is_fast:
        try:
            try:
                from yamlr_native import native_batch_fast_audit
            except ImportError:
                from yamlr.native import native_batch_fast_audit
                
            paths = [f.get("full_path") for f in files]
            # [VAL-02-6] High-performance batch processing in Rust
            # Offloads parallel I/O and parallel auditing to Rayon
            batch_findings = native_batch_fast_audit(paths)
            
            results = []
            for f, findings in zip(files, batch_findings):
                # [Zero-Blindspot] Extract hollow identities even in fast-path to support Global Analysis
                # and Cross-Resource healing.
                hollow_identities = []
                try:
                    from yamlr.parsers.scanner import YamlrScanner
                    scanner = YamlrScanner()
                    # Use a very fast fallback scan for identity convergence
                    with open(f.get("full_path"), "r", encoding="utf-8") as fh:
                        hollow_identities = scanner.fast_scan(fh.read())
                except Exception:
                    pass

                results.append({
                    "file_path": f["path"],
                    "full_path": f.get("full_path"),
                    "success": True,
                    "status": "PASSED",
                    "kind": hollow_identities[0].kind if hollow_identities else "Unknown",
                    "logic_logs": [],
                    "findings": [{
                        "stage": r.get("stage"),
                        "action_type": r.get("action_type"),
                        "target": r.get("target"),
                        "description": r.get("description"),
                        "severity": r.get("severity").upper(),
                        "rule_id": r.get("rule_id"),
                    } for r in findings],
                    "dna_integrity_score": 100 if not findings else 80,
                    "identities": [id.to_dict() for id in hollow_identities],
                    "_is_fast_dict": True
                })
            return results
        except ImportError:
            # Fallback to slow path if native not available
            pass

    # [VAL-02-5] On-demand initialization for Joblib workers (Slow/Default Path)
    if _worker_pipeline is None:
        catalog_path = chunk_info.get("catalog_path")
        catalog_data = chunk_info.get("catalog_data")
        
        if catalog_path and os.path.exists(catalog_path):
            import joblib
            catalog_data = joblib.load(catalog_path, mmap_mode='r')
            
        _init_worker(
            catalog_data=catalog_data,
            cpu_limit=chunk_info.get("cpu_limit", "0.5"),
            mem_limit=chunk_info.get("mem_limit", "512Mi"),
            default_namespace=chunk_info.get("default_namespace", "default"),
            app_name=chunk_info.get("app_name", "yamlr"),
            k8s_version=chunk_info.get("k8s_version", "1.28"),
            workspace_path=chunk_info.get("workspace_path", "."),
            log_level=chunk_info.get("log_level", logging.INFO)
        )

    results = []
    for f in files:
        results.append(_execute_healing_task(f))
    return results

def _apply_semantic_stubs_task(target_info: Dict[str, Any]) -> tuple[bool, str, Optional[str]]:
    """Parallel worker task to apply semantic stubs to a file.
    
    Why: Offloads heavy I/O and YAML formatting for stubs from main process.
         Supports on-demand initialization for Joblib workers.
    """
    global _worker_fs
    if _worker_fs is None:
        # On-demand initialization for semantic pass
        _init_worker(
            catalog_data=target_info.get("catalog_data", {}),
            cpu_limit=target_info.get("cpu_limit", "0.5"),
            mem_limit=target_info.get("mem_limit", "512Mi"),
            default_namespace=target_info.get("default_namespace", "default"),
            app_name=target_info.get("app_name", "yamlr"),
            k8s_version=target_info.get("k8s_version", "1.28"),
            workspace_path=target_info.get("workspace_path", "."),
            log_level=target_info.get("log_level", logging.INFO)
        )

    try:
        from io import StringIO
        from yamlr.core.utils import get_hardened_yaml
        from pathlib import Path

        full_p = Path(target_info["full_path"])
        dry_run = target_info.get("dry_run", True)
        stubs = target_info.get("stubs", [])
        
        # The orchestrator sends the 'current_content' (post-Pass 1) to this task
        final_content = target_info.get("current_content", "")
        if not final_content and full_p.exists():
            final_content = full_p.read_text(encoding="utf-8")
            
        if final_content and not final_content.endswith("\n"): 
            final_content += "\n"

        for stub_doc in stubs:
            stream = StringIO()
            yaml_h = get_hardened_yaml(typ="safe")
            yaml_h.dump(stub_doc, stream)
            stub_yaml = stream.getvalue()
            is_unsafe = stub_doc.get("metadata", {}).get("annotations", {}).get("yamlr.dev/safety") == "UNSAFE"
            
            header = "---\n# [Yamlr] Auto-Generated Stub\n"
            if is_unsafe:
                header += "# ⚠️  SAFETY WARNING: This resource is sensitive.\n# Generic values have been injected. Verify manually before use.\n"
            final_content += header + stub_yaml
        
        if not dry_run:
            _worker_fs.atomic_write(full_p, final_content)
        
        return True, str(full_p), None
    except (OSError, IOError, ValueError, TypeError) as e:
        return False, target_info.get("full_path", ""), str(e)
    except Exception as e:
        return False, target_info.get("full_path", ""), f"Unexpected error: {str(e)}"
def _execute_global_resolution_task(task_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parallel worker task to run RefResolver validation on a chunk of identities."""
    from yamlr.analyzers.ref_resolver import ReferenceResolver
    from yamlr.models import ManifestIdentity

    identities_data = task_info.get("identities", [])
    index = task_info.get("index", {})
    
    # Reconstruct identities
    identities = [ManifestIdentity.from_dict(d) for d in identities_data]
    
    resolver = ReferenceResolver()
    # resolve_references now handles the mapping to AnalysisResult
    results = resolver.resolve_references(identities, index=index)
    
    # Return as dicts for pickling
    return [asdict(r) for r in results]

def _execute_global_analysis_task(task_info: Dict[str, Any]) -> List[Any]:
    """Parallel worker task to run Cross-Resource detectors on a chunk of data."""
    from yamlr.analyzers.detectors.traffic import detect_ghost_services
    from yamlr.analyzers.detectors.config import detect_broken_refs
    from yamlr.analyzers.detectors.storage import detect_broken_volumes, CrossDomainDetectors
    from yamlr.analyzers.network_logic import NetworkDetectors
    from yamlr.models import ManifestIdentity

    task_type = task_info.get("type")
    
    if task_type == "ghost_services":
        # ... (cached)
        services_data = task_info.get("services", [])
        workloads = task_info.get("workloads", [])
        pro_mode = task_info.get("pro_mode", False)
        services = [ManifestIdentity.from_dict(d) for d in services_data]
        workload_idents = [ManifestIdentity.from_dict(d) for d in workloads]
        return detect_ghost_services(services, workload_idents, pro_mode)
        
    elif task_type == "broken_refs":
         identities = [ManifestIdentity.from_dict(d) for d in task_info.get("identities", [])]
         index = task_info.get("index")
         return detect_broken_refs(identities, index=index)

    elif task_type == "broken_volumes":
         workloads_chunk = [ManifestIdentity.from_dict(d) for d in task_info.get("workloads", [])]
         pvcs = [ManifestIdentity.from_dict(d) for d in task_info.get("pvcs", [])]
         return detect_broken_volumes(workloads_chunk, pvcs)

    elif task_type == "port_mismatches":
         services_chunk = [ManifestIdentity.from_dict(d) for d in task_info.get("services", [])]
         workloads = [ManifestIdentity.from_dict(d) for d in task_info.get("workloads", [])]
         return NetworkDetectors.validate_service_ports(services_chunk, workloads)

    elif task_type == "broken_cloud_refs":
         pvs = [ManifestIdentity.from_dict(d) for d in task_info.get("pvs", [])]
         cloud = [ManifestIdentity.from_dict(d) for d in task_info.get("cloud", [])]
         return CrossDomainDetectors.detect_broken_cloud_refs(pvs, cloud)

    elif task_type == "broken_credential_links":
         secrets = [ManifestIdentity.from_dict(d) for d in task_info.get("secrets", [])]
         cloud = [ManifestIdentity.from_dict(d) for d in task_info.get("cloud", [])]
         return CrossDomainDetectors.detect_broken_credential_links(secrets, cloud)

    return []

