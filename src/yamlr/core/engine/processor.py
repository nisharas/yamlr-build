"""
Yamlr BATCH PROCESSOR
----------------------
Coordinates the parallel/threaded execution of scanners, analyzers, and healers.

Why: Refactored to leverage specialized helper modules (processor_helpers)
     to ensure 100% modularity and compliance with the <500 lines per module guardrail.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Generator, List, Optional

from yamlr.core.forensics import ForensicLogger
from yamlr.models import HealFileResult, HealStatus
from yamlr.core.utils.journal import HealJournal

logger = logging.getLogger("yamlr.engine.processor")


def batch_heal(
    engine,
    files_to_process: List[str],
    dry_run: bool = True,
    concurrency: int = 4,
    task_label: str = "Healing Batch",
    stream_to: Optional[Any] = None,
    _idp_export: bool = False,
    is_ultra_scale: bool = False,
    engine_context: Optional[Dict[str, Any]] = None,
    _from_report_path: Optional[str] = None,
    external_findings_map: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Generator[HealFileResult, None, None]:
    """
    Principal Entry Point for batch manifest healing.

    Why: Coordinates the end-to-end batch lifecycle from chunking to
         parallel surgery and telemetry recording.
    """
    PROCESS_START = time.time()

    from yamlr.core.engine.processor_helpers import (
        check_batch_quota,
        prepare_batch_context,
        record_batch_telemetry,
        run_parallel_surgery_pool,
    )

    # 0. Infrastructure Prep
    context = prepare_batch_context(engine, engine_context or {}, external_findings_map)

    # 1. Quota Verification (Community Tier Gate)
    allowed, reason = check_batch_quota(dry_run, len(files_to_process))
    if not allowed and reason:
        yield HealFileResult(
            file_path="BATCH",
            full_path="N/A",
            success=False,
            status="QUOTA_EXCEEDED",
            kind="System",
            logic_logs=[reason],
            findings=[],
            dna_integrity_score=0,
            identities=[],
            cluster_version="Unknown",
            reconciled_count=0,
            phy_status="0%",
            kbs_status="0%",
            sem_status="0%",
        )
        return

    # [PHASE 29] Apex Unified Chunk Size Logic
    # 🛡️ OOM Protection: Use smaller chunks for hyperscale workloads
    chunk_size = 50 if is_ultra_scale else 20
    chunks = [files_to_process[i : i + chunk_size] for i in range(0, len(files_to_process), chunk_size)]

    # 2. Execution Cycle
    results = []
    
    # 🧪 Forensic Journaling: Initialize WAL
    journal = None
    if not dry_run:
        journal = HealJournal(engine.workspace)
        engine.journal = journal
        journal.start_batch()

    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            heal_task = progress.add_task(f"[cyan]{task_label}...", total=len(files_to_process))

            # 🛡️ APEX SOVEREIGN: Delegate execution to the parallel pool
            # This caller handles yield and progress update
            for res in run_parallel_surgery_pool(
                engine, chunks, concurrency, stream_to, is_ultra_scale, context, progress, heal_task
            ):
                # 🛡️ Memory Guardrail: Drop large buffers for non-essential results
                if is_ultra_scale or len(results) > 100:
                    res.original_content = None
                    if not dry_run:
                        res.healed_content = None
                
                # Update journal status
                if journal and res.status == HealStatus.HEALED:
                    journal.mark_done(res.file_path)

                results.append(res)
                yield res

        # 3. Telemetry and Cleanup
        record_batch_telemetry(engine, results, dry_run, PROCESS_START)
        
        if journal:
            journal.cleanup()

    except Exception as e:
        logger.error(f"Batch healing failed: {e}")
        raise e
    finally:
        engine.journal = None
        # Final cleanup logic moves here to avoid memory bloat
        import gc
        gc.collect()


def _execute_batch_execution(*args, **kwargs):
    """Old stub for backward compatibility with 1.6 architecture."""
    return batch_heal(*args, **kwargs)
