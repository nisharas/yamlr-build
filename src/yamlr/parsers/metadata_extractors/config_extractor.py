#!/usr/bin/env python3
"""
Extractor for ConfigMap/Secret references.

Extracts:
- volumes[].configMap.name
- volumes[].secret.secretName
- env[].valueFrom.configMapKeyRef.name
- envFrom[].configMapRef.name
"""

from typing import List

from yamlr.models import ManifestIdentity, Shard


class ConfigExtractor:
    """Extracts ConfigMap/Secret references from Pod specs."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract ConfigMap/Secret name if in config reference context.

        Returns:
            bool: True if extraction was performed
        """
        # Volume references
        if key in ("name", "secretName"):
            if "volumes" in path_keys:
                if "configMap" in path_keys:
                    if val and val not in identity.config_refs:
                        identity.config_refs.append(val)
                    return True
                if "secret" in path_keys:
                    if val and val not in identity.secret_refs:
                        identity.secret_refs.append(val)
                    if val and val not in identity.secret_volume_refs:
                        identity.secret_volume_refs.append(val)
                    return True

        # Env references
        if key == "name":
            if "env" in path_keys or "envFrom" in path_keys:
                # Differentiate ConfigMap vs Secret
                if "configMapKeyRef" in path_keys or "configMapRef" in path_keys:
                    if val and val not in identity.config_refs:
                        identity.config_refs.append(val)
                    return True
                elif "secretKeyRef" in path_keys or "secretRef" in path_keys:
                    if val and val not in identity.secret_refs:
                        identity.secret_refs.append(val)
                    return True

        return False
