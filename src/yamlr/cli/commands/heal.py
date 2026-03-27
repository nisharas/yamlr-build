from yamlr.core.entrypoints.heal import handle_heal_command
import os

__all__ = ["handle_heal_command", "is_ci_environment"]

def is_ci_environment() -> bool:
    """Detects if the current environment is a CI/CD pipeline."""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
