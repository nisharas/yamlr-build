#!/usr/bin/env python3
"""
Yamlr EXCEPTIONS - The Diagnostic Repository
--------------------------------------------
Standardized exception hierarchy for high-fidelity error reporting.
Every exception includes a 'remediation' hint for the Chief Surgeon.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-03
"""

from __future__ import annotations
from typing import Optional
__all__ = ['YamlrError', 'YamlrSecurityError', 'YamlrParseError', 'YamlrValidationError', 'YamlrIdentityError', 'YamlrEngineError', 'YamlrBridgeError', 'YamlrQuotaError']


class YamlrError(Exception):
    """Base exception for all Yamlr-related errors."""
    def __init__(self, message: str, remediation: Optional[str] = None):
        """Initializes a Yamlr error with an optional remediation hint.
        
        Why: To provide consistent error handling and user guidance.
        """
        super().__init__(message)
        self.message = message
        self.remediation = remediation or "No automated remediation available. Please check the logs."

    def __str__(self):
        """
        Why: Ensures sensitive system paths are masked in all user-facing errors. [PARTIAL-1]
        """
        from yamlr.core.logging_config import mask_path
        masked_msg = mask_path(self.message)
        masked_rem = mask_path(self.remediation)
        return f"{masked_msg} (Hint: {masked_rem})"

class YamlrSecurityError(YamlrError):
    """Raised when a security boundary (e.g. Path Anchoring) is violated."""
    def __init__(self, message: str, remediation: Optional[str] = "Ensure the file is within the allowed host paths or the current workspace."):
        """Initializes a security-related error."""
        super().__init__(message, remediation)

class YamlrParseError(YamlrError):
    """Raised when the Lexer or Structurer fails to process the YAML stream."""
    def __init__(self, message: str, remediation: Optional[str] = "Check for extremely malformed syntax like unclosed triple quotes or binary data."):
        """Initializes a parsing-related error."""
        super().__init__(message, remediation)

class YamlrValidationError(YamlrError):
    """Raised when strict validation is enabled and the manifest fails schema checks."""
    def __init__(self, message: str, remediation: Optional[str] = "Validate the manifest against the target Kubernetes version schema."):
        """Initializes a validation-related error."""
        super().__init__(message, remediation)

class YamlrIdentityError(YamlrError):
    """Raised when a file cannot be identified as a Kubernetes resource in strict mode."""
    def __init__(self, message: str, remediation: Optional[str] = "Ensure 'kind' and 'apiVersion' are present at the root level, or use '--identity-mode infer'."):
        """Initializes an identity-related error."""
        super().__init__(message, remediation)

class YamlrEngineError(YamlrError):
    """Raised when an internal orchestration or pipeline stage crashes."""
    def __init__(self, message: str, remediation: Optional[str] = "This may be a bug in the healing orchestrator. Please report it with the trace log."):
        """Initializes an engine-related error."""
        super().__init__(message, remediation)

class YamlrBridgeError(YamlrError):
    """Raised when the Yamlr Enterprise (Pro) bridge fails to load pro features."""
    def __init__(self, message: str, remediation: Optional[str] = "Check your Yamlr Enterprise (Pro) installation and license status."):
        """Initializes a bridge-related error."""
        super().__init__(message, remediation)

class YamlrQuotaError(YamlrError):
    """Raised when the free tier healing quota is exceeded."""
    def __init__(self, message: str, remediation: Optional[str] = "Visit https://yamlr.dev/pro to upgrade to Yamlr Pro for unlimited healing."):
        """
        Why: To provide a clear, actionable error when licensing limits are hit, 
             driving conversion to Pro.
        """
        super().__init__(message, remediation)
