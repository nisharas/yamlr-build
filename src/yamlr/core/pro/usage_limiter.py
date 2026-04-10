#!/usr/bin/env python3
"""
Yamlr USAGE LIMITER - Free Tier Boundary Enforcement
-----------------------------------------------------
Codifies the 'Detection is Free / Remediation is Paid' model by enforcing
daily healing limits for non-Pro users.

Why: To protect the commercial value of Yamlr Surgeon while allowing
     OSS users to experience the healing magic on small tasks.
"""

from __future__ import annotations

import logging
from typing import Tuple

from yamlr.core.bridge import YamlrBridge

logger = logging.getLogger("yamlr.pro.usage_limiter")

DAILY_FREE_HEAL_LIMIT = 1000


class UsageLimiter:
    """
    Enforces surgical limits for the Free tier.
    """

    DAILY_FREE_HEAL_LIMIT = 1000

    @staticmethod
    def _get_quota_signature(usage: int, date_str: str) -> str:
        """Derives a machine-specific signature for the quota file.
        
        Parity: Matches legacy 'quota.json' signature format.
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
    def get_quota_path() -> Path:
        """Returns the path to the daily usage tracking file."""
        from pathlib import Path
        base_dir = Path.home() / ".yamlr"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "quota.json"

    @staticmethod
    def is_healing_allowed(files_requested: int) -> Tuple[bool, int, str]:
        """Checks if healing is permitted based on current quota."""
        from yamlr.core.bridge import YamlrBridge
        if YamlrBridge.is_pro_enabled():
            return True, -1, ""

        if files_requested > UsageLimiter.DAILY_FREE_HEAL_LIMIT:
            return (
                False,
                0,
                f"Batch healing is limited to {UsageLimiter.DAILY_FREE_HEAL_LIMIT} files per run on the Free tier.",
            )

        from datetime import date
        import json
        
        quota_path = UsageLimiter.get_quota_path()
        today_str = date.today().isoformat()
        
        current_usage = 0
        if quota_path.exists():
            try:
                stats = json.loads(quota_path.read_text())
                last_date = stats.get("date", "")
                current_usage = stats.get("usage", 0)
                sig = stats.get("sig", "")
                
                if last_date != today_str:
                    current_usage = 0
                elif sig and sig != UsageLimiter._get_quota_signature(current_usage, last_date):
                    logger.warning("Quota integrity check failed. Enforcing conservative limit.")
                    current_usage = UsageLimiter.DAILY_FREE_HEAL_LIMIT
            except Exception:
                current_usage = UsageLimiter.DAILY_FREE_HEAL_LIMIT

        if current_usage + files_requested > UsageLimiter.DAILY_FREE_HEAL_LIMIT:
            remaining = max(0, UsageLimiter.DAILY_FREE_HEAL_LIMIT - current_usage)
            return (
                False,
                remaining,
                f"Daily free healing limit reached ({UsageLimiter.DAILY_FREE_HEAL_LIMIT} files/day). You have {remaining} remaining today.",
            )

        return True, UsageLimiter.DAILY_FREE_HEAL_LIMIT - current_usage, ""

    @staticmethod
    def record_healing_usage(files_count: int):
        """Persists the usage of the free tier quota."""
        from yamlr.core.bridge import YamlrBridge
        if YamlrBridge.is_pro_enabled():
            return

        from datetime import date
        import json
        
        quota_path = UsageLimiter.get_quota_path()
        import sys
        
        quota_path = UsageLimiter.get_quota_path()
        today_str = date.today().isoformat()
        
        current_usage = 0
        if quota_path.exists():
            try:
                stats = json.loads(quota_path.read_text())
                if stats.get("date") == today_str:
                    current_usage = stats.get("usage", 0)
            except Exception:
                pass

        new_usage = current_usage + files_count
        new_stats = {
            "date": today_str,
            "usage": new_usage,
            "sig": UsageLimiter._get_quota_signature(new_usage, today_str)
        }
        quota_path.write_text(json.dumps(new_stats))

    @staticmethod
    def check_healing_quota(files_requested: int) -> Tuple[bool, int, str]:
        """Wrapper that checks and records usage if allowed."""
        allowed, remaining, msg = UsageLimiter.is_healing_allowed(files_requested)
        if allowed:
            UsageLimiter.record_healing_usage(files_requested)
            new_remaining = remaining - files_requested if remaining != -1 else -1
            return True, new_remaining, ""
        return False, remaining, msg

    @staticmethod
    def get_remaining_quota() -> int:
        """Returns the number of free heals remaining today."""
        _, remaining, _ = UsageLimiter.is_healing_allowed(0)
        return remaining if remaining != -1 else 999999
