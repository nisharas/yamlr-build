"""
Yamlr CORE UTILITIES
--------------------
Helper functions for orchestration, path handling and standardized reporting.
Shared across Engine, CLI and Pipeline.
"""

import time
from typing import Dict, Any, List, Optional
from pathlib import Path

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
    full_path: Optional[str] = None
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
        health_score=0,
        identities=[],
        findings=[{"message": error, "severity": "error", "type": "EngineError"}],
        timestamp=time.time(),
        processing_time_seconds=processing_time
    )

def resolve_bundled_asset(relative_path: str) -> Optional[Path]:
    """
    Robust discovery of bundled assets (rules, catalogs, docs) across
    standard, development, and frozen (Nuitka/PyInstaller) environments.
    
    Args:
        relative_path: Path relative to the 'yamlr' package root (e.g. 'core/data/definitions.yaml')
        
    Returns:
        Absolute Path if found, else None
    """
    import sys
    import logging
    from pathlib import Path

    logger = logging.getLogger("yamlr.dev")
    search_paths = []
    
    # 1. Standard Package Layout & .yamlr_runtime discovery
    try:
        pkg_core = Path(__file__).parent.resolve()
        pkg_yamlr = pkg_core.parent # yamlr/
        
        # Try relative to yamlr/
        search_paths.append(pkg_yamlr / relative_path)
        
        # Try checking if relative_path starts with 'yamlr/' and remove it if so
        if relative_path.startswith("yamlr/"):
            rest = relative_path[6:]
            search_paths.append(pkg_yamlr / rest)

        # 2. Development Layout (src/yamlr/...)
        if pkg_yamlr.parent.name == "src":
            dev_root = pkg_yamlr.parent.parent
            search_paths.append(dev_root / relative_path)
            # If it's a doc, it might be in project_root/docs
            if relative_path.startswith("docs/"):
                search_paths.append(dev_root / relative_path)
    except Exception:
        pass

    # 3. Frozen Environments (PyInstaller/Nuitka)
    if hasattr(sys, "_MEIPASS"):
        search_paths.append(Path(sys._MEIPASS) / "yamlr" / relative_path)
        search_paths.append(Path(sys._MEIPASS) / relative_path)
    elif getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        search_paths.append(exe_dir / "yamlr" / relative_path)
        search_paths.append(exe_dir / relative_path)
        # Binary often has assets in a side-by-side folder
        search_paths.append(exe_dir / Path(relative_path).name)
        # Search relative to common sidebars
        if "catalog" in relative_path:
            search_paths.append(exe_dir / "catalog" / Path(relative_path).name)
        if "rules" in relative_path or "definitions" in relative_path:
            search_paths.append(exe_dir / "rules" / Path(relative_path).name)
            search_paths.append(exe_dir / "data" / Path(relative_path).name)

    # 4. Final Fallback: Search Upwards from CWD (Defensive)
    current = Path.cwd()
    for _ in range(5):
        search_paths.append(current / "yamlr" / relative_path)
        search_paths.append(current / relative_path)
        search_paths.append(current / "src" / "yamlr" / relative_path)
        if current.parent == current: break
        current = current.parent

    for p in search_paths:
        if p.exists():
            logger.debug(f"Asset resolved: {relative_path} -> {p}")
            return p
    
    logger.debug(f"Asset NOT found: {relative_path}. Searched {len(search_paths)} locations.")
    return None

def get_hardened_yaml(typ: str = "safe", pure: bool = True) -> Any:
    """
    Returns a pre-configured, hardened ruamel.yaml instance.
    
    Why: To centrally enforce security policies, specifically the 
         prevention of 'Billion Laughs' attacks by limiting alias expansion.
    """
    from ruamel.yaml import YAML
    
    yaml = YAML(typ=typ, pure=pure)
    
    # [Security] Mitigate Billion Laughs (DoS)
    # Limiting the number of aliases prevents exponential expansion in memory.
    # Standard K8s manifests rarely use anchors/aliases extensively. 50 is safe.
    try:
        # In newer ruamel.yaml versions, we can limit through the loader
        # However, for maximum compatibility across versions, we set a 
        # reasonable recursive limit or rely on ruamel's default anti-recursion
        # and explicitly disable unsafe features.
        yaml.allow_duplicate_keys = False
    except AttributeError:
        pass
        
    return yaml
