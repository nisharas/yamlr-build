import logging
import copy
from typing import List, Dict, Any, Union
from yamlr.core.rule_manager import RuleManager

logger = logging.getLogger("yamlr.healers.semantic.missing_target")

class MissingTargetHealer:
    """
    Implements the 'Two-Tier' healing logic:
    1. Warning (Default)
    2. Stub (Opt-in via --stub-refs)
    3. Prune (Opt-in via --prune-refs) - *Future*
    """
    
    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.rules = RuleManager()

    def heal(self, candidates: List[Dict[str, Any]], cli_flags: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes missing resource candidates and generates stubs.
        
        Args:
            candidates: List of missing resource dicts (from RefResolver).
            cli_flags: Parsed CLI args (stub_refs, unsafe, etc.)
            
            
        Returns:
            Tuple[List[Dict[str, Any]], List[str]]: (New Resources, Suggestion Logs)
        """
        generated_resources = []
        suggestions = []
        processed_keys = set() # Avoid duplicates (e.g. 5 deployments missing 'web-config', stub it once)
        
        stub_flag = cli_flags.get('stub_refs', False)
        unsafe_flag = cli_flags.get('unsafe', False)
        
        # Early return removed to allow analysis/logging of missing items
        # if not stub_flag:
        #    return []

        for issue in candidates:
            rule_id = issue['rule_id']
            missing_name = issue['name']
            kind = issue['kind']
            
            # Unique key for deduplication
            resource_key = f"{kind}/{missing_name}"
            if resource_key in processed_keys:
                continue
                
            # 1. Safety Check
            is_safe = self.rules.is_safe_to_autoheal(rule_id)
            
            # 2. Determine Scope
            should_heal = False
            
            # --- Logic Table ---
            # Safe Res | --stub-refs (True) | Heal? Yes.
            # Safe Res | --stub-refs (List) | Heal if Kind in List.
            # Unsafe   | --unsafe (False)   | Heal? NO.
            # Unsafe   | --unsafe (True)    | Heal? Yes.
            # Unsafe   | --unsafe (List)    | Heal if Kind in List.
            
            # Check A: Is it Safe?
            if is_safe:
                # If stub_refs is a boolean True -> Yes
                if isinstance(stub_flag, bool) and stub_flag:
                    should_heal = True
                # If stub_refs is a list (String CSV), check content
                elif isinstance(stub_flag, str):
                    targets = [t.strip().lower() for t in stub_flag.split(',')]
                    if kind.lower() in targets:
                        should_heal = True
                
                # [Optimization] Log Suggestion if safe but not enabled
                if not should_heal:
                    msg = f"Missing {kind}/{missing_name} detected. Use --stub-refs to auto-heal."
                    suggestions.append(msg)
                    logger.warning(msg)
            
            # Check B: Unsafe Override?
            # Even if Safe check failed (or wasn't applicable), Unsafe args can force it?
            # Actually, Unsafe is ADDITIVE.
            # If it's UNSAFE, we require Unsafe flag.
            if not is_safe:
                if isinstance(unsafe_flag, bool) and unsafe_flag:
                    should_heal = True
                elif isinstance(unsafe_flag, str):
                     targets = [t.strip().lower() for t in unsafe_flag.split(',')]
                     if kind.lower() in targets:
                         should_heal = True
                else:
                    # Unsafe resource, no unsafe flag -> Skip
                    # Only log if we haven't already decided to heal (unlikely unless logic changes)
                    if not should_heal:
                        msg = f"Skipping unsafe heal for {kind}/{missing_name} (sensitive). Use --unsafe to stub."
                        suggestions.append(msg)
                        logger.warning(msg)
                    continue

            # 3. Apply Healing
            if should_heal:
                template = self.rules.get_stub_template(rule_id)
                if template:
                    stub = copy.deepcopy(template)
                    # Simple Substitution (No dependency on Jinja2 for zero-dep)
                    stub['metadata']['name'] = missing_name
                    if 'namespace' in issue and issue['namespace'] != 'default':
                        stub['metadata']['namespace'] = issue['namespace']
                        
                    # 4. Safety Marking (TASK-16-6)
                    if not is_safe:
                        stub['metadata'].setdefault('annotations', {})['yamlr.dev/safety'] = "UNSAFE"
                        logger.warning(f"⚠️  INJECTING UNSAFE STUB: {kind}/{missing_name}. Verify authentication/data manually.")
                        suggestions.append(f"CRITICAL: {kind}/{missing_name} is a sensitive resource. Stub is marked UNSAFE.")

                    generated_resources.append(stub)
                    processed_keys.add(resource_key)
                    logger.info(f"Generated Stub: {kind}/{missing_name}")
                else:
                    logger.warning(f"No stub template for rule {rule_id}")

        return generated_resources, suggestions
