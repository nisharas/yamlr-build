from __future__ import annotations

"""
SURGERY POOL - Parallel Execution Specialist
--------------------------------------------
Orchestrates high-concurrency repair cycles for large manifest sets.

Why: Extracted from processor_helpers.py to ensure modularity 
     and to isolate the 'Apex Sovereign' (Zero-Deadlock) threading logic.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, Generator, List, Optional, Tuple

import argparse

from yamlr.core.k8s_versions import MATRIX
from yamlr.core.engine.base import YamlrEngine
from yamlr.models import HealFileResult

logger = logging.getLogger("yamlr.engine.processor.pool")


def run_parallel_surgery_pool(
    engine: YamlrEngine,
    chunks: List[List[str]],
    concurrency: int,
    stream_fh: Any,
    is_ultra_scale: bool,
    engine_context: Dict[str, Any],
    progress: Any,
    heal_task: Any,
) -> Generator[HealFileResult, None, None]:
    """Orchestrates the parallel repair cycle with Segmented Dispatch."""
    catalog_source, mem_manager = _prepare_catalog_source(engine, is_ultra_scale)

    try:
        # [Phase 2] Fast Path: Bypass Pool for single-file batches
        if len(chunks) <= 1:
            yield from _run_sequential_fallback(
                engine, chunks, engine_context, progress, heal_task, catalog_source, mem_manager
            )
            return

        # [Phase 9] Segmented Dispatch: Process in waves to prevent OOM
        # Wave size is derived from concurrency to keep pipe full but limited.
        segment_size = max(concurrency * 4, 10)
        for i in range(0, len(chunks), segment_size):
            segment = chunks[i : i + segment_size]
            if _should_use_threading():
                yield from _run_threaded_surgery(
                    engine, segment, concurrency, stream_fh, is_ultra_scale,
                    engine_context, progress, heal_task, catalog_source, mem_manager
                )
            else:
                yield from _run_process_surgery(
                    engine, segment, concurrency, stream_fh, is_ultra_scale,
                    engine_context, progress, heal_task, catalog_source, mem_manager
                )
    except Exception as e:
        logger.error(f"Sovereign Bridge Failure: {e}")
        yield from _run_sequential_fallback(
            engine, chunks, engine_context, progress, heal_task, catalog_source, mem_manager
        )
    finally:
        if mem_manager:
            mem_manager.cleanup()


def _prepare_catalog_source(engine: YamlrEngine, is_ultra_scale: bool) -> Tuple[Any, Optional[Any]]:
    """Dumps catalog to memmap if necessary for memory efficiency."""
    from yamlr.core.engine.memmap import MemmapManager
    import json
    
    catalog_source = engine.catalog
    mem_manager = None
    if is_ultra_scale or len(json.dumps(engine.catalog)) > 1_000_000:
        mem_manager = MemmapManager(engine.config.runtime_dir)
        catalog_source = mem_manager.dump("catalog", engine.catalog)
    return catalog_source, mem_manager


def _should_use_threading() -> bool:
    """Determines if the ThreadPoolExecutor should be used based on environment."""
    is_frozen = getattr(sys, "frozen", False)
    return is_frozen or os.getenv("YAMLR_FORCE_THREADING") == "1"


def _run_threaded_surgery(
    engine, chunks, concurrency, stream_fh, is_ultra_scale, 
    engine_context, progress, heal_task, catalog_source, mem_manager
) -> Generator[HealFileResult, None, None]:
    """Executes surgery using ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from yamlr.core.engine.worker import _execute_healing_chunk
    import json

    logger.debug("🏎️  Apex Sovereign: Using ThreadPoolExecutor (Zero-Hang Path)")
    pool_size = min(concurrency, 8) if not is_ultra_scale else 4
    context = engine_context or {}

    with ThreadPoolExecutor(max_workers=pool_size) as executor:
        futures = {
            executor.submit(
                _execute_healing_chunk,
                _build_worker_payload(engine, c, catalog_source, mem_manager, context)
            ): c for c in chunks
        }
        for future in as_completed(futures):
            chunk_results = future.result()
            if chunk_results:
                for res in _inflate_chunk_results(chunk_results):
                    _process_individual_result(res, stream_fh, is_ultra_scale, progress, heal_task)
                    yield res


