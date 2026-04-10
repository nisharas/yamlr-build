#!/usr/bin/env python3
"""
Yamlr MANAGER - The Infrastructure Base
---------------------------------------
Handles workspace, configuration, I/O, and platform-specific bootstrapping.
Decoupled from the Engine to allow for better testability and modularity.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from yamlr.core.catalog_manager import CatalogManager
from yamlr.core.config import ConfigManager
from yamlr.core.context import HealContext
from yamlr.core.io import FileSystemManager
from yamlr.core.k8s_versions import MATRIX

logger = logging.getLogger("yamlr.manager")

__all__ = ["YamlrManager"]

# [MAGIC MOMENT] Core Resource Catalog (Bundled Safety)
# Why: Ensures the engine ALWAYS has basic schema knowledge for K8s essentials.
CORE_CATALOG_JSON = {
    "version": f"v{MATRIX.default_recommended}-core",
    "definitions": {
        "io.k8s.api.core.v1.Pod": {"properties": {"kind": {"type": "string"}}},
        "io.k8s.api.apps.v1.Deployment": {"properties": {"kind": {"type": "string"}}},
        "io.k8s.api.core.v1.Service": {"properties": {"kind": {"type": "string"}}},
    },
    "resources": ["Pod", "Deployment", "Service", "ConfigMap", "Secret", "Ingress"],
}


class YamlrManager:
    """
    Infrastructure manager for the Yamlr project.

    Responsibilities:
    - Path anchoring and workspace security
    - Configuration orchestration
    - Schema catalog resolution and loading
    - Filesystem interaction bootstrapping
    """

    def __init__(
        self,
        workspace_path: str,
        app_name: str = "Yamlr",
        catalog_path: Optional[str] = None,
        catalog_data: Optional[Dict[str, Any]] = None,
        health_threshold: int = 70,
        allowed_host_paths: Optional[List[str]] = None,
        concurrency: Optional[int] = None,
        cluster_version: Optional[str] = None,
    ):
        """
        Initializes the infrastructure layer for Yamlr.
        """
        self.workspace = Path(workspace_path).resolve()
        self.app_name = app_name
        
        # [Phase 13] Platform Sentinel: Auto-tune concurrency for Windows
        # Why: Prevents process thrashing in restricted VDI/CI environments.
        raw_cpu = os.cpu_count() or 1
        if platform.system() == "Windows":
             self.concurrency = concurrency or min(raw_cpu, 12)
        else:
             self.concurrency = concurrency or raw_cpu

        # 1. Environment Overrides
        self.provider = os.getenv("Yamlr_PROVIDER", "auto")
        self.kubectl_path = os.getenv("Yamlr_KUBECTL_PATH", "kubectl")

        # 1. Initialize core managers
        self.fs = FileSystemManager(self.workspace, app_name=self.app_name)
        self.fs.ensure_workspace()
        self.config = ConfigManager(self.workspace, app_name=self.app_name)
        self.catalog_manager = CatalogManager()

        # 2. OS-Aware Path Anchoring
        self._init_security_context(allowed_host_paths)

        # 3. Resolve Metrics and Context
        self.health_threshold = health_threshold if health_threshold != 70 else self.config.health_threshold
        self._init_cluster_context(cluster_version)

        # 4. Store Catalog Path (Deferred Loading)
        self._catalog_override_path = catalog_path
        self._catalogs: Dict[str, Any] = {}
        if catalog_data:
            # If explicit data is provided, it pins specifically to the initialized version
            self._catalogs[self.cluster_version] = catalog_data
        self._is_closed = False

    @property
    def catalog(self) -> Dict[str, Any]:
        """Lazy-loaded catalog for the current cluster version."""
        v = self.cluster_version
        if v not in self._catalogs:
            self._catalogs[v] = self._load_catalog(v, self._catalog_override_path)
        return self._catalogs[v]

    def get_catalog_for_version(self, version: str) -> Dict[str, Any]:
        """Retrieves or loads a catalog for a specific K8s version."""
        if version not in self._catalogs:
            self._catalogs[version] = self._load_catalog(version, self._catalog_override_path)
        return self._catalogs[version]

    def _init_security_context(self, allowed_host_paths: Optional[List[str]]):
        """Sets up the operational security context for hostPath validation."""
        if allowed_host_paths:
            self.allowed_host_paths = allowed_host_paths
        elif self.config.allowed_host_paths:
            self.allowed_host_paths = self.config.allowed_host_paths
        else:
            if platform.system() == "Windows":
                self.allowed_host_paths = [
                    "C:\\ProgramData",
                    "C:\\Windows\\Temp",
                    "C:\\Users\\Public",
                ]
            else:
                import tempfile

                self.allowed_host_paths = [
                    "/data",
                    "/etc/config",
                    "/var/log",
                    tempfile.gettempdir(),
                    "/mnt",
                ]

    def _init_cluster_context(self, cluster_version: Optional[str]):
        """Standardizes cluster version across the engine with Phase 12 DNA Sync."""
        from yamlr.core.k8s_versions import is_supported, closest_supported
        
        explicit_version = None

        # 1. Explicit Flag (Override)
        if cluster_version and cluster_version != "auto":
            explicit_version = HealContext.set_cluster_version(cluster_version)

        # 2. Config File
        elif self.config.kubernetes_version and self.config.kubernetes_version != "auto":
            explicit_version = HealContext.set_cluster_version(self.config.kubernetes_version)

        # 3. Dynamic Inference (AUTO)
        else:
            from yamlr.core.inference import VersionInferenceEngine
            engine = VersionInferenceEngine()
            explicit_version = engine.infer_version(self)

        # [Phase 12] Cluster DNA Sync: Match against support matrix
        if not is_supported(explicit_version):
            best_match = closest_supported(explicit_version)
            logger.warning(
                f"⚠️ DNA MISMATCH: Version 'v{explicit_version}' is not natively bundled. "
                f"Syncing to closest supported DNA: 'v{best_match}'."
            )
            self.cluster_version = best_match
        else:
            self.cluster_version = explicit_version

        # Propagate Provider Hint
        if self.provider != "auto":
            logger.debug(f"Manager: Using provider hint '{self.provider}' for context.")

        logger.debug(f"Context initialized for target K8s: {self.cluster_version}")

    def _load_catalog(self, version: str, catalog_path: Optional[str]) -> Dict[str, Any]:
        """
        Industrial-grade catalog resolution with multi-layered fallbacks.
        Uses CatalogManager for cache/upstream resolution and falls back to
        embedded assets and finally a hardcoded minimal schema.
        """
        # Priority 1: Use CatalogManager to resolve versioned catalog (Cache > Bundled > Remote > Adaptive)

        # If user provided a path, we try that first
        if catalog_path:
            physical_path = Path(catalog_path).resolve()
            if physical_path.exists():
                return self._read_json_catalog(physical_path)

        # Resolve via CatalogManager (Cache > Bundled > Remote > Adaptive)
        resolved_path_str = self.catalog_manager.resolve_catalog(version, intent="analysis")

        resolved_path = Path(resolved_path_str)
        if resolved_path.exists():
            return self._read_json_catalog(resolved_path)

        # Final Fallback: Hardcoded Core Essentials
        logger.warning("Manager: No physical catalog found. Engaging [Core Safety Fallback].")
        return CORE_CATALOG_JSON

    def _read_json_catalog(self, path: Path) -> Dict[str, Any]:
        """Helper to safely read and parse a JSON catalog."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Loaded resource catalog from {path}")
            return data
        except (json.JSONDecodeError, OSError, IOError) as e:
            logger.error(f"Failed to load catalog at {path}: {e}")
            return CORE_CATALOG_JSON

    def close(self):
        """Releases infrastructure resources."""
        if self._is_closed:
            return
        # Placeholder for any explicit cleanup (e.g. closing open config locks)
        self._is_closed = True
