"""
HEAL COMMAND LOGIC
------------------
Responsible for the safe, interactive multi-stage repair pipeline.
"""

from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from yamlr.models import HealFileResult

from yamlr.core.entrypoints.base import (
    get_console, 
    extract_cli_options, 
    handle_interactive_export,
    verify_stability_consent
)
from yamlr.core.advisory import AdvisoryData, AdvisoryRenderer
from yamlr.core.entrypoints.heal_batch import perform_batch_dry_run, perform_batch_apply

__all__ = ["handle_heal_command"]

def handle_heal_command(args, engine, is_pro: bool):
    """
    Handles 'heal' subcommand execution.

    Why: To provide a safe, interactive multi-stage repair pipeline that
         honors Pro-gating, ensures backups, and supports NDJSON streaming.
    """
    # [SECURITY] License Gating (Strategic Enforcement)
    from yamlr.pro.license import license_manager
    if getattr(args, "sovereign", False):
        license_manager.feature_gate("sovereign", "heal --sovereign")
    if getattr(args, "fast", False):
        license_manager.feature_gate("fast", "heal --fast")

    options = extract_cli_options(args, is_pro)
    
    # [SECURITY] Stability Gate: Enforce consent for experimental K8s versions
    if options.kube_version:
         if not verify_stability_consent(options.kube_version, args):
              return 1  # User aborted
              
    console = get_console()
    _ = time.time()

    # 1. Preparation & Safety
    heal_ctx = _prepare_heal_options(engine, args, options, console)
    if heal_ctx is None: return 1 # Error already printed

    # 2. Logic Selection (Single vs Batch)
    targets = options.targets
    if not targets: return 1
    
    is_batch_mode = len(targets) > 1 or (len(targets) == 1 and os.path.isdir(targets[0]))
    all_results = []

    if not is_batch_mode:
        exit_code, single_results = _handle_single_file_healing(engine, targets[0], heal_ctx, options, args)
        if exit_code != 0: return exit_code
        all_results = single_results
    else:
        exit_code, batch_results = _handle_batch_healing(engine, targets, heal_ctx, options, args)
        if exit_code != 0: return exit_code
        all_results = batch_results

    # [QA-12-05] Crash Detection Loop
    if any(res.status == "ENGINE_ERROR" for res in all_results):
        console.print("\n[bold red]❌ CRITICAL: Engine failure detected.[/]")
        return 2

    # 3. Final Output & CTAs
    return _report_heal_finalization(all_results, engine, heal_ctx, is_pro, options, console)

def _report_heal_finalization(all_results, engine, heal_ctx, is_pro, options, console) -> int:
    """Finalizes the heal command by rendering reports, CTAs, and streaming."""
    output_fmt = heal_ctx["output_format"]
    
    if output_fmt == "text":
        advisory_data = AdvisoryData(
            results=all_results,
            is_pro=is_pro,
            is_dry_run=heal_ctx["is_dry"],
            verbose=options.verbose
        )
        renderer = AdvisoryRenderer(console)
        renderer.render_heal_results(advisory_data, engine)
    elif output_fmt == "json":
        AdvisoryRenderer(console).render_json_results(all_results, heal_ctx["is_dry"])
    elif output_fmt == "sarif":
        from yamlr.core.bridge import YamlrBridge
        if not (YamlrBridge.capabilities.can_export_format("sarif") or options.pro_preview):
             YamlrBridge.notify_pro_required("SARIF Export")
             return 0
        AdvisoryRenderer(console).render_sarif_results(all_results)
    
    # [INTERACTIVE EXPORT] Phase 10 Requirement
    if options.export:
        handle_interactive_export(all_results, options.export)
    
    # [Supplier Pivot] GitOps streaming remains in entrypoint for IO isolation
    if output_fmt == "text":
        _handle_gitops_streaming(all_results)
    
    return 0

