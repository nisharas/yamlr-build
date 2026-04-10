from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.engine.stages.plan")

def execute_plan_stage(_engine: Any, _config: Optional[Any], _ingest_data: Dict[str, Any], analyze_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Macro-Stage 3: Plan (Strategy Generation).
    
    Why: Determines the optimal healing strategy based on analysis results and tier capabilities.
    """
    from yamlr.core.gatekeeper import LicenseGate
    
    findings = analyze_data.get("findings", [])
    capabilities = LicenseGate.get_capabilities()
    
    # Risk Assessment & Deduplication
    plan = {
        "strategy": "full_heal" if not (_config and getattr(_config, "skip_repair", False)) else "scan_only",
        "healers_to_run": [],
        "risk_score": 0,
        "capabilities": capabilities,
        "deduplicated_findings": findings 
    }
    
    if plan["strategy"] == "full_heal":
        # Map findings to required healers + Capability Gating
        if any(f.rule_id and f.rule_id.startswith("schema/") for f in findings):
            # Structural healing is a CORE feature (Free)
            plan["healers_to_run"].append("structural")
            
        if any(f.rule_id and f.rule_id.startswith("security/") for f in findings):
            # Security hardening is a PRO feature
            if capabilities.has_unlimited_quota or LicenseGate.is_feature_allowed("security_hardening"):
                plan["healers_to_run"].append("security")
            else:
                logger.info("Security hardening requested but not available in the current tier.")
        
        # Always run cleanup (Core feature)
        plan["healers_to_run"].append("cleanup")
        
    return plan
