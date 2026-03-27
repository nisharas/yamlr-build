from __future__ import annotations

"""
Auditor Module for Yamlr Engine.

Why: To decouple single-file and stream-based auditing logic from the main orchestrator,
improving maintainability and testing scope.
"""
"""
### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-03-23: Decoupled Audit Helpers**
   - **Context**: `auditor.py` grew into a 1500-line monolith.
   - **Decision**: Move path resolution, quota checks, and result factory logic into `auditor_helpers.py`.
   - **Consequence**: Improved unit test isolation and cleaner orchestration.

2. **2026-03-24: Unified Result Factory**
   - **Context**: Inconsistent `HealFileResult` objects between scan and stream.
   - **Decision**: Centralize result construction in `ResultFactory`.
   - **Consequence**: Single source of truth for HAS scores and telemetry.
"""
import logging
import time
from pathlib import Path
from typing import Any, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine

from yamlr.core.exceptions import (YamlrEngineError, YamlrError,
                                   YamlrParseError)
from yamlr.core.pipeline import HealStatus
from yamlr.core.utils import construct_file_error, derive_status
from yamlr.models import HealFileResult
from yamlr.core.engine.auditor_helpers import (
    detect_manifest_version,
    serialize_findings,
    build_heal_config
)

from yamlr.core.engine.result_factory import ResultFactory
from yamlr.core.engine.adapter_handler import apply_enterprise_pro_adapters

logger = logging.getLogger("yamlr.engine.auditor")

__all__ = ["audit_and_heal_file", "audit_stream"]

