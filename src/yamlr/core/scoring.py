#!/usr/bin/env python3
"""
Yamlr SCORING ENGINE - The Credit Scorer
----------------------------------------
Consolidates all manifest health scoring logic.
Eliminates fragmented penalty calculations across the pipeline.
"""

from enum import Enum
from typing import Dict, List, Any
from yamlr.analyzers.rules import Rules

class Severity(Enum):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    INFO = 100
    WARNING = 200
    ERROR = 300

class ScoringEngine:
    """
    Centralized service for calculating manifest health scores.
    """
    
    # Penalty mapping: RuleID -> Deduction points
    PENALTIES = {
        # Lexical/Syntax Errors (Max 30)
        "LEX_FLUSH_LEFT": 2,
        "LEX_QUOTE_ERR": 3,
        "LEX_SPACING": 1,
        
        # Schema Validation (Max 50)
        "SCHEMA_MISMATCH": 5,
        
        # Cross-Resource Analyzers
        Rules.GHOST_SERVICE: 10,
        Rules.ORPHAN_RESOURCE: 3,
        Rules.BROKEN_VOLUME: 15,
        
        # Best Practices (Content)
        "BEST_PRACTICE_WARN": 3,
        "BEST_PRACTICE_ERR": 10,
    }

    @staticmethod
    def calculate_penalty(rule_id: str, severity: str = "WARNING") -> int:
        """
        Returns the deduction points for a specific rule violation.
        """
        # Normalize severity
        sev = severity.upper()
        
        # Try specific rule ID first
        if rule_id in ScoringEngine.PENALTIES:
            return ScoringEngine.PENALTIES[rule_id]
        
        # Default by severity
        if sev == "ERROR":
            return 10
        elif sev == "WARNING":
            return 3
        return 0

    @staticmethod
    def get_severity_label(severity: str) -> str:
        """
        Normalizes severity labels to uppercase.
        """
        return severity.upper()
