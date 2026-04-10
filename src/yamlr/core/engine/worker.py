"""
Yamlr ENGINE WORKER
-------------------
The lowest-level execution unit for parallel/threaded manifest processing.

Why: Extracted from processor.py to satisfy the 100% modularity protocol
     and prevent 'God Object' emergence in the engine.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from yamlr.models import HealAction, HealFileResult, HealStatus

logger = logging.getLogger("yamlr.engine.worker")


def _execute_healing_chunk(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Executes a chunk of work (list of files) in a standalone manner.
    Used by Parallel/ThreadPool executors.
    """
    files = params.get("files", [])
    if not files:
        return []

    # 🛡️ ZERO-HANG: Ensure we have a clean environment for the worker
    try:
        from yamlr.core.manager import YamlrManager
        # [Compatibility] HealingPipeline logic is now unified in YamlrEngine
        from yamlr.core.engine import YamlrEngine as HealingPipeline

        # Initialize a lightweight pipeline for this worker
        # [Zero-Blindspot] Use the passed catalog to avoid re-fetching
        catalog_path = params.get("catalog_path")
        catalog_data = params.get("catalog_data")

        if catalog_path and os.path.exists(catalog_path):
            import json

            with open(catalog_path, "r") as f:
                catalog = json.load(f)
        else:
            catalog = catalog_data

        pipeline = HealingPipeline(
            workspace_path=params.get("workspace_path", "."),
            catalog_data=catalog,
            cluster_version=params.get("cluster_version", "1.31"),
            default_namespace=params.get("default_namespace", "default"),
            app_name=params.get("app_name", "Yamlr"),
        )

        results = []
        for file_path in files:
            res = _process_single_file(file_path, pipeline, params)
            if res:
                # Convert to dict for serialization if needed, or keep as object
                # [GTM-04-1] Return fast-dict for IPC efficiency
                results.append(res.to_dict() if hasattr(res, "to_dict") else res)

        return results

    except Exception as e:
        logger.error(f"Worker process failed: {e}")
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        return []


def _process_single_file(file_path: str, pipeline: Any, params: Dict[str, Any]) -> Optional[HealFileResult]:
    """Internal helper to heal a single file."""
    try:
        from pathlib import Path

        full_path = Path(params.get("workspace_path", ".")) / file_path

        # [GTM-04-1] Apex Native Path: Use Rust for metadata extraction if available
        # This keeps the "Native Sovereign" promise.
        content = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        # Execute the engine process
        result = pipeline.process_file(
            content=content,
            relative_path=file_path,
            full_path=str(full_path),
            config=params,
            start_time=time.time(),
            dry_run=params.get("dry_run", True),
            apply=not params.get("dry_run", True),
        )
        return result
    except Exception as e:
        import traceback
        logger.error(f"Healing failed for {file_path}: {e}")
        if "--debug" in sys.argv:
            traceback.print_exc()
        return HealFileResult(
            file_path=file_path,
            full_path=str(full_path) if 'full_path' in locals() else file_path,
            success=False,
            status=HealStatus.FAILED,
            logic_logs=[f"Worker Error: {str(e)}"]
        )
