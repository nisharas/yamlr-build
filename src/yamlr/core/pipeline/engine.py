#!/usr/bin/env python3
"""
Yamlr HEALING PIPELINE - The Chief Surgeon
-------------------------------------------
Modular Orchestrator for the Yamlr Healing Pipeline.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
from .plan import PipelinePlan
from .executor import PipelineExecutor
from yamlr.core.context import HealContext
from yamlr.models import HealConfig, PipelineStats, HealStatus, HealResult
from yamlr.parsers.lexer import YamlrLexer
from yamlr.parsers.scanner import YamlrScanner
from yamlr.parsers.shadow import YamlrShadow
from yamlr.parsers.structurer import YamlrStructurer
from yamlr.validators.schema_validator import SchemaValidator
from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer
from yamlr.healers.best_practices.network_policy import NetworkPolicyHealer
from yamlr.core.bridge import YamlrBridge
from yamlr.healers.semantic.port_healer import PortMismatchHealer
from yamlr.healers.semantic.missing_target import MissingTargetHealer
from yamlr.analyzers.ref_resolver import ReferenceResolver

logger = logging.getLogger("yamlr.pipeline")

class HealingPipeline:
    """
    Modular Orchestrator for the Yamlr Healing Pipeline.
    """

    def __init__(
        self,
        catalog: Dict[str, Any],
        cpu_limit: str = "500m",
        mem_limit: str = "512Mi",
        default_namespace: str = "default",
        app_name: str = "Yamlr",
        k8s_version: str = "1.31",
        pro_brand: str = "Yamlr Enterprise (Pro)",
        allowed_host_paths: List[str] = None,
        trusted_registries: List[str] = None,
        pro: Optional[bool] = None,
    ):
        """
        Why: To initialize the central orchestrator with the necessary
             domain knowledge (catalog) and environment defaults.
        """
        self.catalog = catalog
        self._pro_override = pro
        self.k8s_version = k8s_version
        self.default_namespace = default_namespace
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.allowed_host_paths = allowed_host_paths or []
        self.trusted_registries = trusted_registries or []

        # --- Base Components ---
        self.lexer = YamlrLexer()
        self.shadow = YamlrShadow()
        self.scanner = YamlrScanner(catalog, app_name=app_name)
        self.schema_validator = SchemaValidator(catalog, k8s_version=k8s_version)
        from yamlr.parsers.physicist import IndentationPhysicist
        self.physicist = IndentationPhysicist()
        self.structurer = YamlrStructurer(catalog, validator=self.schema_validator)
        
        self.selector_healer = ServiceSelectorHealer()
        from yamlr.healers.semantic.referential_healer import ReferentialHealer
        self.referential_healer = ReferentialHealer()
        self.network_policy_healer = NetworkPolicyHealer()
        from yamlr.healers.best_practices.image_tag import ImageTagHealer
        self.image_healer = ImageTagHealer()
        self.port_healer = PortMismatchHealer()
        self.missing_target_healer = MissingTargetHealer()
        self.ref_resolver = ReferenceResolver()

        # Enterprise Hook
        self.shield = YamlrBridge.get_shield()
        self.validator = YamlrBridge.get_validator() or self.schema_validator
        self.exporter = YamlrBridge.get_exporter(catalog)
        self.judge = YamlrBridge.get_judge(catalog)

    def bind_catalog(self, catalog: Dict[str, Any], version: str):
        """Re-binds the pipeline to a different version and its corresponding catalog."""
        self.catalog = catalog
        self.k8s_version = version
        self.scanner.catalog = catalog
        self.schema_validator.k8s_version = version
        self.structurer.catalog = catalog
        if hasattr(self.validator, "k8s_version"):
            self.validator.k8s_version = version
        if hasattr(self.exporter, "catalog"):
            self.exporter.catalog = catalog
        logger.debug(f"Pipeline: Re-bound to K8s {version}")

    def create_context(self, raw_text: str, config: "HealConfig") -> HealContext:
        """Creates a new HealContext for the pipeline, pre-populated with config."""
        context = HealContext(
            raw_text=raw_text, file_path=config.file_path,
            cluster_version=config.cluster_version or self.k8s_version,
            catalog=self.catalog
        )
        context.config = config
        context.shadow_engine = self.shadow
        context.physicist = self.physicist
        context.default_namespace = config.default_namespace or self.default_namespace
        context.allowed_host_paths = self.allowed_host_paths
        context.trusted_registries = self.trusted_registries
        context.strict_mode = config.strict_mode
        context._config_embed_receipt = config.embed_receipt
        return context

    def find_schema_key(self, api_version: str, kind: str) -> Optional[str]:
        """Maps generic resource references to their specific OpenAPI definitions."""
        if not kind: return None
        exact = f"{api_version}/{kind}"
        if exact in self.catalog: return exact
        for k in self.catalog.keys():
            if str(k).split("/")[-1].lower() == kind.lower(): return k
        return None

    def heal(
        self,
        raw_yaml: str,
        config: Optional[HealConfig] = None,
        context: Optional[HealContext] = None,
        **kwargs: Union[str, bool, int, List[str], None]
    ) -> HealResult:
        """Executes the full multi-stage healing pipeline for a YAML string."""
        config = self._resolve_config(config, kwargs)
        
        # [VAL-02-6] Native Fast Path Optimization
        if config.fast and config.skip_repair:
            try:
                from yamlr_native import native_fast_audit, native_extract_metadata
                start_fast = time.time()
                audit_res = native_fast_audit(raw_yaml)
                native_docs = native_extract_metadata(raw_yaml)
                
                from yamlr.models import HealAction, ManifestIdentity
                from yamlr.core.stages.boundaries import MutationScope
                
                findings = []
                for f in audit_res.get("findings", []):
                    findings.append(HealAction(
                        stage=f["stage"], action_type=f["action_type"], target=f["target"],
                        description=f["description"], severity=f["severity"], rule_id=f["rule_id"],
                        scope=MutationScope.STRUCTURAL, field=f["target"]
                    ))
                
                identities = []
                for doc in native_docs:
                    if isinstance(doc, dict) and "kind" in doc and "apiVersion" in doc:
                        meta = doc.get("metadata", {})
                        identities.append(ManifestIdentity(
                            kind=doc["kind"], api_version=doc["apiVersion"],
                            name=meta.get("name", "unknown"), namespace=meta.get("namespace", "default"),
                            labels=meta.get("labels", {})
                        ))

                return HealResult(
                    content=raw_yaml, status=HealStatus.SUCCESS if findings else HealStatus.SKIPPED,
                    findings=findings, identities=identities, dna_integrity_score=100,
                    stats=PipelineStats(timings={"total": time.time() - start_fast}),
                    logs=["Native: Fast-path high-speed audit (150MB/s) successful"]
                )
            except Exception as e:
                logger.error(f"Native fast-path failed: {e}. Falling back.")

        if context is None:
            context = self.create_context(raw_yaml, config)
        
        context.config = config
        plan = PipelinePlan.for_mode("heal", config, self)
        executor = PipelineExecutor(plan)
        stage_results = executor.execute(context)
        
        from yamlr.core.engine.result_aggregator import ResultAggregator
        return ResultAggregator.build_result(context, stage_results, config)

    def _resolve_config(self, config: Optional[HealConfig], kwargs: Dict[str, Any]) -> HealConfig:
        """Ensures a valid HealConfig object with resolved capabilities."""
        if config is None:
            is_pro = self._pro_override if self._pro_override is not None else YamlrBridge.is_pro()
            config = HealConfig(
                skip_repair=not is_pro,
                **{k: v for k, v in kwargs.items() if k in HealConfig.__annotations__}
            )
        
        if self._pro_override is True:
            config.skip_repair = False
            
        from yamlr.core.license_manager import LicenseManager
        if not config.capabilities.can_generate_evidence:
            config.capabilities = LicenseManager.resolve_capabilities()
        return config
