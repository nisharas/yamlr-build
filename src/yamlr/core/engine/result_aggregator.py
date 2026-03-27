#!/usr/bin/env python3
"""
Yamlr RESULT AGGREGATOR
------------------------
Final assembly unit for manifest heal results.
Converts mutated context into a high-fidelity HealResult.
"""

from typing import Any, Dict, Tuple, TYPE_CHECKING
import logging
from yamlr.models import HealResult, HealStatus, PipelineStats

if TYPE_CHECKING:
    from yamlr.core.context import HealContext
    from yamlr.core.pipeline import HealConfig

logger = logging.getLogger("yamlr.engine.aggregator")

class ResultAggregator:
    """
    [THE CLINICAL REPORTER]
    Aggregates stage telemetry and context mutations into the final HealResult.
    Why: Keeps the Pipeline logic focused on orchestration, while this class 
         handles the complex reporting and scoring logic.
    """

    @staticmethod
    def build_result(context: "HealContext", stage_results: Dict[str, Any], config: "HealConfig") -> HealResult:
        """Translates the mutated context and stage telemetry into a HealResult.
        
        Why: Consolidates scoring, DNA hashing, and safety checks into a single pass.
        """
        from yamlr.core.dna_utils import calculate_semantic_dna
        from yamlr.models import HealFileResult
        
        # 1. Scoring & Truth-in-Healing
        phy_val, kbs_val, sem_val = ResultAggregator._calculate_truth_in_healing(context)
        
        
        # Prepare a dummy result to use the model's scoring calculation
        res_obj = HealFileResult(
            file_path=context.file_path, full_path=context.file_path, success=True,
            status="SUCCESS", kind=context.identities[0].kind if context.identities else "Unknown",
            logic_logs=context.audit_log, findings=context.findings, 
            dna_integrity_score=0, identities=[i.to_dict() for i in context.identities],
            phy_status=phy_val, kbs_status=kbs_val, sem_status=sem_val
        )
        final_score = res_obj.calculate_integrity_score()

        # 2. Safety Enforcement
        if final_score < config.safety_threshold:
            context.audit_log.append(f"🛑 CRITICAL: Safety threshold violation ({final_score} < {config.safety_threshold})")
            return HealResult(
                status=HealStatus.FAILED, content=context.raw_text, logs=context.audit_log,
                dna_integrity_score=final_score, identities=context.identities, findings=context.findings,
                error_message=f"Safety threshold violation ({final_score} < {config.safety_threshold})"
            )

        if config.strict_mode:
            errors = [f for f in context.findings if f.severity == "ERROR"]
            if errors:
                return HealResult(
                    status=HealStatus.FAILED, content=context.raw_text, logs=context.audit_log,
                    dna_integrity_score=final_score, identities=context.identities, findings=context.findings,
                    error_message=f"Strict mode violation: {errors[0].message}"
                )

        # 3. Final Assembly
        dna_hash = calculate_semantic_dna(context.raw_text)
        
        return HealResult(
            status=HealStatus.SUCCESS, content=context.raw_text, logs=context.audit_log,
            dna_integrity_score=final_score, identities=context.identities, findings=context.findings,
            stats=context.stats, 
            deprecation_info=[log for log in context.audit_log if "Stage 6.1" in log],
            depth=context.depth, phy_status=phy_val, kbs_status=kbs_val, sem_status=sem_val,
            dna_hash=dna_hash,
            trust_score=getattr(context, "trust_score", 100.0),
            safety_verdict=getattr(context, "safety_verdict", "N/A"),
            safety_messages=getattr(context, "safety_messages", []),
            evidence_receipt=getattr(context, "evidence_receipt", None)
        )

    @staticmethod
    def collect_stage_stats(stage: Any, res: dict, stats: PipelineStats):
        """Aggregates telemetry from stage results into global stats.
        
        Why: To build the final PipelineStats object by summing the repairs 
             and findings identified across all stages.
        """
        s_data = res.get("stats", {})
        if s_data:
            stats.lexer_repairs += s_data.get("lexer_repairs", 0)
            stats.lexer_typos += s_data.get("lexer_typos", 0)
            stats.migrator_changes += s_data.get("migrator_changes", 0)
            stats.semantic_repairs += s_data.get("semantic_repairs", 0)
            stats.security_hardens += s_data.get("security_hardens", 0)
        
        modified = res.get("modified", 0)
        if modified:
            from yamlr.core.stages.healing import (
                StageIngressHardening,
                StagePrivilegeEscalation,
                StageRBACAuditing,
            )
            from yamlr.core.stages.transformation import StageSixOneMigration
            
            # [Security forensics] Multi-stage security telmetry
            is_sec = isinstance(stage, (StagePrivilegeEscalation, StageRBACAuditing, StageIngressHardening))
            if is_sec:
                 stats.security_hardens += modified
            elif isinstance(stage, StageSixOneMigration):
                 stats.migrator_changes += modified
            else:
                 stats.semantic_repairs += modified
        if res.get("typo_count", 0): stats.lexer_typos += res.get("typo_count", 0)

    @staticmethod
    def _calculate_truth_in_healing(context: "HealContext") -> Tuple[str, str, str]:
        """Calculates Truth-in-Healing (Phase 1) status strings."""
        phy_val = "100%"
        findings = context.findings
        v_errs = sum(1 for f in findings if f.rule_id and "schema" in f.rule_id.lower())
        kbs_val = "100%" if v_errs == 0 else f"{max(0, 100 - (v_errs * 10))}%"
        
        # [SEM-FIX] Include forensic and security findings in Semantic Score
        sem_keywords = ["resource", "auditing", "privilege", "ingress"]
        rule_keywords = ["logical", "rule/unsafe", "rule/rbac", "rule/ingress"]
        
        s_errs = sum(1 for f in findings if 
                     (f.analyzer_name and any(x in f.analyzer_name.lower() for x in sem_keywords)) or 
                     (f.rule_id and any(x in f.rule_id.lower() for x in rule_keywords)))
        
        sem_val = "100%" if s_errs == 0 else f"{max(0, 100 - (s_errs * 15))}%"
        return phy_val, kbs_val, sem_val
