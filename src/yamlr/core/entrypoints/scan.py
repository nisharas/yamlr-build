"""
SCAN COMMAND LOGIC (Hidden)
"""

import os
import sys
import time

from yamlr.core.bridge import YamlrBridge
from yamlr.core.entrypoints.base import get_console, extract_cli_options
from yamlr.ui.reporters import JSONReporter, SARIFReporter

def _render_local_upgrade_advisory(console, from_v, to_v, score, findings):
    """Local advisory rendering to break CLI dependency."""
    if not score or score == 0:
        return
    color = "red" if score > 70 else "yellow" if score > 40 else "green"
    console.print(f"\n[{color} bold]⚠️  Upgrade Advisory (K8s {from_v} -> {to_v})[{color} bold]")
    console.print(f"[{color}]Risk Score: {score}/100[{color}]")
    if findings:
        console.print(f"[dim]See rule explanations below for deprecation details.[/dim]\n")


def handle_scan_command(args, engine, formatter):
    """
    Handles 'scan' subcommand execution.

    Why: To separate CLI argument processing from the core audit engine
         and provide structured feedback for batch and single-file scans.
    """
    options = extract_cli_options(args, YamlrBridge.is_pro_enabled())
    
    start_time = time.time()
    job_results = []

    # Handle implicit "." and stdin mapping
    targets = options.targets if options.targets else ["."]
    if not options.targets and not sys.stdin.isatty():
        targets = ["-"]

    console = get_console()
    
    for target in targets:
        if target == "-":
            content = sys.stdin.read()
            job_results.append(
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
                    check_deprecations=options.check_deprecations or engine.config.check_deprecations,
                )
            )
        elif os.path.isfile(target):
            result = engine.audit_and_heal_file(
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
                check_deprecations=options.check_deprecations or engine.config.check_deprecations,
            )
            job_results.append(result)
        elif os.path.isdir(target):
            batch_results = engine.batch_heal(
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
                check_deprecations=options.check_deprecations or engine.config.check_deprecations,
                task_label="Scanning",
            )
            job_results.extend(batch_results)
        else:
            console.print(f"[red]❌ File not found: {target}[/red]")
            from yamlr.models import HealFileResult
            job_results.append(HealFileResult(
                file_path=target,
                full_path=target,
                success=False,
                status="FILE_NOT_FOUND",
                kind="Unknown",
                logic_logs=["File not found"],
                findings=[{"message": "File not found", "severity": "error"}],
                health_score=0,
                identities=[]
            ))

    # Handle Output Formats
    output_fmt = getattr(args, "output", "text")

    if output_fmt in ["json", "sarif"]:
        # Prepare data for reporters
        duration = time.time() - start_time
        
        if output_fmt == "json":
            # Helper to get attributes from both dicts and dataclasses
            def _gv(obj, key, default=None):
                """
                Why: Internal documentation policy compliance.
                What: Auto-generated summary.
                """
                if hasattr(obj, key): return getattr(obj, key)
                if isinstance(obj, dict): return obj.get(key, default)
                return default

            data = {
                "processed_files": [
                    (r.to_dict() if hasattr(r, "to_dict") else (r.__dict__ if hasattr(r, "__dict__") else r)) for r in job_results
                ],
                "healed_count": sum(
                    1 for r in job_results if _gv(r, "written") or _gv(r, "healed_content")
                ),
                "success_count": sum(1 for r in job_results if _gv(r, "success")),
            }
            from yamlr.ui.reporters import JSONReporter
            print(JSONReporter().generate(data, duration))
        elif output_fmt == "sarif":
            from yamlr.core.io.sarif_formatter import SarifFormatter
            print(SarifFormatter().format(job_results))

    else:
        # Standard Text/Table Output

        # Heuristic: If we only have 1 result, show detailed view
        if len(job_results) == 1:
            result = job_results[0]
            formatter.display_report(result, verbose=options.verbose)

            # Support --diff
            if getattr(args, "diff", False):
                from yamlr.ui.diff import DiffEngine

                if result.get("healed_content") and result.get(
                    "raw_content"
                ) != result.get("healed_content"):
                    DiffEngine.render_diff(
                        result.get("raw_content", ""),
                        result.get("healed_content", ""),
                        result.get("file_path", "Unknown"),
                    )

        else:
            duration = time.time() - start_time
            formatter.print_final_table(job_results, summary_only=options.summary_only, elapsed_time=duration, telemetry_data=engine.telemetry.get_stats())

            # Support --diff for Batch Scan
            if getattr(args, "diff", False):
                from yamlr.ui.diff import DiffEngine

                console = get_console()
                changed_jobs = [
                    j
                    for j in job_results
                    if j.get("healed_content")
                    and j.get("raw_content") != j.get("healed_content")
                ]

                if changed_jobs:
                    console.print(
                        f"\n[bold yellow]Found {len(changed_jobs)} files with proposed repairs:[/bold yellow]"
                    )
                    for job in changed_jobs:
                        DiffEngine.render_diff(
                            job.get("raw_content", ""),
                            job.get("healed_content", ""),
                            job.get("file_path", "Unknown"),
                        )
                else:
                    if not summary_mode:  # Don't double print if table shows it
                        console.print(
                            "\n[green]No changes proposed (files are healthy).[/green]"
                        )

    # Calculate Exit Code
    # Issue if:
    # 1. Success is False (Engine error)
    # 2. Healed content differs from raw (Proposed repairs)
    # 3. Status is SKIPPED (Unidentified resource)
    # 4. There are ANY findings (Validation issues, even if skipped)
    def _gv(obj, key, default=None):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if hasattr(obj, key): return getattr(obj, key)
        if isinstance(obj, dict): return obj.get(key, default)
        return default

    files_with_issues = [
        j
        for j in job_results
        if not _gv(j, "success")
        or (_gv(j, "healed_content") and _gv(j, "raw_content") != _gv(j, "healed_content"))
        or _gv(j, "status") == "SKIPPED"
        or _gv(j, "findings")
    ]
    exit_code = 1 if files_with_issues else 0

    if exit_code != 0 and output_fmt == "text":
        console = get_console()
        
        # [EPIC-23] Upgrade Safety Advisory
        if options.check_deprecations or engine.config.check_deprecations:
            # We assume 'current' version is whatever the manifest identity says, 
            # but for a general summary we can use the cluster version as 'to' and 
            # some reasonable 'from' or just a representative range.
            # Best: use the earliest detected version as 'from'.
            from_v = "1.24" # Default fallback
            if job_results:
                # Heuristic: Find minimum API version in findings
                pass 
            
            risk_data = engine.get_upgrade_advisory_data(from_v, engine.cluster_version)
            all_findings = []
            for j in job_results:
                all_findings.extend(_gv(j, "findings", []))
            
            # Map risk_level to score for the UI
            risk_map = {"HIGH": 80, "MEDIUM": 50, "LOW": 30, "NONE": 0}
            score = risk_map.get(risk_data["risk_level"], 0)
            
            _render_local_upgrade_advisory(console, from_v, engine.cluster_version, score, all_findings)

        # Check if stdin was used
        is_stdin = (not options.targets) and (not sys.stdin.isatty())
        if not is_stdin and "-" not in options.targets:
            # Construct a helpful heal command string
            if options.targets and len(options.targets) <= 3:
                path_str = " ".join(options.targets)
                heal_cmd = f"yamlr heal {path_str} --diff"
            else:
                heal_cmd = "yamlr heal <paths> --diff"

            console.print(
                f"[bold yellow]💡 Advice:[/bold yellow] Run [cyan]{heal_cmd}[/cyan] "
                f"to review and optionally apply Yamlr's proposed repairs.\n"
            )
            # Suggest yamlr explain if findings exist
            all_findings = []
            for j in job_results:
                findings = _gv(j, "findings", [])
                all_findings.extend(findings)

            if all_findings:
                unique_rules = sorted(
                    list(
                        set(f.get("rule_id") for f in all_findings if f.get("rule_id"))
                    )
                )
                if len(unique_rules) == 1:
                    console.print(
                        f"      Run [magenta]yamlr explain {unique_rules[0]}[/magenta] to understand this issue.\n"
                    )
                elif unique_rules:
                    console.print(
                        f"      Run [magenta]yamlr explain[/magenta] to see details on the {len(unique_rules)} rule types that were triggered in this scan.\n"
                    )
            else:
                console.print("")  # Final newline
        else:
            console.print(
                f"\n[bold yellow]⚠️  Found {len(files_with_issues)} issues in input stream.[/bold yellow]\n"
            )

    # [GTM-02-3] GitHub PR Comment Summaries
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            from yamlr.cli.github_bot import post_pr_comment
            post_pr_comment(job_results)
        except Exception as e:
            # Don't fail the scan if comment posting fails
            import logging
            logging.getLogger("yamlr").debug(f"Failed to post PR comment: {e}")

    return exit_code
