import os
import json
import pytest
from pathlib import Path
from yamlr.core.telemetry import TelemetryManager

def test_telemetry_lifecycle(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / ".yamlr").mkdir()
    
    tm = TelemetryManager(workspace)
    
    # Initial state
    stats = tm.get_stats()
    assert stats["total_scans"] == 0
    assert stats["total_fixed_issues"] == 0
    
    # Record a session
    tm.record_session(files_count=10, fixed_issues=5, avg_health_score=85.0, is_heal=True)
    
    # Verify update
    stats = tm.get_stats()
    assert stats["total_scans"] == 1
    assert stats["total_heals"] == 1
    assert stats["total_fixed_issues"] == 5
    assert stats["total_time_saved_minutes"] == 10.0
    assert stats["peak_health_score"] == 85.0
    
    # Verify persistence
    tm2 = TelemetryManager(workspace)
    assert tm2.get_stats()["total_scans"] == 1
    
    # Record another session with improvement
    tm.record_session(files_count=1, fixed_issues=2, avg_health_score=95.0, is_heal=True)
    assert tm.get_stats()["peak_health_score"] == 95.0
    assert tm.get_stats()["total_heals"] == 2
    assert tm.get_stats()["surgical_efficiency"] == 3.5 # (5+2)/2

def test_telemetry_rank_logic():
    # This logic is in welcome.py, but we can verify TelemetryManager handles raw data
    pass
