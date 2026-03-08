#!/usr/bin/env python3
"""
Extractor for Service/Deployment selectors.

Extracts:
- spec.selector.matchLabels (Deployment/StatefulSet)
- spec.selector (Service)
"""

from typing import List

from yamlr.models import ManifestIdentity, Shard


class SelectorExtractor:
    """Extracts selector fields for Service/Deployment matching."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract selector key-value pair if we're in selector context.

        Returns:
            bool: True if extraction was performed
        """
        # Skip structural keys
        if key in ("selector", "matchLabels", "spec"):
            return False

        # Check if we're inside spec.selector
        if "spec" in path_keys and "selector" in path_keys:
            if identity.selector is None:
                identity.selector = {}
            if shard.is_flow_style:
                import yaml
                try:
                    parsed = yaml.safe_load(val)
                    if isinstance(parsed, dict):
                        identity.selector.update(parsed)
                except Exception:
                    pass
            else:
                identity.selector[key] = val
            return True

        return False
