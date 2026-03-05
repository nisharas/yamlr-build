#!/usr/bin/env python3
"""
Yamlr HEALING PIPELINE - The Chief Surgeon (Modular v2)
------------------------------------------------------
The central coordinator for the complete healing workflow.
Transforms malformed manifests into production-ready, validated YAML.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from yamlr.analyzers.base import AnalysisResult
from yamlr.core.bridge import YamlrBridge
from yamlr.core.context import HealContext
from yamlr.models import ManifestIdentity, Shard, HealConfig, PipelineStats
from yamlr.parsers.lexer import YamlrLexer
from yamlr.parsers.scanner import YamlrScanner
from yamlr.parsers.shadow import YamlrShadow
from yamlr.parsers.structurer import YamlrStructurer
from yamlr.validators.schema_validator import SchemaValidator
from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer
from yamlr.healers.best_practices.network_policy import NetworkPolicyHealer

# Modular Stages
from yamlr.core.stages.epistemic import StageSixTwoEpistemicRepair
from yamlr.core.stages.referential import StageReferentialAlignment
from yamlr.core.stages.extraction import (
    StageZeroReset,
    StageOneLexicalRepair,
    StageTwoLayoutCapture,
    StageThreeIdentityExtraction,
)
from yamlr.core.stages.transformation import (
    StageFourSemanticAnalysis,
    StageFiveSchemaSelection,
    StageSixReconstruction,
    StageSixOneMigration,
    StageSixFiveContentAnalysis,
    StageEightValidationScoring,
    StageNineSerialization,
)
from yamlr.core.stages.healing import (
    StageResourceNormalization,
    StageImageTagHealing,
    StageSecurityHardening,
    StageProbeInjection,
    StageSelectorAlignment,
    StageNetworkPolicyEnforcement,
    StageNamespaceEnforcement,
    StagePortAlignment,
    StageGhostResourceGeneration,
)
from yamlr.core.stages.risk import StageTenRiskClassification
from yamlr.healers.semantic.port_healer import PortMismatchHealer
from yamlr.healers.semantic.missing_target import MissingTargetHealer
from yamlr.analyzers.ref_resolver import ReferenceResolver

logger = logging.getLogger("yamlr.pipeline")

class HealStatus(str, Enum):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class HealResult:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    status: HealStatus
    content: str
    logs: List[str]
    health_score: int
    identities: List[ManifestIdentity] = field(default_factory=list)
    findings: List[AnalysisResult] = field(default_factory=list)
    stats: PipelineStats = field(default_factory=PipelineStats)
    deprecation_info: List[str] = field(default_factory=list)
    depth: str = "Light"
    error_message: Optional[str] = None
    
    # Truth-in-Healing (Phase 1 Shield)
    phy_status: str = "100%"
    kbs_status: str = "0%"
    sem_status: str = "0%"

class HealingPipeline:
    """
    Modular Orchestrator for the Yamlr Healing Pipeline.
    """

    def __init__(
        self,
        catalog: Dict[Any, Any],
        cpu_limit: str = "500m",
        mem_limit: str = "512Mi",
        default_namespace: str = "default",
        app_name: str = "Yamlr",
        k8s_version: str = "1.31",
        pro_brand: str = "Yamlr Enterprise",
        allowed_host_paths: List[str] = None,
        trusted_registries: List[str] = None,
    ):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.catalog = catalog
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
        self.schema_validator = SchemaValidator(k8s_version=k8s_version)
        self.structurer = YamlrStructurer(catalog, validator=self.schema_validator)
        
        self.selector_healer = ServiceSelectorHealer()
        from yamlr.healers.semantic.referential_healer import ReferentialHealer
        self.referential_healer = ReferentialHealer()
        self.netpol_healer = NetworkPolicyHealer()
        self.port_healer = PortMismatchHealer()
        self.missing_target_healer = MissingTargetHealer()
        self.ref_resolver = ReferenceResolver()

        # Enterprise Hook
        self.shield = YamlrBridge.get_shield()
        self.validator = YamlrBridge.get_validator() or self.schema_validator
        self.exporter = YamlrBridge.get_exporter()

    def _find_schema_key(self, kind: str, api_version: str) -> Optional[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
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
        **kwargs
    ) -> HealResult:
        """Executes the full multi-stage healing pipeline for a YAML string.

        Why: Orchestrates 15+ discrete stages of analysis, transformation, and
             validation. `fix_refs` gates the three cross-resource healing stages
             (StageSelectorAlignment, StagePortAlignment, StageGhostResourceGeneration)
             behind the Pro flag [PRO-12-05], preventing any side-effects on OSS runs.

        Args:
            raw_yaml (str): The raw manifest text to heal.
            config (HealConfig, optional): Validated configuration object.
            **kwargs: Backward compatibility for legacy flat parameters.

        Returns:
            HealResult: A structured object containing healed content,
                health score, identities, and detailed audit logs.
        """
        # --- BI-DIRECTIONAL COMPATIBILITY GAP ---
        if config is None:
            # Pydantic v2/v1 cross-version field discovery
            model_fields = getattr(HealConfig, "model_fields", getattr(HealConfig, "__fields__", {}))
            valid_fields = list(model_fields.keys())
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
            config = HealConfig(**filtered_kwargs)

        context = HealContext(raw_text=raw_yaml, cluster_version=config.cluster_version or self.k8s_version)
        context.shadow_engine = self.shadow
        context.default_namespace = config.default_namespace or self.default_namespace
        context.allowed_host_paths = self.allowed_host_paths
        context.trusted_registries = self.trusted_registries
        stats = PipelineStats()
        start_time = time.time()

        # 1. Pipeline Definition
        # Base stages always run (OSS + Pro)
        all_stages = [
            StageZeroReset(self.shadow),
            StageOneLexicalRepair(self.lexer),
            StageTwoLayoutCapture(self.shadow),
            StageThreeIdentityExtraction(self.lexer, self.scanner, config.identity_mode, config.file_path),
            StageFourSemanticAnalysis(),
            StageFiveSchemaSelection(self._find_schema_key),
            StageSixReconstruction(self.structurer),
            StageSixTwoEpistemicRepair(self.structurer),
            StageSixOneMigration(config.cluster_version or self.k8s_version, enabled=config.check_deprecations),
            StageSixFiveContentAnalysis(),
            StageResourceNormalization(self.structurer, config.enforce_limits),
            StageImageTagHealing(config.fix_tags),
            StageSecurityHardening(config.harden),
            StageProbeInjection(config.enforce_probes),
            StageNetworkPolicyEnforcement(self.netpol_healer, config.harden),
            StageNamespaceEnforcement(config.enforce_namespace),
            StageEightValidationScoring(self.schema_validator),
            StageTenRiskClassification(),
            StageNineSerialization(self.structurer, config.compact),
        ]

        # [PRO-12-05] Cross-Resource Auto-Fix stages (Pro-only).
        if config.fix_refs:
            cross_resource_stages = [
                StageSelectorAlignment(self.selector_healer),
                StagePortAlignment(self.port_healer),
                StageGhostResourceGeneration(self.missing_target_healer, self.ref_resolver, stub_refs=True),
                StageReferentialAlignment(self.referential_healer),
            ]
            # Insert before StageEightValidationScoring
            insert_at = next(
                (i for i, s in enumerate(all_stages) if isinstance(s, StageEightValidationScoring)),
                len(all_stages) - 2,
            )
            for j, stage in enumerate(cross_resource_stages):
                all_stages.insert(insert_at + j, stage)

        # Filter stages for 'fast' mode
        if config.fast:
            skip_types = (
                StageFourSemanticAnalysis,
                StageSixFiveContentAnalysis,
                StageSelectorAlignment,
                StageNetworkPolicyEnforcement,
            )
            stages = [s for s in all_stages if not isinstance(s, skip_types)]
        else:
            stages = all_stages
            
        # 2. Execution Loop
        final_content = raw_yaml
        total_penalty = 0
        
        for stage in stages:
            s_start = time.time()
            try:
                res = stage.run(context)
                stage_duration = time.time() - s_start
                stats.stage_timings[stage.__class__.__name__] = stage_duration

                if isinstance(res, dict):
                    if not res.get("success", True):
                        if res.get("skipped"):
                            return HealResult(HealStatus.SKIPPED, raw_yaml, context.audit_log, 100, identities=context.identities)
                        return HealResult(HealStatus.FAILED, raw_yaml, context.audit_log, 0, error_message=str(res.get("error")))
                    
                    # Accumulate penalties from all stages
                    total_penalty += res.get("penalty", 0)

                    # Special result handling for serialization
                    if isinstance(stage, StageNineSerialization):
                        final_content = res.get("content", raw_yaml)
                    
                    # --- STATS AGGREGATION ---
                    s_data = res.get("stats", {})
                    if s_data:
                        stats.lexer_repairs += s_data.get("lexer_repairs", 0)
                        stats.lexer_typos += s_data.get("lexer_typos", 0)
                        stats.migrator_changes += s_data.get("migrator_changes", 0)
                        stats.semantic_repairs += s_data.get("semantic_repairs", 0)
                        stats.security_hardens += s_data.get("security_hardens", 0)
                    
                    # Standard 'modified' count mapping
                    modified = res.get("modified", 0)
                    if modified:
                        if isinstance(stage, StageSecurityHardening):
                            stats.security_hardens += modified
                        elif isinstance(stage, StageSixOneMigration):
                            stats.migrator_changes += modified
                        else:
                            stats.semantic_repairs += modified
                            
                    # Typo mapping
                    typos = res.get("typo_count", 0)
                    if typos:
                        stats.lexer_typos += typos
                
            except Exception as e:
                logger.exception(f"Pipeline Stage Crash: {stage.name}")
                return HealResult(HealStatus.FAILED, raw_yaml, context.audit_log, 0, error_message=f"Crash in {stage.name}: {e}")

        final_score = max(0, 100 - total_penalty)

        # Truth-in-Healing Status Calculation (Phase 1 Shield)
        # PHY: 100% if Stage 1/2 didn't crash (Physical health)
        phy_val = "100%"
        
        # KBS: Calculated from Schema Validation errors (prefix 'schema/')
        all_findings = context.findings
        val_errors = sum(1 for f in all_findings if f.rule_id and "schema" in f.rule_id.lower())
        kbs_val = "100%" if val_errors == 0 else f"{max(0, 100 - (val_errors * 10))}%"
        
        # SEM: Logic health (Cross-resource issues or custom logic)
        sem_errors = sum(1 for f in all_findings if (f.analyzer_name and "resource" in f.analyzer_name.lower()) or (f.rule_id and "logical" in f.rule_id.lower()))
        sem_val = "100%" if sem_errors == 0 else f"{max(0, 100 - (sem_errors * 15))}%"
        
        stats.timings["total"] = time.time() - start_time
        return HealResult(
            status=HealStatus.SUCCESS,
            content=final_content,
            logs=context.audit_log,
            health_score=final_score,
            identities=context.identities,
            findings=context.findings,
            stats=stats,
            deprecation_info=[log for log in context.audit_log if "Stage 6.1" in log],
            depth=context.depth,
            phy_status=phy_val,
            kbs_status=kbs_val,
            sem_status=sem_val
        )
