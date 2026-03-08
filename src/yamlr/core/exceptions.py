#!/usr/bin/env python3
"""
Yamlr EXCEPTIONS - The Diagnostic Repository
--------------------------------------------
Standardized exception hierarchy for high-fidelity error reporting.
Every exception includes a 'remediation' hint for the Chief Surgeon.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-03
"""

from typing import Optional

class YamlrError(Exception):
    """Base exception for all Yamlr-related errors."""
    def __init__(self, message: str, remediation: Optional[str] = None):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message)
        self.message = message
        self.remediation = remediation or "No automated remediation available. Please check the logs."

    def __str__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return f"{self.message} (Hint: {self.remediation})"

class YamlrSecurityError(YamlrError):
    """Raised when a security boundary (e.g. Path Anchoring) is violated."""
    def __init__(self, message: str, remediation: Optional[str] = "Ensure the file is within the allowed host paths or the current workspace."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)

class YamlrParseError(YamlrError):
    """Raised when the Lexer or Structurer fails to process the YAML stream."""
    def __init__(self, message: str, remediation: Optional[str] = "Check for extremely malformed syntax like unclosed triple quotes or binary data."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)

class YamlrValidationError(YamlrError):
    """Raised when strict validation is enabled and the manifest fails schema checks."""
    def __init__(self, message: str, remediation: Optional[str] = "Validate the manifest against the target Kubernetes version schema."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)

class YamlrIdentityError(YamlrError):
    """Raised when a file cannot be identified as a Kubernetes resource in strict mode."""
    def __init__(self, message: str, remediation: Optional[str] = "Ensure 'kind' and 'apiVersion' are present at the root level, or use '--identity-mode infer'."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)

class YamlrEngineError(YamlrError):
    """Raised when an internal orchestration or pipeline stage crashes."""
    def __init__(self, message: str, remediation: Optional[str] = "This may be a bug in the healing orchestrator. Please report it with the trace log."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)

class YamlrBridgeError(YamlrError):
    """Raised when the Yamlr Enterprise bridge fails to load pro features."""
    def __init__(self, message: str, remediation: Optional[str] = "Check your Yamlr Enterprise installation and license status."):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__(message, remediation)
