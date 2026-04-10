#!/usr/bin/env python3
"""
Yamlr Sorting Engine
--------------------
Provides schema-aware field prioritization for Kubernetes manifests.
Standardizes layout to match Google-quality aesthetics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class SortingEngine:
    """
    The 'Aesthetic Architect': Ensures keys appear in the expected order.

    Why: Consistent key ordering reduces Git diff noise and improves
         human readability (e.g., apiVersion/kind always at top).
    """

    def __init__(self, custom_priority: Optional[Dict[str, int]] = None):
        """
        Initialize the engine with optional user-defined priorities.
        """
        self.custom_priority = custom_priority or {}

    # Global priorities for all Kubernetes resources
    GLOBAL_PRIORITY: Dict[str, int] = {
        "apiVersion": 10,
        "kind": 20,
        "metadata": 30,
        "type": 35,  # For Secrets/Services
        "spec": 40,
        "data": 45,  # For ConfigMaps/Secrets
        "stringData": 46,
        "status": 500,  # Always at the bottom
    }

    # Resource-specific priorities for common types
    KIND_PRIORITY: Dict[str, Dict[str, int]] = {
        "Service": {
            "selector": 41,
            "ports": 42,
            "clusterIP": 43,
            "type": 35,
        },
        "Deployment": {
            "replicas": 41,
            "selector": 42,
            "template": 43,
            "strategy": 44,
        },
        "Pod": {
            "containers": 41,
            "volumes": 45,
            "restartPolicy": 46,
        },
        "Ingress": {
            "ingressClassName": 33,
            "rules": 41,
            "tls": 42,
        },
        "ConfigMap": {
            "data": 45,
            "binaryData": 46,
        },
        "Secret": {
            "type": 35,
            "data": 45,
            "stringData": 46,
        },
        "Role": {
            "rules": 41,
        },
        "ClusterRole": {
            "rules": 41,
        },
        "RoleBinding": {
            "roleRef": 41,
            "subjects": 42,
        },
        "ClusterRoleBinding": {
            "roleRef": 41,
            "subjects": 42,
        },
    }

    def get_priority(
        self,
        key: str,
        kind: Optional[str] = None,
        required_fields: Optional[List[str]] = None,
        original_keys: Optional[List[str]] = None,
    ) -> int:
        """
        Returns a sort weight for a given key. Lower is higher in the file.

        [PRO-ENHANCEMENT] Logic from SchemaAwareSorter merged here.
        """
        # 1. Custom User Priority (Highest Precedence - Legacy Parity)
        if key in self.custom_priority:
            return self.custom_priority[key]

        # 2. Core Identity (always first if not overridden)
        if key == "apiVersion":
            return 10
        if key == "kind":
            return 20
        if key == "metadata":
            return 30

        # 3. Schema-aware 'required' fields get boosted
        if required_fields and key in required_fields:
            return 32 + (required_fields.index(key) if key in required_fields else 0)

        # 4. Kind-specific priorities
        if kind and kind in self.KIND_PRIORITY and key in self.KIND_PRIORITY[kind]:
            return self.KIND_PRIORITY[kind][key]

        # 5. Global priorities
        if key in self.GLOBAL_PRIORITY:
            return self.GLOBAL_PRIORITY[key]

        # 6. Default priority (preserve original order if possible, with alphabetical tie-break)
        if original_keys and key in original_keys:
            # We use a large base (1000) but add an alphabetical component to ensure
            # that even if original_keys is somehow unstable, this is deterministic.
            return 1000 + original_keys.index(key)

        return 2000

    def sort_keys(
        self,
        keys: List[str],
        kind: Optional[str] = None,
        validator: Optional[Any] = None,
        catalog: Optional[Dict] = None,
    ) -> List[str]:
        """
        Sorts keys based on global and kind-specific priorities.
        """
        required_fields = self._get_required_fields(kind, validator, catalog)
        # Sort by (priority, alphabetical_name) for 100% determinism
        return sorted(keys, key=lambda k: (self.get_priority(k, kind, required_fields, keys), str(k)))

    def _get_required_fields(self, kind: Optional[str], validator: Optional[Any], catalog: Optional[Dict]) -> List[str]:
        """Helper to extract required fields from schema sources."""
        if not kind:
            return []
        required_fields = []

        if validator:
            required_fields.extend(self._get_required_from_validator(kind, validator))

        if catalog:
            required_fields.extend(self._get_required_from_catalog(kind, catalog))

        return list(dict.fromkeys(required_fields))

    def _get_required_from_validator(self, kind: str, validator: Optional[Any]) -> List[str]:
        """Discovery logic for validator-based required fields."""
        from yamlr.models import RESOURCE_CATALOG

        primary_api = RESOURCE_CATALOG.get(kind)
        def_key = validator.get_resource_definition(primary_api, kind) if primary_api else None

        if not def_key:
            # Dynamic discovery (skipping the one we already tried)
            other_apis = sorted([a for a in set(RESOURCE_CATALOG.values()) if a != primary_api])
            for api in other_apis:
                def_key = validator.get_resource_definition(api, kind)
                if def_key:
                    break

        if def_key and hasattr(validator, "schema"):
            definitions = validator.schema.get("definitions", {})
            definition = definitions.get(def_key, {})
            # Handle pointer resolution ($ref)
            if "$ref" in definition:
                ref = definition["$ref"].split("/")[-1]
                definition = definitions.get(ref, {})
            return definition.get("required", [])
        return []

    def _get_required_from_catalog(self, kind: str, catalog: Dict) -> List[str]:
        """Discovery logic for catalog-based required fields."""
        required = []
        for k, cat_entry in catalog.items():
            cat_kind = k[1] if isinstance(k, tuple) else k
            if kind == cat_kind and isinstance(cat_entry, dict):
                required.extend(cat_entry.get("required", []))
        return required

    def _get_nested_required_fields(
        self, path: str, validator: Optional[Any], definition_key: Optional[str]
    ) -> List[str]:
        """Helper to extract required fields for a sub-path in the schema."""
        if not validator or not path or not definition_key:
            return []

        # [PHASE 10] Recursive Boosting for Parity
        definition = validator.get_definition_for_path(definition_key, path)
        if definition and isinstance(definition, dict):
            return definition.get("required", [])

        return []

    def reorder_node(
        self,
        node: Any,
        kind: Optional[str] = None,
        validator: Optional[Any] = None,
        catalog: Optional[Dict] = None,
        path: str = "",
        definition_key: Optional[str] = None,
    ):
        """Recursively reorders a YamlrNode based on priorities."""
        if not hasattr(node, "keys") or not hasattr(node, "move_to_end"):
            return

        kind = kind or (node.get("kind") if hasattr(node, "get") else None)

        # Resolve definition key if at root
        if not path and not definition_key and validator and kind:
            api_version = node.get("apiVersion")
            if api_version:
                definition_key = validator.get_resource_definition(api_version, kind)

        original_keys = list(node.keys())

        # [PARITY] Use path-based required fields for nested sorting
        if path:
            required_fields = self._get_nested_required_fields(path, validator, definition_key)
        else:
            required_fields = self._get_required_fields(kind, validator, catalog)

        sorted_keys = sorted(
            original_keys, key=lambda k: (self.get_priority(k, kind, required_fields, original_keys), str(k))
        )

        if original_keys != sorted_keys:
            for key in sorted_keys:
                node.move_to_end(key, last=True)

        self._reorder_children(node, kind, validator, catalog, path, definition_key)

    def _reorder_children(
        self,
        node: Any,
        kind: Optional[str],
        validator: Optional[Any],
        catalog: Optional[Dict],
        path: str = "",
        definition_key: Optional[str] = None,
    ):
        """Helper for recursive sorting of child nodes."""
        for key in node.keys():
            try:
                val = node[key]
                new_path = f"{path}.{key}" if path else key

                if hasattr(val, "is_map") and val.is_map:
                    self.reorder_node(val, kind, validator, catalog, new_path, definition_key)
                elif hasattr(val, "is_seq") and val.is_seq:
                    self._reorder_sequence_items(val, kind, validator, catalog, new_path, definition_key)
            except (KeyError, TypeError):
                continue

    def _reorder_sequence_items(
        self,
        sequence: Any,
        kind: Optional[str],
        validator: Optional[Any],
        catalog: Optional[Dict],
        path: str = "",
        definition_key: Optional[str] = None,
    ):
        """Helper to reorder maps inside a sequence."""
        for item in sequence:
            if hasattr(item, "is_map") and item.is_map:
                self.reorder_node(item, kind, validator, catalog, path, definition_key)
