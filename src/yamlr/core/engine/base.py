from __future__ import annotations

"""
BASE ENGINE - The Heart of Yamlr
--------------------------------
The fundamental execution layer that coordinates scanners, analyzers, 
and healers across a workspace.

Why: Refactored to leverage specialized modules (auditor, processor, security)
to ensure 100% modularity and compliance with the <500 lines per module guardrail.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-02-10: Engine Base Abstraction**
   - **Context**: Multiple engine variants (OSS, Pro, Native) needed a common API.
   - **Decision**: Define a base `YamlrEngine` with mandatory auditing/healing hooks.
   - **Consequence**: Guaranteed feature parity across execution environments.

2. **2026-03-20: Integrated Telemetry Manager**
   - **Context**: Measuring the "Yield" of Yamlr required deep data hooks.
   - **Decision**: Embed `TelemetryManager` directly into the engine lifecycle.
   - **Consequence**: Real-time ROI and performance tracking available via `yamlr status`.
"""
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from yamlr.core.pipeline import HealingPipeline
    from yamlr.models import HealFileResult
from yamlr.core.pipeline import HealStatus

from yamlr.core.manager import YamlrManager
from yamlr.core.telemetry import TelemetryManager

logger = logging.getLogger("yamlr.engine")

__all__ = ["YamlrEngine", "AuditEngineV3"]

YAML_EXT = ".yaml"
YML_EXT = ".yml"

SEVERITY_RANK: Dict[str, int] = {"error": 100, "warning": 50, "info": 10, "none": 0}
RISK_RANK: Dict[str, int] = {"high": 100, "medium": 50, "low": 10, "none": 0}

