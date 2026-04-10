"""
Yamlr PROCESSOR HELPERS
-----------------------
Helper functions for batch-level healing and global analysis.
Extracted from processor.py to maintain 100% modularity and line-count compliance.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

from yamlr.core.entrypoints.base import get_console
from yamlr.core.gatekeeper import ProGate
from yamlr.models import HealFileResult

from .telemetry_handler import record_batch_telemetry
from .surgery_pool import run_parallel_surgery_pool

logger = logging.getLogger("yamlr.engine.processor.helpers")

__all__ = [
    "prepare_batch_context",
    "check_batch_quota",
    "run_global_analysis",
    "record_batch_telemetry",
    "run_parallel_surgery_pool",
]


def prepare_batch_context(
    engine, config_params: Dict[str, Any], external_findings_map: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs the standard engine context for batch processing.
    """
    return {
        "strict_validation": config_params.get("strict_validation", False),
        "compact": config_params.get("compact", False),
        "version": engine.cluster_version,
        "identity_mode": config_params.get("identity_mode", "infer"),
        "threshold": engine.health_threshold,
        "enforce_limits": config_params.get("enforce_limits", False) or engine.config.enforce_limits,
        "fix_tags": config_params.get("fix_tags", False) or engine.config.fix_tags,
        "harden": config_params.get("harden", False) or engine.config.harden,
        "enforce_probes": config_params.get("enforce_probes", False) or engine.config.enforce_probes,
        "dry_run": config_params.get("dry_run", True),
        "force_write": config_params.get("force_write", False),
        "skip_backup": config_params.get("skip_backup", False),
        "enforce_namespace": config_params.get("enforce_namespace", False) or engine.config.enforce_namespace,
        "fast": config_params.get("fast", False),
        "sovereign": config_params.get("sovereign", False),
        "check_deprecations": config_params.get("check_deprecations", False),
        "fix_refs": config_params.get("stub_healing") or config_params.get("allow_unsafe"),
        "pro_preview": config_params.get("pro_preview", False),
        "evidence_dir": config_params.get("evidence_dir"),
        "generate_receipts": config_params.get("generate_receipts", False),
        "adapters_dir": config_params.get("adapters_dir"),
        "from_report_path": config_params.get("from_report_path"),
        "allowed_host_paths": engine.allowed_host_paths,
        "quota_checked": True,
        "config_manager": engine.config,
        "external_findings_map": external_findings_map,
    }


def check_batch_quota(dry_run: bool, files_count: int) -> Tuple[bool, Optional[str]]:
    """
    Enforces the Community Tier healing quota for batch operations.
    """
    console = get_console()
    if not ProGate.is_pro_enabled() and files_count >= 5:
        console.print(
            f"\n[bold yellow]⚠️  Community Quota Notice:[/bold yellow] This batch contains {files_count} files."
        )
        console.print(f"[dim]{ProGate.get_pro_hint('generic')}[/dim]")

    if not dry_run and files_count > 0:
        from yamlr.core.license_manager import LicenseManager
        allowed, _, reason = LicenseManager.is_healing_allowed(files_count)
        if not allowed:
            # We don't notify here, we let the orchestrator handle the specific Quota UI
            return False, reason
    return True, None


def run_global_analysis(
    results: Optional[List[HealFileResult]],
    tf_identities: List[Any],
    file_map: Optional[Dict[str, HealFileResult]],
    index: Optional["DiskIndex"] = None,
    concurrency: int = 1,
):
    """
    Performs global Cross-Resource Analysis across all discovered manifests.
    """
    all_identities = _collect_all_identities(results, tf_identities, index)
    if not all_identities:
        return

    try:
        from yamlr.core.resource_graph import ResourceGraph

        graph = ResourceGraph()
        # [ROUND-12] Support streaming build for ResourceGraph
        graph.build(all_identities)

        cross_findings = _execute_global_detectors(all_identities, graph, index, file_map, concurrency)
        if cross_findings:
            _attach_global_findings(cross_findings, file_map)

    except Exception as e:
        logger.warning(f"Global Graph Analysis failed: {e}")