def _run_process_surgery(
    engine, chunks, concurrency, stream_fh, is_ultra_scale, 
    engine_context, progress, heal_task, catalog_source, mem_manager
) -> Generator[HealFileResult, None, None]:
    """Executes surgery using joblib Multiprocessing."""
    from joblib import Parallel, delayed
    from yamlr.core.engine.worker import _execute_healing_chunk

    context = engine_context or {}
    with Parallel(n_jobs=concurrency, prefer="processes", timeout=300) as parallel_executor:
        iterable = (
            delayed(_execute_healing_chunk)(
                _build_worker_payload(engine, c, catalog_source, mem_manager, context)
            ) for c in chunks
        )
        results_list = parallel_executor(iterable)
        for chunk_results in results_list:
            if chunk_results:
                for res in _inflate_chunk_results(chunk_results):
                    _process_individual_result(res, stream_fh, is_ultra_scale, progress, heal_task)
                    yield res


def _run_sequential_fallback(
    engine, chunks, engine_context, progress, heal_task, catalog_source, mem_manager
) -> Generator[HealFileResult, None, None]:
    """Fallback to sequential execution if parallel fails."""
    from yamlr.core.engine.worker import _execute_healing_chunk
    logger.warning("⚠️ Falling back to sequential execution...")
    context = engine_context or {}
    for c in chunks:
        chunk_results = _execute_healing_chunk(
            _build_worker_payload(engine, c, catalog_source, mem_manager, context)
        )
        for res in _inflate_chunk_results(chunk_results):
            yield res
            progress.update(heal_task, advance=1)


def _build_worker_payload(engine, files, catalog_source, mem_manager, context):
    """Constructs the payload for the worker function."""
    import logging
    return {
        "files": files,
        "catalog_path": catalog_source if mem_manager else None,
        "catalog_data": engine.catalog if not mem_manager else None,
        "cpu_limit": engine.cpu_limit,
        "mem_limit": engine.mem_limit,
        "default_namespace": engine.default_namespace,
        "app_name": engine.app_name,
        "k8s_version": engine.cluster_version,
        "workspace_path": str(engine.workspace),
        "log_level": logging.getLogger("yamlr").getEffectiveLevel(),
        **context,
    }


def _process_individual_result(res, stream_fh, is_ultra_scale, progress, heal_task):
    """Handles side-effects for a single result (streaming, pruning, progress)."""
    import json
    if stream_fh:
        stream_fh.write(json.dumps(res.to_dict()) + "\n")
        stream_fh.flush()
    _prune_hyperscale_result(res, is_ultra_scale)
    progress.update(heal_task, advance=1)


def _inflate_chunk_results(chunk_results: List) -> Generator[HealFileResult, None, None]:
    """Re-inflates worker results into HealFileResult objects."""
    from yamlr.models import HealFileResult
    for res in chunk_results:
        if isinstance(res, dict) and res.get("_is_fast_dict"):
            from yamlr.models import HealAction
            yield HealFileResult(
                file_path=res["file_path"],
                full_path=res["full_path"],
                success=res["success"],
                status=res["status"],
                kind=res.get("kind", "Unknown"),
                findings=[HealAction(**f) for f in res["findings"]],
                dna_integrity_score=int(res["dna_integrity_score"]),
                pro_features_triggered=res.get("pro_features_triggered", False),
                trust_score=res.get("trust_score", 100.0),
            )
        else:
            yield res


def _prune_hyperscale_result(res: HealFileResult, is_ultra_scale: bool):
    """Prunes result content for memory efficiency during hyperscale operations."""
    if res.success:
        res.healed_content, res.raw_content = None, None
        if is_ultra_scale:
            res.logic_logs, res.findings = [], []