def audit_and_heal_file(
    engine: "YamlrEngine",
    relative_path: str,
    dry_run: bool = True,
    force_write: bool = False,
    strict_validation: bool = False,
    compact: bool = False,
    identity_mode: str = "infer",
    enforce_limits: bool = False,
    fix_tags: bool = False,
    harden: bool = False,
    enforce_probes: bool = False,
    skip_backup: bool = False,
    enforce_namespace: bool = False,
    fast: bool = False,
    check_deprecations: bool = False,
    fix_refs: bool = False,
    sovereign: bool = False,
    generate_receipts: bool = False,
    evidence_dir: Optional[str] = None,
    adapters_dir: Optional[str] = None,
    safe_mode: bool = False,
    pro_preview: bool = False,
    **kwargs: Any,
) -> HealFileResult:
    """Performs a full audit and healing cycle on a single manifest file.

    Why: Single entry-point for file-level healing to keep orchestration
         consistent and auditable via the telemetry layer.
    """
    from yamlr.core.engine.auditor_helpers import (
        resolve_audit_paths, check_healing_quota
    )
    from yamlr.core.exceptions import YamlrQuotaError, YamlrSecurityError

    start_time = time.time()

    try:
        # 1. Resolve Paths and Security
        try:
            full_path, _ = resolve_audit_paths(engine, relative_path)
        except YamlrSecurityError as e:
            return construct_file_error(relative_path, "SECURITY_ERROR", str(e), exception=e)

        # 2. Config Ignore Check
        if engine.config.is_ignored(relative_path):
            return _create_ignored_result(relative_path, str(full_path))

        # 3. Quota Check
        try:
            check_healing_quota(dry_run, kwargs.get("quota_checked", False))
        except YamlrQuotaError as e:
            return _create_quota_error_result(relative_path, str(full_path), str(e))

        # 4. Read Content (Prioritize kwargs['content'] for ad-hoc validation)
        raw_text = kwargs.get("content")
        if raw_text is None:
            raw_text = _read_manifest_content(full_path, relative_path)
            
        if isinstance(raw_text, HealFileResult):
            return raw_text # Error Result

        # [Security] Credential Sanitization Pre-Scan
        if not kwargs.get("unrestricted", False):
            _detect_secrets(raw_text, relative_path)

        # 5. Execute Pipeline with Version Context Manager [ROUND-12]
        from yamlr.core.utils import version_context
        active_version = detect_manifest_version(raw_text, engine.cluster_version)
        
        with version_context(engine, active_version):
            config = build_heal_config(
                dry_run=dry_run,
                strict_mode=strict_validation,
                strict_validation=strict_validation,
                compact=compact,
                identity_mode=identity_mode,
                enforce_limits=enforce_limits or engine.config.enforce_limits,
                fix_tags=fix_tags or engine.config.fix_tags,
                harden=harden or engine.config.harden,
                enforce_probes=enforce_probes or engine.config.enforce_probes,
                enforce_namespace=enforce_namespace or engine.config.enforce_namespace,
                fast=fast,
                sovereign=sovereign,
                check_deprecations=check_deprecations,
                fix_refs=fix_refs,
                generate_receipts=generate_receipts,
                file_path=relative_path,
                cluster_version=active_version,
                cpu_limit=engine.cpu_limit,
                mem_limit=engine.mem_limit,
                default_namespace=engine.default_namespace,
                evidence_dir=evidence_dir,
                safe_mode=safe_mode or engine.safe_mode,
                pro_preview=pro_preview
            )

            try:
                result = engine.pipeline.heal(raw_text, config=config)
                
                # [VAL-02-6] Fast-Path Optimization
                if config.fast and result.status != HealStatus.FAILED:
                    return ResultFactory.build(
                        file_path=relative_path, full_path=str(full_path),
                        raw_text=raw_text, healed_text=result.content,
                        result=result, processing_time=time.time() - start_time,
                        dry_run=dry_run, force_write=force_write,
                        threshold=engine.health_threshold,
                        serialized_findings=serialize_findings(engine, relative_path, result.findings)
                    )

                # 6. Pipeline Failure/Skip Check
                if result.status == HealStatus.FAILED:
                    return construct_file_error(
                        relative_path, "PIPELINE_ERROR", 
                        result.error_message or "Unknown Pipeline Error",
                        findings=serialize_findings(engine, relative_path, result.findings)
                    )

                if result.status == HealStatus.SKIPPED:
                    return _create_skipped_result(relative_path, str(full_path), result.logs, start_time)

                # 7. Process Successful Result
                healed_text = result.content
                serialized_findings = serialize_findings(engine, relative_path, result.findings)

                # 9. Apply Enterprise Adapters
                if adapters_dir:
                    healed_text = apply_enterprise_pro_adapters(
                        healed_text, serialized_findings, result.logs, adapters_dir,
                        shadow_mode=kwargs.get("adapter_shadow_mode", False),
                        allow_break_glass=kwargs.get("allow_break_glass_adapters", False)
                    )

                # 10. Recursive Contextual Healing (Cross-Resource)
                # [Zero-Blindspot] Pass generator directly to avoid OOM
                context = engine.pipeline.create_context(raw_text, config)
                context.workspace_identities = engine.get_all_identities() # Generator

                result = engine.pipeline.heal(raw_text, config=config, context=context)

                # 11. Final Build
                res_obj = ResultFactory.build(
                    file_path=relative_path, full_path=str(full_path),
                    raw_text=raw_text, healed_text=healed_text,
                    result=result, processing_time=time.time() - start_time,
                    dry_run=dry_run, force_write=force_write,
                    threshold=engine.health_threshold,
                    serialized_findings=serialized_findings
                )

                # 12. Commitment Phase (Writes and Backups)
                can_write = res_obj.status in ["APPLIED", "FIXED", "HEALED"] or force_write
                if not dry_run and can_write:
                    _finalize_healing_file(engine, res_obj, full_path, raw_text, healed_text, skip_backup, evidence_dir)

                return res_obj
            except Exception as e:
                logger.error(f"Execution Error in {relative_path}: {e}")
                raise

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(relative_path, "ENGINE_ERROR", str(e), time.time() - start_time, exception=e)

def _create_ignored_result(relative_path: str, full_path: str) -> HealFileResult:
    """Creates a result for ignored files.
    
    Why: To provide a consistent return object for files explicitly excluded
         via .yamlr.yaml or command-line filters.
    """
    return HealFileResult(
        file_path=relative_path, full_path=full_path, success=True, status="IGNORED",
        written=False, kind="Ignored", logic_logs=["File ignored by .yamlr.yaml config"],
        dna_integrity_score=100, identities=[], findings=[], timestamp=time.time(), processing_time_seconds=0.0
    )

def _create_quota_error_result(relative_path: str, full_path: str, msg: str) -> HealFileResult:
    """Creates a result for quota errors.
    
    Why: To signal to the user when the Free Tier limit has been reached
         and guide them toward Yamlr Enterprise (Pro).
    """
    return HealFileResult(
        file_path=relative_path, full_path=full_path, success=False, status="QUOTA_EXCEEDED",
        written=False, kind="Limit", 
        logic_logs=[msg, "Visit https://yamlr.dev/pro for unlimited healing."],
        dna_integrity_score=0, identities=[], findings=[], timestamp=time.time(), processing_time_seconds=0.0
    )

