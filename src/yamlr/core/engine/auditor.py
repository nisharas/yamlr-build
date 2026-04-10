from __future__ import annotations

"""
Auditor Module for Yamlr Engine.

Why: To decouple single-file and stream-based auditing logic from the main orchestrator,
     improving maintainability and testing scope.
"""
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine

from yamlr.core.engine.auditor_helpers import build_heal_config, detect_manifest_version
from yamlr.core.exceptions import YamlrEngineError, YamlrError, YamlrParseError
from yamlr.core.gatekeeper import ProGate
from yamlr.core.engine.models import HealAction, HealFileResult
from yamlr.core.utils import construct_file_error

logger = logging.getLogger("yamlr.engine.auditor")

__all__ = ["audit_and_heal_file", "audit_stream", "HealOptions"]


@dataclass
class HealOptions:
    """Unified container for healing orchestration flags."""
    dry_run: bool = True
    force_write: bool = False
    strict_validation: bool = False
    compact: bool = False
    identity_mode: str = "infer"
    enforce_limits: bool = False
    fix_tags: bool = False
    harden: bool = False
    enforce_probes: bool = False
    skip_backup: bool = False
    enforce_namespace: bool = False
    fast: bool = False
    check_deprecations: bool = False
    fix_refs: bool = False
    sovereign: bool = False
    generate_receipts: bool = False
    evidence_dir: Optional[str] = None
    safe_mode: bool = False
    pro_preview: bool = False
    cluster_version: Optional[str] = None
    patch_mode: bool = False
    emulate: List[str] = field(default_factory=list)
    shadow: bool = False
    kube_context: Optional[str] = None

    @classmethod
    def from_kwargs(cls, kwargs: Dict[str, Any]) -> "HealOptions":
        """Factory to create options from legacy keyword arguments."""
        keys = [
            "dry_run", "force_write", "strict_validation", "compact", 
            "identity_mode", "enforce_limits", "fix_tags", "harden", 
            "enforce_probes", "skip_backup", "enforce_namespace", "fast",
            "check_deprecations", "fix_refs", "sovereign", "generate_receipts", 
            "evidence_dir", "safe_mode", "pro_preview", "cluster_version",
            "patch_mode", "emulate", "shadow", "kube_context"
        ]
        vals = {}
        for k in keys:
            if k in kwargs:
                vals[k] = kwargs.get(k) # Do NOT pop, we need these for downstream engine calls
        
        if "strict" in kwargs:
            vals["strict_validation"] = kwargs.pop("strict")
            
        return cls(**vals)


def audit_and_heal_file(
    engine: "YamlrEngine",
    relative_path: str,
    options: Optional[HealOptions] = None,
    **kwargs: Any,
) -> HealFileResult:
    """Performs a full audit and healing cycle on a single manifest file."""
    from yamlr.core.engine.auditor_helpers import resolve_audit_paths
    from yamlr.core.exceptions import YamlrSecurityError

    start_time = time.time()

    try:
        # 1. Option Normalization
        opt = options or HealOptions.from_kwargs(kwargs)

        # 2. Resolve Paths and Security
        try:
            full_path, _ = resolve_audit_paths(engine, relative_path)
        except YamlrSecurityError as e:
            return construct_file_error(relative_path, "SECURITY_ERROR", str(e), exception=e)

        # 3. Config Ignore Check (Audit only what matters)
        if engine.config.is_ignored(relative_path):
            return _create_ignored_result(relative_path, str(full_path))

        # 4. Quota Check (Remediation phase only)
        if not ProGate.check_quota(1, is_dry_run=opt.dry_run):
            return _create_quota_error_result(relative_path, str(full_path), "Free Tier Limit Reached")

        # 5. Read Content
        raw_text = kwargs.get("content")
        if raw_text is None:
            raw_text = _read_manifest_content(full_path, relative_path)

        if isinstance(raw_text, HealFileResult):
            return raw_text  # Return pre-packaged Error Result

        # [Security] Pre-Scan for Credentials
        if not opt.safe_mode and not engine.safe_mode:
            _detect_secrets(raw_text, relative_path)

        # 6. Build High-Fidelity Config
        active_version = opt.cluster_version or detect_manifest_version(raw_text, engine.cluster_version)
        config = _build_orchestration_config(engine, relative_path, active_version, opt)

        # 7. Execute Diagnostic Cycle
        res_obj = _execute_healing_cycle(
            engine, relative_path, raw_text, str(full_path), config, start_time, opt, **kwargs
        )

        # 8. Commitment Phase (Writes and Backups)
        can_write = res_obj.status in ["APPLIED", "FIXED", "HEALED"] or opt.force_write
        if not opt.dry_run and can_write:
            _finalize_healing_file(
                engine, res_obj, full_path, raw_text, res_obj.healed_content,
                opt.skip_backup, opt.evidence_dir,
                patch_mode=opt.patch_mode
            )

        return res_obj

    except Exception as e:
        logger.error(f"Pipeline failure in {relative_path}: {str(e)}", exc_info=True)
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(relative_path, "ENGINE_ERROR", str(e), time.time() - start_time, exception=e)


