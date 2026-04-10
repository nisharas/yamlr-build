"""
Schema catalog management for Kubernetes resources.
Extracted from scanner.py to improve maintainability.
"""

from __future__ import annotations

import difflib
import time
from typing import Any, Dict, List, Optional, Set


class SchemaManager:
    """
    Manages K8s schema catalogs and validation.
    """

    CACHE_TTL = 3600  # 1 hour default

    def __init__(
        self,
        catalog: Optional[Dict[Any, Any]] = None,
        openapi_catalog: Optional[Dict[Any, Any]] = None,
        crd_catalog: Optional[Dict[Any, Any]] = None,
        plugin_catalogs: Optional[List[Dict[Any, Any]]] = None,
    ):
        self.catalog = catalog or {}
        self.openapi_catalog = openapi_catalog
        self.crd_catalog = crd_catalog
        self.plugin_catalogs = plugin_catalogs or []

        self._last_built = time.time()
        self.known_structure_keys = self._build_structure_keys()

    def refresh_if_stale(self):
        """Rebuilds keys if TTL expired."""
        if time.time() - self._last_built > self.CACHE_TTL:
            self.known_structure_keys = self._build_structure_keys()
            self._last_built = time.time()

        logger.debug(
            f"SchemaManager initialized with {len(self.known_structure_keys)} "
            f"structure keys from {self._count_catalog_sources()} source(s)"
        )

    def _count_catalog_sources(self) -> int:
        """Count number of active catalog sources."""
        count = 1  # Primary catalog always counts
        if self.openapi_catalog:
            count += 1
        if self.crd_catalog:
            count += 1
        count += len(self.plugin_catalogs)
        return count

    def _build_structure_keys(self) -> Set[str]:
        """
        Builds a comprehensive set of known structure keys from all schema sources.

        This is the core of the scanner's intelligence - it knows what fields are
        important by combining knowledge from multiple sources:
        1. Core K8s fields (hardcoded, always valid)
        2. Common nested fields (containers, volumes, etc.)
        3. K8s catalog-derived fields (from schema definitions)
        4. OpenAPI catalog-derived fields (future expansion)
        5. CRD catalog-derived fields (custom resources)
        6. Plugin catalog-derived fields (user extensions)

        Returns:
            Set of all recognized structural keys across all schema types
        """
        # Core K8s fields - these are ALWAYS valid for Kubernetes manifests
        core_keys = {
            "apiVersion",
            "kind",
            "metadata",
            "spec",
            "status",
            "data",
            "name",
            "namespace",
            "labels",
            "annotations",
            "finalizers",
            "ownerReferences",
            "resourceVersion",
            "generation",
            "uid",
            "creationTimestamp",
            "deletionTimestamp",
        }

        # Nested keys - these appear frequently in specs
        nested_keys = {
            # Container-related
            "containers",
            "initContainers",
            "ephemeralContainers",
            "image",
            "imagePullPolicy",
            "imagePullSecrets",
            "command",
            "args",
            "workingDir",
            "ports",
            "port",
            "containerPort",
            "hostPort",
            "protocol",
            "env",
            "envFrom",
            "valueFrom",
            # Volume-related
            "volumes",
            "volumeMounts",
            "volumeDevices",
            "mountPath",
            "subPath",
            "readOnly",
            "configMap",
            "secret",
            "configMapRef",
            "secretRef",
            "configMapKeyRef",
            "secretKeyRef",
            "persistentVolumeClaim",
            "emptyDir",
            "hostPath",
            "nfs",
            "csi",
            # Resource management
            "resources",
            "limits",
            "requests",
            "cpu",
            "memory",
            "storage",
            "ephemeral-storage",
            # Networking
            "service",
            "clusterIP",
            "externalIPs",
            "loadBalancerIP",
            "sessionAffinity",
            "externalTrafficPolicy",
            "targetPort",
            "nodePort",
            # Security
            "securityContext",
            "runAsUser",
            "runAsGroup",
            "fsGroup",
            "capabilities",
            "privileged",
            "allowPrivilegeEscalation",
            "readOnlyRootFilesystem",
            "runAsNonRoot",
            # Probes
            "livenessProbe",
            "readinessProbe",
            "startupProbe",
            "initialDelaySeconds",
            "periodSeconds",
            "successThreshold",
            "failureThreshold",
            "timeoutSeconds",
            # Common spec fields
            "replicas",
            "selector",
            "matchLabels",
            "matchExpressions",
            "template",
            "strategy",
            "type",
            "rules",
            "subjects",
            "roleRef",
            "apiGroups",
            "verbs",
        }

        # Deterministic accumulation prevents Kind collisions during scans.
        # Priority: Core > Primary > OpenAPI > Plugins > CRDs
        all_keys = core_keys | nested_keys

        if self.catalog:
            all_keys |= self._extract_keys_from_catalog(self.catalog)

        if self.openapi_catalog:
            # OpenAPI takes priority over generic CRDs
            all_keys |= self._extract_openapi_keys(self.openapi_catalog)

        for plugin_catalog in self.plugin_catalogs or []:
            if isinstance(plugin_catalog, dict):
                all_keys |= self._extract_keys_from_catalog(plugin_catalog)

        if self.crd_catalog:
            # CRDs are at the bottom of the priority chain to allow core overrides
            all_keys |= self._extract_keys_from_catalog(self.crd_catalog)

        return all_keys

    def _extract_keys_from_catalog(self, node: Any, depth: int = 0, _seen: Optional[Set[int]] = None) -> Set[str]:
        """
        Extracts field keys from a catalog structure recursively.
        """
        keys = set()
        if not isinstance(node, dict) or depth > 20:
            return keys

        if _seen is None:
            _seen = set()

        node_id = id(node)
        if node_id in _seen:
            return keys
        _seen.add(node_id)

        # 1. Collect properties at this level
        keys.update(self._get_node_properties(node))

        # 2. Recurse into all items
        for k, v in node.items():
            if k in ["properties", "fields"]:
                continue
            keys |= self._recurse_node_value(v, depth, _seen)

        return keys

    def _get_node_properties(self, node: Dict[str, Any]) -> Set[str]:
        """Helper to extract property keys from a node."""
        props = node.get("properties") or node.get("fields", {})
        if isinstance(props, dict):
            return set(props.keys())
        return set()

    def _recurse_node_value(self, value: Any, depth: int, _seen: Set[int]) -> Set[str]:
        """Helper to recurse into dictionary or list values."""
        keys = set()
        if isinstance(value, dict):
            keys |= self._extract_keys_from_catalog(value, depth + 1, _seen)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    keys |= self._extract_keys_from_catalog(item, depth + 1, _seen)
        return keys

    def _extract_resource_keys(self, schema: Dict[str, Any]) -> Set[str]:
        """Helper to extract keys from a specific resource schema."""
        keys = set()
        properties = schema.get("properties") or {}
        if isinstance(properties, dict):
            keys.update(properties.keys())
            keys |= self._extract_nested_properties(properties)
        return keys

    def _extract_nested_properties(self, properties: Optional[Dict[str, Any]], depth: int = 0) -> Set[str]:
        """
        Recursively extracts property keys from nested schema.
        """
        if depth > 10 or not properties or not isinstance(properties, dict):
            return set()

        keys = set()

        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue

            # Add nested properties
            nested_props = prop_schema.get("properties") or {}
            if isinstance(nested_props, dict):
                keys.update(nested_props.keys())
                keys |= self._extract_nested_properties(nested_props, depth + 1)

        return keys

    def _extract_openapi_keys(self, openapi_catalog: Dict[Any, Any]) -> Set[str]:
        """
        Extracts keys from OpenAPI 3.0 catalog.

        Args:
            openapi_catalog: OpenAPI 3.0 schema definitions

        Returns:
            Set of field keys from OpenAPI schemas
        """
        keys = set()

        # OpenAPI schemas are typically under "components.schemas"
        schemas = openapi_catalog.get("components", {}).get("schemas", {})

        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue

            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                keys.update(properties.keys())
                keys |= self._extract_nested_properties(properties)

        return keys

    def has_schema_for(self, kind: str) -> bool:
        """
        Checks if any catalog contains a schema for this Kind.

        Searches across:
        1. Primary K8s catalog
        2. OpenAPI catalog
        3. CRD catalog
        4. Plugin catalogs

        Args:
            kind: The Kubernetes Kind name (e.g., "Deployment", "Service")

        Returns:
            True if schema exists in any catalog
        """
        # Check primary catalog
        if self._kind_in_catalog(kind, self.catalog):
            return True

        # Check OpenAPI catalog
        if self.openapi_catalog:
            # OpenAPI might have schemas under different structure
            schemas = self.openapi_catalog.get("components", {}).get("schemas", {})
            if kind in schemas:
                return True

        # Check CRD catalog
        if self.crd_catalog and self._kind_in_catalog(kind, self.crd_catalog):
            return True

        # Check plugin catalogs
        for plugin_catalog in self.plugin_catalogs:
            if isinstance(plugin_catalog, dict) and self._kind_in_catalog(kind, plugin_catalog):
                return True

        return False

    def _kind_in_catalog(self, kind: str, catalog: Dict[Any, Any]) -> bool:
        """
        Checks if a kind exists in a specific catalog.

        Args:
            kind: Kind name to search for
            catalog: Catalog to search in

        Returns:
            True if kind found in catalog
        """
        # Check for (apiVersion, kind) tuple keys
        for key in catalog.keys():
            if isinstance(key, tuple) and len(key) == 2 and key[1] == kind:
                return True
        return False

    def get_structure_keys(self) -> Set[str]:
        """
        Returns the set of known structure keys.

        Returns:
            Set of recognized field keys
        """
        return self.known_structure_keys

    def fuzzy_match(self, key: str, cutoff: float = 0.8, kind: Optional[str] = None) -> Optional[str]:
        """
        Finds the closest match for a key among known structure keys.

        Args:
            key: The potentially misspelled key
            cutoff: Similarity threshold (0.0 to 1.0)
            kind: Optional resource kind to narrow the search space

        Returns:
            The closest matching key if found, otherwise None
        """
        # [Zero-Blindspot] Scoped Registry Search
        # Why: Prevents "Semantic Collisions" where a typo in one Kind
        # matches a field from a completely different API group.
        search_keys = self.known_structure_keys
        if kind and self.has_schema_for(kind):
            # Narrow search to this specific kind if possible
            kind_keys = self._get_keys_for_kind(kind)
            if kind_keys:
                search_keys = kind_keys

        # 1. Exact case-sensitive match
        if key in search_keys:
            return key

        # 2. Case-insensitive 100% match
        key_lower = key.lower()
        for k in search_keys:
            if k.lower() == key_lower:
                return k

        # 3. Fuzzy match (Levensthein)
        matches = difflib.get_close_matches(key, search_keys, n=1, cutoff=cutoff)

        # 4. Fallback to Global Search if scoped search failed to yield a high-confidence match
        if not matches and search_keys is not self.known_structure_keys:
            return self.fuzzy_match(key, cutoff=cutoff, kind=None)

        return matches[0] if matches else None

    def _get_keys_for_kind(self, kind: str) -> Set[str]:
        """Retrieves known keys for a specific resource kind."""
        # Core keys are ALWAYS relevant
        core_keys = {
            "apiVersion",
            "kind",
            "metadata",
            "spec",
            "status",
            "data",
            "name",
            "namespace",
            "labels",
            "annotations",
        }

        # Extract from catalog if available
        # Find the node for this kind
        kind_keys = set()
        for k_tuple, schema in self.catalog.items():
            if isinstance(k_tuple, tuple) and k_tuple[1] == kind:
                kind_keys |= self._extract_keys_from_catalog(schema)
                break

        return core_keys | kind_keys
