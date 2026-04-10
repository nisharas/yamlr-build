"""
SCAN COMMAND LOGIC (Hidden)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

from yamlr.core.advisory import AdvisoryData, AdvisoryRenderer
from yamlr.core.bridge import YamlrBridge
from yamlr.core.entrypoints.base import (
    extract_cli_options,
    get_console,
    handle_interactive_export,
    verify_stability_consent,
)
from yamlr.models import HealFileResult

__all__ = ["handle_scan_command"]


def handle_scan_command(args, engine, timing_report: Optional[Dict[str, Any]] = None) -> int:
    """
    Handles 'scan' subcommand execution.

    Why: To separate CLI argument processing from the core audit engine
         and provide structured feedback for batch and single-file scans.
    """
    try:
        options = extract_cli_options(args, YamlrBridge.is_pro_enabled())

        # [SECURITY] Stability Gate: Enforce consent for experimental K8s versions
        if options.kube_version:
            if not verify_stability_consent(options.kube_version, args):
                return 1  # User aborted

        start_time = time.time()

        # 1. Target Preparation
        targets = _prepare_scan_targets(options)

        # 2. Execution Phase
        job_results = _execute_scan_loop(engine, targets, options, args)

        # [ACCELERATION] Apply Baseline Filtering
        baseline_file = getattr(args, "baseline", None)
        if baseline_file:
            job_results = _apply_baseline_filter(engine, job_results, baseline_file)

        duration = time.time() - start_time

        # 3. Reporting Phase
        output_fmt = getattr(args, "output", "text")
        if output_fmt in ["json", "sarif"]:
            _report_structured_scan(job_results, output_fmt, duration, options, timing_report=timing_report)
        else:
            advisory_data = AdvisoryData(
                results=job_results, duration=duration, summary_only=options.summary_only, verbose=options.verbose
            )
            renderer = AdvisoryRenderer(get_console())
            renderer.render_scan_report(advisory_data, args)

        # 4. Finalization (Advice and Exit Code)
        exit_code = _calculate_scan_exit_code(job_results)

        # [INTERACTIVE EXPORT] Phase 10 Requirement
        if options.export:
            handle_interactive_export(job_results, options.export)

        if output_fmt == "text":
            if options.check_deprecations or engine.config.check_deprecations:
                renderer.render_api_upgrade_advisory(engine, job_results)
            renderer.render_next_steps("scan", job_results)

        # 5. Integration (GitHub PR)
        if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("INPUT_COMMENT", "true").lower() == "true":
            _try_post_github_comment(job_results)

        return exit_code
    except Exception:
        import traceback

        traceback.print_exc()
        raise


def _prepare_scan_targets(options) -> List[str]:
    """Resolves scan targets from CLI options or stdin.

    Why: To ensure that Yamlr correctly handles various input sources,
         including explicit paths and piped standard input.
    """
    import glob

    raw_targets = options.targets if options.targets else ["."]
    if not options.targets and not sys.stdin.isatty():
        return ["-"]

    expanded_targets = []
    for t in raw_targets:
        if "*" in t or "?" in t:
            matches = glob.glob(t, recursive=True)
            if matches:
                # Filter out directories if they were meant to be files?
                # No, engine handles dirs.
                expanded_targets.extend(matches)
            else:
                expanded_targets.append(t)
        else:
            expanded_targets.append(t)
    return expanded_targets


def _execute_scan_loop(engine, targets: List[str], options, args) -> List[HealFileResult]:
    """Iterates over targets and performs audits.

    Why: To orchestrate the analysis of multiple files and directories,
         delegating to the appropriate engine entry points.
    """
    results = []
    console = get_console()
    check_deprecations = options.check_deprecations or engine.config.check_deprecations
    gen_receipts = getattr(args, "generate_receipts", False)

    for target in targets:
        if target == "-":
            content = sys.stdin.read()
            results.append(
                engine.audit_stream(
                    content,
                    source_name="<stdin>",
                    identity_mode=options.identity_mode,
                    enforce_limits=options.enforce_limits,
                    fix_tags=options.fix_tags,
                    harden=options.harden,
                    enforce_probes=options.enforce_probes,
                    enforce_namespace=options.enforce_namespace,
                    strict_validation=options.strict,
                    compact=options.compact,
                    fast=options.fast,
                    check_deprecations=check_deprecations,
                    generate_receipts=gen_receipts,
                    pro_preview=options.pro_preview,
                )
            )
        elif os.path.isfile(target):
            results.append(
                engine.audit_and_heal_file(
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
                    fast=options.fast,
                    check_deprecations=check_deprecations,
                    generate_receipts=gen_receipts,
                    pro_preview=options.pro_preview,
                )
            )
        elif os.path.isdir(target):
            results.extend(
                engine.batch_heal(
                    root_path=target,
                    extensions=options.extensions,
                    max_depth=options.max_depth,
                    dry_run=True,
                    identity_mode=options.identity_mode,
                    enforce_limits=options.enforce_limits,
                    fix_tags=options.fix_tags,
                    harden=options.harden,
                    enforce_probes=options.enforce_probes,
                    enforce_namespace=options.enforce_namespace,
                    strict_validation=options.strict,
                    compact=options.compact,
                    fast=options.fast,
                    stream_to=options.stream_to,
                    check_deprecations=check_deprecations,
                    task_label="Scanning",
                    generate_receipts=gen_receipts,
                    use_rust=options.use_rust,
                    from_report_path=options.from_report,
                    pro_preview=options.pro_preview,
                )
            )
        else:
            console.print(f"[red]❌ File not found: {target}[/red]")
            from yamlr.core.engine.models import AnalysisResult, HealFileResult

            results.append(
                HealFileResult(
                    file_path=target,
                    full_path=target,
                    success=False,
                    status="FILE_NOT_FOUND",
                    kind="Unknown",
                    logic_logs=["File not found"],
                    findings=[
                        AnalysisResult(
                            analyzer_name="Lexer",
                            severity="ERROR",
                            message="File not found",
                            file_path=target,
                            rule_id="fs/not-found",
                            suggestion="Verify the file path or current working directory."
                        )
                    ],
                    dna_integrity_score=0,
                    identities=[],
                )
            )
    return results


def _report_structured_scan(job_results, output_fmt, duration, options, timing_report: Optional[Dict[str, Any]] = None):
    """Generates machine-readable scan reports (JSON/SARIF/SBOM)."""
    if output_fmt == "json":
        _report_json(job_results, duration, options, timing_report)
    elif output_fmt == "sarif":
        _report_sarif(job_results, options, timing_report)
    elif output_fmt == "sbom":
        _report_sbom(job_results, options)


def _report_json(job_results, duration, options, timing_report):
    from yamlr.ui.reporters import JSONReporter
    data = {
        "processed_files": job_results,
        "healed_count": sum(1 for r in job_results if getattr(r, "written", False) or getattr(r, "healed_content", None)),
        "success_count": sum(1 for r in job_results if getattr(r, "success", False)),
    }
    sys.stdout.write(JSONReporter().generate(data, duration, scout=options.scout, timing=timing_report) + "\n")


def _report_sarif(job_results, options, timing_report):
    from yamlr.core.bridge import YamlrBridge
    if not (YamlrBridge.capabilities.can_export_format("sarif") or options.pro_preview):
        YamlrBridge.notify_pro_required("SARIF Export")
        return

    used_versions = sorted({getattr(r, "cluster_version", options.kube_version or "v1.31") for r in job_results})
    default_version = os.environ.get("YAMLR_KUBE_VERSION", "v1.31")
    extra = {
        "kubeVersion": used_versions[0] if used_versions else default_version,
        "engineMode": "PRO" if YamlrBridge.is_pro_enabled() else "OSS",
    }
    from yamlr.core.io.sarif_formatter import SarifFormatter
    sys.stdout.write(SarifFormatter().format(job_results, timing=timing_report, extra_props=extra) + "\n")


def _report_sbom(job_results, options):
    from yamlr.core.bridge import YamlrBridge
    if not (YamlrBridge.capabilities.can_export_format("sbom") or options.pro_preview):
        YamlrBridge.notify_pro_required("SBOM Export")
        return

    from yamlr.core.forensics.sbom_generator import CycloneDXExporter
    all_findings = []
    for r in job_results:
        all_findings.extend(getattr(r, "findings", []))
    metadata = {"project_name": os.path.basename(os.getcwd())}
    sys.stdout.write(CycloneDXExporter(metadata=metadata).export(all_findings) + "\n")


def _calculate_scan_exit_code(job_results) -> int:
    """Determines exit code based on scan findings and stability.

    Why: To enforce the 'Non-Zero Exit Pillar' for CI/CD, ensuring that
         any violation or proposed fix blocks the build pipeline.
    """
    for j in job_results:
        success = getattr(j, "success", False)
        status_val = getattr(j, "status", "")
        # Handle string or Enum
        status = str(status_val).upper()
        if hasattr(status_val, "value"):
            status = str(status_val.value).upper()

        findings = getattr(j, "findings", [])

        # [QA-12-05] Crash Detection Loop
        if "ENGINE_ERROR" in status:
            return 2

        # Exit code 1 if:
        # 1. Pipeline failed
        # 2. Pipeline skipped (requires attention)
        # 3. Non-filtered findings exist (regressions or non-ignored issues)
        if not success or "SKIPPED" in status or "FAILED" in status or "QUOTA" in status or findings:
            return 1
    return 0


def _try_post_github_comment(job_results):
    """Attempts to post PR comments when running in GitHub Actions.

    Why: To enhance developer workflow by surfacing Yamlr findings
         directly in Pull Request comments on GitHub.
    """
    try:
        from yamlr.cli.github_bot import post_pr_comment

        # Scan command is effectively always a dry run (no content modified)
        post_pr_comment(job_results, is_dry_run=True)
    except Exception as e:
        import logging

        logging.getLogger("yamlr").debug(f"Failed to post PR comment: {e}")
