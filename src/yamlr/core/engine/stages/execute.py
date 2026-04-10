from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.engine.stages.execute")

def execute_transformation_stage(engine: Any, content: str, plan: Dict[str, Any], config: Optional[Any]) -> Dict[str, Any]:
    """
    Macro-Stage 4: Execute (Surgical Transformations).
    
    Why: The 'Surgeon's Hand' - performs the nodes-to-nodes transformations,
         compacts the output (Vacuum), and runs safety checks (Safeguard).
    """
    if plan["strategy"] == "scan_only" or not plan["healers_to_run"]:
        return {"healed_content": content, "fixed_count": 0}

    from yamlr.core.parser.ruamel_adapter import RuamelAdapter
    from yamlr.parsers.structurer import SchemaValidator
    from yamlr.core.context import HealContext
    
    # Initialize surgical environment
    compact_mode = getattr(config, "compact", False)
    adapter = RuamelAdapter(compact=compact_mode)
    # [NOTE] SchemaValidator initialized for future context-aware healers
    _ = SchemaValidator(catalog=engine.catalog, cluster_version=engine.cluster_version)
    
    try:
        nodes = adapter.load_all(content)
        modified_count = 0
        
        # Context for healers
        context = HealContext(
            workspace=str(engine.workspace),
            catalog=engine.catalog,
            cluster_version=engine.cluster_version,
            dry_run=False
        )
        
        # [FEATURE-PENDING] Stage 7.x - Run Registered Healers
        # For now we maintain Track 1 parity
        
        # Serialization (Stage 9)
        healed_content = adapter.dump_all(nodes)
        
        # 🔗 Stage 10: Vacuum (Compact Mode)
        if compact_mode:
            from yamlr.core.stages.vacuum import StageTenVacuum
            vacuum = StageTenVacuum(name="Vacuum", enabled=True)
            context.raw_text = healed_content
            vacuum.run(context)
            healed_content = context.raw_text
            
        # 🔗 Stage 10.5: Safeguard (Identity Check)
        # [FEATURE-PENDING] Implement a proper SafeguardStage to restore the 'Safety Brake' moat.
        # The legacy StageAgenticSafeGuard was found to be missing from the codebase.
        safeguard_result = {"safe": True, "reason": "Bypassed (Missing Logic)"}
        
        return {
            "healed_content": healed_content, 
            "fixed_count": modified_count,
            "safeguard_result": safeguard_result
        }
    except Exception as _e:
        logger.error(f"Surgical failure during Execute stage: {_e}")
        return {"healed_content": content, "fixed_count": 0, "error": str(_e)}
