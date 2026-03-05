"""
HEAL COMMAND LOGIC (Hidden)
"""

import json
import os
import time

from rich.panel import Panel

from yamlr.core.bridge import ProStatus, YamlrBridge
from yamlr.core.entrypoints.base import get_console, extract_cli_options

def _render_local_upgrade_advisory(console, from_v, to_v, score, findings):
    """Local advisory rendering to break CLI dependency."""
    if not score or score == 0:
        return
    color = "red" if score > 70 else "yellow" if score > 40 else "green"
    console.print(f"\n[{color} bold]⚠️  Upgrade Advisory (K8s {from_v} -> {to_v})[{color} bold]")
    console.print(f"[{color}]Risk Score: {score}/100[{color}]")
    if findings:
        console.print(f"[dim]See rule explanations below for deprecation details.[/dim]\n")

logger = get_console()


def handle_heal_command(args, engine, formatter, is_pro: bool):
    """
    Handles 'heal' subcommand execution.

    Why: To provide a safe, interactive multi-stage repair pipeline that
         honors Pro-gating, ensures backups, and supports NDJSON streaming.
    """
    options = extract_cli_options(args, is_pro)
    console = get_console()
    start_time = time.time()
    
    # [PRO-12-06] Intercept Demo Mode
    if getattr(options, "pro_preview", False):
        options.harden = True
        options.enforce_limits = True
        options.enforce_probes = True
        options.fix_tags = True
        options.enforce_namespace = True
        options.fix_refs = True
        options.check_deprecations = True
        # Force dry run
        setattr(args, "dry_run", True)
        setattr(args, "diff", True)

    # 1. Option Recovery / Specific to Heal
    is_dry = getattr(args, "dry_run", False)
    auto_yes = getattr(args, "yes", False)
    auto_yes_all = getattr(args, "yes_all", False) or auto_yes
    
    raw_stub = getattr(args, "stub_refs", False)
    raw_unsafe = getattr(args, "unsafe", False)
    stub_healing = True if raw_stub == "*" else raw_stub
    allow_unsafe = True if raw_unsafe == "*" else raw_unsafe

    # [PRO-12-05] --fix-refs: Cross-Resource Auto-Fix.
    # Superset of --stub-refs: activates selector typo correction,
    # port mismatch alignment, AND ghost stub generation.
    fix_refs = options.fix_refs
    if fix_refs:
        stub_healing = True  # --fix-refs implies stub generation
    
    skip_backup = getattr(args, "no_backup", False)
    quiet_mode = getattr(args, "quiet", False)

    # Automatically enable stub_healing if check_deprecations is on,
    # as deprecations often require structural replacements.
    check_deprecations = options.check_deprecations or engine.config.check_deprecations
    if check_deprecations and not stub_healing:
        stub_healing = True

    # [Scale Enhancement] Streaming & Output
    stream_to = getattr(args, "stream_to", None)
    output_format = getattr(args, "output", "text")
    is_json = output_format == "json"
    is_sarif = output_format == "sarif"

    # JSON/SARIF Mode Safety Check
    if (is_json or is_sarif) and not (is_dry or auto_yes or auto_yes_all):
        console.print(
            f"[red]Error: {output_format.upper()} output requires non-interactive mode. Please use --yes or --dry-run.[/red]",
            style="bold red",
        )
        return 1

    from yamlr.ui.diff import DiffEngine

    if not options.targets:
        return 1

    targets = options.targets
    is_batch_mode = len(targets) > 1 or (
        len(targets) == 1 and os.path.isdir(targets[0])
    )

    # Result Aggregator
    all_results = []

    if not is_batch_mode:
        target_file = targets[0]
        if not os.path.exists(target_file):
            if not (is_json or is_sarif):
                console.print(f"[red]❌ File not found: {target_file}[/red]")
            return 1

        # SINGLE FILE MODE
        result = engine.audit_and_heal_file(
            target_file,
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
            evidence_dir=options.evidence_dir,
            adapters_dir=options.adapters_dir,
        )

        # Logic to determine if we should write
        has_changes = result.get("healed_content") and result.get(
            "raw_content"
        ) != result.get("healed_content")

        if has_changes:
            # UI Diff Logic (Text only)
            if not (is_json or is_sarif) and not getattr(args, "quiet", False):
                try:
                    original = (
                        result.get("raw_content", "")
                        or open(target_file, "r", encoding="utf-8").read()
                    )
                except:
                    original = ""
                DiffEngine.render_diff(
                    original, result.get("healed_content", ""), target_file
                )

            if is_dry:
                if not (is_json or is_sarif):
                    if getattr(options, "pro_preview", False):
                        console.print("[bold cyan]💎 PRO PREVIEW MODE: No changes written.[/bold cyan]")
                    else:
                        console.print(
                            "[dim yellow]Dry-run: No changes written.[/dim yellow]"
                        )
                    formatter.display_report(result)

                if stub_healing:
                    engine.apply_semantic_fixes(
                        [result], stub_healing, allow_unsafe, dry_run=True
                    )

                all_results.append(result)
            elif auto_yes:
                # Apply
                final_result = engine.audit_and_heal_file(
                    target_file,
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
                    evidence_dir=options.evidence_dir,
                    adapters_dir=options.adapters_dir,
                )
                if getattr(final_result, "status", None) == "QUOTA_EXCEEDED":
                    from yamlr.core.license_manager import LicenseManager
                    LicenseManager.notify_quota_exceeded(final_result.logic_logs[0])
                    return 1

                if not (is_json or is_sarif) and not quiet_mode:
                    formatter.display_report(final_result)

                if stub_healing:
                    engine.apply_semantic_fixes(
                        [final_result], stub_healing, allow_unsafe, dry_run=False
                    )

                all_results.append(final_result)
            else:
                # Interactive (Text only)
                confirm = console.input(
                    f"\n[bold yellow]Apply changes to {target_file}? (y/n) [n]: [/bold yellow]"
                )
                if confirm.lower() == "y":
                    final_result = engine.audit_and_heal_file(
                        target_file,
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
                    evidence_dir=options.evidence_dir,
                    adapters_dir=options.adapters_dir,
                )
                    if getattr(final_result, "status", None) == "QUOTA_EXCEEDED":
                        from yamlr.core.license_manager import LicenseManager
                        LicenseManager.notify_quota_exceeded(final_result.logic_logs[0])
                        return 1

                    if stub_healing:
                        engine.apply_semantic_fixes(
                            [final_result], stub_healing, allow_unsafe, dry_run=False
                        )

                    if not quiet_mode:
                        formatter.display_report(final_result)
                    all_results.append(final_result)
                else:
                    if not (is_json or is_sarif):
                        console.print("[red]Aborted.[/red]")
                    return 0
        else:
            if not (is_json or is_sarif):
                # [EPIC-23] Upgrade Safety Advisory
                if check_deprecations:
                    from_v = "1.24" # Heuristic: assume 1.24 as common baseline if unknown
                    # We can refine this by looking at result.identities
                    risk_data = engine.get_upgrade_advisory_data(from_v, engine.cluster_version)
                    risk_map = {"HIGH": 80, "MEDIUM": 50, "LOW": 30, "NONE": 0}
                    score = risk_map.get(risk_data["risk_level"], 0)
                    _render_local_upgrade_advisory(console, from_v, engine.cluster_version, score, result.get("findings", []))

                console.print(f"[green]No changes required for {target_file}[/green]")
            all_results.append(result)

    else:
        # BATCH MODE
        if not (is_json or is_sarif):
            console.print(f"[bold cyan]Scanning {len(targets)} targets...[/bold cyan]")

        # 1. Dry Run Pass
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
                    evidence_dir=options.evidence_dir,
                    adapters_dir=options.adapters_dir,
                )
                if stub_healing:
                    engine.apply_semantic_fixes(
                        [res], stub_healing, allow_unsafe, dry_run=True
                    )
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
                        task_label="Healing",
                        evidence_dir=options.evidence_dir,
                        adapters_dir=options.adapters_dir,
                    )
                )

        changed_jobs = [
            j
            for j in dry_results
            if j.get("healed_content")
            and j.get("raw_content") != j.get("healed_content")
        ]

        if not changed_jobs:
            if not (is_json or is_sarif):
                console.print(
                    "[green]All files are healthy! No changes needed.[/green]"
                )
            all_results = dry_results
        elif is_dry:
            if not (is_json or is_sarif):
                duration = time.time() - start_time
                formatter.print_final_table(dry_results, summary_only=True, elapsed_time=duration, telemetry_data=engine.telemetry.get_stats())
                if getattr(options, "pro_preview", False):
                    console.print(
                        f"\n[bold cyan]💎 PRO PREVIEW Complete. {len(changed_jobs)} files are fixable with Enterprise.[/bold cyan]"
                    )
                else:
                    console.print(
                        f"\n[bold yellow]Dry Run Complete. Found {len(changed_jobs)} files to heal.[/bold yellow]"
                    )
            all_results = dry_results
        elif auto_yes or auto_yes_all:
            if not (is_json or is_sarif):
                console.print("[green]Applying repairs...[/green]")
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
                        evidence_dir=options.evidence_dir,
                        adapters_dir=options.adapters_dir,
                    )
                    if getattr(res, "status", None) == "QUOTA_EXCEEDED":
                        from yamlr.core.license_manager import LicenseManager
                        LicenseManager.notify_quota_exceeded(res.logic_logs[0])
                        return 1

                    if stub_healing:
                        engine.apply_semantic_fixes(
                            [res], stub_healing, allow_unsafe, dry_run=False
                        )
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
                        task_label="Healing",
                        evidence_dir=options.evidence_dir,
                        adapters_dir=options.adapters_dir,
                        )
                    )
            
            # [EPIC-23] Upgrade Safety Advisory (Batch)
            if not (is_json or is_sarif) and check_deprecations:
                from_v = "1.24"
                risk_data = engine.get_upgrade_advisory_data(from_v, engine.cluster_version)
                risk_map = {"HIGH": 80, "MEDIUM": 50, "LOW": 30, "NONE": 0}
                score = risk_map.get(risk_data["risk_level"], 0)
                all_findings = []
                for j in real_results:
                    all_findings.extend(getattr(j, "findings", []))
                _render_local_upgrade_advisory(console, from_v, engine.cluster_version, score, all_findings)

            all_results = real_results
        else:
            if not (is_json or is_sarif):
                console.print(
                    f"\n[bold red]WARNING: You are about to modify {len(changed_jobs)} files.[/bold red]"
                )
                console.print("[red]Files to be modified:[/red]")
                for job in changed_jobs[:10]:
                    console.print(f"  - {job.get('file_path')}")
                if len(changed_jobs) > 10:
                    console.print(
                        f"  [dim]... and {len(changed_jobs) - 10} more.[/dim]"
                    )
                console.print(
                    f"\n[dim]Backups will be created in: [bold]{engine.fs.backup_dir.resolve()}[/bold][/dim]"
                )

                confirm = console.input(
                    "[bold red]Type 'CONFIRM' to proceed: [/bold red]"
                )
                if confirm == "CONFIRM":
                    if not (is_json or is_sarif):
                        console.print("[green]Applying repairs...[/green]")
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
                                evidence_dir=options.evidence_dir,
                                adapters_dir=options.adapters_dir,
                            )
                            if getattr(res, "status", None) == "QUOTA_EXCEEDED":
                                from yamlr.core.license_manager import LicenseManager
                                LicenseManager.notify_quota_exceeded(res.logic_logs[0])
                                return 1

                            if stub_healing:
                                engine.apply_semantic_fixes(
                                    [res], stub_healing, allow_unsafe, dry_run=False
                                )
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
                                    task_label="Healing",
                                    evidence_dir=options.evidence_dir,
                                    adapters_dir=options.adapters_dir,
                                )
                            )
                    all_results = real_results
                else:
                    return 0

    # FINAL OUTPUT
    if is_json:
        output = {
            "summary": {
                "total_files": len(all_results),
                "healed": sum(1 for r in all_results if r.get("status") in ("HEALED", "MODIFIED") or (r.get("actions") and len(r["actions"]) > 0)),
                "mode": "dry-run" if is_dry else "live",
            },
            "results": [],
        }

        for r in all_results:
            output["results"].append({
                "file": r.get("file_path"),
                "status": r.get("status"),
                "findings": [f.get("message") for f in r.get("findings", [])],
                "repairs": r.get("logic_logs", []),
            })
        print(json.dumps(output, indent=2))
        
    elif is_sarif:
        from yamlr.core.io.sarif_formatter import SarifFormatter
        sarif = SarifFormatter().format(all_results)
        print(sarif)

    # [PRO-12-06] The CTA End Screen
    if getattr(options, "pro_preview", False):
        console.print("\n")
        console.print(Panel(
            "[bold white]This run was a 💎 PRO PREVIEW simulation.[/bold white]\n"
            "None of the changes above were written to disk.\n\n"
            "To unlock these Enterprise security and compliance features for real: \n"
            "▶ [cyan bold]https://yamlr.dev/pro[/cyan bold]",
            title="[bold red]Unlock Yamlr Enterprise[/bold red]",
            border_style="red",
            expand=False
        ))

    return 0

    return 0


