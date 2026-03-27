"""
Yamlr Pro: Rate Limiter Tests
-----------------------------
Validates token-bucket logic and persistence.
"""

import os
import json
import time
import pytest
from pathlib import Path
from yamlr.pro.rate_limiter import ProRateLimiter

@pytest.fixture
def clean_limiter(tmp_path):
    # Mock home for the limiter
    state_file = tmp_path / ".yamlr" / "quota.json"
    limiter = ProRateLimiter()
    limiter._state_file = state_file
    limiter._bucket_state = {}
    return limiter

def test_token_bucket_decrement(clean_limiter):
    user = "test_user"
    op = "opa"
    
    # 1st attempt: Allowed, tokens = 4
    assert clean_limiter.is_allowed(user, op, tier="free") is True
    assert clean_limiter._bucket_state[user][op][0] == pytest.approx(4.0)

def test_token_exhaustion(clean_limiter):
    user = "test_exhaust"
    op = "shield"
    
    # Shield has 10 burst for free
    for _ in range(10):
        assert clean_limiter.is_allowed(user, op, tier="free") is True
        
    assert clean_limiter.is_allowed(user, op, tier="free") is False

def test_tier_multipliers(clean_limiter):
    user_pro = "pro_user"
    op = "opa" # Default 5 burst
    
    # Pro gets 5x multiplier -> 25 tokens
    for _ in range(25):
        assert clean_limiter.is_allowed(user_pro, op, tier="pro") is True
        
    assert clean_limiter.is_allowed(user_pro, op, tier="pro") is False

def test_persistence(tmp_path):
    state_file = tmp_path / ".yamlr" / "quota.json"
    user = "persist_user"
    op = "kyverno"
    
    # 1. Create limiter and use a token
    limiter1 = ProRateLimiter()
    limiter1._state_file = state_file
    assert limiter1.is_allowed(user, op, tier="free") is True
    
    # Verify file saved
    assert state_file.exists()
    
    # 2. Create new limiter instance (simulating new CLI run)
    limiter2 = ProRateLimiter()
    limiter2._state_file = state_file
    limiter2._load_state()
    
    # Verify state loaded (tokens should be 4)
    assert user in limiter2._bucket_state
    assert limiter2._bucket_state[user][op][0] == pytest.approx(4.0)

def test_refill_logic(clean_limiter):
    user = "refill_user"
    op = "opa" # 5 capacity
    
    # Exhaust tokens
    for _ in range(5):
        clean_limiter.is_allowed(user, op, tier="free")
        
    assert clean_limiter.is_allowed(user, op, tier="free") is False
    
    # Mock time jump forward (1 hour)
    # opa refill is 5 per hour (1/720 per sec)
    clean_limiter._bucket_state[user][op] = (0.0, time.time() - 3600)
    
    # Should be refilled and allowed
    assert clean_limiter.is_allowed(user, op, tier="free") is True
