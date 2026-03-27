import pytest
from yamlr.core.scoring import ScoringEngine

def test_scoring_basic():
    engine = ScoringEngine()
    # Basic sanity check
    assert engine.calculate_penalty("unknown") == 3 # Default WARNING
    assert engine.calculate_penalty("unknown", severity="CRITICAL") >= 10
