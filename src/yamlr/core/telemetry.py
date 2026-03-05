#!/usr/bin/env python3
"""
Yamlr TELEMETRY MANAGER - Habit Formation Infrastructure
---------------------------------------------------------
Handles persistent tracking of cumulative surgical metrics to drive user engagement.

Why: To provide a 'gamified' experience and mathematical proof of ROI (time saved) 
     without requiring an external database or cloud connectivity. Persistence 
     is local to the workspace to ensure privacy.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.telemetry")

class TelemetryManager:
    """
    Manages workspace-specific surgical telemetry.
    
    Why: To track cumulative 'Magic Moments' and health score improvements over time.
    """
    
    def __init__(self, workspace: Path, app_name: str = "yamlr"):
        """
        Initializes telemetry storage in the hidden workspace directory.
        
        Why: Ensures metrics are portable with the project but hidden from regular view.
        """
        self.workspace = workspace
        self.telemetry_path = workspace / f".{app_name}" / "telemetry.json"
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """
        Loads telemetry data from JSON.
        
        Why: Persistence layer for local metrics.
        """
        default_state = {
            "total_scans": 0,
            "total_heals": 0,
            "total_fixed_issues": 0,
            "total_time_saved_minutes": 0.0,
            "total_bytes_processed": 0,
            "total_execution_seconds": 0.0,
            "peak_throughput_fps": 0.0, # Files per second
            "peak_health_score": 0.0,
            "last_health_score": 0.0,
            "surgical_efficiency": 0.0,
            "history": [] # List of {timestamp: ..., score: ...}
        }
        
        if not self.telemetry_path.exists():
            return default_state
            
        try:
            with open(self.telemetry_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                # Merge with default_state to ensure all keys exist (Legacy Support)
                return {**default_state, **loaded_data}
        except Exception as e:
            logger.warning(f"Could not load telemetry: {e}")
            return default_state

    def save(self):
        """
        Commits current state to disk.
        
        Why: Ensures 'Magic Moments' are preserved across CLI sessions.
        """
        try:
            self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.telemetry_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")

    def record_session(self, 
                       files_count: int, 
                       fixed_issues: int, 
                       avg_health_score: float,
                       is_heal: bool = False,
                       max_severity: str = "info",
                       max_risk: str = "low",
                       breakdown: Optional[Dict[str, int]] = None,
                       duration_seconds: float = 0.0,
                       bytes_processed: int = 0):
        """
        Updates cumulative metrics with session data.
        
        Why: Aggregates atomic CLI runs into a holistic project health narrative.
        """
        self.data["total_scans"] += 1
        if is_heal:
            self.data["total_heals"] += 1
            
        self.data["total_fixed_issues"] += fixed_issues
        self.data["total_bytes_processed"] += bytes_processed
        self.data["total_execution_seconds"] += duration_seconds
        
        if duration_seconds > 0 and files_count > 0:
            current_fps = files_count / duration_seconds
            if current_fps > self.data.get("peak_throughput_fps", 0.0):
                self.data["peak_throughput_fps"] = current_fps
        
        # [GTM-03-2] Complexity-Based Time-Saved Estimation
        # Weights (Minutes): Lexer=2, Semantic=15, Security=20, Migration=45
        if breakdown:
            saved = (breakdown.get("lexer_repairs", 0) * 2.0 +
                     breakdown.get("lexer_typos", 0) * 2.0 +
                     breakdown.get("semantic_repairs", 0) * 15.0 +
                     breakdown.get("security_hardens", 0) * 20.0 +
                     breakdown.get("migrator_changes", 0) * 45.0)
            self.data["total_time_saved_minutes"] += saved
        else:
            # Fallback for old/legacy calls (Conservative baseline)
            self.data["total_time_saved_minutes"] += fixed_issues * 5.0 # Increased from 2.0 to 5.0 for realistic manual fix time
        
        self.data["last_health_score"] = avg_health_score
        if avg_health_score > self.data["peak_health_score"]:
            self.data["peak_health_score"] = avg_health_score
            
        # Surgical Efficiency: ratio of fixed issues to total issues detected is harder to track 
        # cumulatively without 'total detected' history, but we can track 'fixes per heal'.
        if self.data["total_heals"] > 0:
            self.data["surgical_efficiency"] = self.data["total_fixed_issues"] / self.data["total_heals"]

        # Track history (limit to last 50 entries)
        import time
        self.data["history"].append({
            "timestamp": time.time(),
            "score": avg_health_score,
            "fixed": fixed_issues,
            "max_severity": max_severity,
            "max_risk": max_risk,
            "throughput_fps": files_count / duration_seconds if duration_seconds > 0 else 0
        })
        self.data["history"] = self.data["history"][-50:]
        
        # Store for immediate lookup by CLI (Persistent)
        self.data["last_max_severity"] = max_severity
        self.data["last_max_risk"] = max_risk
        
        self.save()

    @property
    def last_max_severity(self) -> str:
        """Helper to access the most recent session's peak severity."""
        return self.data.get("last_max_severity", "info")

    @property
    def last_max_risk(self) -> str:
        """Helper to access the most recent session's peak risk level."""
        return self.data.get("last_max_risk", "low")

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns stats for UI consumption.
        
        Why: Abstraction for the dashboard display logic.
        """
        return self.data
