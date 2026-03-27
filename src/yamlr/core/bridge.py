#!/usr/bin/env python3
"""
Yamlr BRIDGE - The Capability Discovery Layer
----------------------------------------------
Manages the interface between Yamlr Free Version and Yamlr Pro.
Refactored and Hardened: v1.1 Sprint.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations
import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

from yamlr.core.license_manager import LicenseManager, ProStatus

logger = logging.getLogger("yamlr.bridge")
__all__ = ['YamlrBridge']



class CapabilityShield:
    """
    A strict, policy-only interface for discovering tiered capabilities.
    
    Why: To centralize Pro vs Free behavior without leaking IO/Logging into 
    decision checkpoints.
    """

    @staticmethod
    def can_auto_fix_refs() -> bool:
        """Determines if cross-resource auto-remediation is allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_harden_security() -> bool:
        """Determines if PSS-style hardening is allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_enforce_resource_limits() -> bool:
        """Determines if automatic resource limit injection is allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_use_sovereign_sorting() -> bool:
        """Determines if Enterprise-grade field sorting is allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_use_advanced_probes() -> bool:
        """Determines if smart Liveness/Readiness probe injection is allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_use_opa_bundles() -> bool:
        """Determines if remote OPA policy bundles are allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def produces_evidence_receipts() -> bool:
        """Determines if DNA-signed compliance receipts are allowed."""
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def can_export_format(fmt: str) -> bool:
        """Determines if a specific export format (e.g., Sarif) is allowed."""
        if fmt in ["sarif", "prometheus", "backstage", "sovereign"]:
            return YamlrBridge.is_pro_enabled()
        return True # Text/JSON are free

    @staticmethod
    def get_healing_limit() -> int:
        """Returns the maximum number of files that can be healed per day."""
        if YamlrBridge.is_pro_enabled():
            return 999999
        return 5

    @staticmethod
    def can_heal(files_count: int) -> Tuple[bool, int, str]:
        """Policy: Is healing allowed for this batch size?"""
        if YamlrBridge.is_pro_enabled():
            return True, 0, "Unlimited Pro"
        
        limit = CapabilityShield.get_healing_limit()
        if files_count > limit:
            return False, limit, f"Free Tier healing is capped at {limit} files/day."
        
        # Mechanics of tracking still handled by LicenseManager/UsageLimiter
        return LicenseManager.is_healing_allowed(files_count)

    @staticmethod
    def is_fast_scan_allowed() -> bool:
        """Determines if the high-performance native scanner is enabled."""
        return YamlrBridge.is_pro_enabled()


class YamlrBridge:
    """
    Orchestrates capabilities and identity across Yamlr tiers.
    """
    
    # Capability Accessor
    capabilities = CapabilityShield

    @staticmethod
    def is_pro_enabled() -> bool:
        """Simple boolean check for Enterprise enablement."""
        status, _ = LicenseManager.check_pro_status()
        return status.is_usable()

    # ... (remaining methods ... I'll use replace_file_content to insert the shield before YamlrBridge)

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
        
        status_map = {
            ProStatus.NOT_INSTALLED: (default_label, "Yamlr Free Version active", "cyan"),
            ProStatus.VALID: ("PRO ✓", message, "green"),
            ProStatus.TRIAL_ACTIVE: ("TRIAL", message, "yellow"),
            ProStatus.TRIAL_EXPIRED: ("EXPIRED", message, "red"),
            ProStatus.LICENSE_EXPIRED: ("EXPIRED", message, "red"),
            ProStatus.LICENSE_INVALID: ("UNLICENSED", message, "yellow"),
            ProStatus.INSTALLATION_CORRUPT: ("ERROR", "Installation Corrupt", "red"),
            ProStatus.NETWORK_ERROR: (default_label, "Offline / Mode: Safe", "yellow"),
        }
        return status_map.get(status, (default_label, "Yamlr Free Version active", "cyan"))

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
        Retrieves the Shield Engine instance (Pro only).
        
        Why: Centralized access to the enterprise hardening engine.
        """
        module = YamlrBridge.get_pro_module("shield")
        if module and hasattr(module, "ShieldEngine"):
            try:
                return module.ShieldEngine()
            except Exception as e:
                logger.error(f"Failed to instantiate ShieldEngine: {e}")
        return None

    @staticmethod
    def get_validator() -> Optional[Any]:
        """Retrieves the OPA-based analyzer (Pro)."""
        module = YamlrBridge.get_pro_module("opa_adapter")
        return module.OpaAnalyzer() if module and hasattr(module, "OpaAnalyzer") else None

    @staticmethod
    def get_judge(catalog: dict) -> Optional[Any]:
        """
        Retrieves the Enterprise Judge (Safety Verdict Engine).
        Part of VAL-02-8 Heritage Port.
        """
        # Judge is in validators (OSS accessible but Pro-level logic)
        try:
            from yamlr.validators.judge import KubeJudge
            return KubeJudge(catalog)
        except ImportError:
            return None

    @staticmethod
    def get_exporter(catalog: dict) -> Optional[Any]:
        """Retrieves the Enterprise JSON/Sarif Exporter (Pro).
        
        Why: To provide machine-readable output formats for enterprise pipelines.
        """
        module = YamlrBridge.get_pro_module("exporter")
        return module.Exporter(catalog=catalog) if module and hasattr(module, "Exporter") else None

    @staticmethod
    def has_pro_license_file() -> bool:
        """Verifies if a pro license key file exists on the local machine.
        
        Why: Quick filesystem check to determine if Pro features should be considered.
        """
        return (Path.home() / ".yamlr" / "license.key").exists()

    @staticmethod
    def is_offline_mode() -> bool:
        """
        Centralized "Network Kill Switch".
        Returns True if Yamlr should avoid making ANY outbound network calls.
        Driven by: Yamlr_OFFLINE=true OR detected test environments.
        """
        if os.getenv("Yamlr_OFFLINE") == "true":
            return True
        
        # Detect common test environments
        test_markers = [
            "PYTEST_CURRENT_TEST",
            "YAMLR_TEST",
            "UNITTEST_ON"  # Optional marker for native unittest
        ]
        if any(marker in os.environ for marker in test_markers):
            return True
        
        return False

    @staticmethod
    def get_remediation_command(file_path: str) -> str:
        """
        Generates a suggested CLI command to repair the manifest.
        
        Why: To provide immediate, actionable remediation steps in the UI.
        """
        invoked_as = YamlrBridge.get_invoked_command()
        return f"{invoked_as} heal {file_path} --diff"

    _cached_id: Optional[str] = None

    @staticmethod
    def get_machine_id() -> str:
        """
        Returns a stable, unique machine identifier for attribution.
        
        Why: To provide reliable conversion tracking for M&A and affiliate audits.
             Uses Windows Registry for sub-millisecond results on first run.
        """
        if YamlrBridge._cached_id:
            return YamlrBridge._cached_id

        machine_id = "unknown"
        try:
            if sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
                machine_id, _ = winreg.QueryValueEx(key, "MachineGuid")
            else:
                import uuid
                machine_id = str(uuid.getnode())
        except Exception:
            try:
                import platform
                machine_id = f"{platform.node()}-{platform.machine()}"
            except Exception:
                machine_id = "fallback-id"

        import hashlib
        YamlrBridge._cached_id = hashlib.sha256(machine_id.encode()).hexdigest()[:12]
        return YamlrBridge._cached_id

    @staticmethod
    def get_checkout_url() -> str:
        """
        Returns the Pro upgrade checkout URL with machine-level attribution.
        
        Why: To ensure consistent attribution for conversions originating from the CLI.
        """
        machine_id = YamlrBridge.get_machine_id()
        return f"https://yamlr.dev/checkout?utm_source=yamlr_cli&utm_medium=version_tip&attr={machine_id}"
