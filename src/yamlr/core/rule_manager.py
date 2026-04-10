from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Centrally enforce hardened loading
from yamlr.core.utils import get_hardened_yaml

hardened_yaml = get_hardened_yaml(typ="safe", pure=True)

logger = logging.getLogger("yamlr.rules")
__all__ = ["RuleManager"]


class RuleManager:
    """
    Central authority for Semantic Rules and Healing Policies.
    Loads definitions from yamlr/core/data/rules.yaml.
    """

    _instance = None
    _rules: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RuleManager, cls).__new__(cls)
        return cls._instance

    @property
    def rules(self) -> Dict[str, Any]:
        """Lazy-loaded rules dictionary."""
        if self._rules is None:
            self._load_definitions()
        return self._rules

    def _load_definitions(self):
        """
        Loads the embedded rules definitions.
        """
        try:
            from yamlr.core.utils import resolve_bundled_asset

            rules_path = resolve_bundled_asset("core/data/rules.yaml")

            if not rules_path or not rules_path.exists():
                logger.error("FATAL: Rule definitions not found. Searched for: core/data/rules.yaml")
                rules_path = Path("core/data/rules.yaml")
                if not rules_path.exists():
                    self._rules = {}
                    return

            with open(rules_path, "r", encoding="utf-8") as f:
                data = hardened_yaml.load(f) or {}
                # Handle both 'rules:' wrapped and direct top-level rules
                self._rules = data.get("rules", data)

            logger.debug(f"Loaded {len(self._rules)} semantic rules.")

        except (OSError, IOError, AttributeError, KeyError) as e:
            logger.error(f"Failed to load rule definitions: {e}")
            self._rules = {}

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a rule by ID."""
        return self.rules.get(rule_id)

    def is_safe_to_autoheal(self, rule_id: str) -> bool:
        """Returns True if the rule is marked safe_to_autoheal."""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        return rule.get("safe_to_autoheal", False)

    def get_stub_template(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the stub template for a rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        return rule.get("stub_template")

    def get_all_rules(self) -> Dict[str, Any]:
        """Returns all loaded rules."""
        return self.rules
