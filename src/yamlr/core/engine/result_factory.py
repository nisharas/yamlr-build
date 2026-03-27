#!/usr/bin/env python3
"""
Yamlr RESULT FACTORY - The Unified Closer
-----------------------------------------
Centralizes the construction of HealFileResult objects.

Why: Prevents "Logic Drift" between single-file and batch healing modes.
     Ensures that status derivation (APPLIED vs WARN vs FAILED) is consistent
     across the entire engine.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import asdict

from yamlr.models import HealFileResult
from yamlr.core.utils import derive_status

if TYPE_CHECKING:
    from yamlr.core.pipeline import HealResult

class ResultFactory:
    """
    Unified factory for creating and finalizing processing results.
    """

    @staticmethod
    def build(
        file_path: str,
        full_path: str,
        raw_text: str,
        healed_text: str,
        result: HealResult,
        processing_time: float,
        dry_run: bool,
        force_write: bool = False,
        written: bool = False,
        backup_path: Optional[str] = None,
        evidence_receipt: Optional[str] = None,
        threshold: int = 70,
        serialized_findings: Optional[List[Dict[str, Any]]] = None
    ) -> HealFileResult:
        """
        Creates a standardized HealFileResult from pipeline and engine data.
        
        Args:
            file_path: Relative path for reporting.
            full_path: Absolute path for workspace operations.
            raw_text: Original manifest content.
            healed_text: Transformed manifest content.
            result: The raw HealResult from the pipeline.
            processing_time: Duration of the complete per-file operation.
            dry_run: Whether mutations were actually committed.
            force_write: Whether to force write despite threshold violations.
            written: Whether the file was actually saved to disk.
            backup_path: Path to the created backup file, if any.
            evidence_receipt: Path to the generated DNA-signed receipt, if any.
            threshold: The health threshold (0-100) required for "Success".
            serialized_findings: Optionally pre-filtered findings from the Auditor.
        """
        is_modified = raw_text.strip() != healed_text.strip()
        
        # 1. Use existing findings or serialize raw ones
        findings = serialized_findings if serialized_findings is not None else [asdict(f) for f in result.findings]
        
        # 2. Derive Unified Success/Status
        try:
            dna_score = int(result.dna_integrity_score)
            threshold_val = int(threshold)
        except (TypeError, ValueError):
            dna_score = 0
            threshold_val = 0
            
        has_critical_errors = any(f.get("severity", "").upper() == "ERROR" for f in findings)
        
        # [HEAL-SAFE-01] Emergency Brake: Must meet threshold if modified
        meets_threshold = (dna_score >= threshold_val)
        if not is_modified and not has_critical_errors:
             # Identity-less files that required no changes are considered successful (scanned)
             meets_threshold = True
             
        meets_threshold = meets_threshold and not has_critical_errors
        
        # PRIORITIZE PIEPLINE FAILURE
        from yamlr.core.pipeline import HealStatus
        if result.status == HealStatus.FAILED:
            status = "FAILED"
            meets_threshold = False
        else:
            status = derive_status(is_modified, dry_run, meets_threshold)
            
        if has_critical_errors and status != "FAILED" and not dry_run:
            status = "FAILED"

        # 3. Format Identities (including deprecation info)
        identities_list = []
        for identity in result.identities:
            ident_data = identity.to_dict()
            if getattr(identity, "deprecation_info", None):
                dep = identity.deprecation_info
                ident_data["deprecation_info"] = {
                    "deprecated_api": getattr(dep, "deprecated_api", "?"),
                    "replacement_api": getattr(dep, "replacement_api", "?"),
                    "removed_in_version": getattr(dep, "removed_in_version", "?"),
                    "migration_notes": getattr(dep, "migration_notes", ""),
                }
            identities_list.append(ident_data)

        # 4. Construct Final object
        res_obj = HealFileResult(
            file_path=file_path,
            full_path=full_path,
            success=meets_threshold or not is_modified,
            status=status,
            written=written,
            backup_created=backup_path,
            dna_integrity_score=int(dna_score),
            logic_logs=result.logs,
            identities=identities_list,
            findings=findings,
            processing_stats=result.stats.__dict__,
            deprecation_info=getattr(result, "deprecation_info", []),
            healed_content=healed_text,
            raw_content=raw_text,
            evidence_receipt=evidence_receipt,
            kind=identities_list[0]["kind"] if identities_list else "Unknown",
            timestamp=time.time(),
            processing_time_seconds=processing_time,
            phy_status=result.phy_status,
            kbs_status=result.kbs_status,
            sem_status=result.sem_status,
            dna_hash=result.dna_hash,
        )
        
        # Preserve raw identities for global analysis (batch mode)
        res_obj.identities_raw = result.identities
        
        # [PRO] Remediation Hint
        if findings and status in ["WARN", "PREVIEW"]:
             from yamlr.core.bridge import YamlrBridge
             res_obj.remediation_command = YamlrBridge.get_remediation_command(file_path)
             
        # [PRO] Trigger Dopamine Drip UI if Pro fixes were simulated
        if getattr(result, "pro_preview", False) and is_modified:
             res_obj.pro_features_triggered = True

        return res_obj
