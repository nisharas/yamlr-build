import logging
import copy
from typing import List, Dict, Any, Union, Optional, Tuple, TYPE_CHECKING
from yamlr.core.rule_manager import RuleManager

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.semantic.missing_target")
__all__ = ['MissingTargetHealer']


class MissingTargetHealer:
    """
    Implements the 'Two-Tier' healing logic:
    1. Warning (Default)
    2. Stub (Opt-in via --stub-refs)
    3. Prune (Opt-in via --prune-refs) - *Future*
    """
    
    def __init__(self):
        """Initializes the missing target healer with a rule manager.
        
        Why: To manage the templates and safety policies required for generating resource stubs.
        """
        self.rules = RuleManager()

    def heal(self, candidates: List[Union[Dict[str, Any], "AnalysisResult"]], cli_flags: Dict[str, Any], context: Optional["HealContext"] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Processes missing resource candidates and generates stubs.
        
        Why: Decomposed to resolve SonarQube complexity warnings per Audit Round 24.
             Updated in Round 29 to handle both raw dicts and AnalysisResult objects.
        """
        generated_resources = []
        suggestions = []
        processed_keys = set()
        
        stub_flag = cli_flags.get('stub_refs', False)
        unsafe_flag = cli_flags.get('unsafe', False)
        
        for issue in candidates:
            # Normalize issue to a standard dict for internal processing
            norm_issue = self._normalize_issue(issue)
            if not norm_issue: continue
            
            kind = norm_issue["kind"]
            name = norm_issue["name"]
            resource_key = f"{kind}/{name}"
            
            if resource_key in processed_keys:
                continue
                
            if self._should_heal_resource(norm_issue, stub_flag, unsafe_flag, suggestions):
                stub = self._generate_stub(norm_issue)
                if stub:
                    generated_resources.append(stub)
                    processed_keys.add(resource_key)
                    if context:
                        from yamlr.models import HealAction
                        from yamlr.core.stages.boundaries import MutationScope
                        context.prescribe(HealAction(
                            stage="MissingTargetHealer",
                            action_type="stub",
                            target=resource_key,
                            description=f"Injected Ghost Resource stub for {resource_key}",
                            rationale=f"The required resource '{resource_key}' is missing from the workspace. Injected a safe stub to maintain pipeline stability.",
                            suggestion="Ensure all referenced resources (ConfigMaps, Secrets, PVCs) are included in the manifest collection.",
                            severity="warning",
                            rule_id="rule/ghost-resource",
                            scope=MutationScope.RELATIONAL
                        ))
                        
        return generated_resources, suggestions

    def _normalize_issue(self, issue: Union[Dict, Any]) -> Optional[Dict[str, Any]]:
        """Converts diverse issue formats (dict, AnalysisResult) into a standard healer dict."""
        if isinstance(issue, dict):
            # Already a dict (likely from old CrossResourceDetectors or high-speed path)
            return {
                "kind": issue.get("kind"),
                "name": issue.get("name"),
                "rule_id": issue.get("rule_id", "broken-reference"),
                "namespace": issue.get("namespace", "default"),
                "resource_kind": issue.get("resource_kind", "unknown"),
                "resource_name": issue.get("resource_name", "unknown")
            }
        
        # Assume AnalysisResult object
        fix_id = getattr(issue, "fix_id", "")
        if fix_id and ":" in fix_id:
            try:
                kind, name, namespace = fix_id.split(":")
                return {
                    "kind": kind,
                    "name": name,
                    "rule_id": getattr(issue, "rule_id", "broken-reference"),
                    "namespace": namespace,
                    "resource_kind": getattr(issue, "resource_kind", "unknown"),
                    "resource_name": getattr(issue, "resource_name", "unknown")
                }
            except ValueError:
                pass
        
        # Final Fallback
        return {
            "kind": getattr(issue, "resource_kind", "unknown"),
            "name": getattr(issue, "resource_name", "unknown"),
            "rule_id": getattr(issue, "rule_id", "broken-reference"),
            "namespace": "default",
            "resource_kind": "unknown",
            "resource_name": "unknown"
        }

    def _should_heal_resource(self, issue: Dict[str, Any], stub_flag: Any, unsafe_flag: Any, suggestions: List[str]) -> bool:
        """Determines if a resource should be auto-healed based on safety and flags."""
        rule_id = issue['rule_id']
        kind = issue['kind']
        name = issue['name']
        
        is_safe = self.rules.is_safe_to_autoheal(rule_id)
        
        if is_safe:
            if self._check_flag_match(stub_flag, kind):
                return True
            msg = f"Missing {kind}/{name} detected. Use --stub-refs to auto-heal."
            suggestions.append(msg)
            logger.warning(msg)
            return False
            
        # Unsafe check
        if self._check_flag_match(unsafe_flag, kind):
            return True
            
        msg = f"Skipping unsafe heal for {kind}/{name} (sensitive). Use --unsafe to stub."
        suggestions.append(msg)
        logger.warning(msg)
        return False

    def _check_flag_match(self, flag: Any, kind: str) -> bool:
        """Checks if a boolean or CSV flag matches the given kind."""
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            targets = [t.strip().lower() for t in flag.split(',')]
            return kind.lower() in targets
        return False

    def _generate_stub(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generates a stub resource from template."""
        rule_id = issue['rule_id']
        
        template = self.rules.get_stub_template(rule_id)
        if not template:
            # Fallback for dynamic types if no specific template exists
            template = self.rules.get_stub_template("generic")
            if not template:
                  logger.warning(f"No stub template for rule {rule_id}")
                  return None
            
        stub = copy.deepcopy(template)
        stub['metadata']['name'] = issue['name']
        stub['kind'] = issue['kind'] # Ensure kind matches the missing resource
        
        if issue.get('namespace') and issue['namespace'] != 'default':
            stub['metadata']['namespace'] = issue['namespace']
            
        # Safety Marking
        if not self.rules.is_safe_to_autoheal(rule_id):
            stub['metadata'].setdefault('annotations', {})['yamlr.dev/safety'] = "UNSAFE"
            logger.warning(f"⚠️  INJECTING UNSAFE STUB: {issue['kind']}/{issue['name']}. Verify authentication/data manually.")
        
        logger.info(f"Generated Stub: {issue['kind']}/{issue['name']}")
        return stub