def _prepare_heal_options(engine, args, options, console) -> Optional[Dict[str, Any]]:
    """Handles Pro preview, interaction flags, and format validation.
    
    Why: To unify the normalization of CLI flags and ensure interactive 
         modes are only allowed when safe output formats are selected.
    """

    ctx = {
        "is_dry": getattr(args, "dry_run", False) or (os.environ.get("CI", "").lower() == "true" and not getattr(args, "yes", False) and not getattr(args, "yes_all", False)),
        "auto_yes": getattr(args, "yes", False),
        "auto_yes_all": getattr(args, "yes_all", False) or getattr(args, "yes", False),
        "skip_backup": getattr(args, "no_backup", False),
        "quiet": getattr(args, "quiet", False),
        "output_format": getattr(args, "output", "text"),
        "check_deprecations": options.check_deprecations or engine.config.check_deprecations,
        "stub_healing": getattr(args, "stub_refs", False),
        "allow_unsafe": getattr(args, "unsafe", False),
        "fix_refs": options.fix_refs,
        "sovereign": options.sovereign,
        "pro_preview": options.pro_preview
    }
    
    # Normalize stub/unsafe
    if ctx["stub_healing"] == "*": ctx["stub_healing"] = True
    if ctx["allow_unsafe"] == "*": ctx["allow_unsafe"] = True
    if ctx["output_format"] in ["json", "sarif"] and not (ctx["is_dry"] or ctx["auto_yes"] or ctx["auto_yes_all"]):
        console.print(f"[red]Error: {ctx['output_format'].upper()} output requires non-interactive mode. Use --yes or --dry-run.[/red]", style="bold red")
        return None
    return ctx

def _handle_single_file_healing(engine, target_file, ctx, options, args) -> Tuple[int, List[HealFileResult]]:
    """Manages the lifecycle of a single-file repair (Dry -> Confirm -> Apply)."""
    console = get_console()
    if not os.path.exists(target_file):
        if ctx["output_format"] not in ["json", "sarif"]: 
            console.print(f"[red]❌ File not found: {target_file}[/red]")
        return 1, []

    # 1. Initial Dry Run
    result = _run_initial_audit(engine, target_file, ctx, options, args)
    has_changes = result.get("healed_content") and result.get("raw_content") != result.get("healed_content")
    
    if not has_changes:
        return _handle_no_changes(result, target_file, ctx, engine, console)

    # 2. Handle Proposed Changes (Diff + Advisory)
    _render_proposed_changes(result, target_file, ctx, options, engine, console)

    if ctx["is_dry"]:
        if ctx["stub_healing"]:
            engine.apply_semantic_fixes([result], ctx["stub_healing"], ctx["allow_unsafe"], dry_run=True)
        return 0, [result]
    
    # 3. Apply Phase
    if _confirm_apply(target_file, ctx, console):
        return _apply_remedies(target_file, ctx, options, engine, args)
    
    console.print("[red]Aborted.[/red]")
    return 0, []

def _run_initial_audit(engine, target_file, ctx, options, args) -> HealFileResult:
    """Executes the initial diagnostic dry-run."""
    return engine.audit_and_heal_file(
        target_file, dry_run=True, identity_mode=options.identity_mode,
        enforce_limits=options.enforce_limits, fix_tags=options.fix_tags,
        harden=options.harden, enforce_probes=options.enforce_probes,
        enforce_namespace=options.enforce_namespace, strict_validation=options.strict,
        compact=options.compact, skip_backup=ctx["skip_backup"],
        check_deprecations=ctx["check_deprecations"], sovereign=ctx["sovereign"],
        evidence_dir=options.evidence_dir, adapters_dir=options.adapters_dir,
        generate_receipts=getattr(args, "generate_receipts", False),
        pro_preview=ctx["pro_preview"]
    )

def _handle_no_changes(result, target_file, ctx, engine, console) -> Tuple[int, List[HealFileResult]]:
    """Handles the case where no changes are required."""
    if ctx["output_format"] == "text":
        if ctx["check_deprecations"]:
            AdvisoryRenderer(console).render_api_upgrade_advisory(engine, [result])
        if not getattr(console, "_yamlr_quiet", False):
            console.print(f"[green]No changes required for {target_file}[/green]")
    return 0, [result]

def _render_proposed_changes(result, target_file, ctx, options, engine, console):
    """Renders the diff and advisory for proposed changes."""
    from yamlr.ui.diff import DiffEngine
    if ctx["output_format"] not in ["json", "sarif"] and not ctx["quiet"]:
        DiffEngine.render_diff(result.get("raw_content", ""), result.get("healed_content", ""), target_file)
    
    if ctx["is_dry"]:
        AdvisoryRenderer(console).render_heal_results(
            AdvisoryData(results=[result], is_dry_run=True, verbose=options.verbose), engine
        )

def _confirm_apply(target_file, ctx, console) -> bool:
    """Gets user confirmation for applying changes."""
    if ctx["auto_yes_all"]:
        return True
    confirm = console.input(f"\n[bold yellow]Apply changes to {target_file}? (y/n) [n]: [/bold yellow]")
    return confirm.lower() == "y"

