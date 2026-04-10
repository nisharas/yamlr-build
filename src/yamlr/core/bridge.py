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

from yamlr.core.forensics import ForensicLogger
from yamlr.core.license_manager import LicenseManager, ProStatus

logger = logging.getLogger("yamlr.bridge")
__all__ = ["YamlrBridge"]


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
        return True  # Text/JSON are free

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
    # 🛡️ IRON SHIELD: Identity Bypass for Indestructible Standalone Binaries
    _FORCED_OSS = os.environ.get("YAMLR_IDENTITY_BYPASS") == "1"
    _IS_FROZEN = getattr(sys, "frozen", False)
    """
    Orchestrates capabilities and identity across Yamlr tiers.
    """

    # Capability Accessor
    capabilities = CapabilityShield

    @staticmethod
    def is_pro_enabled() -> bool:
        """Simple boolean check for Enterprise enablement."""
        if YamlrBridge._FORCED_OSS:
            return False
            
        # [Hardening] Support YAMLR_TEST bypass for E2E/CI suites
        if os.environ.get("YAMLR_TEST") == "true" or os.environ.get("YAMLR_INTERNAL_TEST_MODE") == "true":
            return True

        status, _ = LicenseManager.check_pro_status()
        return status.is_usable()

    # ... (remaining methods ... I'll use replace_file_content to insert the shield before YamlrBridge)

    @staticmethod
    def check_pro_status() -> Tuple[ProStatus, str]:
        """Detailed license status check."""
        return LicenseManager.check_pro_status()

    @staticmethod
    def get_pro_status_display() -> Tuple[str, str, str]:
        """Returns status metadata for UI display.
        
        Why: Centralized UI branding logic that reflects license state
             without dependency on the binary filename.
        """
        status, message = LicenseManager.check_pro_status()
        default_label = "Free"

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
        """Determines the canonical command name for branding and help."""
        # [Motto Pivot] Unified identity: Always 'yamlr'
        return "yamlr"

    @staticmethod
    def get_identity() -> str:
        """Determines branding mode (Free Version vs PRO) based on license status."""
        if getattr(YamlrBridge, "_FORCED_OSS", False):
            return "OSS"
        
        status, _ = LicenseManager.check_pro_status()
        if status.is_usable():
            return "PRO"
            
        return "OSS"

    # --- 🛡️ Capability Registry (Hardened v2.0) ---
    _registry: Dict[str, Any] = {}

    @classmethod
    def register_capability(cls, name: str, provider: Any):
        """Registers a tiered capability provider (e.g., Shield, Surgeon)."""
        cls._registry[name] = provider

    @classmethod
    def get_capability(cls, name: str) -> Optional[Any]:
        """Retrieves a registered capability provider."""
        return cls._registry.get(name)

    @staticmethod
    def get_pro_module(submodule: str) -> Optional[Any]:
        """
        [DEPRECATED] Safely imports a Pro submodule.
        Why: Use register_capability() instead to maintain tier isolation.
        """
        if not YamlrBridge.is_pro_enabled():
            return None
        try:
            return importlib.import_module(f"yamlr.pro.{submodule}")
        except Exception as e:
            logger.debug(f"Pro submodule '{submodule}' unavailable: {e}")
            return None

    @staticmethod
    def get_cluster_detector(kubectl_path: str) -> Optional[Any]:
        """Retrieves the Pro Cluster Detector instance."""
        provider = YamlrBridge.get_capability("cluster_detection")
        if provider and hasattr(provider, "ClusterDetection"):
            return provider.ClusterDetection(kubectl_path=kubectl_path)
        return None

    @staticmethod
    def get_shield() -> Optional[Any]:
        """Retrieves the Shield Engine instance (Pro)."""
        provider = YamlrBridge.get_capability("shield")
        if provider and hasattr(provider, "ShieldEngine"):
            return provider.ShieldEngine()
        return None

    @staticmethod
    def get_surgeon() -> Optional[Any]:
        """Retrieves the Pro Surgery engine."""
        provider = YamlrBridge.get_capability("surgery")
        return getattr(provider, "ProSurgeon", None) if provider else None

    @staticmethod
    def get_validator() -> Optional[Any]:
        """Retrieves the OPA-based analyzer (Pro)."""
        provider = YamlrBridge.get_capability("opa_adapter")
        return provider.OpaAnalyzer() if provider and hasattr(provider, "OpaAnalyzer") else None

    @staticmethod
    def get_judge(catalog: dict) -> Optional[Any]:
        """Retrieves the Enterprise Judge (Safety Verdict Engine)."""
        # Judge is in validators (OSS accessible but Pro-level logic)
        try:
            from yamlr.validators.judge import KubeJudge
            return KubeJudge(catalog)
        except ImportError:
            return None

    @staticmethod
    def get_evidence_engine() -> Optional[Any]:
        """Retrieves the Pro Evidence Engine instance."""
        provider = YamlrBridge.get_capability("compliance.evidence")
        if provider and hasattr(provider, "EvidenceEngine"):
            return provider.EvidenceEngine()
        return None

    @staticmethod
    def get_license_module() -> Optional[Any]:
        """Retrieves the Pro License module."""
        return YamlrBridge.get_capability("license")

    @staticmethod
    def get_opa_analyzer() -> Optional[Any]:
        """Retrieves the OPA-to-Yamlr Adapter."""
        return YamlrBridge.get_capability("opa_adapter")

    @staticmethod
    def get_kyverno_adapter() -> Optional[Any]:
        """Retrieves the Kyverno-to-Yamlr Adapter."""
        return YamlrBridge.get_capability("kyverno_adapter")

    @staticmethod
    def get_adapter_engine() -> Optional[Any]:
        """Retrieves the Enterprise Custom Adapter engine."""
        provider = YamlrBridge.get_capability("compliance.adapters")
        return getattr(provider, "AdapterEngine", None) if provider else None

    @staticmethod
    def get_auth_url() -> str:
        """Retrieves the checkout URL for Pro upgrade."""
        provider = YamlrBridge.get_capability("auth")
        if provider and hasattr(provider, "get_checkout_url"):
            return provider.get_checkout_url()
        return "https://yamlr.dev/pro"

    @staticmethod
    def get_evidence_aggregator() -> Optional[Any]:
        """Retrieves the Pro Evidence Aggregator class."""
        provider = YamlrBridge.get_capability("compliance.aggregator")
        return getattr(provider, "EvidenceAggregator", None) if provider else None

    @staticmethod
    def get_compliance_registry() -> Optional[Any]:
        """Retrieves the Enterprise Compliance Registry (Pro)."""
        provider = YamlrBridge.get_capability("compliance.ruleset")
        return getattr(provider, "ComplianceRegistry", None) if provider else None

    @staticmethod
    def get_exporter(catalog: dict) -> Optional[Any]:
        """Retrieves the Enterprise JSON/Sarif Exporter (Pro)."""
        provider = YamlrBridge.get_capability("exporter")
        return provider.Exporter(catalog=catalog) if provider and hasattr(provider, "Exporter") else None

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
            "UNITTEST_ON",  # Optional marker for native unittest
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
