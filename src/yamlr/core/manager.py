#!/usr/bin/env python3
"""
Yamlr MANAGER - The Infrastructure Base
---------------------------------------
Handles workspace, configuration, I/O, and platform-specific bootstrapping.
Decoupled from the Engine to allow for better testability and modularity.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import os
import sys
import json
import logging
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from yamlr.core.config import ConfigManager
from yamlr.core.io import FileSystemManager
from yamlr.core.context import HealContext
from yamlr.core.catalog_manager import CatalogManager

logger = logging.getLogger("yamlr.manager")

# [MAGIC MOMENT] Embedded Minimal Catalog Fallback
# Why: Ensures the engine NEVER fails to start, even if assets are missing.
MINIMAL_CATALOG_JSON = {
    "version": "v1.31.0-embedded",
    "definitions": {
        "io.k8s.api.core.v1.Pod": {"properties": {"kind": {"type": "string"}}},
        "io.k8s.api.apps.v1.Deployment": {"properties": {"kind": {"type": "string"}}},
        "io.k8s.api.core.v1.Service": {"properties": {"kind": {"type": "string"}}}
    },
    "resources": ["Pod", "Deployment", "Service", "ConfigMap", "Secret", "Ingress"]
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
        self.concurrency = concurrency or os.cpu_count() or 1
        
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
        self.health_threshold = (
            health_threshold if health_threshold != 70 else self.config.health_threshold
        )
        self._init_cluster_context(cluster_version)

        # 4. Load Catalog
        self.catalog = self._load_catalog(catalog_path)

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
                self.allowed_host_paths = [
                    "/data",
                    "/etc/config",
                    "/var/log",
                    "/tmp",
                    "/mnt",
                ]

    def _init_cluster_context(self, cluster_version: Optional[str]):
        """Standardizes cluster version across the engine."""
        if cluster_version:
            self.cluster_version = HealContext.set_cluster_version(cluster_version)
        elif self.config.kubernetes_version:
             self.cluster_version = HealContext.set_cluster_version(self.config.kubernetes_version)
        else:
            self.cluster_version = HealContext._get_default_cluster_version()
        
        # Propagate Provider Hint
        if self.provider != "auto":
            logger.debug(f"Manager: Using provider hint '{self.provider}' for context.")
            
        logger.debug(f"Context initialized for target K8s: {self.cluster_version}")

    def _load_catalog(self, catalog_path: Optional[str]) -> Dict[str, Any]:
        """
        Industrial-grade catalog resolution with multi-layered fallbacks.
        Uses CatalogManager for cache/upstream resolution and falls back to
        embedded assets and finally a hardcoded minimal schema.
        """
        # Priority 1: Use CatalogManager to resolve versioned catalog (Cache > Upstream)
        # We pass the bundled path as a fallback if the versioned one isn't cached.
        
        bundled_default = self._get_bundled_catalog_path()
        
        # If user provided a path, we try that first
        if catalog_path:
            physical_path = Path(catalog_path).resolve()
            if physical_path.exists():
                return self._read_json_catalog(physical_path)
        
        # Resolve via CatalogManager (checks ~/.Yamlr/catalogs)
        resolved_path_str = self.catalog_manager.resolve_catalog(
            self.cluster_version, 
            fallback_path=str(bundled_default) if bundled_default else None
        )
        
        resolved_path = Path(resolved_path_str)
        if resolved_path.exists():
            return self._read_json_catalog(resolved_path)

        # Final Fallback: Hardcoded Minimal
        logger.warning("Manager: No physical catalog found. Engaging [Embedded Magic Fallback].")
        return MINIMAL_CATALOG_JSON

    def _get_bundled_catalog_path(self) -> Optional[Path]:
        """Discovery logic for bundled k8s_v1_distilled.json across package/frozen environments."""
        from yamlr.core.utils import resolve_bundled_asset
        return resolve_bundled_asset("catalog/k8s_v1_distilled.json")

    def _read_json_catalog(self, path: Path) -> Dict[str, Any]:
        """Helper to safely read and parse a JSON catalog."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Loaded resource catalog from {path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load catalog at {path}: {e}")
            return MINIMAL_CATALOG_JSON