def _apply_remedies(target_file, ctx, options, engine, args) -> Tuple[int, List[HealFileResult]]:
    """Executes the final write and semantic fixes."""
    final_result = engine.audit_and_heal_file(
        target_file, dry_run=False, force_write=True,
        identity_mode=options.identity_mode, enforce_limits=options.enforce_limits,
        fix_tags=options.fix_tags, harden=options.harden, enforce_probes=options.enforce_probes,
        enforce_namespace=options.enforce_namespace, strict_validation=options.strict,
        compact=options.compact, skip_backup=ctx["skip_backup"],
        sovereign=ctx["sovereign"], evidence_dir=options.evidence_dir,
        adapters_dir=options.adapters_dir, generate_receipts=getattr(args, "generate_receipts", False),
        pro_preview=ctx["pro_preview"]
    )
    if getattr(final_result, "status", None) == "QUOTA_EXCEEDED":
        from yamlr.core.license_manager import LicenseManager
        LicenseManager.notify_quota_exceeded(final_result.logic_logs[0])
        return 1, []

    if ctx["stub_healing"]:
        engine.apply_semantic_fixes([final_result], ctx["stub_healing"], ctx["allow_unsafe"], dry_run=False)

    if not ctx["quiet"]:
        from yamlr.ui.formatter import YamlrFormatter
        YamlrFormatter().display_report(final_result)
    return 0, [final_result]

def _handle_batch_healing(engine, targets, ctx, options, args) -> Tuple[int, List[HealFileResult]]:
    """Orchestrates multi-file batch healing (Parallel/Sequential).
    
    Why: To efficiently process entire repositories while maintaining 
         'Zero-Failure Trust' through confirmation and backup safeguards.
    """
    console = get_console()
    if ctx["is_dry"]:
        dry_results = perform_batch_dry_run(
            targets, engine, options, ctx["stub_healing"], ctx["allow_unsafe"],
            ctx["skip_backup"], ctx["check_deprecations"], ctx["sovereign"],
            pro_preview=ctx["pro_preview"]
        )
        AdvisoryRenderer(console).render_heal_results(AdvisoryData(results=dry_results, is_dry_run=True, verbose=options.verbose), engine)
        return 0, dry_results
    
    if ctx["auto_yes_all"]:
        if ctx["output_format"] not in ["json", "sarif"]: console.print("[green]Applying repairs...[/green]")
        results = perform_batch_apply(
            targets, engine, options, ctx["stub_healing"], ctx["allow_unsafe"],
            ctx["skip_backup"], ctx["check_deprecations"], ctx["sovereign"], args,
            pro_preview=ctx["pro_preview"]
        )
        return 0, results

    # Interactive Batch
    dry_results = perform_batch_dry_run(
        targets, engine, options, ctx["stub_healing"], ctx["allow_unsafe"],
        ctx["skip_backup"], ctx["check_deprecations"], ctx["sovereign"],
        pro_preview=ctx["pro_preview"]
    )
    changed = [j for j in dry_results if j.get("healed_content") and j.get("raw_content") != j.get("healed_content")]
    if not changed:
        if ctx["output_format"] not in ["json", "sarif"]: console.print("[green]All files are healthy![/green]")
        return 0, dry_results
    
    console.print(f"\n[bold red]WARNING: You are about to modify {len(changed)} files.[/bold red]")
    confirm = console.input("[bold red]Type 'CONFIRM' to proceed: [/bold red]")
    if confirm == "CONFIRM":
        results = perform_batch_apply(
            targets, engine, options, ctx["stub_healing"], ctx["allow_unsafe"],
            ctx["skip_backup"], ctx["check_deprecations"], ctx["sovereign"], args,
            pro_preview=ctx["pro_preview"]
        )
        return 0, results
    return 0, []

def _handle_gitops_streaming(all_results):
    """Streams healed YAML to stdout for GitOps tools (Argo CD / Flux).
    
    Why: To allow Yamlr to be used as a pure manifest generator in a pipeline, 
         bridging the gap between auditing and automated generation.
    """
    from yamlr.cli.context import is_gitops
    if is_gitops():
        import sys
        import os
        from yamlr.cli.main import _orig_stdout_fd
        
        # If we redirected FD 1, we must use the saved FD to reach the real stdout
        if _orig_stdout_fd is not None:
            out = os.fdopen(_orig_stdout_fd, "w", encoding="utf-8")
        else:
            out = sys.__stdout__ or sys.stdout
            
        for i, res in enumerate(all_results):
            content = res.get("healed_content") or res.get("raw_content")
            if content:
                out.write(content.strip() + "\n")
                if i < len(all_results) - 1:
                    out.write("---\n")
        out.flush()
