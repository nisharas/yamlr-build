#!/usr/bin/env python3
"""
Yamlr LICENSE MANAGER
---------------------
Handles validation and notifications for Yamlr Enterprise licenses.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import importlib.util
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger("yamlr.license")
console = Console()

class ProStatus(Enum):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
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
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self in {ProStatus.VALID, ProStatus.TRIAL_ACTIVE, ProStatus.NETWORK_ERROR}

    def requires_user_action(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self in {ProStatus.TRIAL_EXPIRED, ProStatus.LICENSE_EXPIRED, ProStatus.LICENSE_INVALID}

class LicenseManager:
    """Manages the state and UI for Yamlr Enterprise licensing."""

    @staticmethod
    def check_pro_status() -> Tuple[ProStatus, str]:
        """Comprehensive Pro license validation."""
        try:
            # Tier 1: Installation Check
            pro_spec = importlib.util.find_spec("yamlr.pro")
            if pro_spec is None:
                return ProStatus.NOT_INSTALLED, "Yamlr Enterprise not installed."

            # [Hardening] Verify it's not just a ghost directory
            pro_path = Path(pro_spec.origin).parent if pro_spec.origin else None
            if pro_path and not (pro_path / "license.py").exists() and not (pro_path / "__init__.py").exists():
                 return ProStatus.NOT_INSTALLED, "Yamlr Enterprise not installed."

            # Tier 2: Module Integrity
            try:
                from yamlr.pro import license as pro_license
                if not hasattr(pro_license, "validate"):
                    return ProStatus.INSTALLATION_CORRUPT, "Yamlr installation incomplete."
            except ImportError:
                return ProStatus.NOT_INSTALLED, "Yamlr Enterprise not installed."

            # Tier 3: License Validation
            is_valid, reason = pro_license.validate()
            if is_valid:
                status = ProStatus.TRIAL_ACTIVE if "trial" in reason.lower() else ProStatus.VALID
                return status, reason

            # Map failures
            reason_lower = reason.lower()
            if "trial" in reason_lower and "expired" in reason_lower: return ProStatus.TRIAL_EXPIRED, reason
            if "expired" in reason_lower: return ProStatus.LICENSE_EXPIRED, reason
            if "network" in reason_lower or "offline" in reason_lower: return ProStatus.NETWORK_ERROR, reason
            return ProStatus.LICENSE_INVALID, reason

        except Exception as e:
            logger.debug(f"Pro detection failsafe: {e}")
            return ProStatus.NOT_INSTALLED, "OSS Mode"

    @staticmethod
    def notify_pro_required(feature_name: str):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        message = [
            f"[bold yellow]✨ {feature_name} is a Pro Feature[/bold yellow]",
            "", "This feature requires the [bold]Yamlr Enterprise[/bold] extension.", "",
            "Visit [cyan]https://yamlr.dev[/cyan] to:",
            "  • Start a 30-day free trial", "  • View enterprise pricing", "  • Request a demo", "",
            "[dim]Yamlr OSS continues to provide core healing features.[/dim]",
        ]
        console.print(Panel("\n".join(message), border_style="yellow", expand=False, padding=(1, 2)))

    @staticmethod
    def notify_status(status: ProStatus, message: str):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if status == ProStatus.TRIAL_ACTIVE:
            console.print(f"[yellow]ℹ️  {message}[/yellow]", style="dim")
        elif status.requires_user_action():
            console.print(Panel(f"[bold red]License Issue[/bold red]\n\n{message}", border_style="red", expand=False))

    @staticmethod
    def notify_quota_exceeded(message: str):
        """Displays a specific panel when the healing quota is reached."""
        console.print("")
        console.print(Panel(
            f"[bold red]Free Tier Healing Limit Reached[/bold red]\n\n{message}\n\n"
            "Yamlr provides unlimited read-only `scan` auditing for free forever.\n"
            "However, [bold cyan]remediation and fixing[/bold cyan] require a Pro tier license.\n\n"
            "Visit [cyan]https://yamlr.dev/pro[/cyan] for unlimited healing.",
            title="[yellow]💎 Free Tier Cleanup Guardrail[/yellow]",
            border_style="yellow",
            expand=False
        ))

    @staticmethod
    def get_quota_path() -> Path:
        """Returns the path to the daily usage tracking file."""
        base_dir = Path.home() / ".yamlr"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "quota.json"

    @staticmethod
    def is_healing_allowed(files_requested: int) -> Tuple[bool, int, str]:
        """
        Only checks if healing is permitted based on current quota.
        Does NOT record usage.
        """
        import json
        from datetime import date
        
        status, _ = LicenseManager.check_pro_status()
        if status.is_usable():
            return True, -1, ""  # Pro users have no limits

        FREE_DAILY_LIMIT = 5
        
        if files_requested > FREE_DAILY_LIMIT:
             return False, 0, f"Batch healing is limited to {FREE_DAILY_LIMIT} files per run on the Free tier."

        quota_path = LicenseManager.get_quota_path()
        today_str = date.today().isoformat()
        
        current_usage = 0
        last_date = ""
        
        if quota_path.exists():
            try:
                with open(quota_path, 'r') as f:
                    data = json.load(f)
                    last_date = data.get("date", "")
                    current_usage = data.get("usage", 0)
            except Exception:
                pass

        if last_date != today_str:
            current_usage = 0  # Reset for a new day

        if current_usage + files_requested > FREE_DAILY_LIMIT:
            remaining = max(0, FREE_DAILY_LIMIT - current_usage)
            return False, remaining, f"Daily free healing limit reached ({FREE_DAILY_LIMIT} files/day). You have {remaining} file(s) remaining today."

        return True, FREE_DAILY_LIMIT - current_usage, ""

    @staticmethod
    def record_healing_usage(files_count: int):
        """
        Persists the usage of the free tier quota.
        Only call this if is_healing_allowed was True and healing succeeded.
        """
        import json
        from datetime import date
        
        status, _ = LicenseManager.check_pro_status()
        if status.is_usable():
             return

        quota_path = LicenseManager.get_quota_path()
        today_str = date.today().isoformat()
        
        current_usage = 0
        last_date = ""
        
        if quota_path.exists():
            try:
                with open(quota_path, 'r') as f:
                    data = json.load(f)
                    last_date = data.get("date", "")
                    current_usage = data.get("usage", 0)
            except Exception:
                pass

        if last_date != today_str:
            current_usage = 0

        new_usage = current_usage + files_count
        try:
             with open(quota_path, 'w') as f:
                  json.dump({"date": today_str, "usage": new_usage}, f)
        except Exception as e:
             logger.warning(f"Failed to update quota file: {e}")

    @staticmethod
    def check_healing_quota(files_requested: int) -> Tuple[bool, int, str]:
        """
        Legacy wrapper that checks and records in one go.
        Used by batch_heal to maintain backward compatibility.
        """
        allowed, remaining, msg = LicenseManager.is_healing_allowed(files_requested)
        if allowed:
            LicenseManager.record_healing_usage(files_requested)
            # Recalculate remaining after recording
            new_remaining = remaining - files_requested if remaining != -1 else -1
            return True, new_remaining, ""
        return False, remaining, msg
