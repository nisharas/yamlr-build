#!/usr/bin/env python3
"""
Yamlr BRIDGE - The Capability Discovery Layer
----------------------------------------------
Manages the interface between Yamlr Free Version and Yamlr Pro.
Refactored and Hardened: v1.1 Sprint.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple, List

from yamlr.core.license_manager import LicenseManager, ProStatus

logger = logging.getLogger("yamlr.bridge")

class YamlrBridge:
    """
    Orchestrates capabilities and identity across Yamlr tiers.
    """

    @staticmethod
    def is_pro_enabled() -> bool:
        """Simple boolean check for Enterprise enablement."""
        status, _ = LicenseManager.check_pro_status()
        return status.is_usable()

    @staticmethod
    def check_pro_status() -> Tuple[ProStatus, str]:
        """Detailed license status check."""
        return LicenseManager.check_pro_status()

    @staticmethod
    def get_pro_status_display() -> Tuple[str, str, str]:
        """Returns status metadata for UI display."""
        status, message = LicenseManager.check_pro_status()
        
        # Binary Context for Branding Alignment:
        # If running the Pro binary, we use "Free Tier" for unlicensed states.
        # If running the OSS binary, we use "OSS".
        is_pro_binary = YamlrBridge.get_invoked_command() == "yamlr_pro"
        default_label = "Free Tier" if is_pro_binary else "OSS"
        
        map = {
            ProStatus.NOT_INSTALLED: (default_label, "Yamlr Free Version active", "cyan"),
            ProStatus.VALID: ("PRO ✓", message, "green"),
            ProStatus.TRIAL_ACTIVE: ("TRIAL", message, "yellow"),
            ProStatus.TRIAL_EXPIRED: ("EXPIRED", message, "red"),
            ProStatus.LICENSE_EXPIRED: ("EXPIRED", message, "red"),
            ProStatus.LICENSE_INVALID: ("UNLICENSED", message, "yellow"),
            ProStatus.INSTALLATION_CORRUPT: ("ERROR", "Installation Corrupt", "red"),
            ProStatus.NETWORK_ERROR: (default_label, "Offline / Mode: Safe", "yellow"),
        }
        return map.get(status, (default_label, "Yamlr Free Version active", "cyan"))

    @staticmethod
    def get_invoked_command() -> str:
        """Determines if the tool was called as 'yamlr' or 'yamlr_pro'."""
        binary_name = os.path.basename(sys.argv[0]).lower()
        if "yamlr_pro" in binary_name: return "yamlr_pro"
        return "yamlr"

    @staticmethod
    def get_identity() -> str:
        """Determines branding mode (Free Version vs PRO)."""
        if YamlrBridge.get_invoked_command() == "yamlr_pro":
            if importlib.util.find_spec("yamlr.pro"): return "PRO"
        return "OSS"

    @staticmethod
    def notify_pro_required(feature_name: str):
        """Standardized 'Polite Refusal' for Pro features."""
        LicenseManager.notify_pro_required(feature_name)

    @staticmethod
    def get_pro_module(submodule: str) -> Optional[Any]:
        """Safely imports a Pro submodule."""
        if not YamlrBridge.is_pro_enabled(): return None
        try:
            return importlib.import_module(f"yamlr.pro.{submodule}")
        except Exception as e:
            logger.debug(f"Pro submodule '{submodule}' unavailable: {e}")
            return None

    @staticmethod
    def get_shield() -> Optional[Any]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        module = YamlrBridge.get_pro_module("shield")
        return module.ShieldEngine() if module and hasattr(module, "ShieldEngine") else None

    @staticmethod
    def get_validator() -> Optional[Any]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        module = YamlrBridge.get_pro_module("opa_adapter")
        return module.OpaAnalyzer() if module and hasattr(module, "OpaAnalyzer") else None

    @staticmethod
    def get_exporter() -> Optional[Any]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        module = YamlrBridge.get_pro_module("exporter")
        return module.Exporter() if module and hasattr(module, "Exporter") else None

    @staticmethod
    def has_pro_license_file() -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return (Path.home() / ".Yamlr" / "license.key").exists()