class YamlrEngine:
    """
    Principal Orchestrator for Kubernetes manifest healing.
    
    Responsibilities:
    - Workspace and catalog management (via YamlrManager)
    - Facade for Audit and Healing operations
    - Result aggregation
    """
    
    # Result Status Mapping
    HEAL_STATUS = HealStatus
    audit_status = HealStatus

    def is_pro_enabled(self) -> bool:
        """Checks if enterprise features are active via bridge or license manager."""
        from yamlr.core.bridge import YamlrBridge
        return YamlrBridge.is_pro_enabled()

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
        pro_brand: str = "Yamlr Enterprise (Pro)",
        cpu_limit: str = "500m",
        mem_limit: str = "512Mi",
        default_namespace: str = "default",
        health_threshold: int = 70,
        cluster_version: Optional[str] = None,
        safe_mode: bool = False,
        **kwargs: Union[str, bool, int, List[str], None]
    ):
        """Initializes the Yamlr Engine."""
        self.manager = YamlrManager(
            workspace_path=workspace_path,
            app_name=app_name,
            catalog_path=catalog_path,
            health_threshold=health_threshold,
            allowed_host_paths=kwargs.get("allowed_host_paths"),
            concurrency=kwargs.get("concurrency"),
            cluster_version=cluster_version,
        )
        self.cpu_limit: str = cpu_limit
        self.mem_limit: str = mem_limit
        self.default_namespace: str = default_namespace
        self.safe_mode: bool = safe_mode

        # Expose properties for convenience
        self.workspace: Path = self.manager.workspace
        self.app_name: str = self.manager.app_name
        self.fs = self.manager.fs
        self.config = self.manager.config
        self.allowed_host_paths: List[str] = self.manager.allowed_host_paths
        self.health_threshold: int = self.manager.health_threshold
        self.cluster_version: str = self.manager.cluster_version
        self.concurrency: Optional[int] = self.manager.concurrency
        self.telemetry = TelemetryManager(self.workspace, app_name=self.app_name)
        self._identity_cache: List["ManifestIdentity"] = []
        self.disk_index: Optional["DiskIndex"] = None

        self._cpu_limit: str = cpu_limit
        self._mem_limit: str = mem_limit
        self._default_namespace: str = default_namespace
        self._deep_array_validation: bool = bool(kwargs.get("deep_array_validation", False))
        self._custom_key_order: Optional[List[str]] = kwargs.get("custom_key_order")
        self._opa_bundle_path: Optional[str] = kwargs.get("opa_bundle_path")
        self._kyverno_report_path: Optional[str] = kwargs.get("kyverno_report_path")
        self._from_report_path: Optional[str] = kwargs.get("from_report_path")
        self._pipeline: Optional["HealingPipeline"] = None

    def __enter__(self) -> "YamlrEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit ensures resource cleanup."""
        self.close()

    def __del__(self) -> None:
        """Safety-net to ensure resource cleanup during garbage collection."""
        try:
            self.close()
        except Exception:
            # Suppress errors in __del__ as they are non-actionable during shutdown
            pass

    def get_all_identities(self) -> List["ManifestIdentity"]:
        """Scans the entire workspace to identify all resources and their relationships.
        
        Why: To build the ResourceGraph necessary for Relational Surgery (Stage 5.7).
        """
        if self._identity_cache:
            for ident in self._identity_cache:
                yield ident
            return

        from yamlr.core.engine.crawler import crawl_manifests
        
        extensions = self.config.config.get("ignore", {}).get("extensions", [YAML_EXT, YML_EXT])
        if not isinstance(extensions, list):
            extensions = [YAML_EXT, YML_EXT]

        files = crawl_manifests(
            workspace_root=self.workspace, 
            root_path=str(self.workspace), 
            extensions=extensions,
            max_depth=10,
            engine_context={}
        )
        
        for f in files:
            path = f.get("full_path") or str(self.workspace / f["path"])
            yield from self._scan_file_identities(path)

    def _scan_file_identities(self, path: str) -> List["ManifestIdentity"]:
        """Helper to scan a single file for identities with optimized fallbacks."""
        from yamlr.parsers.lexer import YamlrLexer
        from yamlr.parsers.scanner import YamlrScanner
        from pathlib import Path

        try:
            content = self.fs.read_text(Path(path))
            # 1. Try Native Fast Path
            if os.getenv("YAMLR_DISABLE_NATIVE") != "1":
                try:
                    from yamlr_native import native_extract_metadata
                    raw_meta = native_extract_metadata(content)
                    if raw_meta:
                        results = []
                        for doc in raw_meta:
                            results.append(ManifestIdentity(
                                kind=doc.get("kind"),
                                api_version=doc.get("apiVersion"),
                                name=doc.get("metadata", {}).get("name"),
                                namespace=doc.get("metadata", {}).get("namespace"),
                                labels=doc.get("metadata", {}).get("labels"),
                                file_path=path
                            ))
                        return results
                except (ImportError, RuntimeError, AttributeError): # Optimized fallback triggers
                    pass

            # 2. Fallback to Python Parser
            lexer = YamlrLexer()
            scanner = YamlrScanner(self.catalog, app_name=self.app_name)
            shards = lexer.shard(content)
            ids = scanner.scan_shards(shards)
            for ident in ids:
                ident.file_path = path
            return ids
        except Exception as e:
            logger.debug(f"Identity scan failed for {path}: {e}")
            return []

    @property
    def catalog(self) -> Dict[str, Any]:
        """Lazy-bound catalog from manager."""
        return self.manager.catalog

    @property
    def pipeline(self) -> "HealingPipeline":
        """Lazy-loaded healing pipeline with dynamic version binding."""
        if self._pipeline is None:
            from yamlr.core.pipeline import HealingPipeline
            self._pipeline = HealingPipeline(
                catalog=self.catalog,
                cpu_limit=self._cpu_limit,
                mem_limit=self._mem_limit,
                default_namespace=self._default_namespace,
                app_name=self.app_name,
                k8s_version=self.cluster_version,
                allowed_host_paths=self.allowed_host_paths,
                trusted_registries=self.config.trusted_registries,
            )
            # Apply initial configuration
            self._apply_pipeline_config(self._pipeline)
        
        # [Zero-Leakage] Check if the pipeline's version matches the engine's current target
        if self._pipeline.k8s_version != self.cluster_version:
            logger.debug(f"Engine: Pipeline version mismatch ({self._pipeline.k8s_version} vs {self.cluster_version}). Re-binding...")
            self._pipeline.bind_catalog(self.catalog, self.cluster_version)
            self._apply_pipeline_config(self._pipeline)

        return self._pipeline

    def _apply_pipeline_config(self, pipeline: "HealingPipeline"):
        """Applies engine-level configurations to a pipeline instance."""
        if hasattr(pipeline.validator, "deep_array_check"):
            pipeline.validator.deep_array_check = self._deep_array_validation
        if pipeline.exporter and self._custom_key_order:
            pipeline.exporter.custom_order = self._custom_key_order

        if self._opa_bundle_path:
            self._init_opa_engine(self._opa_bundle_path)
        if self._kyverno_report_path:
            self._init_kyverno_engine(self._kyverno_report_path)
        if self._from_report_path:
            self._init_generic_report_adapter(self._from_report_path)

    def audit_and_heal_file(self, relative_path: str, **kwargs) -> HealFileResult:
        """
        Delegates to auditor.audit_and_heal_file and records telemetry.
        
        Why: Centralized telemetry capture for all single-file operations.
        """
        from yamlr.core.engine import auditor
        start_t = time.time()
        res = auditor.audit_and_heal_file(self, relative_path, **kwargs)
        duration = time.time() - start_t
        
        # Determine bytes processed
        b_proc = 0
        try:
            full_p = self.workspace / relative_path
            if full_p.exists():
                b_proc = full_p.stat().st_size
        except (OSError, IOError, AttributeError):
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
            avg_dna_score=res.trust_score,
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
        from yamlr.core.engine import auditor
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
            avg_dna_score=res.trust_score,
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
        extensions: Optional[List[str]] = None,
        max_depth: int = 10,
        dry_run: bool = True,
        **kwargs: Union[str, bool, int, float, List[str], None]
    ) -> List[HealFileResult]:
        """Delegates to processor.batch_heal."""
        from yamlr.core.engine import processor
        if extensions is None: extensions = [YAML_EXT, YML_EXT]

        # [HYPERSCALE-CACHE] Initialize SQLite-backed DiskIndex (VAL-02-6)
        # Why: Prevents RAM exhaustion during global analysis for 1M+ manifests.
        from yamlr.analyzers.detectors.disk_index import DiskIndex
        index_dir = self.workspace / ".yamlr_cache"
        index_dir.mkdir(parents=True, exist_ok=True)
        self.disk_index = DiskIndex(index_dir / "identity_index.db")
        self.disk_index.clear() # Start fresh for each batch

        if kwargs.get("from_report_path"):
            self._init_generic_report_adapter(str(kwargs.get("from_report_path")))

        # Group remaining kwargs
        return processor.batch_heal(
            self,
            root_path,
            extensions,
            max_depth=max_depth,
            dry_run=dry_run,
            **kwargs
        )

    def apply_semantic_fixes(self, results: List[HealFileResult], stub_healing: bool = False, allow_unsafe: bool = False, dry_run: bool = True) -> int:
        """Delegates to processor.apply_semantic_fixes."""
        from yamlr.core.engine import processor
        return processor.apply_semantic_fixes(self, results, stub_healing, allow_unsafe, dry_run, concurrency=self.concurrency)

    def get_upgrade_advisory_data(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """Calculates risk levels for an upgrade path.
        
        Why: Centralized logic for the Safety Engine to assess version migration risk.
        """
        from yamlr.analyzers.detectors.deprecation import DeprecationChecker
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
        except (ImportError, AttributeError, KeyError) as e:
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
        except (ImportError, AttributeError, KeyError) as e:
            logger.error(f"Failed to initialize Kyverno Engine: {e}")

    def _init_generic_report_adapter(self, report_path: str):
        """Auto-detects and initializes the appropriate adapter for a report file."""
        import json
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Simple heuristic
            if "items" in data or data.get("kind") in ["PolicyReport", "ClusterPolicyReport"]:
                self._init_kyverno_engine(report_path)
            elif "result" in data or "expressions" in str(data):
                self._init_opa_engine(report_path)
            else:
                logger.warning(f"Could not determine report format for {report_path}")
        except (json.JSONDecodeError, OSError, IOError) as e:
            logger.error(f"Failed to auto-detect report format: {e}")

    def close(self):
        """Releases all engine and infrastructure resources safely."""
        try:
            if hasattr(self, "disk_index") and self.disk_index:
                self.disk_index.close()
                self.disk_index = None
            if hasattr(self, "manager") and self.manager:
                self.manager.close()
        except (AttributeError, OSError, IOError) as e:
            logger.debug(f"Engine shutdown warning: {e}")

# Export aliases
audit_status = HealStatus
AUDIT_ENGINE_V3 = YamlrEngine
AuditEngineV3 = YamlrEngine