def _build_orchestration_config(
    engine, relative_path, active_version, options: HealOptions
):
    """Assembles the granular configuration for the healing pipeline."""
    return build_heal_config(
        dry_run=options.dry_run,
        strict_mode=options.strict_validation,
        strict_validation=options.strict_validation,
        compact=options.compact,
        identity_mode=options.identity_mode,
        enforce_limits=options.enforce_limits or engine.config.enforce_limits,
        fix_tags=options.fix_tags or engine.config.fix_tags,
        harden=options.harden or engine.config.harden,
        enforce_probes=options.enforce_probes or engine.config.enforce_probes,
        enforce_namespace=options.enforce_namespace or engine.config.enforce_namespace,
        fast=options.fast,
        sovereign=options.sovereign,
        check_deprecations=options.check_deprecations,
        fix_refs=options.fix_refs,
        generate_receipts=options.generate_receipts,
        file_path=relative_path,
        cluster_version=active_version,
        cpu_limit=engine.cpu_limit,
        mem_limit=engine.mem_limit,
        default_namespace=engine.default_namespace,
        evidence_dir=options.evidence_dir,
        safe_mode=options.safe_mode or engine.safe_mode,
        pro_preview=options.pro_preview,
        debug_stages=engine.debug_stages,
        allowed_registries=engine.config.trusted_registries,
        timing=engine.timing,
        config_manager=engine.config,
    )


