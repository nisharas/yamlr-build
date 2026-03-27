"""
Yamlr AUDITOR HELPERS
---------------------
Helper functions for manifest auditing and healing.
Extracted from auditor.py to maintain 100% modularity and line-count compliance.
"""

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger("yamlr.engine.auditor.helpers")

__all__ = [
    "detect_manifest_version", 
    "generate_evidence_receipt",
    "resolve_audit_paths",
    "check_healing_quota",
    "serialize_findings",
    "build_heal_config"
]

def build_heal_config(
    dry_run: bool = True,
    strict_mode: bool = False,
    **kwargs
) -> Any:
    """
    Unified factory for HealConfig initialization.
    
    Why: Prevents "Sync Drift" by centralizing default values and 
         logic for HealConfig instantiation used by both Auditor and Worker.
    """
    from yamlr.models import HealConfig
    
    # [FIX-MAPPING] dry_run=True means skip_repair=True in the pipeline logic
    # [FIX-DUPES] Use pop to avoid Duplicate Keyword Argument errors
    return HealConfig(
        skip_repair=dry_run,
        pro_preview=kwargs.pop("pro_preview", False),
        strict_mode=strict_mode,
        strict_validation=kwargs.pop("strict_validation", strict_mode),
        compact=kwargs.pop("compact", False),
        file_path=kwargs.pop("file_path", "unknown"),
        **kwargs
    )

def detect_manifest_version(raw_text: str, default_version: str) -> str:
    """
    Detects the Kubernetes API version from the raw manifest text.
    
    Why: Per-file version detection ensures that surgical healing uses 
         the correct schema even in mixed-version repositories.
    """
    from yamlr.core.context import HealContext
    
    try:
        if "apiVersion:" in raw_text:
            for line in raw_text.splitlines():
                if line.strip().startswith("apiVersion:"):
                    val = line.split(":", 1)[1].strip()
                    detected = HealContext.resolve_version_from_api(val)
                    if detected:
                        return detected
    except (ValueError, IndexError, AttributeError):
        pass
    return default_version

# [v31] run_hostpath_security_check removed — pipeline's StageSecurityScoring handles this.


def generate_evidence_receipt(
    full_path: Path,
    raw_text: str,
    healed_text: str,
    findings: List[Dict[str, Any]],
    identities: List[Dict[str, Any]],
    evidence_dir: str
) -> Optional[str]:
    """
    Invokes the Pro Evidence Engine to generate a signed audit receipt.
    """
    try:
        from yamlr.pro.compliance.evidence import EvidenceEngine
        import json
        
        receipt = EvidenceEngine().generate_receipt(
            file_path=str(full_path),
            original_content=raw_text,
            healed_content=healed_text,
            findings=findings,
            identities=identities
        )
        evidence_path = Path(evidence_dir) / f"evidence-{full_path.name}-{int(time.time())}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return str(evidence_path)
    except ImportError:
        # [Blue Team] Fallback to Evidence Engine Lite (OSS)
        # Why: Provides tamper-evident hashing in OSS for local receipts.
        from yamlr.core.receipts import ReceiptManager
        from yamlr.core.dna_utils import calculate_semantic_dna
        
        manager = ReceiptManager(output_dir=evidence_dir)
        receipt = manager.generate_receipt(
            file_path=str(full_path),
            original_dna=calculate_semantic_dna(raw_text),
            healed_dna=calculate_semantic_dna(healed_text),
            findings=findings
        )
        
        evidence_path = Path(manager.output_dir) / f"receipt-{full_path.name}-{int(time.time())}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        evidence_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return str(evidence_path)
    except (json.JSONDecodeError, OSError, IOError) as e:
        logger.error(f"Failed to generate evidence receipt: {e}")
        return None

def resolve_audit_paths(engine, relative_path: str) -> Tuple[Path, Path]:
    """
    Resolves input path to absolute and determines the effective workspace.
    
    Why: Handles both relative (standard) and absolute (advanced) paths while
         enforcing security boundaries.
    """
    from yamlr.core.exceptions import YamlrSecurityError
    
    input_path = Path(relative_path)
    if input_path.is_absolute():
        full_path = input_path.resolve()
        actual_workspace = full_path.parent
    else:
        full_path = (engine.workspace / relative_path).resolve()
        actual_workspace = engine.workspace

    # SECURITY: PREVENT DIRECTORY TRAVERSAL (only for relative paths)
    if not input_path.is_absolute():
        try:
            full_path.relative_to(engine.workspace)
        except ValueError:
            raise YamlrSecurityError(f"Path '{relative_path}' is outside workspace")
            
    return full_path, actual_workspace

def check_healing_quota(dry_run: bool, quota_checked: bool = False):
    """
    Enforces the Free Tier healing quota.
    
    Why: Monetization gate. Prevents bulk healing in OSS mode without a Pro license.
    """
    if not dry_run and not quota_checked:
        # [QA-BYPASS] Selective bypass for internal tests to allow negative testing
        import os
        if os.environ.get("YAMLR_INTERNAL_TEST_MODE") == "true":
            return

        from yamlr.core.license_manager import LicenseManager
        from yamlr.core.exceptions import YamlrQuotaError
        
        is_allowed, _, msg = LicenseManager.is_healing_allowed(1)
        if not is_allowed:
            raise YamlrQuotaError(msg)
            
        # Record usage immediately for single-file cli calls
        LicenseManager.record_healing_usage(1)

def serialize_findings(engine, relative_path: str, findings: List[Any]) -> List[Dict[str, Any]]:
    """
    Filters and serializes AnalysisResult objects according to workspace config.
    
    Why: Centralizes rule-filtering logic and ensures data is serializable for 
         telemetry and report export.
    """
    if not findings:
        return []
        
    # Standardize relative_path (ensure it's relative to workspace root)
    try:
        input_path = Path(relative_path)
        if input_path.is_absolute():
            relative_path = str(input_path.relative_to(engine.workspace))
    except (ValueError, AttributeError):
        pass # Fallback to original if not under workspace
    
    from dataclasses import asdict
    serialized = []
    
    for f in findings:
        f_dict = asdict(f)
        
        # Ensure file_path is consistent for fingerprinting
        if not f_dict.get("file_path") or f_dict["file_path"] == "unknown":
            f_dict["file_path"] = relative_path

        # 1. Check global/local ignore list
        if f.rule_id and engine.config.is_ignored(relative_path, rule_id=f.rule_id):
            continue
            
        # 2. Check baseline (GitOps Guard)
        if engine.config.is_baselined(f_dict):
            continue
            
        serialized.append(f_dict)
        
    return serialized
