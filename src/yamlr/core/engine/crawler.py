"""
Yamlr CRAWLER
-------------
Responsible for filesystem discovery and work unit preparation for the engine.
Extracted from processor.py to maintain 100% modularity.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Set, Optional

logger = logging.getLogger("yamlr.engine.crawler")

def crawl_manifests(
    workspace_root: Path,
    root_path: str,
    extensions: List[str],
    max_depth: int,
    engine_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Crawls the filesystem to find Kubernetes manifests and prepares task info dictionaries.
    
    Args:
        workspace_root (Path): The root of the engine workspace.
        root_path (str): The starting path for the crawl.
        extensions (List[str]): List of file extensions to include (e.g., ['.yaml', '.yml']).
        max_depth (int): Maximum directory depth for the crawl.
        engine_context (Dict[str, Any]): Global engine parameters (version, threshold, etc.)
        
    Returns:
        List[Dict[str, Any]]: A list of task information dictionaries for healing workers.
    """
    files_to_process = []
    search_root = Path(root_path).resolve()
    
    if not search_root.exists():
        logger.error(f"Search root does not exist: {root_path}")
        return []

    ext_set = {e.strip() if e.startswith(".") else f".{e.strip()}" for e in extensions}

    for root, dirs, files in os.walk(search_root, followlinks=False):
        # Prune hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        
        current_path = Path(root)
        try:
            depth = len(current_path.relative_to(search_root).parts)
        except ValueError:
            depth = 0
            
        if depth > max_depth:
            del dirs[:]
            continue
            
        for file in files:
            if file.startswith("."): continue
            if any(file.endswith(ext) for ext in ext_set):
                full_file = current_path / file
                try:
                    relative_path = str(full_file.relative_to(workspace_root))
                except ValueError:
                    relative_path = str(full_file.resolve())

                task_info = {
                    "path": relative_path,
                    "full_path": str(full_file),
                }
                # Merge in the global engine context
                task_info.update(engine_context)
                files_to_process.append(task_info)
                
    return files_to_process

def chunk_tasks(tasks: List[Dict[str, Any]], chunk_size: int) -> List[List[Dict[str, Any]]]:
    """
    Splits a list of tasks into smaller chunks to minimize IPC overhead.
    """
    if not tasks:
        return []
    return [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
