#!/usr/bin/env python3
"""
Referential Healer - Semantic Alignment
-----------------------------------------
Applies auto-correction suggestions for broken ConfigMap, Secret, and PVC references.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.healers.semantic.referential")
__all__ = ["ReferentialHealer"]


class ReferentialHealer:
    """Applies auto-correction for broken cross-resource references."""

    def heal_docs(self, docs: List[Dict[str, Any]], findings: List[Any], context: Optional[HealContext] = None) -> int:
        """Applies suggestions from findings to the documents in-place.

        Why: To resolve broken references automatically based on fuzzy matching.
        """
        from yamlr.core.stages.boundaries import MutationScope
        from yamlr.models import HealAction

        modified_count = 0
        for f in findings:
            if self._should_apply_finding(f):
                if self._apply_finding_to_docs(docs, f):
                    modified_count += 1
                    if context:
                        # Determine scope based on rule
                        scope = MutationScope.SPEC_STORAGE if "volume" in f.rule_id else MutationScope.RELATIONAL
                        new_name = self._extract_suggested_name(f.suggestion)
                        old_name = f.message.split("'")[-2] if "'" in f.message else "unknown"

                        context.prescribe(
                            HealAction(
                                stage="ReferentialHealer",
                                action_type="repair",
                                target=f"{f.resource_kind}/{f.resource_name}",
                                description=f"Repaired broken reference: '{old_name}' -> '{new_name}'",
                                rationale=f"The reference to '{old_name}' was broken (missing or typo). Aligned with nearest match '{new_name}'.",
                                suggestion="Ensure resource names in manifests match their definitions exactly.",
                                severity="warning",
                                rule_id=f.rule_id,
                                scope=scope,
                            )
                        )
        return modified_count

    def _should_apply_finding(self, f: Any) -> bool:
        """Determines if a finding is a candidate for referential repair."""
        if not f.suggestion or "Use " not in f.suggestion:
            return False
        return f.rule_id in ("broken-reference", "broken-volume")

    def _apply_finding_to_docs(self, docs: List[Dict[str, Any]], f: Any) -> bool:
        """Helper to apply a specific finding to the document collection."""
        new_name = self._extract_suggested_name(f.suggestion)
        old_name = f.message.split("'")[-2] if "'" in f.message else None

        if not new_name or not old_name:
            return False

        for doc in docs:
            if doc.get("kind") == f.resource_kind and doc.get("metadata", {}).get("name") == f.resource_name:
                if self._update_ref_in_doc(doc, old_name, new_name):
                    logger.info(
                        f"✨ Referential Repair: {f.resource_kind}/{f.resource_name} ref '{old_name}' → '{new_name}'"
                    )
                    return True
        return False

    def _extract_suggested_name(self, suggestion: str) -> Optional[str]:
        """Parses the suggested resource name from the suggestion string."""
        match = re.search(r"'(.*?)'", suggestion)
        return match.group(1) if match else None

    def _update_ref_in_doc(self, doc: Dict[str, Any], old_name: str, new_name: str) -> bool:
        """Deep search and replace of the reference name in the doc."""
        self._tmp_changed = False
        self._recursive_replace(doc, old_name, new_name, lambda: setattr(self, "_tmp_changed", True))
        return getattr(self, "_tmp_changed", False)

    def _recursive_replace(self, obj: Any, old: str, new: str, mark_changed: Any):
        """Helper to recursively find and replace strings."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v == old:
                    if any(x in k.lower() for x in ("name", "claimname", "configmap", "secret")):
                        obj[k] = new
                        mark_changed()
                else:
                    self._recursive_replace(v, old, new, mark_changed)
        elif isinstance(obj, list):
            for item in obj:
                self._recursive_replace(item, old, new, mark_changed)
