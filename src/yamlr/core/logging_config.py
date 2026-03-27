from __future__ import annotations

from pathlib import Path
import os

__all__ = ["YamlrLoggingConfig", "LogLevelType", "mask_path"]

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Literal

LogLevelType = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class JsonFormatter(logging.Formatter):
    """
    Structured JSON formatter for SRE/SIEM ingestion.
    Why: Enables machine-readable audit trails for surgical events.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Check for explicitly provided session_id or fallback to global
        session_id = getattr(record, "session_id", getattr(sys, "_yamlr_session_id", "N/A"))
        
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": session_id,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def emit_audit_entry(logger: logging.Logger, action: str, details: dict, session_id: str):
    """
    Streams specialized audit entries to the log.
    Why: Provides high-visibility 'Surgical Event' telemetry for SIEMs.
    """
    entry = {
        "event_type": "SURGICAL_AUDIT",
        "action": action,
        "details": details,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    # We use a custom level or just INFO with a specific flag
    logger.info(json.dumps(entry))

def mask_path(path: str | Path | None) -> str:
    """
    Masks absolute system paths to prevent information disclosure [MED-2/3].
    Replaces home directory with 'USER_HOME' and simplifies path exposure.
    """
    if path is None:
        return "None"
    p_str = str(path)
    try:
        # Mask Home / UserProfile
        home = str(Path.home())
        up = os.environ.get("USERPROFILE")
        sensitive_roots = [home]
        if up: sensitive_roots.append(up)
        
        for root in set(sensitive_roots):
            if root and root in p_str:
                p_str = p_str.replace(root, "~")
            
        # Mask Temp [PHASE-15]
        import tempfile
        tmp = tempfile.gettempdir()
        if tmp in p_str:
            p_str = p_str.replace(tmp, "[TMP]")
            
        # Mask CWD [PHASE-15]
        cwd = os.getcwd()
        if cwd in p_str:
            p_str = p_str.replace(cwd, ".")
            
    except Exception:
        pass
    return p_str

class YamlrLoggingConfig:
    """Centralized logging configuration for Yamlr.
    
    Why: To ensure consistent log formatting and level management across 
         all modules, especially for GitOps and CLI environments.
    """
    
    FORMATS = {
        "DEBUG": "[%(name)s:%(lineno)d] %(levelname)s: %(message)s",
        "INFO": "%(levelname)s: %(message)s",
        "AUDIT": "[AUDIT] %(asctime)s | %(message)s",
    }
    
    @classmethod
    def setup(cls, level: LogLevelType = "WARNING", audit_mode: bool = False, json_mode: bool = False):
        """Initialize structured logging across all Yamlr modules.
        
        Args:
            level: The logging level to set for the root 'yamlr' logger.
            audit_mode: Whether to enable specialized audit formatting.
            json_mode: Whether to use machine-readable JSON formatting.
        """
        root_logger = logging.getLogger("yamlr")
        
        # Clear existing handlers to prevent duplicates during re-initialization
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
            
        root_logger.setLevel(getattr(logging, level))
        
        if json_mode:
            formatter = JsonFormatter()
        else:
            # Use INFO format for anything non-DEBUG unless specialized
            fmt_key = "DEBUG" if level == "DEBUG" else "INFO"
            if audit_mode:
                fmt_key = "AUDIT"
            formatter = logging.Formatter(cls.FORMATS.get(fmt_key, cls.FORMATS["INFO"]))
        
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
        # Prevent propagation to the default root logger to avoid double-logging
        root_logger.propagate = False
