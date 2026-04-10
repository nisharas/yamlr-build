#!/usr/bin/env python3
"""
Yamlr Forensic Logger - Security-First Debugging
------------------------------------------------
Provides gated, redacted logging for deep structural forensics.
Why: To prevent sensitive data leakage (PII) into debug logs while
     maintaining acquisition-ready auditability for expert users.
"""

import os
import re
from typing import Any, Dict, List, Optional


class ForensicLogger:
    """
    Centralized controller for forensic logging (DNA, PE, Lex).
    """

    SECRET_KEYS = {
        "password",
        "token",
        "secret",
        "key",
        "auth",
        "credential",
        "data",
        "stringData",
        "binaryData",
        "encryptedData",
    }

    @staticmethod
    def redact(msg: str) -> str:
        """Redacts values in a 'key=value' or 'key: value' string if key is sensitive."""

        def replacer(match):
            key = match.group(1).lower()
            if any(sk in key for sk in ForensicLogger.SECRET_KEYS):
                return f"{match.group(1)}{match.group(2)}[REDACTED]"
            return match.group(0)

        # Match key=value or key: value
        pattern = r"(\w+)([=:]\s*)[^\s,]+"
        return re.sub(pattern, replacer, msg)

    @staticmethod
    def get_log_dir() -> str:
        """Determines the absolute path for the logs directory."""
        # [M&A Readiness] Use a dedicated logs/ folder instead of the root
        log_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError:
                return os.getcwd()  # Fallback to current dir
        return log_dir

    @staticmethod
    def log(filename: str, msg: str, enabled: bool = False, append: bool = True):
        """Writes a redacted message to a forensic journal with ACID-lite durability."""
        if not enabled:
            return

        redacted_msg = ForensicLogger.redact(msg)
        log_path = os.path.join(ForensicLogger.get_log_dir(), filename)
        tmp_path = f"{log_path}.tmp"

        try:
            import portalocker
            # [Phase 11] Journal ACID Recovery: 
            # If not appending, use atomic tmp-move pattern.
            if not append:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    portalocker.lock(f, portalocker.LockFlags.EXCLUSIVE)
                    f.write(redacted_msg + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, log_path)
            else:
                # Durable Append Pattern
                with open(log_path, "a", encoding="utf-8") as f:
                    portalocker.lock(f, portalocker.LockFlags.EXCLUSIVE)
                    f.write(redacted_msg + "\n")
                    f.flush()
                    os.fsync(f.fileno())
        except (IOError, ImportError) as e:
            # Silent fallback if portalocker is missing or I/O fails
            # but log a warning if possible in a non-looping way
            if os.path.exists(tmp_path):
                try: os.unlink(tmp_path)
                except: pass

    @staticmethod
    def calculate_manifest_hash(doc: Any) -> str:
        """
        Calculates a deterministic hash for a manifest.
        Why: Ensures consistent forensic IDs regardless of field ordering.
        """
        import hashlib
        import json

        def _sort_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: _sort_recursive(obj[k]) for k in sorted(obj.keys())}
            if isinstance(obj, list):
                return [_sort_recursive(i) for i in obj]
            return obj

        sorted_doc = _sort_recursive(doc)
        # [Phase 7] Deterministic Rotation: Canonical JSON representation
        data = json.dumps(sorted_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