def _read_manifest_content(full_path: Path, relative_path: str) -> Union[str, HealFileResult]:
    """Reads file content with BOM handling and error reporting.
    
    Why: To centralize encoding handling and ensure empty or malformed
         files are caught early with actionable error messages.
    """
    try:
        raw_text = full_path.read_text(encoding="utf-8-sig")
        if not raw_text.strip():
            err = YamlrParseError("File contains no YAML content")
            return construct_file_error(relative_path, "EMPTY_FILE", str(err), exception=err)
        return raw_text
    except UnicodeDecodeError:
        err = YamlrParseError("File encoding not supported (not a valid UTF-8 text file)")
        return construct_file_error(relative_path, "DECODE_ERROR", str(err), exception=err)

def _detect_secrets(content: str, path: str):
    """
    Scans for potential credentials/secrets before processing.
    Why: Prevents accidental persistence of secrets in logs, backups, or telemetry.
    """
    import re
    from yamlr.core.exceptions import YamlrSecurityError
    
    # Common Patterns (High Entropy / Known Prefixes)
    patterns = {
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Generic Secret Entropy": r"[a-zA-Z0-9+/]{40,}", # Rough entropy check
        "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
        "Slack Token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
    }
    
    for name, pattern in patterns.items():
        if re.search(pattern, content):
            msg = f"Security Violation: Potential {name} detected in {path}. Yamlr refuses to process files containing raw secrets. Please use Secrets/ExternalSecrets instead."
            logger.critical(msg)
            raise YamlrSecurityError(msg)

def _create_skipped_result(relative_path: str, full_path: str, logs: list, start_time: float) -> HealFileResult:
    """Creates a result for skipped files.
    
    Why: To document files that were parsed but required no changes,
         ensuring the user knows their manifest is already clean.
    """
    return HealFileResult(
        file_path=relative_path, full_path=full_path, success=True, status="SKIPPED",
        written=False, kind="Skipped", logic_logs=logs, dna_integrity_score=100, trust_score=100.0,
        identities=[], findings=[], timestamp=time.time(), processing_time_seconds=time.time() - start_time
    )

# [DELETED] _apply_enterprise_adapters (Moved to adapter_handler.py)
# [DELETED] _build_final_result (Moved to result_factory.py)

def _finalize_healing_file(engine: "YamlrEngine", res_obj: HealFileResult, full_path: Path, raw_text: str, healed_text: str, skip_backup: bool, evidence_dir: Optional[str]):
    """Performs backups, evidence generation, and the final atomic write.
    
    Why: To guarantee "Zero-Failure Trust" by ensuring files are only 
         written after successful backup and evidence creation.
    """
    # [DNA-GATE] Final semantic verification before disk commit
    from yamlr.core.dna_utils import DNAValidator
    DNAValidator.verify_or_abort(healed_text, expected_hash=res_obj.dna_hash)

    if not skip_backup:
        backup_path = engine.fs.create_backup(full_path)
        try:
            res_obj.backup_created = str(backup_path.relative_to(engine.workspace))
        except ValueError:
            res_obj.backup_created = str(backup_path)

    if evidence_dir:
        receipt_path = generate_evidence_receipt(
            full_path, raw_text, healed_text, res_obj.findings,
            res_obj.identities, evidence_dir
        )
        if receipt_path == "ERROR_MISSING_PRO":
            res_obj.logic_logs.append("⚠️ Compliance Warning: Could not engage Yamlr Enterprise (Pro) Evidence Engine (Missing .pro module)")
        elif receipt_path:
            res_obj.evidence_receipt = receipt_path
            res_obj.logic_logs.append(f"🛡️ Compliance: Generated DNA-signed evidence -> {Path(receipt_path).name}")

    engine.fs.atomic_write(full_path, healed_text)
    res_obj.written = True
    logger.info(f"Healed and saved: {res_obj.file_path}")

