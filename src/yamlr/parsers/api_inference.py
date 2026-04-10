"""
API version inference for Kubernetes resources.
Extracted from scanner.py to reduce complexity and improve maintainability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
__all__ = ["APIVersionInferrer"]


class APIVersionInferrer:
    """
    Infers API versions for Kubernetes resources when not explicitly specified.

    Uses a three-tier strategy:
    1. Catalog lookup (most accurate)
    2. Common heuristics for well-known resources
    3. Safe fallback to None if unknown

    This is primarily used in Pro mode for intelligent manifest repair.
    """

    def __init__(
        self,
        catalog: Dict[Tuple[str, str], Any],
        crd_catalog: Optional[Dict[Tuple[str, str], Any]] = None,
        plugin_catalogs: Optional[List[Dict[Tuple[str, str], Any]]] = None,
    ):
        """
        Initialize inferrer with K8s API catalogs.

        Args:
            catalog: Primary K8s API schema catalog
            crd_catalog: Custom Resource Definition catalog (optional)
            plugin_catalogs: User-provided schema plugins (optional)
        """
        self.catalog = catalog
        self.crd_catalog = crd_catalog
        self.plugin_catalogs = plugin_catalogs or []
        logger.debug("APIVersionInferrer initialized")

    def infer_version(self, kind: str) -> Optional[str]:
        """
        Infers the most appropriate apiVersion for a given Kind.

        Strategy (in priority order):
        1. Check catalog for exact match (catalog-driven inference)
        2. Use hardcoded heuristics for common K8s resources
        3. Return None if kind is unknown (safe fallback)

        Args:
            kind: The Kubernetes Kind name

        Returns:
            Inferred apiVersion or None if unknown
        """
        # Strategy 1: Catalog-driven inference (most accurate)
        catalog_api = self.infer_from_catalog(kind)
        if catalog_api:
            logger.debug(f"Inferred apiVersion {catalog_api} for kind {kind} from catalog")
            return catalog_api

        # Strategy 2: Heuristic-driven inference (fallback for common kinds)
        heuristic_api = self.infer_from_heuristics(kind)
        if heuristic_api:
            logger.debug(f"Inferred apiVersion {heuristic_api} for kind {kind} from heuristics")
            return heuristic_api

        # Strategy 3: Unknown kind - cannot infer safely
        logger.debug(f"Cannot infer apiVersion for unknown kind {kind}")
        return None

    def infer_from_catalog(self, kind: str) -> Optional[str]:
        """
        Searches all catalogs for this kind and returns its apiVersion.
        """
        # Search priority: K8s -> CRD -> Plugins
        api = self._search_catalog_for_kind(self.catalog, kind)
        if api:
            return api

        if self.crd_catalog:
            api = self._search_catalog_for_kind(self.crd_catalog, kind)
            if api:
                return api

        for plugin_catalog in self.plugin_catalogs:
            api = self._search_catalog_for_kind(plugin_catalog, kind)
            if api:
                return api

        return None

    def _search_catalog_for_kind(self, catalog: Dict[Tuple[str, str], Any], kind: str) -> Optional[str]:
        """Helper to search a single catalog dictionary for a kind."""
        if not isinstance(catalog, dict):
            return None

        for key in catalog.keys():
            if isinstance(key, tuple) and len(key) == 2:
                api_version, catalog_kind = key
                if catalog_kind == kind:
                    return api_version
        return None

    def infer_from_heuristics(self, kind: str) -> Optional[str]:
        """
        Uses centralized heuristics for common Kubernetes kinds.
        Based on stable K8s API versions as of K8s 1.31+ (2026).
        """
        from yamlr.models import RESOURCE_CATALOG

        # Centralized Catalog Check (Source of Truth)
        if kind in RESOURCE_CATALOG:
            return RESOURCE_CATALOG[kind]

        return None
