#!/usr/bin/env python3
"""
STAGE REGISTRY - Pipeline Orchestration Source of Truth
------------------------------------------------------
Centralizes the definition, ordering, and dependency management of 
all healing pipeline stages. 

Why: To ensure deterministic execution and acquisition-ready modularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from yamlr.core.stages.base import PipelineStage
    from yamlr.models import HealConfig

class StageRegistry:
    """
    Maintains the 'Gold Standard' sequence of pipeline stages.
    """
    
    @staticmethod
    def get_plan_specs(mode: str, config: "HealConfig", pipeline: Any) -> List[Any]:
        """Resolves the sequence of stage specifications.
        
        Why: Decouples stage configuration from instantiation, enabling
             lazy loading and structured plan verification.
        """
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.healing import StageGhostResourceGeneration, StagePortAlignment, StageSelectorAlignment

        # 1. Import all stage classes locally to avoid circular dependencies
        from yamlr.core.stages.referential import StageReferentialAlignment
        from yamlr.core.stages.relational import StageRelationalSurgery
        from yamlr.core.stages.transformation import StageEightValidationScoring

        # 2. Build the blueprint of specs
        # 2. Build the blueprint of specs using sub-assemblies
        specs = StageRegistry._get_structural_specs(pipeline, config)
        specs.extend(StageRegistry._get_transformation_specs(pipeline, config))
        specs.extend(StageRegistry._get_healing_specs(pipeline, config))
        specs.extend(StageRegistry._get_risk_specs(pipeline, config))
        specs.extend(StageRegistry._get_finalization_specs(pipeline, config))

        # 3. Filter None results
        specs = [s for s in specs if s is not None]

        # 4. Cross-Resource Dynamic Injection
        if config.fix_refs and config.capabilities.can_heal_cross_resource:
            cr_specs = [
                StageSpec("Selector Alignment", StageSelectorAlignment, {"healer": pipeline.selector_healer}), 
                StageSpec("Port Alignment", StagePortAlignment, {"healer": pipeline.port_healer}),
                StageSpec("Relational", StageRelationalSurgery),
                StageSpec("Ghost Resource Gen", StageGhostResourceGeneration, {
                    "healer": pipeline.missing_target_healer, "resolver": pipeline.ref_resolver, "stub_refs": True
                }),
                StageSpec("Referential Alignment", StageReferentialAlignment, {"healer": pipeline.referential_healer}),
            ]
            # Inject before Validation
            try:
                idx = next(i for i, s in enumerate(specs) if s.stage_cls == StageEightValidationScoring)
            except StopIteration:
                idx = len(specs) - 2
                
            for j, spec in enumerate(cr_specs):
                specs.insert(idx + j, spec)

        return specs

    @staticmethod
    def _get_structural_specs(pipeline: Any, config: "HealConfig") -> List[Any]:
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.extraction import (
            StageOneLexicalRepair,
            StageThreeIdentityExtraction,
            StageTwoLayoutCapture,
            StageZeroReset,
        )
        from yamlr.core.stages.interlock import StageSecurityInterlock
        return [
            StageSpec("Security Interlock", StageSecurityInterlock, abort_on_error=True, category="structural"),
            StageSpec("Reset", StageZeroReset, {"shadow": pipeline.shadow}, abort_on_error=True, is_structural=True, category="structural"),
            StageSpec("Lexical", StageOneLexicalRepair, {"lexer": pipeline.lexer}, abort_on_error=True, is_structural=True, category="structural"),
            StageSpec("Layout", StageTwoLayoutCapture, {"shadow": pipeline.shadow}, abort_on_error=True, is_structural=True, category="structural"),
            StageSpec("Identity", StageThreeIdentityExtraction, {
                "lexer": pipeline.lexer, "scanner": pipeline.scanner, 
                "identity_mode": config.identity_mode, "file_path": config.file_path,
                "kind": config.kind, "api_version": config.api_version
            }, abort_on_error=True, is_structural=True, category="structural"),
        ]

    @staticmethod
    def _get_transformation_specs(pipeline: Any, config: "HealConfig") -> List[Any]:
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.epistemic import StageSixTwoEpistemicRepair
        from yamlr.core.stages.healing import StageStructuralCleanup
        from yamlr.core.stages.safeguard import StageAgenticSafeGuard
        from yamlr.core.stages.transformation import (
            StageFiveSchemaSelection,
            StageFourSemanticAnalysis,
            StageNineSerialization,
            StageSixFiveContentAnalysis,
            StageSixOneMigration,
            StageSixReconstruction,
        )

        specs = [
            StageSpec("Semantics", StageFourSemanticAnalysis, category="semantic"),
            StageSpec("Stage 5: Schema Selection", StageFiveSchemaSelection, {"find_schema_key_fn": pipeline.find_schema_key}, category="semantic"),
            StageSpec("Reconstruction", StageSixReconstruction, {"structurer": pipeline.structurer}, category="structural"),
            StageSpec("Cleanup", StageStructuralCleanup, category="structural"),
            StageSpec("Epistemic", StageSixTwoEpistemicRepair, {"structurer": pipeline.structurer}, category="healing"),
            StageSpec("Migration", StageSixOneMigration, {
                "target_version": config.cluster_version or pipeline.k8s_version, "enabled": True
            }, category="healing") if config.check_deprecations else None,
            StageSpec("Content", StageSixFiveContentAnalysis, category="semantic"),
            StageSpec("Serialization (Intermediate)", StageNineSerialization, {
                "structurer": pipeline.structurer, "exporter": pipeline.exporter, "compact": config.compact
            }, category="structural"),
            StageSpec("Safety Brake", StageAgenticSafeGuard, category="structural"),
        ]
        return [s for s in specs if s]

    @staticmethod
    def _get_healing_specs(pipeline: Any, config: "HealConfig") -> List[Any]:
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.healing import (
            StageImageTagHealing,
            StageIngressHardening,
            StageNamespaceEnforcement,
            StageNetworkPolicyEnforcement,
            StagePrivilegeEscalation,
            StageProbeInjection,
            StageRBACAuditing,
            StageResourceNormalization,
        )
        from yamlr.core.stages.remediation_stage import StageExternalRemediation
        
        specs = [
            StageSpec("Resources", StageResourceNormalization, {
                "structurer": pipeline.structurer, "enforce_limits": config.enforce_limits, "config": config
            }, category="healing"),
            StageSpec("Image Tags", StageImageTagHealing, {"fix_tags": config.fix_tags}, category="healing") if config.fix_tags else None,
            StageSpec("RBAC Auditing", StageRBACAuditing, {"harden": config.harden}, category="healing"),
            StageSpec("Privilege Escalation", StagePrivilegeEscalation, {"harden": config.harden}, category="healing"),
            StageSpec("Ingress Security", StageIngressHardening, {"harden": config.harden}, category="healing"),
            StageSpec("Probes", StageProbeInjection, {"enforce_probes": config.enforce_probes}, category="healing") if config.enforce_probes else None,
            StageSpec("Network Policies", StageNetworkPolicyEnforcement, {
                "healer": pipeline.network_policy_healer, "harden": config.harden
            }, category="healing") if config.harden else None,
            StageSpec("Namespace", StageNamespaceEnforcement, {"enforce": config.enforce_namespace}, category="healing") if config.enforce_namespace else None,
            StageSpec("Remediation", StageExternalRemediation, category="healing"),
        ]
        return [s for s in specs if s]

    @staticmethod
    def _get_risk_specs(pipeline: Any, config: "HealConfig") -> List[Any]:
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.judgment import StageJudgment
        from yamlr.core.stages.risk import StageSecurityScoring, StageTenRiskClassification
        from yamlr.core.stages.transformation import StageEightValidationScoring
        
        specs = [
            StageSpec("Validation", StageEightValidationScoring, {"validator": pipeline.schema_validator}, category="risk"),
            StageSpec("Security Scoring", StageSecurityScoring, {"allowed_host_paths": pipeline.allowed_host_paths}, category="risk"),
            StageSpec("Risk Classification", StageTenRiskClassification, category="risk"),
            StageSpec("Judgment", StageJudgment, {"catalog": pipeline.catalog}, category="risk") if getattr(pipeline, "judge", None) else None,
        ]
        return [s for s in specs if s]

    @staticmethod
    def _get_finalization_specs(pipeline: Any, config: "HealConfig") -> List[Any]:
        from yamlr.core.pipeline import StageSpec
        from yamlr.core.stages.audit_receipt import StageElevenAuditReceipt
        from yamlr.core.stages.transformation import StageNineSerialization
        from yamlr.core.stages.vacuum import StageTenVacuum
        
        specs = [
            StageSpec("Serialization", StageNineSerialization, {
                "structurer": pipeline.structurer, "exporter": pipeline.exporter, "compact": config.compact
            }, category="structural"),
            StageSpec("Vacuum", StageTenVacuum, {"enabled": config.compact}, category="structural"),
            StageSpec("Audit Receipt", StageElevenAuditReceipt, category="telemetry") if (config.generate_receipts and config.capabilities.can_generate_evidence) else None,
        ]
        return [s for s in specs if s]

    @staticmethod
    def get_standard_stages(config: "HealConfig", pipeline: any) -> List["PipelineStage"]:
        """Resolves the sequence of stages using the new Plan Specs logic.
        
        Why: Maintains backward compatibility while migrating to the Spec architecture.
        """
        specs = StageRegistry.get_plan_specs("heal", config, pipeline)
        stages = []
        for spec in specs:
            # Instantiate the stage using the spec
            # In Phase 2, this will move to the PipelineExecutor
            if not spec.enabled:
                continue
                
            # Filter out non-config arguments for __init__ based on legacy signatures
            # This is a temporary shim until Stage classes are refactored to take a generic dict or spec
            if spec.config:
                stage = spec.stage_cls(name=spec.name, **spec.config)
            else:
                stage = spec.stage_cls(name=spec.name)
            stages.append(stage)
        
        return stages