def _check_trial_usage(is_pro: bool, console):
    """Checks and displays trial usage warnings."""
    if not is_pro:
        return
    try:
        from yamlr.pro import license as pro_license

        status, msg = YamlrBridge.check_pro_status()

        if status == ProStatus.TRIAL_ACTIVE:
            summary = pro_license.get_usage_summary()

            high_usage_features = []
            for feature, data in summary.items():
                if data["percentage"] >= 80:
                    feature_name = feature.replace("_", " ").title()
                    high_usage_features.append(
                        f"{feature_name}: {data['used']}/{data['limit']} ({data['percentage']}%)"
                    )

            if high_usage_features:
                console.print("\n[yellow]⚠️  Trial Usage Alert:[/yellow]")
                for feat in high_usage_features:
                    console.print(f"  {feat}")

            if any(d["percentage"] >= 100 for d in summary.values()):
                console.print("\n")
                console.print(
                    Panel(
                        "[bold yellow]🎉 Trial Limit Reached![/bold yellow]\n\n"
                        "You've successfully used Yamlr Pro.\n\n"
                        "Upgrade now for unlimited features:\n"
                        "  • [cyan]https://yamlr.dev/upgrade[/cyan]\n"
                        "  • Special: 20% off with code TRIAL20\n\n"
                        "  [dim]Yamlr OSS features remain unlimited.[/dim]",
                        border_style="yellow",
                        expand=False,
                    )
                )
    except Exception:
        pass