def audit_stream(
    engine: "YamlrEngine",
    content: str,
    source_name: str = "stdin",
    strict_validation: bool = False,
    compact: bool = False,
    identity_mode: str = "infer",
    enforce_limits: bool = False,
    fix_tags: bool = False,
    harden: bool = False,
    enforce_probes: bool = False,
    enforce_namespace: bool = False,
    fast: bool = False,
    sovereign: bool = False,
    check_deprecations: bool = False,
    generate_receipts: bool = False,
    evidence_dir: Optional[str] = None,
    pro_preview: bool = False,
    safe_mode: bool = False,
) -> HealFileResult:
    """Audits content from input stream without disk I/O.
    
    Why: To support 'yamlr scan -' and piped input, enabling Yamlr to 
         be used as a filter in standard Unix pipelines.
    """
    start_time = time.time()
    try:
        if not content.strip():
            err = YamlrParseError("Input stream contains no YAML content")
            return HealFileResult(
                file_path=source_name,
                full_path=source_name,
                success=False,
                status="EMPTY_FILE",
                kind="Error",
                logic_logs=[str(err)],
                findings=[],
                dna_integrity_score=0,
                identities=[],
                timestamp=time.time(),
                processing_time_seconds=0.0,
                error=str(err)
            )

        # [Zero-Leakage] Temporarily switch engine version to manifest version for accurate re-binding
        from yamlr.core.utils import version_context
        active_version = detect_manifest_version(content, engine.cluster_version)
        
        with version_context(engine, active_version):
            config = build_heal_config(
                dry_run=True, # Streams are always dry-run
                strict_mode=strict_validation,
                strict_validation=strict_validation,
                compact=compact,
                identity_mode=identity_mode,
                enforce_limits=enforce_limits,
                fix_tags=fix_tags,
                harden=harden,
                enforce_probes=enforce_probes,
                enforce_namespace=enforce_namespace,
                fast=fast,
                sovereign=sovereign,
                check_deprecations=check_deprecations,
                generate_receipts=generate_receipts,
                evidence_dir=evidence_dir,
                file_path=source_name,
                cluster_version=active_version,
                cpu_limit=engine.cpu_limit,
                mem_limit=engine.mem_limit,
                default_namespace=engine.default_namespace,
                safe_mode=safe_mode or engine.safe_mode,
                pro_preview=pro_preview
            )

            try:
                result = engine.pipeline.heal(content, config=config)
            except Exception as e:
                logger.error(f"Healing error in stream: {e}")
                raise

        healed_text = result.content
        logs = result.logs
        score = result.dna_integrity_score
        identities = result.identities
        findings = result.findings

        is_modified = content.strip() != healed_text.strip()

        from dataclasses import asdict
        serialized_findings = [asdict(f) for f in findings]

        # [AUDIT-DEBT-02] Harden success bit: Any ERROR severity finding fails the manifest
        has_critical_errors = any(
            f.get("severity", "").upper() == "ERROR" 
            for f in serialized_findings
        )
        
        meets_threshold = (score >= engine.health_threshold) and not has_critical_errors
        
        display_status = derive_status(is_modified, dry=True, meets_threshold=meets_threshold)
        
        # [Audit v17] Respect Strict Mode failure even if not modified
        if result.status == HealStatus.FAILED:
            display_status = "FAILED"

        identities_list = []
        res_kind = "Unknown"
        if identities:
            identities_list = [id.to_dict() for id in identities]
            res_kind = identities_list[0].get("kind", "Unknown")

        # [v31] hostPath security checks are handled by StageSecurityScoring in the pipeline.
        # Removed redundant validate_absolute_paths re-check here.

        return HealFileResult(
            file_path=source_name,
            full_path=source_name,
            success=meets_threshold or not is_modified,
            status=display_status,
            written=False,
            kind=res_kind,
            backup_created=None,
            raw_content=content,
            healed_content=healed_text if is_modified else None,
            logic_logs=logs,
            findings=serialized_findings,
            dna_integrity_score=score,
            identities=identities_list,
            timestamp=time.time(),
            processing_time_seconds=time.time() - start_time,
            reconstruction_depth=result.depth,
            phy_status=result.phy_status,
            kbs_status=result.kbs_status,
            sem_status=result.sem_status,
            trust_score=getattr(result, "trust_score", 100.0),
            processing_stats=result.stats.__dict__ if hasattr(result.stats, "__dict__") else result.stats,
        )

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(source_name, "STREAM_ERROR", str(e), exception=e)
