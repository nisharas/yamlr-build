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

DAILY_FREE_HEAL_LIMIT = 5

class UsageLimiter:
    """
    Enforces surgical limits for the Free tier.
    """
    
    DAILY_FREE_HEAL_LIMIT = 5

    @staticmethod
    def _get_quota_signature(usage: int, date_str: str) -> str:
        """Derives a machine-specific signature for the quota file."""
        import hashlib
        machine_id = YamlrBridge.get_machine_id()
        data = f"{usage}:{date_str}:{machine_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def is_healing_allowed(files_requested: int) -> Tuple[bool, int, str]:
        """Checks if healing is permitted based on current quota."""
        if YamlrBridge.is_pro_enabled():
            return True, -1, ""

        if files_requested > UsageLimiter.DAILY_FREE_HEAL_LIMIT:
             return False, 0, f"Batch healing is limited to {UsageLimiter.DAILY_FREE_HEAL_LIMIT} files per run on the Free tier."

        from yamlr.core.telemetry import GlobalTelemetryManager
        gtm = GlobalTelemetryManager()
        stats = gtm.data
        
        from datetime import date
        today_str = date.today().isoformat()
        
        last_date = stats.get("quota_date", "")
        current_usage = stats.get("daily_heals_count", 0)
        sig = stats.get("quota_sig", "")
        
        # [ROUND-12] Quota Integrity Resiliency
        # Why: Prevents blocking users if the telemetry file was partially 
        #      corrupted or the machine ID shifted slightly.
        if last_date != today_str:
            # It's a new day. We reset the usage regardless of signature.
            current_usage = 0
            logger.debug("New quota window detected. Resetting usage.")
        elif sig and sig != UsageLimiter._get_quota_signature(current_usage, last_date):
            # Error only if it's the SAME day but the signature is wrong.
            logger.warning("Quota integrity check failed. Enforcing conservative limit for the day.")
            current_usage = UsageLimiter.DAILY_FREE_HEAL_LIMIT

        if current_usage + files_requested > UsageLimiter.DAILY_FREE_HEAL_LIMIT:
            remaining = max(0, UsageLimiter.DAILY_FREE_HEAL_LIMIT - current_usage)
            return False, remaining, f"Daily free healing limit reached ({UsageLimiter.DAILY_FREE_HEAL_LIMIT} files/day). You have {remaining} remaining today."
            
        return True, UsageLimiter.DAILY_FREE_HEAL_LIMIT - current_usage, ""

    @staticmethod
    def record_healing_usage(files_count: int):
        """Persists the usage of the free tier quota."""
        if YamlrBridge.is_pro_enabled():
            return

        from yamlr.core.telemetry import GlobalTelemetryManager
        gtm = GlobalTelemetryManager()
        stats = gtm.data
        
        from datetime import date
        today_str = date.today().isoformat()
        
        last_date = stats.get("quota_date", "")
        current_usage = stats.get("daily_heals_count", 0) if last_date == today_str else 0
        
        new_usage = current_usage + files_count
        stats["quota_date"] = today_str
        stats["daily_heals_count"] = new_usage
        stats["quota_sig"] = UsageLimiter._get_quota_signature(new_usage, today_str)
        gtm.save()

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
