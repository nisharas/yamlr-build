"""
Yamlr HEAL BATCH
----------------
Logic for batch healing directories and many files.
"""

from __future__ import annotations

import os

__all__ = ["perform_batch_dry_run", "perform_batch_apply"]


def perform_batch_dry_run(
    targets, engine, options, stub_healing, allow_unsafe, skip_backup, check_deprecations, sovereign, pro_preview=False
):
    """Executes a simulated healing run across multiple targets without modifying files.

    Why: To provide a safety-first preview of changes before they are applied to the filesystem.
    """
    dry_results = []
    for target in targets:
        if os.path.isfile(target):
            res = engine.audit_and_heal_file(
                target,
                dry_run=True,
                identity_mode=options.identity_mode,
                enforce_limits=options.enforce_limits,
                fix_tags=options.fix_tags,
                harden=options.harden,
                enforce_probes=options.enforce_probes,
                enforce_namespace=options.enforce_namespace,
                strict_validation=options.strict,
                compact=options.compact,
                skip_backup=skip_backup,
                check_deprecations=check_deprecations,
                sovereign=sovereign,
                evidence_dir=options.evidence_dir,
                adapters_dir=options.adapters_dir,
                from_report_path=options.from_report,
                pro_preview=pro_preview,
                emulate=getattr(options, "emulate", []),
                shadow=getattr(options, "shadow", False),
            )
            if stub_healing:
                engine.apply_semantic_fixes([res], stub_healing, allow_unsafe, dry_run=True)
            dry_results.append(res)
        elif os.path.isdir(target):
            dry_results.extend(
                engine.batch_heal(
                    target,
                    extensions=options.extensions,
                    max_depth=options.max_depth,
                    dry_run=True,
                    identity_mode=options.identity_mode,
                    stub_healing=stub_healing,
                    allow_unsafe=allow_unsafe,
                    enforce_limits=options.enforce_limits,
                    fix_tags=options.fix_tags,
                    harden=options.harden,
                    enforce_probes=options.enforce_probes,
                    strict_validation=options.strict,
                    compact=options.compact,
                    skip_backup=skip_backup,
                    stream_to=options.stream_to,
                    sovereign=sovereign,
                    task_label="Healing",
                    evidence_dir=options.evidence_dir,
                    adapters_dir=options.adapters_dir,
                    use_rust=options.use_rust,
                    from_report_path=options.from_report,
                    pro_preview=pro_preview,
                )
            )
    return dry_results


def perform_batch_apply(
    targets,
    engine,
    options,
    stub_healing,
    allow_unsafe,
    skip_backup,
    check_deprecations,
    sovereign,
    args,
    pro_preview=False,
):
    """Executes a real healing run across multiple targets, modifying files in-place.

    Why: To automate the remediation of Kubernetes manifest issues at scale.
    """
    real_results = []
    for target in targets:
        if os.path.isfile(target):
            res = engine.audit_and_heal_file(
                target,
                dry_run=False,
                force_write=True,
                identity_mode=options.identity_mode,
                enforce_limits=options.enforce_limits,
                fix_tags=options.fix_tags,
                harden=options.harden,
                enforce_probes=options.enforce_probes,
                enforce_namespace=options.enforce_namespace,
                strict_validation=options.strict,
                compact=options.compact,
                skip_backup=skip_backup,
                check_deprecations=check_deprecations,
                sovereign=sovereign,
                evidence_dir=options.evidence_dir,
                adapters_dir=options.adapters_dir,
                generate_receipts=getattr(args, "generate_receipts", False),
                pro_preview=pro_preview,
                patch_mode=getattr(options, "patch_mode", False),
                emulate=getattr(options, "emulate", []),
                shadow=getattr(options, "shadow", False),
            )
            if stub_healing:
                engine.apply_semantic_fixes([res], stub_healing, allow_unsafe, dry_run=False)
            real_results.append(res)
        elif os.path.isdir(target):
            real_results.extend(
                engine.batch_heal(
                    target,
                    extensions=options.extensions,
                    max_depth=options.max_depth,
                    dry_run=False,
                    force_write=True,
                    identity_mode=options.identity_mode,
                    stub_healing=stub_healing,
                    allow_unsafe=allow_unsafe,
                    enforce_limits=options.enforce_limits,
                    fix_tags=options.fix_tags,
                    harden=options.harden,
                    enforce_probes=options.enforce_probes,
                    enforce_namespace=options.enforce_namespace,
                    strict_validation=options.strict,
                    compact=options.compact,
                    skip_backup=skip_backup,
                    stream_to=options.stream_to,
                    check_deprecations=check_deprecations,
                    sovereign=sovereign,
                    task_label="Healing",
                    evidence_dir=options.evidence_dir,
                    adapters_dir=options.adapters_dir,
                    generate_receipts=getattr(args, "generate_receipts", False),
                    use_rust=options.use_rust,
                    from_report_path=options.from_report,
                    pro_preview=pro_preview,
                )
            )
    return real_results
