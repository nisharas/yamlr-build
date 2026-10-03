"""Feature flags and gates for preview features."""
import os


def is_experimental_enabled() -> bool:
    """Check if experimental features are enabled via environment variable.

    Returns:
        True if YAMLR_EXPERIMENTAL is set to a truthy value.
    """
    return os.getenv("YAMLR_EXPERIMENTAL", "").lower() in ("1", "true", "yes")
