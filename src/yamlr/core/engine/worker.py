"""
Worker Module for Yamlr Engine.

Why: Extracted from processor.py to ensure 100% modularity and compliance 
     with the <500 lines per module guardrail. Handles the actual 
     healing execution for single files within multiprocessing workers.
"""
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from yamlr.core.utils import construct_file_error, derive_status
from yamlr.models import HealFileResult, HealConfig

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
        path = Path(file_info["path"])
        full_path = Path(file_info["full_path"])
        dry_run = file_info.get("dry_run", True)
        force_write = file_info.get("force_write", False)
        skip_backup = file_info.get("skip_backup", False)

        raw_text = full_path.read_text(encoding="utf-8-sig")

        config = HealConfig(
            file_path=str(file_info["path"]),
            cluster_version=file_info.get("version") or _worker_pipeline.k8s_version,
            identity_mode=file_info.get("identity_mode", "infer"),
            strict_validation=file_info.get("strict_validation", False),
            compact=file_info.get("compact", False),
            enforce_limits=file_info.get("enforce_limits", False),
            fix_tags=file_info.get("fix_tags", False),
            harden=file_info.get("harden", False),
            enforce_probes=file_info.get("enforce_probes", False),
            enforce_namespace=file_info.get("enforce_namespace", False),
            fast=file_info.get("fast", False),
            check_deprecations=file_info.get("check_deprecations", False),
            fix_refs=file_info.get("fix_refs", False),
            cpu_limit=_worker_pipeline.cpu_limit,
            mem_limit=_worker_pipeline.mem_limit,
            default_namespace=_worker_pipeline.default_namespace
        )

        result = _worker_pipeline.heal(raw_text, config=config)

        healed_text = result.content
        
        # [PRO-14-21-5] Execute Enterprise Custom Remediation Adapters
        adapters_dir = file_info.get("adapters_dir")
        if adapters_dir:
            try:
                from yamlr.pro.compliance.adapters import AdapterEngine
                from yamlr.core.utils import get_hardened_yaml
                ryaml = get_hardened_yaml()
                import io
                
                adapter_engine = AdapterEngine(adapters_dir)
                serialized_findings = [asdict(f) for f in result.findings]
                adapter_hits = [f for f in serialized_findings if f.get("rule_id") in adapter_engine.adapters]
                
                if adapter_hits:
                    ryaml = get_hardened_yaml(typ="rt", pure=False) # Roundtrip
                    ryaml.preserve_quotes = True
                    docs = list(ryaml.load_all(healed_text))
                    adapted_any = False
                    
                    for f in adapter_hits:
                        rule_id = f["rule_id"]
                        for i, doc in enumerate(docs):
                            if isinstance(doc, dict):
                                native_dict = dict(doc)
                                adapted_doc = adapter_engine.execute_adapter(rule_id, native_dict)
                                if adapted_doc:
                                    docs[i] = adapted_doc
                                    adapted_any = True
                                    log_msg = f"🔌 Compliance: Executed external remediation adapter -> {rule_id}"
                                    if log_msg not in result.logs:
                                        result.logs.append(log_msg)
                    if adapted_any:
                        buf = io.StringIO()
                        ryaml.dump_all(docs, buf)
                        healed_text = buf.getvalue()
            except ImportError:
                 result.logs.append("⚠️ Compliance Warning: Could not engage Pro Adapters Engine (Missing .pro module)")
            except Exception as e:
                 result.logs.append(f"⚠️ Adapter execution failed: {e}")

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
                        import json
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
                    except Exception as e:
                        logic_logs.append(f"⚠️ Evidence Generation Failed: {e}")

                _worker_fs.atomic_write(full_path, healed_text)
                written = True
            except Exception as e:
                return construct_file_error(file_info["path"], "WRITE_ERROR", str(e))

        identities_list = [id.to_dict() for id in result.identities]
        for i, id in enumerate(result.identities):
            if id.deprecation_info:
                identities_list[i]["deprecation_info"] = id.deprecation_info

        meets_threshold = result.health_score >= file_info.get("threshold", 70)
        is_modified = raw_text.strip() != healed_text.strip()
        status = derive_status(is_modified, dry=dry_run, meets_threshold=meets_threshold)

        res_obj = HealFileResult(
            file_path=str(file_info["path"]),
            full_path=str(file_info["full_path"]),
            success=meets_threshold or not is_modified,
            status=status,
            written=written,
            backup_created=backup_created,
            health_score=result.health_score,
            logic_logs=logic_logs,
            identities=identities_list,
            findings=[asdict(f) for f in result.findings],
            processing_stats=result.stats.__dict__,
            deprecation_info=result.deprecation_info,
            healed_content=healed_text,
            evidence_receipt=evidence_receipt,
            kind=identities_list[0]["kind"] if identities_list else "Unknown",
            timestamp=time.time(),
            processing_time_seconds=time.time() - start_time,
            phy_status=result.phy_status,
            kbs_status=result.kbs_status,
            sem_status=result.sem_status,
        )
        res_obj._raw_identities = result.identities
        return res_obj
    except Exception as e:
        return construct_file_error(file_info["path"], "PIPELINE_ERROR", str(e), full_path=file_info["full_path"])

def _execute_healing_chunk(chunk_info: Dict[str, Any]) -> List[HealFileResult]:
    """Processes a chunk of files in a single worker call to minimize IPC."""
    results = []
    files = chunk_info.get("files", [])
    for f in files:
        results.append(_execute_healing_task(f))
    return results
