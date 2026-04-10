#!/usr/bin/env python3
"""
Yamlr PIPELINE UTILS
--------------------
Shared utilities for the modular pipeline.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("yamlr.pipeline.utils")
__all__ = ["diff_dicts", "detect_manifest_changes"]


def diff_dicts(d1: Dict, d2: Dict, path: str = "") -> List[str]:
    """Recursively find changed keys."""
    changes = []
    all_keys = set(d1.keys()) | set(d2.keys())
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        if key not in d1:
            changes.append(f"+{current_path}")
        elif key not in d2:
            changes.append(f"-{current_path}")
        elif d1[key] != d2[key]:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                changes.extend(diff_dicts(d1[key], d2[key], current_path))
            else:
                changes.append(f"~{current_path}")
    return changes


def detect_manifest_changes(before: List[Dict[str, Any]], after: List[Dict[str, Any]]) -> List[str]:
    """Detects which keys changed between versions."""
    changes = []
    if len(before) != len(after):
        changes.append(f"Document count changed: {len(before)} → {len(after)}")
        return changes
    for i, (doc_before, doc_after) in enumerate(zip(before, after, strict=False)):
        changed_keys = diff_dicts(doc_before, doc_after)
        if changed_keys:
            doc_name = doc_after.get("metadata", {}).get("name", f"doc-{i}")
            changes.append(f"{doc_name}: {', '.join(changed_keys[:5])}")
    return changes
