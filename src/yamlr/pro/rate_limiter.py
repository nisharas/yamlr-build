"""
Yamlr Enterprise (Pro): Rate Limiting
-------------------------------
Implements token-bucket rate limiting for Pro features to prevent abuse.
"""

from __future__ import annotations
import json
import time
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger("yamlr.pro.rate_limiter")

__all__ = ["ProRateLimiter", "pro_limiter"]

class ProRateLimiter:
    """
    Token-bucket rate limiter for enterprise operations.
    """
    
    # Defaults: (Capacity, Leak Rate per second)
    DEFAULT_LIMITS = {
        "shield": (10, 1.0 / 360.0),   # 10 burst, 10 per hour refill
        "opa": (5, 1.0 / 720.0),      # 5 burst, 5 per hour refill
        "kyverno": (5, 1.0 / 720.0),  # 5 burst, 5 per hour refill
    }

    def __init__(self):
        # Maps user_id -> operation -> (tokens, last_refill_time)
        self._bucket_state: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self._state_file = Path.home() / ".yamlr" / "quota.json"
        self._load_state()

    def _load_state(self):
        """Loads quota state from local file."""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r") as f:
                self._bucket_state = json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load quota state: {e}")

    def _save_state(self):
        """Saves current quota state to local file."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump(self._bucket_state, f)
        except Exception as e:
            logger.debug(f"Failed to save quota state: {e}")

    def is_allowed(self, user_id: str, operation: str, tier: str = "free") -> bool:
        """
        Checks if the operation is allowed for the user under the current quota. [CRITICAL-1]
        """
        if tier == "enterprise":
            return True # Enterprise has no rate limits for this MVP

        # Adjust limits based on tier (Pro gets 5x more than Free)
        multiplier = 5.0 if tier == "pro" else 1.0
        
        limit_config = self.DEFAULT_LIMITS.get(operation, (5, 1.0 / 3600.0))
        max_tokens = limit_config[0] * multiplier
        refill_rate = limit_config[1] * multiplier

        if user_id not in self._bucket_state:
            self._bucket_state[user_id] = {}
        
        if operation not in self._bucket_state[user_id]:
            self._bucket_state[user_id][operation] = (max_tokens - 1.0, time.time())
            self._save_state()
            return True

        tokens, last_refill = self._bucket_state[user_id][operation]
        now = time.time()
        
        # Refill tokens
        elapsed = now - last_refill
        refilled_tokens = min(max_tokens, tokens + (elapsed * refill_rate))
        
        if refilled_tokens >= 1.0:
            self._bucket_state[user_id][operation] = (refilled_tokens - 1.0, now)
            self._save_state()
            return True
        
        logger.warning(f"Rate limit exceeded for {user_id} on operation '{operation}'")
        return False

# Global Singleton
pro_limiter = ProRateLimiter()