def _execute_global_detectors(all_identities, graph, index, file_map, concurrency) -> List:
    """Selects and runs the appropriate analysis path based on scale."""
    from yamlr.analyzers.cross_resource import CrossResourceAnalyzer

    analyzer = CrossResourceAnalyzer()

    is_large = index is not None or (isinstance(all_identities, list) and len(all_identities) > 100)
    if is_large and concurrency > 1:
        findings = []
        _run_large_global_analysis(all_identities, index, analyzer, file_map, concurrency, findings)
        return findings
    else:
        return analyzer.analyze(all_identities, graph=graph)


def _attach_global_findings(cross_findings: List, file_map: Dict):
    """Enriches and attaches cross-resource findings to individual results."""
    from yamlr.analyzers.risk_classifier import RiskClassifier

    norm_file_map = {str(Path(k).resolve()).lower(): v for k, v in file_map.items()}
    classifier = RiskClassifier()

    for finding in cross_findings:
        _enrich_and_attach_finding(finding, norm_file_map, classifier)


def _run_large_global_analysis(all_identities, index, analyzer, file_map, concurrency, cross_findings):
    """Execute parallel global analysis for large datasets with OOM protection."""
    logger.info("🚀 Global Analysis: Analyzing graph in parallel...")

    # [Zero-Blindspot] Avoid materializing 1M+ identities into RAM.
    # We use a streaming categorization pass to stay within constant RAM.
    services, workloads, configs, pvcs, pvs, cloud = _categorize_identities_streaming(all_identities)

    from yamlr.analyzers.detectors.base import build_index

    # build_index should also be made scale-aware or we use the disk index summary
    index_data = (
        index.get_summary()
        if (index and hasattr(index, "get_summary"))
        else build_index(workloads + services + configs)
    )

    raw_findings = _execute_parallel_analysis_tasks(
        services, workloads, configs, pvcs, pvs, cloud, index_data, analyzer.pro_mode, concurrency
    )

    norm_file_map = {str(Path(k).resolve()).lower(): v for k, v in file_map.items()}
    from yamlr.analyzers.risk_classifier import RiskClassifier

    classifier = RiskClassifier()

    for rf in raw_findings:
        temp_findings = []
        _map_finding_to_results(rf, analyzer, temp_findings)
        for f in temp_findings:
            cross_findings.append(f)
            _enrich_and_attach_finding(f, norm_file_map, classifier)


def _enrich_and_attach_finding(finding: Any, norm_file_map: Dict[str, HealFileResult], classifier: Any):
    """Enriches a single finding and attaches it to the corresponding result."""
    f_path = str(Path(finding.file_path).resolve()).lower()
    target_res = norm_file_map.get(f_path)
    if not target_res:
        return

    if target_res.logic_logs is None:
        target_res.logic_logs = []
    if target_res.findings is None:
        target_res.findings = []

    classifier.enrich_finding(finding)

    if not finding.impact_description:
        from yamlr.core.rule_manager import RuleManager

        rule_meta = RuleManager().get_rule(finding.rule_id)
        if rule_meta:
            finding.impact_description = rule_meta.get("impact_description")
            # [PRO] Only use static rationale if the detector hasn't provided a contextual one
            if not getattr(finding, "rationale", None):
                finding.rationale = rule_meta.get("rationale")

    msg = f"Graph Analysis: {finding.message} ({finding.suggestion})"
    target_res.logic_logs.append(msg)

    target_res.findings.append(
        {
            "stage": "Cross-Resource",
            "action_type": "detect",
            "target": f"{finding.resource_kind}/{finding.resource_name}",
            "description": finding.message,
            "message": finding.message,
            "severity": finding.severity.upper(),
            "suggestion": finding.suggestion,
            "rule_id": finding.rule_id,
            "rationale": finding.rationale,
            "impact_description": finding.impact_description,
            "risk_level": finding.risk_level,
        }
    )
    if finding.severity.upper() == "ERROR":
        target_res.success = False
        target_res.status = "FAILED"
    target_res.sem_status = "⚠️ FAIL"


