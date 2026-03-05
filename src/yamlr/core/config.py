"""
Yamlr CONFIGURATION MANAGER
------------------------------
Handles loading and parsing of user configuration (.yamlr.yaml).
Allows customization of:
- Rule ignore patterns (glob-based)
- Health thresholds
- Analyzer settings
"""

import logging
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

logger = logging.getLogger("yamlr.config")


class ConfigManager:
    """
    Manages user configuration state.
    defaults:
      threshold: 70
      ignore: []
    """

    DEFAULT_CONFIG = {
        "rules": {
            "threshold": 70,
            "ignore": [".git/*", "node_modules/*", "venv/*", "__pycache__/*"],
        },
        "kubernetes": {"version": "v1.31"},
        "analyzers": {"enabled": ["*"]},
        "security": {"allowed_host_paths": []},
        "healing": {
            "enforce_limits": False,
            "harden": False,
            "enforce_probes": False,
            "fix_tags": False,
            "check_deprecations": False,
            "enforce_namespace": False,
        },
        "ignore": {
            "files": []
        }
    }

    def __init__(self, workspace_root: Path, app_name: str = "Yamlr"):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.workspace = Path(workspace_root)
        self.app_name = app_name
        self.config_path = None
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()

    def _load_config(self):
        """
        Attempts to load configuration by walking UP the directory tree.
        Stops walking if it hits a .git directory or the filesystem root.
        Looks for:
        1. .<app_name>/config.yaml
        2. .<app_name>.yaml
        3. .yamlr.yaml
        """
        yaml = YAML(typ="safe")
        current_dir = self.workspace.resolve()

        while True:
            # 1. State Directory Config
            state_config = current_dir / f".{self.app_name}" / "config.yaml"

            # 2. Root File Configs
            possible_files = [
                state_config,
                current_dir / f".{self.app_name}.yaml",
                current_dir / ".yamlr.yaml",
            ]

            for path in possible_files:
                if path.exists():
                    try:
                        loaded = yaml.load(path)
                        if loaded:
                            self._merge_config(loaded)
                        self.config_path = path
                        logger.debug(f"Loaded configuration from {path}")
                        return
                    except Exception as e:
                        logger.warning(f"Failed to parse {path.name}: {e}")
            
            # Stop if we hit a git root or the filesystem root
            if (current_dir / ".git").exists() or current_dir.parent == current_dir:
                break
            
            # Move up one directory level
            current_dir = current_dir.parent

    def _merge_config(self, user_config: Dict[str, Any]):
        """Deep merge of user config into defaults."""
        # Simple depth-1 merge for now, can be expanded if needed
        if "rules" in user_config:
            self.config["rules"].update(user_config["rules"])
        if "analyzers" in user_config:
            self.config["analyzers"].update(user_config["analyzers"])
        if "security" in user_config:
            self.config["security"].update(user_config["security"])
        if "healing" in user_config:
            self.config["healing"].update(user_config["healing"])
        if "kubernetes" in user_config:
            self.config["kubernetes"].update(user_config["kubernetes"])
        if "ignore" in user_config:
            # Handle both flat list and nested 'files' key
            user_ignore = user_config["ignore"]
            if isinstance(user_ignore, list):
                self.config["ignore"]["files"].extend(user_ignore)
            elif isinstance(user_ignore, dict):
                self.config["ignore"].update(user_ignore)

    def is_ignored(self, file_path: str, rule_id: Optional[str] = None) -> bool:
        """
        Determines if a file or rule should be ignored.

        Args:
            file_path: Relative path to the file.
            rule_id: Optional rule ID (e.g., 'rules/no-latest-tag').

        Returns:
            True if ignored, False otherwise.
        """
        # 1. Check Rule-specific ignores
        rule_ignores = self.config["rules"].get("ignore", [])
        if rule_id and rule_id in rule_ignores:
            return True

        # 2. Check File-level ignores (from both sections for compatibility)
        file_ignores = self.config["ignore"].get("files", [])
        # Also check rules.ignore for wildcard patterns that might be file-based
        file_ignores.extend([p for p in rule_ignores if "*" in p or "/" in p])

        for pattern in file_ignores:
            if fnmatch(file_path, pattern):
                return True

        return False

    @property
    def health_threshold(self) -> int:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["rules"].get("threshold", 70)

    @property
    def allowed_host_paths(self) -> List[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["security"].get("allowed_host_paths", [])

    @property
    def enforce_limits(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["healing"].get("enforce_limits", False)

    @property
    def harden(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["healing"].get("harden", False)

    @property
    def enforce_probes(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["healing"].get("enforce_probes", False)

    @property
    def fix_tags(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config["healing"].get("fix_tags", False)

    @property
    def kubernetes_version(self) -> Optional[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config.get("kubernetes", {}).get("version")

    @property
    def enforce_namespace(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config.get("healing", {}).get("enforce_namespace", False)

    @property
    def trusted_registries(self) -> List[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config.get("security", {}).get("trusted_registries", [])

    @property
    def check_deprecations(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.config.get("healing", {}).get("check_deprecations", False)

    def has_local_config(self) -> bool:
        """Checks if a valid configuration file was loaded."""
        return self.config_path is not None and self.config_path.exists()
