"""
Yamlr CORE UTILITIES
--------------------
Helper functions for orchestration, path handling and standardized reporting.
Shared across Engine, CLI and Pipeline.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

__all__ = ["derive_status", "construct_file_error", "resolve_bundled_asset", "get_hardened_yaml", "is_path_ignored", "xml_escape", "version_context"]

def xml_escape(text: str) -> str:
    """
    Safely escapes characters for XML/HTML-like markup (used by reportlab).
    
    Why: Prevents tag injection in PDF reports when manifest data contains 
         reserved characters (e.g. <, >, &).
    """
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def is_path_ignored(path: str) -> bool:
    """
    Standardized path ignore check for the crawler.
    Why: To provide a consistent, zero-config ignore mechanism for structural scans.
    """
    ignored_dirs = {".git", "node_modules", "venv", "__pycache__", ".yamlr_runtime", ".pytest_cache"}
    parts = Path(path).parts
    return any(p in ignored_dirs for p in parts)

def derive_status(modified: bool, dry: bool, meets_threshold: bool) -> str:
    """
    Derives human-readable status from healing state.
    
    Args:
        modified: Whether file content changed
        dry: Whether in dry-run mode
        meets_threshold: Whether health score meets threshold
        
    Returns:
        Status string (UNCHANGED, PREVIEW, HEALED, FAILED)
    """
    if not modified: 
        return "UNCHANGED"
    if dry: 
        return "PREVIEW"
    return "HEALED" if meets_threshold else "FAILED"

def construct_file_error(
    path: str,
    status: str,
    error: str,
    processing_time: float = 0.0,
    exception: Optional[Exception] = None,
    full_path: Optional[str] = None,
    findings: Optional[List[Dict[str, Any]]] = None
) -> "HealFileResult":
    """
    Constructs a standardized error result object.
    
    Args:
        path: Relative file path that failed
        status: Error status code
        error: Error message
        processing_time: Time spent before error
        exception: Optional exception object
        full_path: Absolute file path
        
    Returns:
        HealFileResult object
    """
    from yamlr.models import HealFileResult
    
    remediation = None
    log_msg = f"Error: {error}"
    
    if exception and hasattr(exception, 'remediation'):
        remediation = getattr(exception, 'remediation')
        if remediation:
            log_msg = f"Error: {error}\n  Hint: {remediation}"

    return HealFileResult(
        file_path=path,
        full_path=full_path or path,
        kind="Error",
        status=status,
        error=error,
        remediation_command=remediation,
        success=False,
        written=False,
        backup_created=None,
        raw_content=None,
        healed_content=None,
        logic_logs=[log_msg],
        dna_integrity_score=0,
        identities=[],
        findings=(findings or []) + [{"message": error, "severity": "error", "rule_id": "General", "type": "EngineError"}],
        timestamp=time.time(),
        processing_time_seconds=processing_time
    )

def resolve_bundled_asset(relative_path: str) -> Optional[Path]:
    """
    Robust discovery of bundled assets across environments.
    """
    import logging
    logger = logging.getLogger("yamlr.dev")
    
    search_paths = []
    _add_package_paths(search_paths, relative_path)
    _add_frozen_paths(search_paths, relative_path)
    _add_fallback_paths(search_paths, relative_path)

    for p in search_paths:
        if p.exists():
            logger.debug(f"Asset resolved: {relative_path} -> {p}")
            return p
    
    logger.debug(f"Asset NOT found: {relative_path}. Searched {len(search_paths)} locations.")
    return None

def _add_package_paths(paths: List[Path], rel: str):
    try:
        pkg_core = Path(__file__).parent.resolve()
        pkg_yamlr = pkg_core.parent
        paths.append(pkg_yamlr / rel)
        if rel.startswith("yamlr/"):
            paths.append(pkg_yamlr / rel[6:])
        if pkg_yamlr.parent.name == "src":
            dev_root = pkg_yamlr.parent.parent
            paths.append(dev_root / rel)
    except Exception: pass

def _add_frozen_paths(paths: List[Path], rel: str):
    import sys
    if hasattr(sys, "_MEIPASS"):
        paths.append(Path(sys._MEIPASS) / "yamlr" / rel)
        paths.append(Path(sys._MEIPASS) / rel)
    elif getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        paths.append(exe_dir / "yamlr" / rel)
        paths.append(exe_dir / rel)
        paths.append(exe_dir / Path(rel).name)

def _add_fallback_paths(paths: List[Path], rel: str):
    current = Path.cwd()
    for _ in range(5):
        paths.append(current / "yamlr" / rel)
        paths.append(current / rel)
        paths.append(current / "src" / "yamlr" / rel)
        if current.parent == current: break
        current = current.parent

def get_hardened_yaml(typ: str = "rt", pure: bool = True, indent: int = 2, offset: int = 0, compact: bool = False) -> "YamlrParser":
    """
    Returns a pre-configured, hardened YamlrParser instance.
    
    Why: To centrally enforce security policies while providing a stable
         abstraction layer (via YamlrParser) that decouples the engine
         from specific library versions.
    """
    from yamlr.core.parser.ruamel_adapter import RuamelAdapter
    
    # We default to 'rt' (RoundTrip) as it's the core engine requirement.
    # The RuamelAdapter handles internal security hardening (max_aliases).
    return RuamelAdapter(typ=typ, pure=pure, indent=indent, offset=offset, compact=compact)

def parse_flow_style_dict(val: str) -> Dict[str, Any]:
    """
    Safely parses flow-style YAML (inline JSON-like) into a dictionary.
    
    Why: Centralizes security-hardened parsing for metadata extractors 
         (Labels, Selectors, Annotations) to prevent duplication and ensure VULN-008 compliance.
    """
    from ruamel.yaml import YAMLError
    try:
        hyaml = get_hardened_yaml(typ="safe")
        parsed_node = hyaml.load(val)
        if parsed_node.is_map:
            return parsed_node.to_dict()
        return {}
    except (YAMLError, Exception):
        return {}

def parse_flow_style_list(val: str) -> List[Any]:
    """
    Safely parses flow-style YAML (inline JSON-like) into a list.
    
    Why: Centralizes security-hardened parsing for metadata extractors 
         (NetworkPolicies) to prevent duplication and ensure VULN-008 compliance.
    """
    from ruamel.yaml import YAMLError
    try:
        hyaml = get_hardened_yaml(typ="safe")
        parsed_node = hyaml.load(val)
        if parsed_node.is_seq:
            return parsed_node.to_dict()
        return []
    except (YAMLError, Exception):
        return []


from contextlib import contextmanager
from typing import Generator

@contextmanager
def version_context(engine: Any, version: str) -> Generator[None, None, None]:
    """
    Temporarily switches the engine's cluster version for accurately 
    binding the catalog to a specific file's version.
    
    Why: Prevents 'Version Leakage' between files in a single batch or stream.
    """
    old_version = getattr(engine, "cluster_version", None)
    engine.cluster_version = version
    try:
        yield
    finally:
        if old_version is not None:
            engine.cluster_version = old_version
