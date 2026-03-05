"""
Yamlr ENGINE - The High Orchestrator (Refactored)
---------------------------------------
Coordinates the complete healing workflow for Kubernetes manifests.

Why: Refactored to leverage specialized modules (auditor, processor, security)
to ensure 100% modularity and compliance with the <500 lines per module guardrail.
"""
import logging
from typing import Any, Dict, List, Optional

from yamlr.core.deprecations import DeprecationChecker

from yamlr.core.manager import YamlrManager
from yamlr.core.engine import auditor, processor, security
from yamlr.models import HealFileResult
from yamlr.core.telemetry import TelemetryManager

logger = logging.getLogger("yamlr.engine")

SEVERITY_RANK = {"error": 100, "warning": 50, "info": 10, "none": 0}
RISK_RANK = {"high": 100, "medium": 50, "low": 10, "none": 0}

class YamlrEngine:
    """
    Principal Orchestrator for Kubernetes manifest healing.
    
    Responsibilities:
    - Workspace and catalog management (via YamlrManager)
    - Facade for Audit and Healing operations
    - Result aggregation
    """

    @staticmethod
    def quick(workspace_path: str = ".") -> "YamlrEngine":
        """Factory method for ultra-fast, zero-config engine initialization."""
        # Detect workspace and default cluster version
        return YamlrEngine(workspace_path=workspace_path, catalog_path=None)

    def __init__(
        self,
        workspace_path: str,
        catalog_path: Optional[str] = None,
        app_name: str = "Yamlr",
        pro_brand: str = "Yamlr Enterprise",
        cpu_limit: str = "500m",
        mem_limit: str = "512Mi",
        default_namespace: str = "default",
        deep_array_validation: bool = False,
        custom_key_order: Optional[List[str]] = None,
        health_threshold: int = 70,
        cluster_version: Optional[str] = None,
        opa_bundle_path: Optional[str] = None,
        kyverno_report_path: Optional[str] = None,
        allowed_host_paths: Optional[List[str]] = None,
        concurrency: Optional[int] = None,
    ):
        """Initializes the Yamlr Engine."""
        self.manager = YamlrManager(
            workspace_path=workspace_path,
            app_name=app_name,
            catalog_path=catalog_path,
            health_threshold=health_threshold,
            allowed_host_paths=allowed_host_paths,
            concurrency=concurrency,
            cluster_version=cluster_version,
        )
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.default_namespace = default_namespace

        # Expose properties for convenience
        self.workspace = self.manager.workspace
        self.app_name = self.manager.app_name
        self.fs = self.manager.fs
        self.config = self.manager.config
        self.catalog = self.manager.catalog
        self.allowed_host_paths = self.manager.allowed_host_paths
        self.health_threshold = self.manager.health_threshold
        self.cluster_version = self.manager.cluster_version
        self.concurrency = self.manager.concurrency
        self.telemetry = TelemetryManager(self.workspace, app_name=self.app_name)

        from yamlr.core.pipeline import HealingPipeline, HealStatus
        self.HealStatus = HealStatus
        self.pipeline = HealingPipeline(
            catalog=self.catalog,
            cpu_limit=cpu_limit,
            mem_limit=mem_limit,
            default_namespace=default_namespace,
            app_name=self.app_name,
            k8s_version=self.cluster_version,
            allowed_host_paths=self.allowed_host_paths,
            trusted_registries=self.config.trusted_registries,
        )

        if hasattr(self.pipeline.validator, "deep_array_check"):
            self.pipeline.validator.deep_array_check = deep_array_validation
        if self.pipeline.exporter and custom_key_order:
            self.pipeline.exporter.custom_order = custom_key_order

        if opa_bundle_path:
            self._init_opa_engine(opa_bundle_path)
            
        if kyverno_report_path:
            self._init_kyverno_engine(kyverno_report_path)

    def audit_and_heal_file(self, relative_path: str, **kwargs) -> HealFileResult:
        """
        Delegates to auditor.audit_and_heal_file and records telemetry.
        
        Why: Centralized telemetry capture for all single-file operations.
        """
        import time
        start_t = time.time()
        res = auditor.audit_and_heal_file(self, relative_path, **kwargs)
        duration = time.time() - start_t
        
        # Determine bytes processed
        b_proc = 0
        try:
            full_p = self.workspace / relative_path
            if full_p.exists():
                b_proc = full_p.stat().st_size
        except Exception:
            pass
        
        # Record Telemetry
        s = getattr(res, "processing_stats", {})
        if not s: # Fallback
             s = getattr(res, "stats", {})
        
        # Ensure s is a dict for get() calls
        if not isinstance(s, dict):
            s = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}
        
        fixed = (s.get("lexer_repairs", 0) + s.get("lexer_typos", 0) + 
                 s.get("semantic_repairs", 0) + s.get("security_hardens", 0) + 
                 s.get("migrator_changes", 0))
        
        # Calculate Max Severity & Risk for CI Gating
        max_sev_label = "info"
        max_sev_rank = 0
        max_risk_label = "low"
        max_risk_rank = 0
        for f in res.findings:
            sev = f.get("severity", "info").lower()
            rank = SEVERITY_RANK.get(sev, 10)
            if rank > max_sev_rank:
                max_sev_rank = rank
                max_sev_label = sev

            risk = f.get("risk_level", "low").lower()
            rrank = RISK_RANK.get(risk, 10)
            if rrank > max_risk_rank:
                max_risk_rank = rrank
                max_risk_label = risk

        self.telemetry.record_session(
            files_count=1,
            fixed_issues=fixed,
            avg_health_score=res.health_score,
            is_heal=not kwargs.get("dry_run", True),
            max_severity=max_sev_label,
            max_risk=max_risk_label,
            breakdown=s,
            duration_seconds=duration,
            bytes_processed=b_proc
        )
        return res

    def audit_stream(self, content: str, **kwargs) -> HealFileResult:
        """
        Delegates to auditor.audit_stream and records telemetry.
        
        Why: Centralized telemetry capture for all stream operations.
        """
        import time
        start_t = time.time()
        res = auditor.audit_stream(self, content, **kwargs)
        duration = time.time() - start_t
        b_proc = len(content.encode("utf-8"))
        
        # Record Telemetry
        s = getattr(res, "processing_stats", {})
        if not s: # Fallback
             s = getattr(res, "stats", {})
             
        if not isinstance(s, dict):
            s = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}
            
        fixed = (s.get("lexer_repairs", 0) + s.get("lexer_typos", 0) + 
                 s.get("semantic_repairs", 0) + s.get("security_hardens", 0) + 
                 s.get("migrator_changes", 0))
        
        # Calculate Max Severity & Risk
        max_sev_label = "info"
        max_sev_rank = 0
        max_risk_label = "low"
        max_risk_rank = 0
        for f in res.findings:
            sev = f.get("severity", "info").lower()
            rank = SEVERITY_RANK.get(sev, 10)
            if rank > max_sev_rank:
                max_sev_rank = rank
                max_sev_label = sev
            
            risk = f.get("risk_level", "low").lower()
            rrank = RISK_RANK.get(risk, 10)
            if rrank > max_risk_rank:
                max_risk_rank = rrank
                max_risk_label = risk

        self.telemetry.record_session(
            files_count=1,
            fixed_issues=fixed,
            avg_health_score=res.health_score,
            is_heal=not kwargs.get("dry_run", True),
            max_severity=max_sev_label,
            max_risk=max_risk_label,
            breakdown=s,
            duration_seconds=duration,
            bytes_processed=b_proc
        )
        return res

    def batch_heal(
        self,
        root_path: str,
        extensions: List[str] = None,
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
        """Delegates to processor.batch_heal."""
        if extensions is None: extensions = [".yaml", ".yml"]
        return processor.batch_heal(
            self,
            root_path,
            extensions,
            max_depth=max_depth,
            dry_run=dry_run,
            force_write=force_write,
            identity_mode=identity_mode,
            stub_healing=stub_healing,
            allow_unsafe=allow_unsafe,
            enforce_limits=enforce_limits,
            fix_tags=fix_tags,
            harden=harden,
            enforce_probes=enforce_probes,
            strict_validation=strict_validation,
            compact=compact,
            skip_backup=skip_backup,
            enforce_namespace=enforce_namespace,
            fast=fast,
            stream_to=stream_to,
            check_deprecations=check_deprecations,
            task_label=task_label,
            evidence_dir=evidence_dir,
            adapters_dir=adapters_dir,
        )

    def apply_semantic_fixes(self, results: List[HealFileResult], stub_healing: Any = False, allow_unsafe: Any = False, dry_run: bool = True) -> int:
        """Delegates to processor.apply_semantic_fixes."""
        return processor.apply_semantic_fixes(self, results, stub_healing, allow_unsafe, dry_run)

    def get_upgrade_advisory_data(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """Calculates risk levels for an upgrade path.
        
        Why: Centralized logic for the Safety Engine to assess version migration risk.
        """
        checker = DeprecationChecker()
        return checker.upgrade_risk_score(from_version, to_version)

    def _init_opa_engine(self, opa_bundle_path: str):
        """Initializes the OPA Policy Engine (Enterprise Feature)."""
        try:
            from yamlr.analyzers.registry import AnalyzerRegistry
            from yamlr.pro.license import license_manager
            from yamlr.pro.opa_adapter import OpaAnalyzer

            if license_manager.check_feature_access("opa"):
                opa_analyzer = OpaAnalyzer(policy_path=opa_bundle_path)
                AnalyzerRegistry.register_instance(opa_analyzer)
                logger.info(f"💎 OPA Policy Engine enabled (Bundle: {opa_bundle_path})")
            else:
                logger.warning("⛔ OPA Feature requires Enterprise license.")
        except Exception as e:
            logger.error(f"Failed to initialize OPA Engine: {e}")

    def _init_kyverno_engine(self, kyverno_report_path: str):
        """Initializes the Kyverno Policy Engine (Enterprise Feature)."""
        try:
            from yamlr.analyzers.registry import AnalyzerRegistry
            from yamlr.pro.license import license_manager
            from yamlr.pro.kyverno_adapter import KyvernoAdapter

            if license_manager.check_feature_access("kyverno"):
                kyverno_analyzer = KyvernoAdapter(report_path=kyverno_report_path)
                AnalyzerRegistry.register_instance(kyverno_analyzer)
                logger.info(f"💎 Kyverno Adapter enabled (Report: {kyverno_report_path})")
            else:
                logger.warning("⛔ Kyverno Feature requires Enterprise license.")
        except Exception as e:
            logger.error(f"Failed to initialize Kyverno Engine: {e}")

# Legacy Alias
AuditEngineV3 = YamlrEngine
