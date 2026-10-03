"""Binary discovery module for yamlr native core.

Why: Implements the Ruff model for instant CLI startup by locating
     the precompiled native Rust binary across bundled wheels,
     environment overrides, development target directories, and system paths.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def find_yamlr_bin() -> Optional[str]:
    """Locate the standalone native yamlr binary executable.

    Why: Prioritizes local, bundled, or explicitly configured native binaries
         before searching system paths, while preventing recursive execution loops
         against Python entrypoint wrappers.

    Returns:
        Absolute path to the native executable, or None if not found.
    """
    binary_name = "yamlr.exe" if sys.platform == "win32" else "yamlr"

    # 1. Environment variable override
    env_override = os.environ.get("YAMLR_BINARY")
    if env_override and os.path.isfile(env_override) and os.access(env_override, os.X_OK):
        return os.path.abspath(env_override)

    # 2. Bundled binary inside Python package (e.g. site-packages/yamlr/bin/yamlr)
    pkg_dir = Path(__file__).resolve().parent
    bundled_bin = pkg_dir / "bin" / binary_name
    if bundled_bin.is_file() and os.access(str(bundled_bin), os.X_OK):
        return str(bundled_bin)

    # 3. Development workspace target directory (native_core/target/...)
    # Search upwards from current file to find native_core target directories
    for parent in [pkg_dir.parent.parent, Path.cwd()]:
        for mode in ("release", "debug"):
            dev_candidate = parent / "native_core" / "target" / mode / binary_name
            if dev_candidate.is_file() and os.access(str(dev_candidate), os.X_OK):
                return str(dev_candidate)

    # 4. User profile installation directories (~/.yamlr/bin or ~/.local/bin)
    home = Path.home()
    user_candidates = [
        home / ".yamlr" / "bin" / binary_name,
        home / ".local" / "bin" / binary_name,
    ]
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            user_candidates.append(Path(local_app_data) / "yamlr" / "bin" / binary_name)

    for candidate in user_candidates:
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)

    # 5. System PATH (excluding python venv scripts folder to prevent self-recursion)
    system_bin = shutil.which(binary_name)
    if system_bin:
        sys_path = Path(system_bin).resolve()
        # Avoid picking up venv's Python script launcher
        py_scripts_dir = Path(sys.executable).parent.resolve()
        if sys_path.parent != py_scripts_dir:
            return str(sys_path)

    return None
