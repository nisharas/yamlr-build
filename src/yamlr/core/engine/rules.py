#!/usr/bin/env python3
"""
Yamlr RULE GOVERNANCE & METADATA
---------------------------------
Defines the Pydantic-backed metadata schema for all Yamlr rules.

Why: To ensure that every finding (AnalysisResult) is explainable, 
     actionable, and tied to a formal remediation resource.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class RuleSeverity(str):
    """
    Standard severity levels for findings.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class RuleMetadata(BaseModel):
    """
    Declarative metadata for a Yamlr healing/analysis rule.
    """
    id: str
    name: str
    description: str
    severity: str = "medium"
    impact: str = "Unknown"
    remediation: str = "No specialized remediation provided."
    external_url: Optional[str] = None
    category: str = "Forensic"
    reconciled_count: int = 0
    risk_level: str = "low"

    def get_remediation_link(self) -> str:
        """Returns the primary docs or issue link for this rule."""
        return self.external_url or f"https://docs.yamlr.com/rules/{self.id}"