def _categorize_identities_streaming(identities: Any) -> Tuple[List, List, List, List, List, List]:
    """
    Sorts identities into buckets using a single streaming pass.
    Why: Prevents loading the entire workspace manifest graph into memory.
    """
    services, workloads, configs, pvcs, pvs, cloud = [], [], [], [], [], []
    from yamlr.models import WORKLOAD_KINDS

    for i in identities:
        k = i.kind
        if k == "Service":
            services.append(i)
        elif k in WORKLOAD_KINDS:
            workloads.append(i)
        elif k in ("ConfigMap", "Secret"):
            configs.append(i)
        elif k == "PersistentVolumeClaim":
            pvcs.append(i)
        elif k == "PersistentVolume":
            pvs.append(i)
        if getattr(i, "is_terraform", False):
            cloud.append(i)

    return services, workloads, configs, pvcs, pvs, cloud


def _execute_parallel_analysis_tasks(
    services, workloads, configs, pvcs, pvs, cloud, index, pro_mode, concurrency
) -> List[Dict]:
    """Orchestrates parallel detectors."""
    from joblib import Parallel, delayed

    from yamlr.core.engine.worker import _execute_global_analysis_task

    tasks = [
        {
            "type": "ghost_services",
            "services": [s.to_dict() for s in services],
            "workloads": [w.to_dict() for w in workloads],
            "pro_mode": pro_mode,
        },
        {"type": "broken_refs", "identities": [w.to_dict() for w in workloads], "index": index, "pro_mode": pro_mode},
        {
            "type": "broken_volumes",
            "workloads": [w.to_dict() for w in workloads],
            "pvcs": [p.to_dict() for p in pvcs],
            "pro_mode": pro_mode,
        },
        {
            "type": "port_mismatches",
            "services": [s.to_dict() for s in services],
            "workloads": [w.to_dict() for w in workloads],
            "pro_mode": pro_mode,
        },
        {
            "type": "broken_cloud_refs",
            "pvs": [p.to_dict() for p in pvs],
            "cloud": [c.to_dict() for c in cloud],
            "pro_mode": pro_mode,
        },
        {
            "type": "broken_credential_links",
            "secrets": [c.to_dict() for c in configs],
            "cloud": [c.to_dict() for c in cloud],
            "pro_mode": pro_mode,
        },
    ]
    # [Phase 2] Fast Path: Bypass Parallel overhead for low concurrency or tiny tasks
    if concurrency == 1 or len(tasks) <= 1:
        raw_results = [_execute_global_analysis_task(t) for t in tasks]
    else:
        parallel_executor = Parallel(n_jobs=min(len(tasks), concurrency), prefer="processes")
        raw_results = parallel_executor(delayed(_execute_global_analysis_task)(t) for t in tasks)

    findings = []
    for r_list in raw_results:
        if r_list:
            findings.extend(r_list)
    return findings


def _map_finding_to_results(rf: Dict, analyzer: Any, cross_findings: List):
    """Dispatches raw findings to appropriate analyzer mapping logic."""
    if "service_name" in rf and "pod_name" in rf:  # Port mismatch
        analyzer._map_ports([rf], cross_findings)
    elif "missing_pvc" in rf:  # Broken volume
        analyzer._map_volumes([rf], cross_findings)
    elif "hint" in rf:  # Ghost service
        analyzer._map_ghosts([rf], cross_findings)
    elif "kind" in rf and "name" in rf and "resource_name" in rf:  # Broken ref
        analyzer._map_broken_refs([rf], cross_findings)
    elif "volume_id" in rf:  # Broken cloud ref
        analyzer._map_cloud_refs([rf], cross_findings)
    elif "is_credential_leak" in rf or ("name" in rf and "resource_kind" not in rf and "missing_pvc" not in rf):
        analyzer._map_credential_links([rf], cross_findings)


def _collect_all_identities(
    results: Optional[List], tf_identities: List, index: Optional["DiskIndex"]
) -> Optional[Iterable]:
    """Unifies identities across results, disk index, and terraform sources."""
    if results:
        return _gen_identities_from_results(results, tf_identities)

    if index:
        all_ids = index.get_all()
        if tf_identities:
            from itertools import chain
            return chain(all_ids, tf_identities)
        return all_ids

    return tf_identities or None


def _gen_identities_from_results(results: List, tf_identities: List) -> Generator:
    """Inner generator for result-based identity extraction."""
    for res in results:
        path = res.full_path or res.file_path
        raw_ids = getattr(res, "identities_raw", []) or []
        for ident in raw_ids:
            ident.file_path = path
            yield ident
    
    if tf_identities:
        yield from tf_identities
