#!/usr/bin/env python3
"""
Yamlr Enterprise (Pro) SURGERY
------------------------
Houses advanced, monetized epistemic and structural repair algorithms that
were previously available in the OSS version.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger("yamlr.pro.surgery")
__all__ = ["ProSurgeon"]


class ProSurgeon:
    """Enterprise-only structural Yamlr operations."""

    @staticmethod
    def invert_structure(val: Any, field_name: str, dot_path: str = "") -> Any:
        """
        [Deep Healing] Inverts a nested map into a K8s-compliant list.
        Example: env: { KEY: VAL } -> env: [{name: KEY, value: VAL}]
        Handles: env, ports, volumeMounts, volumeDevices.
        """
        from yamlr.core.parser.base import YamlrNode

        # If not a map-like thing, we can't invert it
        if not (isinstance(val, (dict, YamlrNode)) and (not hasattr(val, "is_map") or val.is_map)):
            return val

        field = field_name.lower()
        items = val.items() if hasattr(val, "items") else val.items()
        flattened = []

        for k, v in items:
            node = {"name": k}

            # Context-Aware Inversion
            if field == "env":
                node["value"] = str(v)
            elif field == "ports":
                # Handle cases like "8080: TCP" or just "8080"
                if isinstance(v, (int, str)):
                    try:
                        node["containerPort"] = int(k)
                        node["protocol"] = str(v).upper() if isinstance(v, str) else "TCP"
                        del node["name"]  # Ports usually don't have name as the key
                    except ValueError:
                        node["containerPort"] = v if isinstance(v, int) else 8080
                elif isinstance(v, dict):
                    v_dict = v.to_dict() if hasattr(v, "to_dict") else dict(v)
                    node.update(v_dict)
            elif "mount" in field or "device" in field:
                node["mountPath"] = v if isinstance(v, str) else k
            else:
                # Generic Inversion (Key as 'name', Value as 'value')
                if isinstance(v, (dict, YamlrNode)):
                    v_dict = v.to_dict() if hasattr(v, "to_dict") else dict(v)
                    node.update(v_dict)
                else:
                    node["value"] = v

            flattened.append(node)

        if flattened:
            logger.info(f"🔄 Structure Inversion: {field_name} at {dot_path}")
            return flattened

        return val

    @staticmethod
    def cast_to_array(val: Any, dot_path: str, key: str) -> Any:
        # Try inversion first (handles maps -> lists)
        inverted = ProSurgeon.invert_structure(val, key, dot_path)
        if inverted is not val:
            return inverted

        # If still a scalar (or something not a list), wrap it
        if not isinstance(val, list) and not (hasattr(val, "is_seq") and val.is_seq):
            # Specific logic for common K8s object-arrays (like imagePullSecrets)
            # Note: If the user just gave a scalar, we often wrap it in a list.
            # If it's a field like imagePullSecrets, we technically need [{name: val}]
            # but to maintain compatibility with the healer's expectations:
            if key in {"imagePullSecrets"}:
                return [{"name": val}]
            return [val]
        return val
