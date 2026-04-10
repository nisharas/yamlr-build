"""
Yamlr CONFIGURATION MANAGER
------------------------------
Handles loading and parsing of user configuration (.yamlr.yaml).
Allows customization of:
- Rule ignore patterns (glob-based)
- Health thresholds
- Analyzer settings
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.config")


class ConfigManager:
    """Manages user configuration and workspace state.

    Why: To provide a centralized store for rules, security policies, and environment-specific settings.
    """

    DEFAULT_RUNTIME_DIR = ".yamlr_runtime"
    DEFAULT_INFERENCE_FALLBACK_VERSION = "1.28"

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
        "ignore": {"files": []},
    }

    def __init__(self, workspace_root: Path, app_name: str = "Yamlr"):
        """Initializes the configuration manager by resolving the workspace and loading config files.

        Why: To establish a single source of truth for the engine's behavior across different environments.
        Args:
            workspace_root: The root directory of the project to analyze.
            app_name: The name of the application (default: 'Yamlr').
        """
        self.workspace = Path(workspace_root)
        self.app_name = app_name
        self.config_path = None
        self.config = self.DEFAULT_CONFIG.copy()
        self.baseline_set = set()
        self._load_config()

    def _load_config(self):
        """
        Attempts to load configuration by walking UP the directory tree.
        Stops walking if it hits a .git directory or the filesystem root.
        """
        from yamlr.core.utils import get_hardened_yaml

        loader = get_hardened_yaml(typ="safe")
        current_dir = self.workspace.resolve()

        while True:
            if self._try_load_from_dir(current_dir, loader):
                return

            if self._is_root_or_git(current_dir):
                break
            current_dir = current_dir.parent

    def _try_load_from_dir(self, directory: Path, loader: Any) -> bool:
        """Helper to try loading config from a specific directory."""
        possible_files = [
            directory / f".{self.app_name}" / "config.yaml",
            directory / f".{self.app_name}.yaml",
            directory / ".yamlr.yaml",
        ]

        for path in possible_files:
            if path.exists():
                try:
                    loaded = loader.load(path)
                    if loaded:
                        # Ensure we have a plain dict for merging
                        config_data = loaded.to_dict() if hasattr(loaded, "to_dict") else loaded
                        self._merge_config(config_data)
                    self.config_path = path
                    logger.debug(f"Loaded configuration from {path}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to parse {path.name}: {e}")
        return False

    def _is_root_or_git(self, directory: Path) -> bool:
        """Checks if the directory is a git root or filesystem root."""
        return (directory / ".git").exists() or directory.parent == directory

    def _merge_config(self, user_config: Dict[str, Any]):
        """Deep merge of user config into defaults and invalidate cache."""
        # Simple depth-1 merge for now, can be expanded if needed
        if "rules" in user_config:
            self.config["rules"].update(user_config["rules"])
            # Alias support: exclude -> ignore
            if "exclude" in user_config["rules"]:
                self.config["rules"].setdefault("ignore", []).extend(user_config["rules"]["exclude"])
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

        # Invalidate compiled pattern cache
        self._compiled_ignore = None
        self._rule_ignore_cache = None

    def _get_compiled_ignore(self):
        """Compiles all file/wildcard ignore patterns into a single regex."""
        if hasattr(self, "_compiled_ignore") and self._compiled_ignore is not None:
            return self._compiled_ignore

        import re
        from fnmatch import translate

        rule_ignores = self.config["rules"].get("ignore", [])
        file_ignores = self.config["ignore"].get("files", [])

        # Consolidate all wildcard/path patterns
        all_patterns = list(file_ignores)
        all_patterns.extend([p for p in rule_ignores if "*" in p or "/" in p])

        if not all_patterns:
            self._compiled_ignore = False  # Sentinel for active but empty
            return False

        # Translate globs to regex and join with OR
        regex_str = "|".join(f"(?:{translate(p)})" for p in all_patterns)
        try:
            self._compiled_ignore = re.compile(regex_str)
        except Exception as e:
            logger.warning(f"Failed to compile ignore patterns: {e}")
            self._compiled_ignore = False

        return self._compiled_ignore

    def is_ignored(self, file_path: str, rule_id: Optional[str] = None) -> bool:
        """
        Determines if a file or rule should be ignored.
        Uses pre-compiled regex for O(1) matching vs patterns.
        """
        if not file_path:
            return False

        # 1. Check Rule-specific ignores (Exact string matching)
        if rule_id:
            if not hasattr(self, "_rule_ignore_cache") or self._rule_ignore_cache is None:
                self._rule_ignore_cache = set(self.config["rules"].get("ignore", []))
            if rule_id in self._rule_ignore_cache:
                return True

        # 2. Check File-level patterns (Regex matching)
        pattern = self._get_compiled_ignore()
        if pattern:  # If it's a compiled re object
            # Normalize path for matching (standardize separators)
            match_path = file_path.replace("\\", "/")
            if pattern.match(match_path):
                return True

        return False

    def load_baseline(self, baseline_path: Optional[str] = None):
        """Loads violation fingerprints from a baseline file.

        Why: To enable regression testing by ignoring known, existing issues.
        """
        import json

        path = Path(baseline_path) if baseline_path else self.workspace / ".yamlr-baseline.json"

        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.baseline_set = set(data)
                elif isinstance(data, dict) and "fingerprints" in data:
                    self.baseline_set = set(data["fingerprints"])
                logger.debug(f"Loaded {len(self.baseline_set)} fingerprints from baseline: {path}")
            except Exception as e:
                logger.warning(f"Failed to load baseline {path}: {e}")

    def is_baselined(self, finding: Dict[str, Any]) -> bool:
        """Checks if a finding matches a fingerprint in the baseline."""
        if not self.baseline_set:
            return False

        fingerprint = self.generate_finding_fingerprint(finding)
        return fingerprint in self.baseline_set

    @staticmethod
    def generate_finding_fingerprint(finding: Dict[str, Any]) -> str:
        """Generates a stable SHA256 fingerprint for a finding.

        Why: To uniquely identify a violation across different runs,
             even if line numbers change.
        """
        import hashlib

        # Key stability components: Rule, Target Resource, File Path (normalized), and Message
        # Note: Line number is EXCLUDED to ensure stability during file edits.
        rule_id = finding.get("rule_id", "unknown")
        kind = finding.get("resource_kind", "unknown")
        name = finding.get("resource_name", "unknown")
        file_path = finding.get("file_path", "unknown").replace("\\", "/")
        message = finding.get("message", "")

        raw = f"{rule_id}|{kind}|{name}|{file_path}|{message}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def health_threshold(self) -> int:
        """The minimum trust score required for a manifest to be considered 'Healthy'.

        Why: To define the safety threshold for CI/CD gates.
        """
        return self.config["rules"].get("threshold", 70)

    @property
    def allowed_host_paths(self) -> List[str]:
        """Returns the list of filesystem paths allowed for hostPath volumes.

        Why: To prevent security scanners from flagging legitimate
             infrastructure paths used by the platform.
        """
        return self.config["security"].get("allowed_host_paths", [])

    @property
    def enforce_limits(self) -> bool:
        """Whether to automatically inject resource limits if missing.

        Why: Ensures all workloads have defined resource boundaries to
             prevent cluster-wide noisy neighbor issues.
        """
        return self.config["healing"].get("enforce_limits", False)

    @property
    def harden(self) -> bool:
        """Whether to apply security hardening patches (e.g., readOnlyRootFilesystem).

        Why: To enforce a 'Secure by Default' posture for all
             manifests processed by the healing engine.
        """
        return self.config["healing"].get("harden", False)

    @property
    def enforce_probes(self) -> bool:
        """Whether to inject liveness/readiness probes if missing.

        Why: To improve the reliability of workloads by ensuring
             Kubelet can monitor their health.
        """
        return self.config["healing"].get("enforce_probes", False)

    @property
    def fix_tags(self) -> bool:
        """Whether to pin image tags to their digest or latest stable version.

        Why: To ensure deployment determinism and prevent 'Latest'
             tag drift in production environments.
        """
        return self.config["healing"].get("fix_tags", False)

    @property
    def kubernetes_version(self) -> Optional[str]:
        """The target Kubernetes version for validation and deprecation checks.

        Why: To ensure that Yamlr validates manifests against the
             correct OpenAPI schema for the target cluster.
        """
        return self.config.get("kubernetes", {}).get("version")

    @property
    def enforce_namespace(self) -> bool:
        """Whether to force a specific namespace on all resources.

        Why: To ensure organizational compliance and prevent accidental
             deployment into the 'default' namespace.
        """
        return self.config.get("healing", {}).get("enforce_namespace", False)

    @property
    def trusted_registries(self) -> List[str]:
        """The list of container registries trusted by the organization.

        Why: To prevent supply chain attacks by blocking images
             from untrusted or public anonymous registries.
        """
        return self.config.get("security", {}).get("trusted_registries", [])

    @property
    def check_deprecations(self) -> bool:
        """Whether to check for Kubernetes API deprecations during scanning.

        Why: To enable proactively warning about future migration risks.
        """
        return self.config.get("healing", {}).get("check_deprecations", False)

    @property
    def runtime_dir(self) -> Path:
        """Returns the absolute path to the runtime directory for temporary artifacts.

        Why: To ensure that Yamlr doesn't clutter the project root with test/audit logs.
        """
        path = self.workspace / self.DEFAULT_RUNTIME_DIR
        return path

    def has_local_config(self) -> bool:
        """Checks if a valid configuration file was loaded."""
        return self.config_path is not None and self.config_path.exists()
