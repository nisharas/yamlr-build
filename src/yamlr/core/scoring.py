from __future__ import annotations
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from yamlr.analyzers.rules import Rules, RuleCategory

__all__ = ['Severity', 'ScoringEngine', 'AppSafetySummary', 'AppSafetyReport', 'ScoringConfig']


class Severity(Enum):
    """Enumeration of violation severity levels and their base scoring values."""
    INFO = 100
    WARNING = 200
    ERROR = 300


class ScoringConfig(BaseModel):
    """Configuration for the Scoring Engine.
    
    Why: To allow enterprise users to tune penalty weights and track scoring 
         evolutions via versioning.
    """
    version: int = Field(default=1, alias="scoring_version")
    penalties: Dict[str, int] = Field(default_factory=dict)
    blast_radius_multiplier: float = 1.5

    class Config:
        populate_by_name = True


class AppSafetySummary(BaseModel):
    """Consolidated safety metrics for a specific application."""
    app_name: str
    score: float = 100.0
    top_categories: List[str] = Field(default_factory=list)
    top_rules: List[str] = Field(default_factory=list)
    findings_count: int = 0
    detailed_findings: List[Dict[str, Any]] = Field(default_factory=list)


class AppSafetyReport(BaseModel):
    """Global report containing safety summaries for all apps in the workspace."""
    apps: List[AppSafetySummary] = Field(default_factory=list)
    overall_score: float = 100.0
    scoring_version: int = 1


class ScoringEngine:
    """
    Centralized service for calculating manifest health scores.
    """
    
    # Shipped Defaults (Tier 0)
    DEFAULT_PENALTIES = {
        "LEX_FLUSH_LEFT": 2,
        "LEX_QUOTE_ERR": 3,
        "LEX_SPACING": 1,
        Rules.SCHEMA_MISMATCH: 5,
        Rules.GHOST_SERVICE: 10,
        Rules.ORPHAN_RESOURCE: 3,
        Rules.BROKEN_VOLUME: 15,
        Rules.RBAC_WILDCARD: 15,
        Rules.RBAC_PRIVILEGE_ESCALATION: 25,
        "BEST_PRACTICE_WARN": 3,
        "BEST_PRACTICE_ERR": 10,
    }

    def __init__(self, config: Optional[ScoringConfig] = None):
        self.config = config or ScoringConfig(penalties=self.DEFAULT_PENALTIES)

    def calculate_penalty(self, rule_id: str, severity: str = "WARNING", has_blast_impact: bool = False) -> int:
        """
        Returns the deduction points for a specific rule violation.
        
        Why: To provide a deterministic, config-aware penalty calculation.
        """
        sev = severity.upper()
        
        # 1. Config override -> 2. Default mapping -> 3. Severity fallback
        penalty = self.config.penalties.get(rule_id)
        if penalty is None:
            penalty = self.DEFAULT_PENALTIES.get(rule_id)
        
        if penalty is None:
            if sev == "CRITICAL":
                penalty = 25
            elif sev in ("ERROR", "HIGH"):
                penalty = 10
            elif sev in ("WARNING", "MEDIUM"):
                penalty = 3
            else:
                penalty = 0

        # Apply Blast Radius Multiplier if applicable
        if has_blast_impact:
            penalty = int(penalty * self.config.blast_radius_multiplier)
            
        return penalty

    def generate_app_report(self, app_results: Dict[str, List[Any]]) -> AppSafetyReport:
        """
        Aggregates findings per app and generates a global safety report.
        
        Why: To provide the 'App Safety Score' headline metric for IDPs and CI.
        """
        summaries = []
        total_score_sum = 0
        
        for app_name, results in app_results.items():
            score = 100.0
            category_penalties: Dict[RuleCategory, int] = {}
            rule_penalties: Dict[str, int] = {}
            total_findings = 0
            detailed_findings: List[Dict[str, Any]] = []
            
            for result in results:
                # Support both HealFileResult objects and dicts
                findings = result.get("findings", []) if isinstance(result, dict) else getattr(result, "findings", [])
                total_findings += len(findings)
                
                # Check for blast impact (traffic path to Ingress)
                has_blast = result.get("is_on_critical_path", False) if isinstance(result, dict) else getattr(result, "is_on_critical_path", False)
                
                for f in findings:
                    # Robust attribute extraction (finding can be AnalysisResult obj or dict)
                    if isinstance(f, dict):
                        rid = f.get("rule_id", "unknown")
                        sev = f.get("severity", "WARNING")
                    else:
                        rid = getattr(f, "rule_id", "unknown")
                        sev = getattr(f, "severity", "WARNING")
                        
                    points = self.calculate_penalty(rid, sev, has_blast_impact=has_blast)
                    
                    score -= points
                    
                    # Track categories
                    cat = Rules.get_category(rid)
                    category_penalties[cat] = category_penalties.get(cat, 0) + points
                    
                    # Track rule contributors
                    rule_penalties[rid] = rule_penalties.get(rid, 0) + points
                    
                    # [Round 13] Collect detailed context for IDP alerts
                    f_detail = {
                        "rule_id": rid,
                        "severity": sev,
                        "message": f.get("message", "") if isinstance(f, dict) else getattr(f, "message", ""),
                        "line": f.get("line_no", 0) if isinstance(f, dict) else getattr(f, "line_no", 0),
                        "col": f.get("column_no", 0) if isinstance(f, dict) else getattr(f, "column_no", 0),
                        "file": result.get("file_path", "") if isinstance(result, dict) else getattr(result, "file_path", "")
                    }
                    if len(detailed_findings) < 50: # Cap per app to prevent payload bloat
                        detailed_findings.append(f_detail)
            
            # Clamp score
            score = max(0.0, score)
            
            # Sort categories and rules by impact
            top_cats = sorted(category_penalties.items(), key=lambda x: x[1], reverse=True)[:3]
            top_rids = sorted(rule_penalties.items(), key=lambda x: x[1], reverse=True)[:3]
            
            summaries.append(AppSafetySummary(
                app_name=app_name,
                score=score,
                top_categories=[c[0].value for c in top_cats],
                top_rules=[r[0] for r in top_rids],
                findings_count=total_findings,
                detailed_findings=sorted(detailed_findings, key=lambda x: x["line"])[:10] if 'detailed_findings' in locals() else []
            ))
            total_score_sum += score
            
        overall = total_score_sum / len(summaries) if summaries else 100.0
        return AppSafetyReport(
            apps=summaries,
            overall_score=overall,
            scoring_version=self.config.version
        )

    @staticmethod
    def get_severity_label(severity: str) -> str:
        """Normalizes severity labels."""
        return severity.upper()
