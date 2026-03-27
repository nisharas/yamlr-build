#!/usr/bin/env python3
"""
Yamlr TELEMETRY MANAGER - Habit Formation Infrastructure
---------------------------------------------------------
Handles persistent tracking of cumulative surgical metrics to drive user engagement.

Why: To provide a 'gamified' experience and mathematical proof of ROI (time saved) 
     without requiring an external database or cloud connectivity. Persistence 
     is local to the workspace to ensure privacy.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import portalocker

logger = logging.getLogger("yamlr.telemetry")
__all__ = ['TelemetryManager', 'GlobalTelemetryManager']

class GlobalTelemetryManager:
    """
    Manages machine-wide cumulative telemetry across all projects.
    
    Why: To provide 'Budget Justification' by showing the total impact 
         Yamlr has had on the entire engineering organization's codebase.
    """
    _instance: Optional[GlobalTelemetryManager] = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GlobalTelemetryManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, app_name: str = "yamlr"):
        if getattr(self, "_initialized", False):
            return
        self.path = Path.home() / f".{app_name}" / "global_stats.json"
        self._data: Optional[Dict[str, Any]] = None
        self._salt: Optional[str] = None
        self._initialized = True

    def _get_machine_salt(self) -> str:
        """Returns a stable, machine-specific salt for path masking."""
        if self._salt: return self._salt
        import hashlib
        import platform
        # Machine-specific seed: node + processor + platform
        seed = f"{platform.node()}-{platform.processor()}-{platform.system()}"
        self._salt = hashlib.sha256(seed.encode()).hexdigest()[:16]
        return self._salt

    @property
    def data(self) -> Dict[str, Any]:
        """Lazy-loads the telemetry data."""
        if self._data is None:
            self._data = self._load()
        return self._data

    def _load(self) -> Dict[str, Any]:
        default_state = {
            "total_projects": 0,
            "total_scans": 0,
            "total_heals": 0,
            "total_fixed_issues": 0,
            "total_time_saved_minutes": 0.0,
            "known_workspaces": []
        }
        if not self.path.exists(): return default_state
        try:
            # Optimized read: check size first
            if self.path.stat().st_size > 10 * 1024 * 1024: # 10MB
                logger.warning(f"Global telemetry file is large ({self.path.stat().st_size / 1024 / 1024:.2f} MB). Performance may be impacted.")
            
            with portalocker.Lock(self.path, "r", encoding="utf-8", timeout=5) as f:
                return {**default_state, **json.load(f)}
        except Exception as e: 
            logger.debug(f"Global telemetry load failed: {e}")
            return default_state

    def save(self):
        if self._data is None: return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic-ish write with platform lock
            with portalocker.Lock(self.path, "w", encoding="utf-8", timeout=5) as f:
                json.dump(self._data, f, separators=(",", ":")) # Compact JSON for speed
        except Exception as e:
            logger.error(f"Global telemetry save failed: {e}")

    def record_global(self, 
                      workspace_path: str,
                      fixed_issues: int, 
                      time_saved_minutes: float,
                      is_heal: bool = False):
        data = self.data # Trigger lazy load
        data["total_scans"] += 1
        if is_heal: data["total_heals"] += 1
        data["total_fixed_issues"] += fixed_issues
        data["total_time_saved_minutes"] += time_saved_minutes
        
        # [Security] Privacy Anonymization with Machine Salt
        ws_p = Path(workspace_path)
        import hashlib
        salt = self._get_machine_salt()
        raw_path = str(ws_p.absolute())
        path_hash = hashlib.sha256(f"{salt}:{raw_path}".encode()).hexdigest()[:12]
        project_id = f"Project-{path_hash}"
        
        if project_id not in data["known_workspaces"]:
            data["known_workspaces"].append(project_id)
            data["total_projects"] = len(data["known_workspaces"])
        
        # Optimization: Don't save for every atomic scan if we want true hyperscale, 
        # but for now, the compact JSON write is faster.
        self.save()

    def record_pro_usage(self, feature: str, value: int = 1):
        """Records usage of an enterprise feature."""
        pro_stats = self.data.setdefault("pro_usage", {})
        pro_stats[feature] = pro_stats.get(feature, 0) + value
        self.save()

    def get_org_summary(self) -> Dict[str, Any]:
        """
        Aggregates metrics across all known workspaces into a company-wide report.
        
        Why: To provide the 'Big Picture' ROI for CTO/Founder visibility.
        """
        data = self.data
        return {
            "org_impact": {
                "total_projects": data.get("total_projects", 0),
                "total_surgical_events": data.get("total_scans", 0),
                "total_heals": data.get("total_heals", 0),
                "total_fixed_issues": data.get("total_fixed_issues", 0),
                "total_hours_saved": round(data.get("total_time_saved_minutes", 0) / 60, 1)
            },
            "efficiency_metrics": {
                "avg_fixes_per_project": round(data.get("total_fixed_issues", 0) / data.get("total_projects", 1), 1),
                "adoption_depth": len(data.get("pro_usage", {})),
            },
            "pro_usage": data.get("pro_usage", {})
        }

class PulseManager:
    """
    Founder Analytics & Strategic Intelligence Manager.
    
    Why: Provides the 'Pulse' of the product ecosystem to the founder.
         Focuses on growth metrics and rule efficacy without touching user code.
    """
    def __init__(self):
        self.gtm = GlobalTelemetryManager()

    def get_founder_intelligence(self) -> Dict[str, Any]:
        """Aggregates machine-wide metrics into an executive summary."""
        data = self.gtm.data
        return {
            "ecosystem_health": {
                "total_workspaces": data.get("total_projects", 0),
                "total_surgical_events": data.get("total_scans", 0),
                "total_fixes": data.get("total_fixed_issues", 0),
                "cumulative_hours_saved": round(data.get("total_time_saved_minutes", 0) / 60, 1)
            },
            "pro_adoption": data.get("pro_usage", {}),
            "anonymized_projects": data.get("known_workspaces", [])[:10], # Limit for CLI display
            "engine_version": "1.1.0-commercial"
        }

    def record_pulse_event(self, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Records a strategic event (e.g., 'first_pro_login', 'large_repo_scan')."""
        events = self.gtm.data.setdefault("founder_events", [])
        import time
        events.append({
            "type": event_type,
            "timestamp": time.time(),
            "meta": metadata or {}
        })
        # Keep only the last 100 strategic events to prevent bloat
        self.gtm.data["founder_events"] = events[-100:]
        self.gtm.save()

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
            "peak_dna_integrity_score": 0.0,
            "last_dna_integrity_score": 0.0,
            "surgical_efficiency": 0.0,
            "history": [] # List of {timestamp: ..., score: ...}
        }
        
        if not self.telemetry_path.exists():
            return default_state
            
        try:
            with portalocker.Lock(self.telemetry_path, "r", encoding="utf-8", timeout=5) as f:
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
            with portalocker.Lock(self.telemetry_path, "w", encoding="utf-8", timeout=5) as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")

    def record_session(self, 
                       files_count: int, 
                       fixed_issues: int, 
                       avg_dna_score: float,
                       is_heal: bool = False,
                       max_severity: str = "info",
                       max_risk: str = "low",
                       breakdown: Optional[Dict[str, int]] = None,
                       duration_seconds: float = 0.0,
                       bytes_processed: int = 0):
        """Updates cumulative metrics with session data."""
        self.data["total_scans"] += 1
        if is_heal:
            self.data["total_heals"] += 1
            
        self.data["total_fixed_issues"] += fixed_issues
        self.data["total_bytes_processed"] += bytes_processed
        self.data["total_execution_seconds"] += duration_seconds
        
        self._update_performance_metrics(files_count, duration_seconds)
        saved = self._calculate_and_apply_roi(fixed_issues, breakdown)
        self._sync_with_global_telemetry(fixed_issues, saved, is_heal)
        self._update_dna_and_history(avg_dna_score, files_count, duration_seconds, fixed_issues, max_severity, max_risk)
        
        self.data["last_max_severity"] = max_severity
        self.data["last_max_risk"] = max_risk
        self.save()

    def _update_performance_metrics(self, files_count: int, duration_seconds: float):
        """Updates FPS and Latency metrics."""
        if duration_seconds > 0 and files_count > 0:
            current_fps = files_count / duration_seconds
            if current_fps > self.data.get("peak_throughput_fps", 0.0):
                self.data["peak_throughput_fps"] = current_fps
            
            current_latency = (duration_seconds / files_count) * 1000 # ms
            if "avg_latency_ms" not in self.data or self.data["avg_latency_ms"] == 0:
                self.data["avg_latency_ms"] = current_latency
            else:
                self.data["avg_latency_ms"] = (self.data["avg_latency_ms"] * 0.9) + (current_latency * 0.1)

    def _calculate_and_apply_roi(self, fixed_issues: int, breakdown: Optional[Dict[str, int]]) -> float:
        """Calculates time saved based on fix weights."""
        if breakdown:
            saved = (breakdown.get("lexer_repairs", 0) * 2.0 +
                     breakdown.get("lexer_typos", 0) * 2.0 +
                     breakdown.get("semantic_repairs", 0) * 15.0 +
                     breakdown.get("security_hardens", 0) * 30.0 +
                     breakdown.get("migrator_changes", 0) * 60.0)
        else:
            saved = fixed_issues * 5.0
        
        self.data["total_time_saved_minutes"] += saved
        return saved

    def _sync_with_global_telemetry(self, fixed_issues: int, saved: float, is_heal: bool):
        """Syncs workspace stats to the global machine-wide manager."""
        try:
            gtm = GlobalTelemetryManager()
            gtm.record_global(
                workspace_path=str(self.workspace),
                fixed_issues=fixed_issues,
                time_saved_minutes=saved,
                is_heal=is_heal
            )
        except Exception as e:
            logger.debug(f"Global telemetry sync failed: {e}")

    def _update_dna_and_history(self, avg_dna_score: float, files_count: int, duration_seconds: float, 
                                fixed_issues: int, max_severity: str, max_risk: str):
        """Updates DNA peaks and creates a history entry."""
        self.data["last_dna_integrity_score"] = avg_dna_score
        if avg_dna_score > self.data["peak_dna_integrity_score"]:
            self.data["peak_dna_integrity_score"] = avg_dna_score
            
        if self.data["total_heals"] > 0:
            self.data["surgical_efficiency"] = self.data["total_fixed_issues"] / self.data["total_heals"]

        import time
        self.data["history"].append({
            "timestamp": time.time(),
            "score": avg_dna_score,
            "fixed": fixed_issues,
            "max_severity": max_severity,
            "max_risk": max_risk,
            "throughput_fps": files_count / duration_seconds if duration_seconds > 0 else 0
        })
        self.data["history"] = self.data["history"][-50:]

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