def _execute_healing_cycle(
    engine, relative_path, raw_text, full_path_str, config, start_time, opt: HealOptions, **kwargs
) -> HealFileResult:
    """Manages the version-aware execution of the diagnostic pipeline."""
    from yamlr.core.utils import version_context

    with version_context(engine, config.cluster_version):
        try:
            external_findings = kwargs.pop("external_findings", None)
            return engine.pipeline.process_file(
                raw_text,
                relative_path,
                full_path_str,
                config,
                start_time,
                external_findings=external_findings,
                patch_mode=opt.patch_mode,
                emulate=opt.emulate,
                shadow=opt.shadow,
                kube_context=opt.kube_context,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Execution Error in {relative_path}: {e}")
            raise


def _create_ignored_result(relative_path: str, full_path: str) -> HealFileResult:
    """Creates a standardized result for ignored files."""
    return HealFileResult(
        file_path=relative_path,
        full_path=full_path,
        success=True,
        status="IGNORED",
        written=False,
        kind="Ignored",
        logic_logs=["File ignored by .yamlr.yaml config"],
        dna_integrity_score=100,
        identities=[],
        findings=[],
        timestamp=time.time(),
        processing_time_seconds=0.0,
        identities_raw=[],
        phy_status="100%",
        kbs_status="100%",
        sem_status="100%",
    )


def _create_quota_error_result(relative_path: str, full_path: str, msg: str) -> HealFileResult:
    """Creates a standardized result for quota errors."""
    return HealFileResult(
        file_path=relative_path,
        full_path=full_path,
        success=False,
        status="QUOTA_EXCEEDED",
        written=False,
        kind="Limit",
        logic_logs=[msg, "Visit https://yamlr.dev/pro for unlimited healing."],
        dna_integrity_score=0,
        identities=[],
        findings=[
            HealAction(
                stage="Licensing",
                action_type="limit_reached",
                target=relative_path,
                description=msg,
                severity="ERROR",
                rule_id="QUOTA",
            )
        ],
        timestamp=time.time(),
        processing_time_seconds=0.0,
        identities_raw=[],
        phy_status="0%",
        kbs_status="0%",
        sem_status="0%",
    )


def _read_manifest_content(full_path: Path, relative_path: str) -> Union[str, HealFileResult]:
    """Reads manifest content with forensic safety checks."""
    try:
        raw_text = full_path.read_text(encoding="utf-8-sig")
        if not raw_text.strip():
            err = YamlrParseError("File contains no YAML content")
            return construct_file_error(relative_path, "EMPTY_FILE", str(err), exception=err)
        return raw_text
    except UnicodeDecodeError:
        err = YamlrParseError("File encoding not supported (Use UTF-8)")
        return construct_file_error(relative_path, "DECODE_ERROR", str(err), exception=err)


def _detect_secrets(content: str, path: str):
    """Pre-scan deterrent for raw secrets."""
    import re
    from yamlr.core.exceptions import YamlrSecurityError
    patterns = {
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Generic Secret Entropy": r"[a-zA-Z0-9+/]{40,}",
        "Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
        "Slack Token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, content):
            msg = f"Security Violation: Potential {name} detected in {path}. Yamlr refuses to process files containing raw secrets."
            logger.critical(msg)
            raise YamlrSecurityError(msg)


def _finalize_healing_file(
    engine: "YamlrEngine", res_obj: HealFileResult, full_path: Path, 
    raw_text: str, healed_text: str, skip_backup: bool, 
    evidence_dir: Optional[str], patch_mode: bool = False
):
    """Finalizes persistence: Backups, Evidence, and Atomic Write."""
    # 5. [DNA-SAFEGUARD] Forensic Verification
    if healed_text is not None:
        from yamlr.core.dna_utils import DNAValidator
        DNAValidator.verify_or_abort(healed_text, expected_hash=res_obj.dna_hash)
    
    if not skip_backup:
        backup_path = engine.fs.create_backup(full_path)
        try:
            res_obj.backup_created = str(backup_path.relative_to(engine.workspace))
        except ValueError:
            res_obj.backup_created = str(backup_path)

    if evidence_dir:
        from yamlr.core.pro.evidence_engine import generate_evidence_receipt
        receipt_path = generate_evidence_receipt(
            full_path, raw_text, healed_text, res_obj.findings, res_obj.identities, evidence_dir
        )
        if receipt_path == "ERROR_MISSING_PRO":
            res_obj.logic_logs.append("⚠️ Compliance Warning: Evidence Engine unavailable.")
        elif receipt_path:
            res_obj.evidence_receipt = receipt_path

    # 6. [NEW] Patch Bridge (Plan 1B)
    if patch_mode:
        import sys
        sys.stderr.write(f"DEBUG: Entering Patch Bridge logic. patch_mode={patch_mode}\n")
        from yamlr.core.utils.patch_generator import PatchGenerator
        patch_path = engine.workspace / "yamlr-patches.yaml"
        
        # Mandatory Backup for Safety (V2 Protocol)
        if patch_path.exists() and not skip_backup:
            sys.stderr.write(f"DEBUG: Creating backup for {patch_path}\n")
            engine.fs.create_backup(patch_path)
            
        sys.stderr.write(f"DEBUG: calling generate_and_append. diff_exists={raw_text != healed_text}\n")
        PatchGenerator.generate_and_append(patch_path, raw_text, healed_text)
        res_obj.logic_logs.append(f"📦 Patch Bridge: Remediation appended to {patch_path.name}")
        return

    engine.fs.atomic_write(full_path, healed_text)
    res_obj.written = True


def audit_stream(
    engine: "YamlrEngine", content: str, source_name: str = "stdin", 
    options: Optional[HealOptions] = None, **kwargs: Any,
) -> HealFileResult:
    """Audits content from a stream without disk persistence."""
    start_time = time.time()
    try:
        if not content.strip():
            err = YamlrParseError("Stream contains no content")
            return construct_file_error(source_name, "EMPTY_FILE", str(err), exception=err)

        opt = options or HealOptions.from_kwargs(kwargs)
        if not opt.safe_mode and not engine.safe_mode:
            _detect_secrets(content, source_name)

        active_version = opt.cluster_version or detect_manifest_version(content, engine.cluster_version)
        config = _build_orchestration_config(engine, source_name, active_version, opt)

        return _execute_healing_cycle(
            engine, source_name, content, source_name, config, start_time, **kwargs
        )
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(source_name, "STREAM_ERROR", str(e), time.time() - start_time, exception=e)
