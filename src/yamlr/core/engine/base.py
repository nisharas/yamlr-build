from __future__ import annotations

"""
BASE ENGINE - The Heart of Yamlr (v4.2)
--------------------------------------
Production-validated orchestrator for manifest healing.
"""
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from yamlr.core.engine.models import HealConfig
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineState
from yamlr.core.bridge import YamlrBridge
from yamlr.core.manager import YamlrManager
from yamlr.core.telemetry import TelemetryManager

from .models import HealStatus

logger = logging.getLogger("yamlr.engine")

class YamlrEngine:
    """
    Principal Orchestrator for Kubernetes manifest healing (The 'Brain').
    """
    
    def __init__(
        self,
        workspace_path: str,
        catalog_path: Optional[str] = None,
        cluster_version: Optional[str] = None,
        app_name: Optional[str] = None,
        **kwargs,
    ):
        from yamlr.core.gatekeeper import LicenseGate
        tier_meta = LicenseGate.get_tier_metadata()
        
        self.app_name: str = app_name or str(kwargs.get("app_name", tier_meta["name"]))
        self.pro_brand: str = tier_meta["name"]
        
        # [Modularity] manager handles the heavy lifting of workspace discovery
        self.manager = YamlrManager(
            workspace_path=workspace_path,
            catalog_path=catalog_path,
            cluster_version=cluster_version,
            concurrency=kwargs.get("concurrency"),
            app_name=self.app_name,
            health_threshold=kwargs.get("health_threshold", 70),
            allowed_host_paths=kwargs.get("allowed_host_paths")
        )
        
        # Essential Surface Area for Stage Handlers and Helpers
        self.workspace: Path = self.manager.workspace
        self.fs = self.manager.fs
        self.config = self.manager.config
        self.cluster_version: str = self.manager.cluster_version
        self.health_threshold: int = self.manager.health_threshold
        self.allowed_host_paths: List[str] = self.manager.allowed_host_paths or []
        self.concurrency: Optional[int] = self.manager.concurrency
        
        self.cpu_limit: str = str(kwargs.get("cpu_limit", "500m"))
        self.mem_limit: str = str(kwargs.get("mem_limit", "512Mi"))
        self.default_namespace: str = str(kwargs.get("default_namespace", "default"))
        self.safe_mode: bool = bool(kwargs.get("safe_mode", False))
        
        self.telemetry = TelemetryManager(self.workspace, app_name=self.app_name)
        self._parser = None
        
        # 5. Initialize Diagnostic Subsystems (Analyzer Suite)
        from yamlr.analyzers.registry import AnalyzerRegistry
        AnalyzerRegistry.register_defaults()
        
        # [Zero-Blindspot] Support engine.pipeline boundary 
        self.pipeline = self

        # Forensic Journal (WAL)
        self.journal: Optional[Any] = None

    @property
    def parser(self) -> Any:
        """Lazy-loaded shared parser instance."""
        if self._parser is None:
            from yamlr.core.parser.ruamel_adapter import RuamelAdapter
            self._parser = RuamelAdapter()
        return self._parser

    @property
    def catalog(self) -> Dict[str, Any]:
        """Lazy-bound catalog from manager."""
        return self.manager.catalog

    def process_file(
        self, 
        relative_path: str, 
        content: Optional[str] = None, 
        full_path: Optional[str] = None, 
        config: Any = None, 
        start_time: Optional[float] = None, 
        **kwargs
    ) -> Any:
        """
        Principal Entry Point for the modularized PipelineStage execution cycle (v4.2).
        """
        from yamlr.core.engine.models import HealFileResult, HealStatus
        from yamlr.core.stages.normalization import NormalizationStage
        from yamlr.core.stages.analysis import AnalysisStage
        from yamlr.core.stages.emulation import EmulationStage
        
        # [Zero-Blindspot] Signature Normalization for mixed v3/v4 callers
        if "apiVersion" in relative_path or "kind:" in relative_path:
             # Positional swap: auditor.py passes (content, relative_path, ...)
             _tmp = relative_path
             relative_path = content or "unknown"
             content = _tmp
        
        start_time = start_time or time.time()
        full_path = full_path or str(self.workspace / relative_path) if not os.path.isabs(relative_path) else relative_path
        
        # 1. Acquire Content
        content = content if content is not None else self._read_content(full_path, relative_path)
        if isinstance(content, HealFileResult):
            return content

        # 2. Setup Context & State
        engine_context, state = self._initialize_state(content, relative_path, config, **kwargs)

        # 3. Normalization (Stage 1)
        norm_res = NormalizationStage().execute(state, engine=self)
        if not norm_res.success:
            return self._build_error_result(relative_path, full_path, content, norm_res, start_time)
        
        # 4. Emulation (Stage 1.5 - Hybrid Sidecar Simulation)
        emu_res = EmulationStage().execute(state, engine=self)
        if not emu_res.success and state.context.shadow:
             state.context.audit_log.append(f"⚠️ Shadow Mode Degradation: {emu_res.errors[0] if emu_res.errors else 'Unknown'}")

        engine_context.docs = state.documents
        self._populate_container_context(state, engine_context)

        # 5. Analysis (Stage 2)
        analysis_res = AnalysisStage(catalog=self.manager.catalog).execute(state)
        engine_context.findings = state.findings

        # 6. Remediation (Stage 3)
        self._run_remediation_cycle(state, config, **kwargs)

        # 7. Result Aggregation
        from yamlr.core.engine.result_aggregator import ResultAggregator
        final_telemetry = ResultAggregator.build_result(state, {"analysis": analysis_res}, config, engine=self)
        
        # 8. Status Mapping & Final Packaging
        status = self._map_status(state, analysis_res.success, **kwargs)

        # 9. Patch Bridge Persistence (v4.2)
        # Why: Enforces GitOps compatibility by writing surgical patches to disk
        # only when a heal action was successfully computed.
        if kwargs.get("patch_mode") and status == HealStatus.HEALED:
            from yamlr.core.engine.patch_engine import PatchGenerator
            patch_path = os.path.join(os.getcwd(), "yamlr-patches.yaml")
            
            # [Safety First] Create backup of existing patch file
            if os.path.exists(patch_path):
                 self.fs.create_backup(patch_path)
            
            PatchGenerator.generate_and_append(patch_path, content, final_telemetry.content)

        # 10. Forensic Integrity: Record intent and status in journal
        if not kwargs.get("dry_run", True) and self.journal:
             if status == HealStatus.HEALED:
                 self.journal.log_pending(relative_path, hashlib.sha256(content.encode()).hexdigest())
                 # The actual write happens in the FS layer; we mark as DONE in the processor loop
             elif status == HealStatus.FAILED:
                 self.journal.mark_failed(relative_path)

        return HealFileResult(
            file_path=relative_path,
            full_path=full_path,
            success=analysis_res.success,
            status=status,
            kind=final_telemetry.identities[0].kind if final_telemetry.identities else "Unknown",
            logic_logs=final_telemetry.logs,
            findings=final_telemetry.findings,
            dna_integrity_score=final_telemetry.dna_integrity_score,
            original_content=content,
            healed_content=final_telemetry.content,
            reconciled_count=final_telemetry.reconciled_count,
            processing_time_seconds=time.time() - start_time
        )

    def _read_content(self, full_path: str, relative_path: str) -> Union[str, Any]:
        """Reads file content with error handling."""
        from yamlr.core.engine.models import HealFileResult, HealStatus, AnalysisResult
        try:
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except UnicodeDecodeError:
            return self._build_io_error(relative_path, full_path, "DECODE_ERROR: File contains non-UTF-8 binary data.")
        except Exception as e:
            return self._build_io_error(relative_path, full_path, f"Read Error: {e}")

    def _initialize_state(self, content: str, relative_path: str, config: Any, **kwargs) -> Tuple[Any, Any]:
        """Initializes the engine context and pipeline state."""
        from yamlr.core.engine.stages.ingest import execute_ingest_stage
        from yamlr.core.stages.base import PipelineState

        engine_context = HealContext(
            workspace=str(self.workspace),
            catalog=self.manager.catalog,
            cluster_version=getattr(config, "cluster_version", self.cluster_version),
            dry_run=kwargs.get("dry_run", True),
            emulate=kwargs.get("emulate", []),
            shadow=kwargs.get("shadow", False),
            original_content=content,
            kube_context=kwargs.get("kube_context")
        )

        ingest_data = execute_ingest_stage(self, content, relative_path, config)
        state = PipelineState(
            content=content,
            shards=ingest_data.get("shards", []),
            identities=ingest_data.get("identities", []),
            context=engine_context
        )
        return engine_context, state

    def _populate_container_context(self, state: Any, engine_context: Any):
        """Extracts container metadata for analyzers."""
        from yamlr.core.k8s_utils import extract_containers
        container_ctx = []
        for doc in state.documents:
            container_ctx.extend(extract_containers(doc))
        engine_context.container_context = container_ctx

    def _run_remediation_cycle(self, state: Any, config: Any, **kwargs):
        """Executes the remediation stages (Safe/Pro)."""
        from yamlr.core.stages.healing_core import HealingCoreStage
        from yamlr.core.stages.healing_security import HealingSecurityStage
        from yamlr.core.stages.healing_best_practices import HealingBestPracticesStage
        
        dry_run = kwargs.get("dry_run", True)
        if not dry_run:
            from yamlr.core.license_manager import LicenseManager
            allowed, _, msg = LicenseManager.is_healing_allowed(1)
            if not allowed:
                state.context.quota_exceeded = True
                state.context.audit_log.append(f"❌ Quota Exceeded: {msg}")
                return

            LicenseManager.record_healing_usage(1)
        
        # Execute Healing Tier Trophies
        HealingCoreStage().execute(state)
        HealingSecurityStage(harden=kwargs.get("harden", False)).execute(state)
        HealingBestPracticesStage(
            fix_tags=kwargs.get("fix_tags", False) or getattr(config, "fix_tags", False),
            enforce_probes=kwargs.get("enforce_probes", False)
        ).execute(state)

    def _map_status(self, state: Any, analysis_success: bool, **kwargs) -> Any:
        """Determines the final HealStatus for the file."""
        from yamlr.core.engine.models import HealStatus
        
        if state.context.quota_exceeded:
            return HealStatus.QUOTA_EXCEEDED
        if not analysis_success:
            return HealStatus.FAILED
        if state.context.fixed_count > 0:
            return HealStatus.HEALED
        if not state.findings:
            return HealStatus.UNCHANGED
        
        return HealStatus.UNCHANGED if kwargs.get("dry_run", True) else HealStatus.SKIPPED

    def _build_io_error(self, relative_path: str, full_path: str, message: str) -> Any:
        """Builds a standardized HealFileResult for IO errors."""
        from yamlr.core.engine.models import HealFileResult, HealStatus, AnalysisResult
        return HealFileResult(
            file_path=relative_path,
            full_path=full_path,
            success=False,
            status=HealStatus.FAILED,
            kind="Unknown",
            logic_logs=[f"❌ {message}"],
            findings=[
                AnalysisResult(
                    analyzer_name="System",
                    severity="ERROR",
                    message=message,
                    resource_name="unknown",
                    resource_kind="Unknown",
                    file_path=relative_path,
                    suggestion="Check file permissions or encoding.",
                    rule_id="system/io-error"
                )
            ],
            original_content="",
            healed_content="",
        )

    def _build_error_result(self, relative_path: str, full_path: str, content: str, norm_res: Any, start_time: float) -> Any:
        """Builds a standardized error result for normalization failures."""
        from yamlr.core.engine.models import HealFileResult, HealStatus
        return HealFileResult(
            file_path=relative_path,
            full_path=full_path,
            success=False,
            status=HealStatus.FAILED,
            kind="Error",
            logic_logs=[f"❌ {norm_res.errors[0] if norm_res.errors else 'Parsing failed'}"],
            findings=[],
            original_content=content,
            healed_content=content,
            processing_time_seconds=time.time() - start_time
        )

    def audit_and_heal_file(self, relative_path, **kwargs):
        """Legacy entrypoint redirected to v3 loop."""
        return self.process_file(relative_path=relative_path, **kwargs)

    def audit_stream(self, content, source_name="<stdin>", **kwargs):
        """Legacy entrypoint redirected to v3 loop."""
        return self.process_file(source_name, content=content, **kwargs)

    def audit_stream(self, content, source_name="<stdin>", **kwargs):
        """Legacy entrypoint redirected to v3 loop."""
        return self.process_file(source_name, content=content, **kwargs)

    def batch_heal(self, root_path, **kwargs):
        """Batch processing entrypoint (Unified Crawler)."""
        from yamlr.core.engine import processor
        from yamlr.core.engine.crawler import crawl_manifests

        extensions = kwargs.get("extensions", [".yaml", ".yml"])
        files = crawl_manifests(self.workspace, root_path, extensions=extensions, max_depth=10, engine_context={})
        files_to_process = [f["path"] for f in files]
        return processor.batch_heal(self, files_to_process, **kwargs)

    def close(self):
        """Ensures safe resource release."""
        if hasattr(self, "manager") and self.manager:
            self.manager.close()

# Export aliases
AuditEngineV3 = YamlrEngine
AuditEngine = YamlrEngine
