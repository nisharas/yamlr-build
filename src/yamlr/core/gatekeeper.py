from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine

logger = logging.getLogger("yamlr.gatekeeper")


class LicenseGate:
    """
    Centralized authority for Yamlr license, quotas, and Tier discovery.

    Why: To decouple tiered logic from the core engine, ensuring that 
         YamlrEngine remains a pure orchestrator while the LicenseGate 
         manages feature availability and branding.
    """

    @staticmethod
    def is_pro_enabled() -> bool:
        """Checks if enterprise features are active via the bridge."""
        from yamlr.core.bridge import YamlrBridge
        return YamlrBridge.is_pro_enabled()

    @staticmethod
    def get_tier_metadata() -> Dict[str, str]:
        """Returns branding and identity metadata based on active tier.
        
        Why: Centralizes all marketing/branding strings to prevent leakage 
             into core engine logic.
        """
        is_pro = LicenseGate.is_pro_enabled()
        return {
            "name": "Yamlr Enterprise (Pro)" if is_pro else "Yamlr (Free Version)",
            "short_name": "PRO" if is_pro else "FREE",
            "tier": "enterprise" if is_pro else "community",
            "tagline": "Enterprise reliability layer" if is_pro else "Deterministic K8s healing",
        }

    @staticmethod
    def check_quota(files_count: int, is_dry_run: bool = True) -> bool:
        """Enforces free-tier limits for non-pro users."""
        if LicenseGate.is_pro_enabled():
            return True

        if is_dry_run:
            # Hardcoded Free Tier Limits for simulation
            LIMIT = 500
            if files_count > LIMIT:
                logger.warning(f"⚠️  Quota Limit Reached: {files_count} files exceeds the Free Tier limit ({LIMIT}).")
                return False
            return True
        
        # Non-dry-run (Heal): Delegate to persistent UsageLimiter
        from yamlr.core.license_manager import LicenseManager
        allowed, _, reason = LicenseManager.is_healing_allowed(files_count)
        if not allowed:
            # We must use 'limit reached' string to ensure test parity
            logger.warning(f"⛔ Free Tier Healing Limit Reached: {reason}")
            return False
        return True

    @staticmethod
    def get_feature_hint(context: str = "generic") -> Optional[str]:
        """Returns context-aware hints to guide users toward Pro features."""
        if LicenseGate.is_pro_enabled():
            return None

        hints = {
            "generic": "The Free tier is optimized for single-file focus. Batches > 5 files require Yamlr Pro.",
            "scan": "💎 PRO available in this repo – after scan, try: yamlr heal --harden .",
            "quota": "⛔ Quota Exceeded. Visit yamlr.dev/pro for unlimited healing.",
            "security": "💎 PRO: Use OPA/Kyverno adapters for enterprise-grade compliance.",
            "upsell": "Run yamlr heal --harden to automatically resolve them.",
        }
        return hints.get(context, hints["generic"])

    @staticmethod
    def get_capabilities() -> Any:
        """Resolves the set of active capabilities based on license status.
        
        Why: Decouples the engine's execution capabilities from the 
             licensing logic. The engine asks "can I do X?", not "is this Pro?".
        """
        from yamlr.core.license_manager import LicenseManager
        return LicenseManager.resolve_capabilities()

    @staticmethod
    def is_feature_allowed(feature_id: str) -> bool:
        """Gates specific enterprise features based on license capabilities."""
        from yamlr.core.bridge import YamlrBridge
        return YamlrBridge.check_feature_access(feature_id)

    @staticmethod
    def get_pro_title(context: str = "generic") -> str:
        """Returns a standardized branding title for Pro features.
        
        Why: Ensures consistent "Dopamine Drip" conversion UI across all 
             renderers (Advisory, Formatter, CLI).
        """
        titles = {
            "preview": "SIMULATION: Yamlr Pro Preview",
            "repairs": "Yamlr Pro Repairs",
            "advisory": "PRO ADVISORY",
            "quota": "Free Tier Healing Limit Reached",
            "generic": "Yamlr Enterprise (Pro) Feature",
        }
        return titles.get(context, titles["generic"])

    @staticmethod
    def get_pro_hint(feature_id: str = "generic") -> str:
        """Returns a helpful hint on why to upgrade to Pro."""
        hints = {
            "batch": "Yamlr Pro supports unlimited files in a single pass.",
            "quota": "Daily free healing limit reached. Upgrade to Pro for unlimited healing.",
            "generic": "Upgrade to Pro for advanced cross-resource auto-repair.",
        }
        return hints.get(feature_id, hints["generic"])


# [Compatibility Alias] Redirect ProGate to LicenseGate
ProGate = LicenseGate
