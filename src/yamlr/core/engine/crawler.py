"""
Yamlr CRAWLER
-------------
Responsible for filesystem discovery and work unit preparation for the engine.
Extracted from processor.py to maintain 100% modularity.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

try:
    import yamlr_native

    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

logger = logging.getLogger("yamlr.engine.crawler")

__all__ = ["crawl_manifests", "chunk_tasks"]


def crawl_manifests(
    workspace_root: Path,
    root_path: Union[str, List[str]],
    extensions: List[str],
    max_depth: int,
    engine_context: Dict[str, Any],
    use_rust: bool = False,
) -> List[Dict[str, Any]]:
    """
    Crawls the filesystem to find Kubernetes manifests and prepares task info dictionaries.
    """
    ext_set = {e.strip() if e.startswith(".") else f".{e.strip()}" for e in extensions}
    roots = [root_path] if isinstance(root_path, str) else root_path

    all_files = []
    for r in roots:
        search_root = Path(r).resolve()
        if not search_root.exists():
            logger.error(f"Search root does not exist: {r}")
            continue

        # --- [STRATEGIC EXPANSION] NATIVE FAST PATH (VAL-02-6) ---
        if use_rust and HAS_NATIVE:
            # Try native library first (no subprocess overhead)
            try:
                all_files.extend(_walk_with_native(search_root, workspace_root, ext_set, engine_context))
                continue
            except Exception as e:
                logger.warning(f"Native fast-scan failed: {e}. Falling back to binary/Python.")

        if use_rust:
            rust_results = _crawl_with_rust(search_root)
            if rust_results:
                all_files.extend(_process_rust_results(rust_results, workspace_root, engine_context))
                continue
        # ----------------------------------------------------

        if search_root.is_file():
            all_files.extend(_handle_single_file(search_root, workspace_root, ext_set, engine_context))
        else:
            all_files.extend(_walk_directory(search_root, workspace_root, ext_set, max_depth, engine_context))

    return all_files


def _process_rust_results(
    rust_results: Dict[str, Any], workspace_root: Path, engine_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Processes results from the Rust-based scanner."""
    files_to_process = []
    results_list = rust_results.get("results", [])
    logger.info(f"⚡ [Yamlr-Light] Rust-scanner discovered {len(results_list)} manifests")

    for res in results_list:
        identities = res.get("identities", [])
        api_version = identities[0].get("api_version") if identities else "v1"
        task_info = {
            "path": res["file_path"],
            "full_path": res.get("full_path") or str(workspace_root / res["file_path"]),
            "kind": res["kind"],
            "api_version": api_version,
        }
        task_info.update(engine_context)
        files_to_process.append(task_info)
    return files_to_process


def _handle_single_file(
    file_path: Path, workspace_root: Path, ext_set: Set[str], engine_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Handles discovery for a single manifest file."""
    if any(file_path.name.endswith(ext) for ext in ext_set):
        try:
            relative_path = str(file_path.relative_to(workspace_root))
        except ValueError:
            relative_path = str(file_path.resolve())

        task_info = {
            "path": relative_path,
            "full_path": str(file_path),
        }
        task_info.update(engine_context)
        return [task_info]
    return []


def _walk_directory(
    search_root: Path, workspace_root: Path, ext_set: Set[str], max_depth: int, engine_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Performs an optimized directory walk to find manifests."""
    from yamlr.core.utils import is_path_ignored

    files_to_process = []

    # Industrial Scan: Respect standard ignore rules
    for root, dirs, files in os.walk(search_root, followlinks=False):
        # Prune hidden and explicitly ignored directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and not is_path_ignored(str(Path(root) / d))]

        current_path = Path(root)
        try:
            depth = len(current_path.relative_to(search_root).parts)
        except ValueError:
            depth = 0

        if depth > max_depth:
            del dirs[:]
            continue

        for file in files:
            if file.startswith("."):
                continue
            if any(file.endswith(ext) for ext in ext_set):
                full_file = current_path / file

                # Double-check file specifically isn't ignored
                if is_path_ignored(str(full_file)):
                    continue

                try:
                    relative_path = str(full_file.relative_to(workspace_root))
                except ValueError:
                    relative_path = str(full_file.resolve())

                task_info = {
                    "path": relative_path,
                    "full_path": str(full_file),
                }
                task_info.update(engine_context)
                files_to_process.append(task_info)
    return files_to_process


def _walk_with_native(
    search_root: Path, workspace_root: Path, ext_set: Set[str], engine_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Uses yamlr_native.fast_scan to find manifests ultra-fast."""
    files_to_process = []

    # We still use os.walk but we use Rust for the content scanning
    for root, dirs, files in os.walk(search_root):
        # Prune ignored dirs
        from yamlr.core.utils import is_path_ignored

        dirs[:] = [d for d in dirs if not d.startswith(".") and not is_path_ignored(str(Path(root) / d))]

        for file in files:
            if any(file.endswith(ext) for ext in ext_set):
                full_file = Path(root) / file
                if is_path_ignored(str(full_file)):
                    continue

                raw_text = full_file.read_text(encoding="utf-8-sig", errors="ignore")
                # Rust-powered identity extraction
                identities = yamlr_native.fast_scan(raw_text)

                if identities:
                    try:
                        relative_path = str(full_file.relative_to(workspace_root))
                    except ValueError:
                        relative_path = str(full_file.resolve())

                    task_info = {
                        "path": relative_path,
                        "full_path": str(full_file),
                        "kind": identities[0].get("kind"),
                        "api_version": identities[0].get("api_version"),
                    }
                    task_info.update(engine_context)
                    files_to_process.append(task_info)
    return files_to_process


def _crawl_with_rust(search_root: Path) -> Optional[Dict[str, Any]]:
    """
    Attempts to invoke the Rust-based yamlr-light binary for ultra-scale scanning.

    Why: Python's os.walk + regex is O(N) but restricted by GIL and FS latency.
         Rust's ignore crate + rayon is O(N/cores) with zero-cost abstractions.
    """
    logger.debug("_crawl_with_rust called with search_root: %s", search_root)
    # Look for binary in common locations
    # 1. Same dir as Python (installed)
    # 2. In src/yamlr-light/target/release (dev)
    # 3. Path
    bin_name = "yamlr-light.exe" if os.name == "nt" else "yamlr-light"

    # Simple discovery logic for dev environment
    cwd = Path.cwd()
    potential_bins = [
        cwd / "src" / "yamlr-light" / "target" / "release" / bin_name,
        cwd / "bin" / bin_name,
        Path(bin_name),  # Hope it's in path
    ]

    selected_bin = None
    for pb in potential_bins:
        # shutil.which is shell-safe and built-in
        if pb.exists() or (isinstance(pb, Path) and shutil.which(str(pb))) or shutil.which(bin_name):
            selected_bin = str(pb) if pb.exists() else shutil.which(bin_name)
            break

    if not selected_bin:
        return None

    try:
        # Run binary with --output json flag
        cmd = [selected_bin, str(search_root), "--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)

        # Parse JSON output
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError, IOError) as e:
        logger.warning(f"Yamlr-Light execution failed (falling back to Python): {e}")
        return None


def chunk_tasks(tasks: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
    """
    Splits a list of tasks into smaller chunks to minimize IPC overhead.
    """
    if not tasks:
        return []
    return [tasks[i : i + chunk_size] for i in range(0, len(tasks), chunk_size)]
