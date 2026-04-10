#!/usr/bin/env python3
"""
Yamlr LICENSE MANAGER
---------------------
Handles validation and notifications for Yamlr Enterprise (Pro) licenses.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import importlib.util
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Tuple

from yamlr.core.entrypoints.base import get_console

logger = logging.getLogger("yamlr.license")
ERR_NOT_INSTALLED = "Yamlr Pro extension not found."

__all__ = ["ProStatus", "LicenseManager"]


class ProStatus(Enum):
    """Enumeration of possible Pro license states.

    Why: To provide a deterministic way to handle license transitions
         and UI notifications throughout the engine, ensuring
         graceful degradation when Pro features are unavailable.
    """

    NOT_INSTALLED = "not_installed"
    VALID = "valid"
    TRIAL_ACTIVE = "trial_active"
    TRIAL_EXPIRED = "trial_expired"
    LICENSE_EXPIRED = "license_expired"
    LICENSE_INVALID = "license_invalid"
    NETWORK_ERROR = "network_error"
    INSTALLATION_CORRUPT = "corrupt"

    def is_usable(self) -> bool:
        """Checks if the current status permits feature execution.

        Why: To centralize the 'Go/No-Go' logic for Pro features, including
             allowing execution during intermittent network failures for reliability.
        """
        return self in {ProStatus.VALID, ProStatus.TRIAL_ACTIVE, ProStatus.NETWORK_ERROR}

    def requires_user_action(self) -> bool:
        """Checks if the user needs to manually resolve a license issue.

        Why: To drive UI logic that determines when to show modal alerts
             vs. subtle background notifications.
        """
        return self in {ProStatus.TRIAL_EXPIRED, ProStatus.LICENSE_EXPIRED, ProStatus.LICENSE_INVALID}


class LicenseManager:
    """Manages the state and UI for Yamlr Enterprise (Pro) licensing."""

    @staticmethod
    def check_pro_status() -> Tuple[ProStatus, str]:
        """Comprehensive Pro license validation."""
        try:
            # Tier 1: Installation Check
            pro_spec = importlib.util.find_spec("yamlr.pro")
            if pro_spec is None:
                return ProStatus.NOT_INSTALLED, ERR_NOT_INSTALLED

            # [Hardening] Verify it's not just a ghost directory
            pro_path = Path(pro_spec.origin).parent if pro_spec.origin else None
            if pro_path and not (pro_path / "license.py").exists() and not (pro_path / "__init__.py").exists():
                return ProStatus.NOT_INSTALLED, ERR_NOT_INSTALLED

            # Tier 2: Module Integrity
            try:
                import yamlr.pro.license as pro_license
            except ImportError:
                return ProStatus.INSTALLATION_CORRUPT, "Yamlr installation incomplete."

            if not pro_license or not hasattr(pro_license, "validate"):
                return ProStatus.INSTALLATION_CORRUPT, "Yamlr installation incomplete."

            # Tier 3: License Validation
            is_valid, reason = pro_license.validate()
            if is_valid:
                status = ProStatus.TRIAL_ACTIVE if "trial" in reason.lower() else ProStatus.VALID
                return status, reason

            # Map failures
            reason_lower = reason.lower()
            if "trial" in reason_lower and "expired" in reason_lower:
                return ProStatus.TRIAL_EXPIRED, reason
            if "expired" in reason_lower:
                return ProStatus.LICENSE_EXPIRED, reason
            if "network" in reason_lower or "offline" in reason_lower:
                return ProStatus.NETWORK_ERROR, reason
            return ProStatus.LICENSE_INVALID, reason

        except (ImportError, AttributeError, OSError) as e:
            logger.debug(f"Pro detection failsafe: {e}")
            return ProStatus.NOT_INSTALLED, "OSS Mode"

    @staticmethod
    def resolve_capabilities() -> Any:
        """Resolves the set of active capabilities based on license status."""
        from yamlr.models import PipelineCapabilities

        status, _ = LicenseManager.check_pro_status()
        is_usable = status.is_usable()

        return PipelineCapabilities(
            can_heal_cross_resource=is_usable,
            can_use_sovereign_sorting=is_usable,
            can_use_rust_acceleration=True,  # Available to all
            can_generate_evidence=is_usable,
            can_verify_dna=is_usable,
            can_run_mcp=is_usable,
            can_auto_detect_version=is_usable,
            has_unlimited_quota=is_usable,
        )

    @staticmethod
    def notify_pro_required(feature_name: str):
        """Displays a panel explaining that a feature requires Pro.

        Why: To provide a high-conversion, non-intrusive path for users
             to discover and upgrade to Yamlr Enterprise (Pro).
        """
        from rich.panel import Panel

        message = [
            "[bold yellow]Yamlr Pro Required[/bold yellow]",
            f"[yellow]✨ {feature_name} is a Pro Feature[/yellow]",
            "",
            "This feature requires the [bold]Yamlr Enterprise (Pro)[/bold] extension.",
            "",
            "Visit [cyan]https://yamlr.dev[/cyan] to:",
            "  • Start a 30-day free trial",
            "  • View enterprise pricing",
            "  • Request a demo",
            "",
            "[dim]Yamlr OSS continues to provide core healing features.[/dim]",
        ]
        get_console().print(Panel("\n".join(message), border_style="yellow", expand=False, padding=(1, 2)))

    @staticmethod
    def notify_status(status: ProStatus, message: str):
        """Notifies the user about their current Pro license status.

        Why: To maintain transparency about license health and ensure
             users are aware of upcoming renewals or expirations.
        """
        from rich.panel import Panel

        if status == ProStatus.TRIAL_ACTIVE:
            get_console().print(f"[yellow]ℹ️  {message}[/yellow]", style="dim")
        elif status.requires_user_action():
            get_console().print(
                Panel(f"[bold red]License Issue[/bold red]\n\n{message}", border_style="red", expand=False)
            )

    @staticmethod
    def notify_quota_exceeded(message: str):
        """Displays a specific panel when the healing quota is reached."""
        from rich.panel import Panel

        con = get_console()
        con.print("")
        con.print(
            Panel(
                f"[bold red]Free Tier Healing Limit Reached[/bold red]\n\n{message}\n\n"
                "Yamlr provides unlimited read-only `scan` auditing for free forever.\n"
                "However, [bold cyan]remediation and fixing[/bold cyan] require a Pro tier license.\n\n"
                "Visit [cyan]https://yamlr.dev/pro[/cyan] for unlimited healing.",
                title="[yellow]💎 Free Tier Cleanup Guardrail[/yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    @staticmethod
    def get_quota_path() -> Path:
        """Returns the path to the daily usage tracking file."""
        base_dir = Path.home() / ".yamlr"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "quota.json"

    @staticmethod
    def _get_quota_signature(usage: int, date_str: str) -> str:
        """Derives a machine-specific signature for the quota file.

        Why: To prevent simple manual tampering with the local quota file
             in the Free tier (monetization integrity).
        """
        import hashlib
        import platform
        import uuid

        machine_id = str(uuid.getnode())
        node = platform.node()
        # [Phase 5] Salted Integrity: Hardened signature prevents trivial local tampering
        v = "0.1.0" 
        salt = "SovereignEngineVortex2026"
        data = f"{usage}:{date_str}:{machine_id}:{node}:{v}:{salt}"
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def is_healing_allowed(files_requested: int) -> Tuple[bool, int, str]:
        """Delegates to UsageLimiter for free-tier check."""
        from yamlr.core.pro.usage_limiter import UsageLimiter

        return UsageLimiter.is_healing_allowed(files_requested)

    @staticmethod
    def record_healing_usage(files_count: int):
        """Delegates to UsageLimiter."""
        from yamlr.core.pro.usage_limiter import UsageLimiter

        UsageLimiter.record_healing_usage(files_count)

    @staticmethod
    def check_healing_quota(files_requested: int) -> Tuple[bool, int, str]:
        """Legacy wrapper for batch_heal."""
        from yamlr.core.pro.usage_limiter import UsageLimiter

        return UsageLimiter.check_healing_quota(files_requested)
