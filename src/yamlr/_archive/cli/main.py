# Root-level imports must remain minimal for fast startup
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union

# Cross-platform terminal encoding stabilization
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

# Documentation Constants
STYLE_BOLD_CYAN = "bold cyan"

# ---------------------------------------------------------------------------
# Backward-compatibility re-exports.
# Extracted into purpose-specific modules for clean modularity.
# Re-exporting them ensures existing imports continue to work unchanged.
# ---------------------------------------------------------------------------
from yamlr.cli.formatters import (  # noqa: F401
    _check_identity_collision,
    _render_batch_summary,
    _render_forensic_diff,
    _render_global_help,
    _render_results_and_collisions,
    _trigger_score_animation,
    render_report,
    render_resource_results,
    scrub_ansi,
)
from yamlr.cli.pipeline import (  # noqa: F401
    _execute_scan_heal_pipeline,
    _export_json_report,
    _handle_exit_code,
    detect_version,
    execute_pipeline,
    ingest_crds,
    initialize_engine,
)
from yamlr.cli.remediation import (  # noqa: F401
    _apply_atomic_fix,
    _handle_cicd_remediation,
    _handle_interactive_remediation,
    apply_remediation,
)
from yamlr.cli.signing import cmd_sign, cmd_verify  # noqa: F401


def run_standalone():
    """Backward-compatible entry point for tests and standalone scripts."""
    main()


def _sync_telemetry_bridge():
    """Synchronizes local forensic telemetry with the central telemetry endpoint."""
    import json as _json
    import os
    import urllib.request

    # Enforce air-gapped compliance
    if "--no-telemetry" in sys.argv or "--disable-telemetry" in sys.argv:
        return
    if os.environ.get("YAMLR_TELEMETRY", "").strip().lower() in ("0", "false", "off", "no"):
        return
    if os.environ.get("DO_NOT_TRACK", "").strip().lower() in ("1", "true"):
        return

    from yamlr.core_logic import LicenseManager

    lm = LicenseManager()
    if not lm.check_pro():
        return  # ROI telemetry sync is an Enterprise feature

    console.print("[dim][!] ROI Bridge: Pushing telemetry to gateway...[/dim]")
    try:
        url = f"{lm.GATEWAY_URL}/pulse"
        data = _json.dumps({
            "machine_id": lm.mid,
            "cli_version": "0.1.0",
            "event_type": "FORENSIC_SYNC",
            "ts": int(time.time())
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Yamlr-Identity", lm.mid)
        req.add_header("User-Agent", f"yamlr-cli/0.1.0 ({sys.platform})")

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                console.print("[green][OK] Telemetry synchronized.[/green]")
            else:
                console.print(f"[yellow][!] Sync deferred (Status: {response.status}).[/yellow]")
    except Exception as e:
        console.print(f"[dim]Sync deferred: {e}[/dim]")


def _dispatch_command(args):
    """Routes parsed CLI arguments to the appropriate command handler."""
    from yamlr.core_logic import LicenseManager, UniversalCommandRegistry, cmd_dna, cmd_explain_universal

    if UniversalCommandRegistry.is_pro(args.command):
        if not LicenseManager().check_pro():
            console.print(f"\n[bold red][!] Access Denied:[/bold red] '{args.command}' is an Enterprise-only feature.")
            sys.exit(0)

    if args.command == "dna": cmd_dna(args.path)
    elif args.command == "sign": cmd_sign(args)
    elif args.command == "verify": cmd_verify(args)
    elif args.command == "explain":
        cmd_explain_universal(args.path if args.path != "." else None, getattr(args, "flag", None))
    elif args.command in ["scan", "heal", "diff", "graph", "audit", "drift"]:
        _execute_scan_heal_pipeline(args)
    else:
        console.print(f"\n[bold red][!] Unknown command:[/bold red] '{args.command}'")
        sys.exit(1)


def _check_telemetry_optin():
    """Prompts the user to opt-in to anonymous telemetry on first run (Bypassed in CI)."""
    import sys
    if os.getenv("YAMLR_TELEMETRY", "").strip().lower() in ("0", "false", "off", "no"):
        return
    if os.getenv("DO_NOT_TRACK", "").strip().lower() in ("1", "true"):
        return
    if "--no-telemetry" in sys.argv or "--disable-telemetry" in sys.argv:
        return
    if not sys.stdin.isatty() or os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        return

    config_dir = os.path.expanduser("~/.yamlr")
    config_path = os.path.join(config_dir, "config.json")

    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    if not os.path.exists(config_path):
        console.print("[bold cyan]Welcome to Yamlr Engine![/bold cyan]")
        try:
            confirm = console.input("[dim]Yamlr collects anonymous metrics to improve healing accuracy. Opt-in? [y/N]: [/dim]")
        except EOFError:
            confirm = ""
        opt_in = confirm.strip().lower() in ("y", "yes")
        with open(config_path, 'w') as f:
            json.dump({"telemetry_opt_in": opt_in}, f)
        console.print("[dim]Preference saved.[/dim]\n")


def main():
    """Yamlr CLI entry point."""
    from yamlr.cli.parser import create_parser
    parser = create_parser()
    if len(sys.argv) == 1:
        from yamlr.core_logic import cmd_welcome
        cmd_welcome()
        return

    args, _ = parser.parse_known_args()
    if args.help:
        _render_global_help(args.all)
        return
    if args.version:
        from yamlr.core_logic import cmd_version
        cmd_version()
        return

    if not args.command:
        _render_global_help(args.all)
        return

    from yamlr.cli.handlers import handle_informational_commands
    if handle_informational_commands(args):
        return

    # Check telemetry opt-in before running commands that might generate telemetry
    _check_telemetry_optin()

    _dispatch_command(args)


if __name__ == "__main__":
    main()
