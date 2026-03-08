import os
import logging
from typing import Dict, Optional, Any
from pathlib import Path

# Use safe standard lib YAML if available or fallback to ruamel
try:
    from yamlr.core.utils import get_hardened_yaml
    yaml = get_hardened_yaml(typ='safe', pure=True)
except ImportError:
    # Fallback to simple parser if strictly needed, but Yamlr implies ruamel
    import yaml

logger = logging.getLogger("yamlr.rules")

class RuleManager:
    """
    Central authority for Semantic Rules and Healing Policies.
    Loads definitions from yamlr/rules/definitions.yaml.
    """
    
    _instance = None
    _rules: Dict[str, Any] = {}
    
    def __new__(cls):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if cls._instance is None:
            cls._instance = super(RuleManager, cls).__new__(cls)
            cls._instance._load_definitions()
        return cls._instance

    def _load_definitions(self):
        """
        Loads the embedded rules definitions.
        """
        try:
            from yamlr.core.utils import resolve_bundled_asset
            rules_path = resolve_bundled_asset("core/data/definitions.yaml")
            
            if not rules_path or not rules_path.exists():
                logger.error(f"FATAL: Rule definitions not found. Searched for: core/data/definitions.yaml")
                # Fallback to current dir if all else fails
                rules_path = Path("core/data/definitions.yaml")
                if not rules_path.exists():
                    self._rules = {}
                    return

            with open(rules_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
                self._rules = data.get('rules', {})
                
            logger.debug(f"Loaded {len(self._rules)} semantic rules.")
            
        except Exception as e:
            logger.error(f"Failed to load rule definitions: {e}")
            self._rules = {}

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self._rules.get(rule_id)

    def is_safe_to_autoheal(self, rule_id: str) -> bool:
        """
        Returns True if the rule is marked safe_to_autoheal.
        Input for --stub-refs flag safety check.
        """
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        return rule.get('safe_to_autoheal', False)

    def get_stub_template(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        return rule.get('stub_template')
    
    def get_all_rules(self) -> Dict[str, Any]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self._rules
