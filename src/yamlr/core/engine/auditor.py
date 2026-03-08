"""
Auditor Module for Yamlr Engine.

Why: To decouple single-file and stream-based auditing logic from the main orchestrator,
improving maintainability and testing scope.
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from yamlr.core.bridge import YamlrBridge
from yamlr.core.context import HealContext
from yamlr.core.exceptions import (YamlrEngineError, YamlrError,
                                   YamlrParseError, YamlrSecurityError)
from yamlr.core.utils import construct_file_error, derive_status
from yamlr.models import HealFileResult, HealConfig
from yamlr.core.engine.security import validate_absolute_paths

logger = logging.getLogger("yamlr.engine.auditor")

def audit_and_heal_file(
    engine,
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
    evidence_dir: Optional[str] = None,
    adapters_dir: Optional[str] = None,
    **kwargs: Any,
) -> HealFileResult:
    """Performs a full audit and healing cycle on a single manifest file.

    Why: Single entry-point for file-level healing to keep orchestration
         consistent and auditable via the telemetry layer.
    """
    # Handle both relative and absolute paths
    input_path = Path(relative_path)
    if input_path.is_absolute():
        full_path = input_path.resolve()
        # For absolute paths, use the file's parent directory as workspace
        actual_workspace = full_path.parent
    else:
        full_path = (engine.workspace / relative_path).resolve()
        actual_workspace = engine.workspace

    # SECURITY: PREVENT DIRECTORY TRAVERSAL (only for relative paths)
    if not input_path.is_absolute():
        try:
            full_path.relative_to(engine.workspace)
        except ValueError:
            err = YamlrSecurityError(f"Path '{relative_path}' is outside workspace")
            return construct_file_error(
                relative_path, "SECURITY_ERROR", str(err), exception=err, full_path=str(full_path)
            )

    # CONFIG CHECK: IGNORE RULES
    if engine.config.is_ignored(relative_path):
        return HealFileResult(
            file_path=str(relative_path),
            full_path=str(full_path),
            success=True,
            status="IGNORED",
            written=False,
            kind="Ignored",
            backup_created=None,
            raw_content=None,
            healed_content=None,
            logic_logs=["File ignored by .yamlr.yaml config"],
            health_score=100,
            identities=[],
            findings=[],
            timestamp=time.time(),
            processing_time_seconds=0.0,
        )

    if not full_path.exists():
        return construct_file_error(
            relative_path, "FILE_NOT_FOUND", "Path does not exist", full_path=str(full_path)
        )

    # --- [MONETIZATION] FREE TIER QUOTA CHECK ---
    # Only check if this is an actual HEAL operation (not dry_run)
    # AND it's not being called as part of a batch that already checked.
    if not dry_run and not kwargs.get("quota_checked", False):
        from yamlr.core.license_manager import LicenseManager
        is_allowed, remaining, msg = LicenseManager.is_healing_allowed(1)
        if not is_allowed:
            # We don't want to use rich here because auditor shouldn't have UI side-effects
            # It should return a failed result that the CLI can then format.
            return HealFileResult(
                file_path=str(relative_path),
                full_path=str(full_path),
                success=False,
                status="QUOTA_EXCEEDED",
                written=False,
                kind="Limit",
                logic_logs=[msg, "Visit https://yamlr.dev/pro for unlimited healing."],
                health_score=0,
                identities=[],
                findings=[],
                timestamp=time.time(),
                processing_time_seconds=0.0,
            )
        # Record usage immediately for single-file cli calls
        LicenseManager.record_healing_usage(1)
    # --------------------------------------------
    start_time = time.time()
    all_logic_logs = []

    try:
        # Read file with BOM handling
        try:
            raw_text = full_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            err = YamlrParseError(
                "File encoding not supported (not a valid UTF-8 text file)"
            )
            return construct_file_error(
                relative_path, "DECODE_ERROR", str(err), exception=err
            )

        if not raw_text.strip():
            err = YamlrParseError("File contains no YAML content")
            return construct_file_error(
                relative_path, "EMPTY_FILE", str(err), exception=err
            )

        # [SURGICAL FIX] Per-File Version Detection (Identity Conflict)
        active_version = engine.cluster_version
        try:
            if "apiVersion:" in raw_text:
                for line in raw_text.splitlines():
                    if line.strip().startswith("apiVersion:"):
                        val = line.split(":", 1)[1].strip()
                        detected = HealContext.resolve_version_from_api(val)
                        if detected:
                            active_version = detected
                            break
        except Exception:
            pass  # Fallback to engine default

        config = HealConfig(
            file_path=relative_path,
            cluster_version=active_version,
            identity_mode=identity_mode,
            strict_validation=strict_validation,
            compact=compact,
            enforce_limits=enforce_limits or engine.config.enforce_limits,
            fix_tags=fix_tags or engine.config.fix_tags,
            harden=harden or engine.config.harden,
            enforce_probes=enforce_probes or engine.config.enforce_probes,
            enforce_namespace=enforce_namespace or engine.config.enforce_namespace,
            fast=fast,
            check_deprecations=check_deprecations,
            fix_refs=fix_refs,
            cpu_limit=engine.cpu_limit,
            mem_limit=engine.mem_limit,
            default_namespace=engine.default_namespace
        )

        result = engine.pipeline.heal(raw_text, config=config)

        # Check for critical pipeline failure
        if result.status == engine.HealStatus.FAILED:
            return construct_file_error(
                relative_path,
                "PIPELINE_ERROR",
                result.error_message or "Unknown Pipeline Error",
            )

        if result.status == engine.HealStatus.SKIPPED:
            return HealFileResult(
                file_path=str(relative_path),
                full_path=str(full_path),
                success=True,
                status="SKIPPED",
                written=False,
                kind="Skipped",
                backup_created=None,
                raw_content=None,
                healed_content=None,
                logic_logs=result.logs,
                health_score=100,
                identities=[],
                findings=[],
                timestamp=time.time(),
                processing_time_seconds=time.time() - start_time,
            )

        # Unpack successful result
        healed_text = result.content
        pipeline_logs = result.logs
        health_score = result.health_score
        identities = result.identities
        findings = result.findings

        # Serialize findings with Rule Filtering
        serialized_findings = []
        if findings:
            from dataclasses import asdict
            for f in findings:
                if f.rule_id and engine.config.is_ignored(
                    relative_path, rule_id=f.rule_id
                ):
                    continue
                serialized_findings.append(asdict(f))

        # [PRO-14-21-5] Execute Enterprise Custom Remediation Adapters
        if adapters_dir:
            try:
                from yamlr.pro.compliance.adapters import AdapterEngine
                from yamlr.core.utils import get_hardened_yaml
                import io
                
                adapter_engine = AdapterEngine(adapters_dir)
                adapter_hits = [f for f in serialized_findings if f.get("rule_id") in adapter_engine.adapters]
                
                if adapter_hits:
                    # Strip string for safety
                    ryaml = get_hardened_yaml(typ="rt", pure=False) # Roundtrip
                    ryaml.preserve_quotes = True
                    docs = list(ryaml.load_all(healed_text))
                    adapted_any = False
                    
                    for f in adapter_hits:
                        rule_id = f["rule_id"]
                        for i, doc in enumerate(docs):
                            if isinstance(doc, dict):
                                # Cast to native dict for pure JSON compatibility with adapters
                                native_dict = dict(doc)
                                adapted_doc = adapter_engine.execute_adapter(rule_id, native_dict)
                                if adapted_doc:
                                    docs[i] = adapted_doc
                                    adapted_any = True
                                    if f"🔌 Compliance: Executed external remediation adapter -> {rule_id}" not in pipeline_logs:
                                        pipeline_logs.append(f"🔌 Compliance: Executed external remediation adapter -> {rule_id}")
                    if adapted_any:
                        buf = io.StringIO()
                        ryaml.dump_all(docs, buf)
                        healed_text = buf.getvalue()
            except ImportError:
                 pipeline_logs.append("⚠️ Compliance Warning: Could not engage Pro Adapters Engine (Missing .pro module)")
            except Exception as e:
                 logger.error(f"Adapter execution failed: {e}")

        all_logic_logs.extend(pipeline_logs)
        processing_time = time.time() - start_time

        # Determine file status
        is_modified = raw_text.strip() != healed_text.strip()
        
        # [AUDIT-DEBT-02] Harden success bit: Any ERROR severity finding fails the manifest
        has_critical_errors = any(
            f.get("severity", "").upper() == "ERROR" 
            for f in serialized_findings
        )
        
        meets_threshold = (health_score >= engine.health_threshold) and not has_critical_errors
        should_apply = is_modified and (meets_threshold or force_write)

        display_status = derive_status(is_modified, dry_run, meets_threshold)
        
        if has_critical_errors and display_status != "FAILED" and not dry_run:
             display_status = "FAILED"

        res_kind = "Unknown"
        identities_list = []

        if identities:
            for identity in identities:
                ident_data = identity.to_dict()
                if hasattr(identity, "deprecation_info") and identity.deprecation_info:
                    dep = identity.deprecation_info
                    if isinstance(dep, dict):
                        ident_data["deprecation_info"] = dep
                    else:
                        ident_data["deprecation_info"] = {
                            "deprecated_api": getattr(dep, "deprecated_api", "?"),
                            "replacement_api": getattr(dep, "replacement_api", "?"),
                            "removed_in_version": getattr(dep, "removed_in_version", "?"),
                            "migration_notes": getattr(dep, "migration_notes", ""),
                        }
                identities_list.append(ident_data)
            res_kind = identities_list[0].get("kind", "Unknown")

        # SECURITY: hostPath SAFEGUARDS
        try:
            from yamlr.core.utils import get_hardened_yaml
            yaml_h = get_hardened_yaml(typ="safe")
            updated_docs = list(yaml_h.load_all(healed_text))
            path_errors = validate_absolute_paths(updated_docs, engine.allowed_host_paths)
            if path_errors:
                all_logic_logs.append("⚠️ Security Warning: Unsafe hostPath detected in manifest:")
                for err in path_errors:
                    all_logic_logs.append(f"  → {err}")
                    health_score = max(0, health_score - 15)
        except Exception as e:
            logger.debug(f"Path security check failed (parsing error): {e}")

        remediation = None
        if serialized_findings and display_status in ["WARN", "PREVIEW"]:
            invoked_as = YamlrBridge.get_invoked_command()
            remediation = f"{invoked_as} heal {relative_path}"
            if any(f.get("rule_id") == "MissingReference" for f in serialized_findings):
                remediation += " --stub-refs"

        res_obj = HealFileResult(
            file_path=Path(relative_path).name,
            full_path=str(full_path),
            success=meets_threshold or not is_modified,
            status=display_status,
            written=False,
            kind=res_kind,
            backup_created=None,
            raw_content=raw_text,
            healed_content=healed_text if is_modified else None,
            logic_logs=all_logic_logs,
            findings=serialized_findings,
            health_score=health_score,
            identities=identities_list,
            timestamp=time.time(),
            processing_time_seconds=processing_time,
            remediation_command=remediation,
            reconstruction_depth=result.depth,
            phy_status=result.phy_status,
            kbs_status=result.kbs_status,
            sem_status=result.sem_status,
            processing_stats=result.stats.__dict__ if hasattr(result.stats, "__dict__") else result.stats,
        )
        res_obj._raw_identities = identities
        
        if not dry_run and should_apply:
            if not skip_backup:
                backup_path = engine.fs.create_backup(full_path)
                try:
                    res_obj.backup_created = str(backup_path.relative_to(engine.workspace))
                except ValueError:
                    res_obj.backup_created = str(backup_path)

            if evidence_dir:
                try:
                    from yamlr.pro.compliance.evidence import EvidenceEngine
                    import json
                    receipt = EvidenceEngine().generate_receipt(
                        file_path=str(full_path),
                        original_content=raw_text,
                        healed_content=healed_text,
                        findings=serialized_findings,
                        identities=identities_list
                    )
                    evidence_path = Path(evidence_dir) / f"evidence-{full_path.name}-{int(time.time())}.json"
                    evidence_path.parent.mkdir(parents=True, exist_ok=True)
                    evidence_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
                    res_obj.evidence_receipt = str(evidence_path)
                    all_logic_logs.append(f"🛡️ Compliance: Generated DNA-signed evidence -> {evidence_path.name}")
                except ImportError:
                    all_logic_logs.append("⚠️ Compliance Warning: Could not engage Pro Evidence Engine (Missing .pro module)")
                except Exception as e:
                    logger.error(f"Failed to generate evidence receipt: {e}")

            engine.fs.atomic_write(full_path, healed_text)
            res_obj.written = True
            logger.info(f"Healed and saved: {relative_path}")

        return res_obj

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(relative_path, "ENGINE_ERROR", str(e), time.time() - start_time, exception=e)

def audit_stream(
    engine,
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
    check_deprecations: bool = False,
) -> HealFileResult:
    """Audits content from input stream without disk I/O."""
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
                health_score=0,
                identities=[],
                timestamp=time.time(),
                processing_time_seconds=0.0,
                error=str(err)
            )

        config = HealConfig(
            file_path=source_name,
            cluster_version=engine.cluster_version,
            identity_mode=identity_mode,
            strict_validation=strict_validation,
            compact=compact,
            enforce_limits=enforce_limits,
            fix_tags=fix_tags,
            harden=harden,
            enforce_probes=enforce_probes,
            enforce_namespace=enforce_namespace,
            fast=fast,
            check_deprecations=check_deprecations,
            cpu_limit=engine.cpu_limit,
            mem_limit=engine.mem_limit,
            default_namespace=engine.default_namespace
        )

        result = engine.pipeline.heal(content, config=config)

        healed_text = result.content
        logs = result.logs
        score = result.health_score
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

        identities_list = []
        res_kind = "Unknown"
        if identities:
            identities_list = [id.to_dict() for id in identities]
            res_kind = identities_list[0].get("kind", "Unknown")

        # SECURITY: hostPath SAFEGUARDS (also for streams)
        try:
            from yamlr.core.utils import get_hardened_yaml
            yaml_h = get_hardened_yaml(typ="safe")
            updated_docs = list(yaml_h.load_all(healed_text))
            path_errors = validate_absolute_paths(updated_docs, engine.allowed_host_paths)
            if path_errors:
                logs.append("⚠️ Security Warning: Unsafe hostPath detected in content:")
                for err in path_errors:
                    logs.append(f"  → {err}")
                    score = max(0, score - 15)
        except Exception as e:
            logger.debug(f"Stream security check failed: {e}")

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
            health_score=score,
            identities=identities_list,
            timestamp=time.time(),
            processing_time_seconds=time.time() - start_time,
            reconstruction_depth=result.depth,
            phy_status=result.phy_status,
            kbs_status=result.kbs_status,
            sem_status=result.sem_status,
            processing_stats=result.stats.__dict__ if hasattr(result.stats, "__dict__") else result.stats,
        )

    except Exception as e:
        logger.error(f"Stream Error: {e}")
        if not isinstance(e, YamlrError):
            e = YamlrEngineError(str(e))
        return construct_file_error(source_name, "STREAM_ERROR", str(e), exception=e)
