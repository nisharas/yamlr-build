"""Output formatting for CLI scan results, diffs, and summaries."""
import logging
import os
import re
import sys
from typing import Any

from yamlr.cli.remediation import apply_remediation
from yamlr.ui.theme import (
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    ICON_PRO,
    ICON_SUCCESS,
    console,
)

logger = logging.getLogger(__name__)

STYLE_BOLD_CYAN = "bold cyan"

def scrub_ansi(text: str) -> str:
    """Neutralizes ANSI escape sequences for clean forensic reporting."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]')
    return ansi_escape.sub('', text)

def render_resource_results(res: Any, telemetry: Any, command: str, apply: bool, dry_run: bool = False, diff: bool = False, create_stubs: bool = False):
    """Renders results for a single resource and handles remediation logic."""
    # Combine both schema and integrity violations for unified output
    all_violations = list(res.violations) + list(res.integrity_violations)
    is_clean = not all_violations and res.health_score > 99.99
    
    status_style = "green" if is_clean else "yellow"
    status_text = "CLEAN" if is_clean else f"VIOLATIONS: {len(all_violations)}"
    
    # --- TASK 60: Forensic Confidence (Heal Probability) ---
    heal_prob = 100 if is_clean else int(res.health_score)
    
    if heal_prob > 80:
        prob_style = "green"
    elif heal_prob > 50:
        prob_style = "yellow"
    else:
        prob_style = "red"
    
    name = f"{res.identity.kind}/{res.identity.name}" if res.identity else res.file_path
    
    # --- TASK 61: Golden DNA Seal Visualization ---
    import yamlr_native
    with open(res.file_path, "r", encoding="utf-8") as f:
        content = f.read()
    dna_hash = yamlr_native.native_calculate_dna_hash(content)
    dna_marker = f" [bold #875fff]{ICON_PRO} DNA: {dna_hash[:8]}[/bold #875fff]"

    console.print(f"  [[{status_style}]{status_text}[/{status_style}]] [bold]{scrub_ansi(name)}[/bold]{dna_marker} [dim]| Heal Prob: [/dim][{prob_style}]{heal_prob}%[/{prob_style}]")
    
    for v in all_violations:
        field = getattr(v, "field_path", getattr(v, "check_name", "General"))
        rule_id = getattr(v, "rule_id", None)
        if rule_id:
            rule_url = f"https://yamlr.dev/errors/{rule_id.lower()}"
            console.print(f"    - [{rule_id}] [dim]{field}:[/dim] {scrub_ansi(v.message)} [dim]({rule_url})[/dim]")
        else:
            console.print(f"    - [dim]{field}:[/dim] {scrub_ansi(v.message)}")
    
    # Emit GitHub Actions workflow commands in CI for inline PR annotations
    if os.getenv("GITHUB_ACTIONS"):
        for v in res.violations:
            field = getattr(v, "field_path", "spec")
            msg = scrub_ansi(v.message)
            print(f"::error file={res.file_path},title=Yamlr Schema Violation::{msg} (field: {field})")
        for iv in res.integrity_violations:
            rule_id = getattr(iv, "rule_id", getattr(iv, "check_name", "INT-001"))
            sev = getattr(iv, "severity", "warning").lower()
            cmd_type = "error" if sev == "error" else "warning"
            msg = scrub_ansi(iv.message)
            print(f"::{cmd_type} file={res.file_path},title=Yamlr {rule_id}::{msg}")
    
    if command == "heal":
        if diff or dry_run:
            _render_forensic_diff(res, use_unified=diff)
        apply_remediation(res, telemetry, apply, dry_run, diff, create_stubs=create_stubs)

def _render_forensic_diff(res, use_unified: bool = False):
    """Visualizes the 'Before vs After' state of the manifest using native reconstruction."""
    import yamlr_native

    from yamlr.ui.renderer import RichRenderer
    try:
        with open(res.file_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        
        # 1. Shard and Structurize
        shards = yamlr_native.native_shard(old_content)
        manifest = yamlr_native.native_structurize(shards)
        
        # 2. Inject violations for the healer
        manifest.integrity_violations = res.integrity_violations
        
        # 3. Perform native healing
        telemetry = yamlr_native.NativeTelemetry()
        healed_manifest, _, changes = yamlr_native.native_heal_manifest(manifest, telemetry)
        
        # 4. Reconstruct
        new_content = yamlr_native.native_reconstruct_from_semantic(healed_manifest)
        
        # 5. Render
        title = f"Diff Preview: {res.file_path}"
        if use_unified:
            RichRenderer.render_unified_diff(old_content, new_content, title=title)
        else:
            RichRenderer.render_side_by_side_diff(old_content, new_content, title=title)
        
        if changes:
            console.print("\n[bold cyan]Predicted Security & Policy Adjustments:[/bold cyan]")
            for change in changes:
                console.print(f"  [dim]•[/dim] {change}")
            console.print("")
            
    except Exception as e:
        logger.error(f"Diff preview unavailable: {e}")
        console.print(f"[dim]Diff preview unavailable: {e}[/dim]")

def render_report(report: Any, telemetry: Any, command: str, apply: bool, dry_run: bool = False, diff: bool = False, push: bool = False, create_stubs: bool = False):
    """Renders the top-level report summary and handles telemetry sync."""
    import yamlr_native
    if report.total_files == 0:
        console.print("[yellow][!] No Kubernetes manifests found in the specified path.[/yellow]")
        return

    yamlr_native.native_record_telemetry(telemetry, "SCAN", 0.0, report.total_time_ms, "INFO")
    if push: 
        try:
            from yamlr.cli.main import _sync_telemetry_bridge
            _sync_telemetry_bridge()
        except Exception:
            pass

    _render_results_and_collisions(report, telemetry, command, apply, dry_run, diff, create_stubs=create_stubs)
    
    from yamlr.ui.renderer import RichRenderer
    RichRenderer.render_batch_summary(report, apply)

    from yamlr.core_logic import audit_topology_outages
    findings = audit_topology_outages(report.results)
    if findings:
        RichRenderer.render_audit_report(findings)
    
    RichRenderer.render_score_animation(report)

    # Sub-15s Time-to-First-Heal: Interactive prompt on scan violations
    has_violations = any(res.violations or res.integrity_violations for res in report.results)
    if has_violations and command == "scan":
        if sys.stdin.isatty() and not os.getenv("CI"):
            console.print("\n[bold cyan][?] Violations detected. Apply instant surgical repair? [Y/n]: [/bold cyan]", end="")
            try:
                choice = input().strip().lower()
                if choice in ("", "y", "yes"):
                    console.print("[bold green][*] Applying instant surgical remediation...[/bold green]\n")
                    for res in report.results:
                        if res.suggested_fixes or res.violations or res.integrity_violations:
                            apply_remediation(res, telemetry, apply=True, dry_run=False, diff=False)
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            # Actionable Resolution Banner (Lint Fatigue Fix)
            fixable_count = sum(len(res.suggested_fixes) for res in report.results if getattr(res, "suggested_fixes", None))
            if fixable_count > 0:
                console.print(f"\n[bold green][remediation][/bold green] {fixable_count} violation(s) can be repaired automatically with comment preservation.")
                console.print("   [bold white]Run:[/bold white] [cyan]yamlr heal --apply[/cyan]\n")

    # CI Enterprise Fleet Tip (Sustainable Monetization & Free CLI Guardrail)
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("GITLAB_CI"):
        console.print("[dim][tip] CI Fleet: Run Yamlr Auto-Fix Bot (.github/workflows/yamlr-autofix.yml) for automated pull requests, or '--evidence-vault' for compliance receipts.[/dim]")

def _render_batch_summary(report):
    """Compatibility shim for tests."""
    from yamlr.ui.renderer import RichRenderer
    RichRenderer.render_score_animation(report)

def _trigger_score_animation(report):
    """Compatibility shim for tests."""
    from yamlr.ui.renderer import RichRenderer
    RichRenderer.render_score_animation(report)

def _render_results_and_collisions(report: Any, telemetry: Any, command: str, apply: bool, dry_run: bool = False, diff: bool = False, create_stubs: bool = False):
    from yamlr.core.backups import BackupManager
    identities = {}
    is_windows = os.name == 'nt'
    
    if command == "heal" and apply:
        files_to_heal = [res.file_path for res in report.results if res.suggested_fixes]
        if files_to_heal:
            bm = BackupManager(".")
            session_id = bm.create_checkpoint(files_to_heal)
            console.print(f"\n[bold green][*] Safety Checkpoint Created:[/bold green] [dim]{session_id}[/dim]")
            console.print(f"[bold green][*] Healed {len(files_to_heal)} manifest(s). Undo anytime with: [bold white]yamlr rollback[/bold white][/bold green]")

    batch_mode = len(report.results) > 20
    for _i, res in enumerate(report.results):
        if res.identity: _check_identity_collision(res, identities, is_windows)
        if batch_mode and not res.violations and not res.integrity_violations and not (res.suggested_fixes and apply):
            continue
        render_resource_results(res, telemetry, command, apply, dry_run, diff, create_stubs=create_stubs)

def _check_identity_collision(res, identities, is_windows):
    identity_key = f"{res.identity.kind}/{res.identity.name}@{res.identity.namespace}"
    lookup_key = identity_key.lower() if is_windows else identity_key
    if lookup_key in identities:
        console.print(f"    [bold red][!] Identity Collision: '{identity_key}'[/bold red]")
    identities[lookup_key] = res.file_path

def _render_global_help(show_all=False):
    from yamlr.core_logic import UniversalCommandRegistry
    from yamlr.ui.renderer import RichRenderer
    categories = {
        "Basic Commands (Core)": [
            {"name": "scan", "purpose": "Audit manifests for schema/integrity violations."},
            {"name": "heal", "purpose": "Remediate violations with comment preservation."},
            {"name": "diff", "purpose": "Preview proposed remediations side-by-side or unified."},
            {"name": "doctor", "purpose": "Perform environment and schema diagnostics."},
            {"name": "status", "purpose": "Engine health and workspace status."},
            {"name": "version", "purpose": "Display engine version."}
        ],
        "Intelligence & Discovery": [
            {"name": "graph", "purpose": "Visualize manifest topology and blast radius."},
            {"name": "pulse", "purpose": "Real-time manifest integrity monitoring."},
            {"name": "drift", "purpose": "Reconcile live cluster state against source of truth."},
            {"name": "audit", "purpose": "Fleet-wide cross-resource analysis and scoring."},
            {"name": "dna", "purpose": "Generate immutable semantic integrity signatures."},
            {"name": "roi", "purpose": "Calculate manifest engineering quality and reliability impact metrics."}
        ],
        "Enterprise Engineering (Advanced)": [
            {"name": "secure", "purpose": "Apply autonomous security hardening policies."},
            {"name": "rollback", "purpose": "Atomic reversal of the last remediation session."},
            {"name": "evidence", "purpose": "Collect and package forensic audit evidence."},
            {"name": "sign", "purpose": "Cryptographically sign manifests."},
            {"name": "verify", "purpose": "Verify manifest integrity against DNA baseline."},
            {"name": "migrate", "purpose": "Automated API version migration (alias: upgrade)."}
        ],
        "Ecosystem & DevOps (Integration)": [
            {"name": "fmt", "purpose": "Canonical YAML formatting for Unix pipes & files."},
            {"name": "fix", "purpose": "Zero-flag auto-repair for Unix pipes & files."},
            {"name": "help", "purpose": "Display precision help and command reference."},
            {"name": "install", "purpose": "Install Git hooks and CI integrations."},
            {"name": "completion", "purpose": "Generate shell completions."},
            {"name": "mcp", "purpose": "Model Context Protocol interface for IDE and editor integrations."},
            {"name": "lsp", "purpose": "Start Language Server Protocol interface."},
            {"name": "init", "purpose": "Initialize a new Yamlr workspace."},
            {"name": "auth", "purpose": "Authenticate and manage Yamlr Pro licensing."},
            {"name": "subscribe", "purpose": "Manage or activate Yamlr Pro workspace subscription."},
            {"name": "admin", "purpose": "Administrative tasks."}
        ]
    }
    RichRenderer.render_precision_help(categories, show_all)
