"""Structured exception hierarchy for the Yamlr manifest engine."""


class YamlrError(Exception):
    """Base exception for all Yamlr domain errors."""


class NativeCoreError(YamlrError):
    """Raised when the Rust native acceleration layer encounters an unexpected error."""


class SchemaLoadError(YamlrError):
    """Raised when Kubernetes OpenAPI schemas cannot be loaded or parsed."""


class HealingError(YamlrError):
    """Raised when an atomic or AST manifest healing mutation fails."""


class LicenseError(YamlrError):
    """Raised when license token validation, signing, or decoding fails."""


class DiscoveryError(YamlrError):
    """Raised when manifest discovery or topology graph traversal fails."""


class YamlrExitCode:
    """Standardized deterministic POSIX exit codes across the Yamlr engine."""
    SUCCESS = 0       # Clean scan, heal applied successfully, or command succeeded
    VIOLATIONS = 1    # Manifest violations or safety warnings found (CI gate failure)
    SYNTAX_ERROR = 2  # Malformed YAML syntax, indentation failure, or unparseable blocks
    CONFIG_ERROR = 3  # Invalid arguments, flag error, or license validation failure
    SYSTEM_ERROR = 4  # File I/O failure, permission denied, or concurrency lock timeout

