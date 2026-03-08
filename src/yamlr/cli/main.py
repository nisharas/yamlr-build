#!/usr/bin/env python3
"""
Yamlr UNIFIED CLI - The Entry Point
------------------------------------
Coordinates argument parsing and command dispatch.

Why: Refactored to externalize logic into specialized modules 
for 100% modularity and compliance with project guardrails.
"""

import logging
import multiprocessing
import os
import platform
import sys
import time

from yamlr.cli.help_formatter import print_kubectl_help, print_subcommand_help
from yamlr.cli.parser_factory import create_parser

# Initialize Logger
logger = logging.getLogger("yamlr")

# 0. Handle Global Log Level (from Env)
env_log_level = os.getenv("Yamlr_LOG_LEVEL", "INFO").upper()
if env_log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    # Configure root logger to respect the env var
    logging.basicConfig(level=env_log_level)
    logger.setLevel(env_log_level)
    if env_log_level == "DEBUG":
        logger.debug(f"Logging initialized at DEBUG level via Yamlr_LOG_LEVEL environment variable")

# Nuitka/PyInstaller Windows multiprocessing fix
if sys.platform == "win32":
    multiprocessing.freeze_support()

# Filter out multiprocessing garbage args
sys.argv = [
    arg
    for arg in sys.argv
    if not ("parent_pid=" in arg or "--multiprocessing-fork" in arg)
]

# Lazily initialized globals
_console = None
_formatter = None

def get_lazy_console(plain: bool = False):
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    global _console
    if plain or _console is None:
        from yamlr.cli.commands.base import get_console
        _console = get_console(plain=plain)
    return _console

def get_lazy_formatter():
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    global _formatter
    if _formatter is None:
        from yamlr.ui.formatter import YamlrFormatter
        _formatter = YamlrFormatter()
    return _formatter

def main():
    """Primary orchestration logic for the CLI."""
    # 0. ULTRA-FAST COMPLETION PATH
    if len(sys.argv) > 1 and "completion" in sys.argv:
        from yamlr.cli.commands.completion import handle_fast_completion
        if handle_fast_completion():
            sys.exit(0)

    # 1. Setup Bridge & Context
    from yamlr.core.bridge import YamlrBridge
    from yamlr.core.context import HealContext
    from yamlr.core.entrypoints.display import print_version, print_custom_header

    try:
        invoked_as = YamlrBridge.get_invoked_command()
        is_pro = YamlrBridge.get_identity() == "PRO"
    except Exception:
        invoked_as = "yamlr"
        is_pro = False

    # 2. Argument Configuration
    parser = create_parser(invoked_as)
    args, unknown = parser.parse_known_args()

    # Initialize Console (Propagate plain & quiet flags)
    console = get_lazy_console(plain=getattr(args, "plain", False))
    console._yamlr_quiet = getattr(args, "quiet", False)

    if unknown:
        console.print(f"[red]Error: Unrecognized arguments: {unknown}[/red]")
        print_kubectl_help(console, invoked_as)
        sys.exit(1)

    # Output Mode Adjustment
    is_json = getattr(args, "output", "text") == "json"
    is_onboarding = getattr(args, "command", None) in ["welcome", "demo"]
    if is_json or (is_onboarding and not getattr(args, "verbose", False)):
        logging.getLogger().setLevel(logging.ERROR)
        logging.getLogger("yamlr").setLevel(logging.ERROR)

    # Path Normalization
    from yamlr.cli.commands.base import normalize_paths
    if hasattr(args, "path") and args.path:
        args.path = normalize_paths(args.path)

    # 3. Version & Help Dispatch
    # Priority: --to (upgrade) > --kube-version (global) > Auto-Detect > Default
    # Determine K8s Version (Defer default resolution to Engine if not explicitly provided)
    target_cluster_version = getattr(args, "kube_version_target", None) or args.kube_version or os.getenv("Yamlr_KUBE_VERSION")
    
    if target_cluster_version:
        try:
            target_cluster_version = HealContext.set_cluster_version(target_cluster_version)
        except ValueError as e:
            if not is_json: console.print(f"[bold red]❌ Invalid K8s version:[/bold red] {e}")
            sys.exit(1)

    if args.version or args.command == "version":
        print_version(invoked_as, is_pro, cluster_version=target_cluster_version or HealContext._get_default_cluster_version())
        sys.exit(0)

    if args.help or not args.command:
        if args.command:
            print_subcommand_help(console, args.command, invoked_as)
            sys.exit(0)
        else:
            # 3.5 MAGIC MOMENT: The Context-Aware Smart Prompt
            # If YAMLR_CLASSIC is set, or if we're not in a TTY, fallback to classic help
            if os.getenv("YAMLR_CLASSIC") or not sys.stdout.isatty():
                if not is_json: 
                    print_custom_header(invoked_as, is_pro)
                    from yamlr.core.config import ConfigManager
                    if not ConfigManager(os.getcwd(), app_name="yamlr").has_local_config():
                        console.print("\n[bold magenta]👋 New here?[/bold magenta] Run [cyan bold]yamlr welcome[/cyan bold] for a guided tour.")
                print_kubectl_help(console, invoked_as)
                sys.exit(0)
            
            # Context Detection
            from yamlr.core.config import ConfigManager
            import glob
            cwd = os.getcwd()
            # Fast, shallow scan for manifests
            yaml_files = []
            for ext in ("*.yaml", "*.yml"):
                yaml_files.extend(glob.glob(f"{cwd}/**/{ext}", recursive=True))
                if len(yaml_files) > 500: break # Cap the count for speed
            
            manifest_count = len(yaml_files)
            config_mgr = ConfigManager(cwd, app_name="yamlr")
            has_config = config_mgr.has_local_config()
            is_git = os.path.exists(os.path.join(cwd, ".git"))
            
            # Render Doctor Panel
            from rich.panel import Panel
            from rich.align import Align
            
            display_count = f"{manifest_count}+" if manifest_count >= 500 else str(manifest_count)
            config_status = "[green].yamlr.yaml present[/green]" if has_config else "[yellow]No .yamlr.yaml found[/yellow]"
            target_kb = target_cluster_version or config_mgr.kubernetes_version or HealContext._get_default_cluster_version()
            
            panel_content = (
                f"📂 Dir:        [cyan]{os.path.basename(cwd)}[/cyan]\n"
                f"📄 Manifests:  [cyan]{display_count} YAML files detected[/cyan]\n"
                f"⚙  Config:     {config_status}\n"
                f"🎯 K8s Target: [cyan]{target_kb}[/cyan]"
            )
            
            console.print(Panel(
                panel_content,
                title="[bold cyan]🛡 Yamlr v1.1 – Workspace Context[/bold cyan]",
                border_style="cyan",
                expand=False
            ))
            
            # Determine "Next Best Action"
            if manifest_count > 0:
                suggested_cmd = "yamlr scan ."
                if not has_config:
                    msg = f"Found {display_count} manifests, but no local config. (Using defaults)"
                    prompt_hint = "(Or type 'i' to init config, 'h' for help, 'q' to quit)"
                else:
                    msg = "Workspace ready for analysis."
                    prompt_hint = "(Or type 'h' for full help, 'q' to quit)"
            else:
                if is_git:
                    suggested_cmd = "yamlr demo"
                    msg = "No Kubernetes manifests found here."
                    prompt_hint = "(Or type 'i' to init config, 'h' for help, 'q' to quit)"
                else:
                    # Not a git repo, no manifests. Same as classic fallback.
                    print_custom_header(invoked_as, is_pro)
                    print_kubectl_help(console, invoked_as)
                    sys.exit(0)
            
            console.print(f"\n{msg}\n[bold]Press Enter to run:[/bold] [bold green]{suggested_cmd}[/bold green]")
            console.print(f"[dim]{prompt_hint}[/dim]")
            
            if is_pro and manifest_count > 0:
                console.print(f"\n[dim]💎 PRO available in this repo – after scan, try: yamlr heal --harden .[/dim]")
                
            try:
                console.print("\n> ", end="")
                choice = input().strip().lower()
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
                
            if choice == "h":
                print_kubectl_help(console, invoked_as)
                sys.exit(0)
            elif choice == "q":
                sys.exit(0)
            elif choice == "i":
                args.command = "init"
                args.path = []

            elif choice == "":
                # Execute the suggested command
                cmd_parts = suggested_cmd.split(" ")[1:] # remove 'yamlr'
                args.command = cmd_parts[0]
                if len(cmd_parts) > 1:
                    args.path = cmd_parts[1:]
                # Suppress logs for the magic moment execution
                logging.getLogger().setLevel(logging.ERROR)
                logging.getLogger("yamlr").setLevel(logging.ERROR)
            else:
                sys.exit(0)

    # 4. Engine Orchestration (Unified Initialization)
    # Why: Initialize engine once for ALL commands that might need it (including dna/status)
    # and delegate catalog resolution to the core manager.
    engine = None
    if args.command in ["scan", "heal", "upgrade", "migrate", "secure", "diagnose", "check", "audit", "dna", "status", "welcome", "demo", "stats"]:
        from yamlr.pro.license import license_manager
        license_manager.preview_mode = getattr(args, "pro_preview", False)

        from yamlr.core.engine import YamlrEngine
        engine = YamlrEngine(
            workspace_path=".", 
            catalog_path=args.catalog, # Let Manager resolve this
            app_name="Yamlr",
            cluster_version=target_cluster_version,
            opa_bundle_path=getattr(args, "opa_bundle", None),
            kyverno_report_path=getattr(args, "kyverno_report", None),
            concurrency=getattr(args, "concurrency", None),
            cpu_limit=getattr(args, "cpu_limit", "500m"),
            mem_limit=getattr(args, "mem_limit", "512Mi"),
            default_namespace=getattr(args, "namespace", "default"),
            health_threshold=getattr(args, "health_threshold", 70),
        )

        if not is_json:
            # Enhanced Transparency: Explicitly log the version source
            version_source = "Auto-Detect"
            if getattr(args, "kube_version_target", None): version_source = "CLI (--to)"
            elif args.kube_version: version_source = "CLI (--kube-version)"
            elif os.getenv("Yamlr_KUBE_VERSION"): version_source = "ENV (Yamlr_KUBE_VERSION)"
            
            console.print(f"🎯 Target K8s: [bold green]{engine.cluster_version}[/bold green] [dim]({version_source})[/dim]")

    # 5. Command Dispatch (Simple Entrypoints)
    simple_commands = {
        "explain": ("yamlr.cli.commands.explain", "handle_explain_command"),
        "init": ("yamlr.core.entrypoints.config", "handle_init_command"),
        "restore": ("yamlr.core.entrypoints.restore", "handle_restore_command"),
        "status": ("yamlr.core.entrypoints.status", "handle_status_command"),
        "welcome": ("yamlr.core.entrypoints.welcome", "handle_welcome_command"),
        "rules": ("yamlr.core.entrypoints.rules", "handle_rules_command"),
        "completion": ("yamlr.cli.commands.completion", "handle_completion_command"),
        "catalog": ("yamlr.core.entrypoints.catalog", "handle_catalog_command"),
        "demo": ("yamlr.core.entrypoints.demo", "handle_demo_command"),
        "manual": ("yamlr.core.entrypoints.manual", "handle_manual_command"),
        "dna": ("yamlr.core.entrypoints.dna", "handle_dna_command"), # Fixed entrypoint name
        "evidence": ("yamlr.core.entrypoints.evidence", "handle_evidence_command"), # PRO Compliance Feature
        "stats": ("yamlr.core.entrypoints.stats", "handle_stats_command"),
    }

    if args.command in simple_commands:
        import importlib
        mod_name, func_name = simple_commands[args.command]
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        
        # Dispatch with appropriate args
        if args.command == "init": sys.exit(func(console, force=getattr(args, "force", False)))
        if args.command == "restore": sys.exit(func(args, "."))
        if args.command == "status": sys.exit(func(args, engine, console))
        if args.command == "welcome": sys.exit(func(args, engine, is_pro))
        if args.command == "catalog": sys.exit(func(args, target_cluster_version))
        if args.command == "completion": sys.exit(func(args, parser, console))
        if args.command == "manual": sys.exit(func(args))
        if args.command == "dna": sys.exit(func(args, engine, console))
        if args.command == "demo": sys.exit(func(args, engine, console))
        if args.command == "evidence": sys.exit(func(args, console))
        if args.command == "stats": sys.exit(func(args, engine, console))
        sys.exit(func(args, console))

    # 6. Primary Healing Commands (Scan/Heal + Aliases)
    try:
        from yamlr.cli.commands.base import validate_required_arg
        # All engine commands require a path
        if args.command in ["scan", "heal", "upgrade", "migrate", "secure", "diagnose", "check", "audit"]:
            if not validate_required_arg(args.path, "path", args.command, 
                                        [f"{invoked_as} {args.command} ."]):
                sys.exit(1)

        formatter = get_lazy_formatter()
        start_time = time.time()
        exit_code = 0

        if args.command == "scan":
            from yamlr.core.entrypoints.scan import handle_scan_command
            exit_code = handle_scan_command(args, engine, formatter)
        elif args.command == "audit":
            from yamlr.cli.commands.audit import handle_audit_command
            exit_code = handle_audit_command(args, engine, formatter)
        elif args.command == "heal":
            if getattr(args, "harden", False) and not is_pro:
                YamlrBridge.notify_pro_required("Shield Security Hardening")
                sys.exit(0)
            from yamlr.core.entrypoints.heal import handle_heal_command
            exit_code = handle_heal_command(args, engine, formatter, is_pro)
        elif args.command == "upgrade":
            from yamlr.cli.commands.upgrade import handle_upgrade_command
            exit_code = handle_upgrade_command(args, engine, formatter, is_pro)
        elif args.command == "migrate":
            from yamlr.cli.commands.upgrade import handle_upgrade_command
            exit_code = handle_upgrade_command(args, engine, formatter, is_pro)
        elif args.command == "secure":
             if not is_pro:
                  YamlrBridge.notify_pro_required("Secure Hardening Mode")
                  sys.exit(0)
             from yamlr.cli.commands.secure import handle_secure_command
             exit_code = handle_secure_command(args, engine, formatter, is_pro)
        elif args.command == "diagnose":
            from yamlr.cli.commands.diagnose import handle_diagnose_command
            exit_code = handle_diagnose_command(args, engine, formatter)
        elif args.command == "check":
            from yamlr.cli.commands.check import handle_check_command
            exit_code = handle_check_command(args, engine, formatter)

        # [ULTRA-SCALE] Final Impact Analysis
        duration = time.time() - start_time
        
        # [CI/CD] Gate Logic: --fail-on (Severity) and --risk-threshold (Impact)
        if exit_code != 0:
            severity_rank = {"error": 100, "warning": 50, "info": 10, "none": 0}
            risk_rank = {"high": 100, "medium": 50, "low": 10, "none": 0}
            
            last_sev = getattr(engine.telemetry, "last_max_severity", "info").lower()
            last_risk = getattr(engine.telemetry, "last_max_risk", "low").lower()
            
            # Severity Gate check
            fail_on = getattr(args, "fail_on", None)
            severity_fail = True # Default if flag not provided
            if fail_on:
                target_sev_rank = severity_rank.get(fail_on.lower(), 10)
                actual_sev_rank = severity_rank.get(last_sev, 10)
                severity_fail = actual_sev_rank >= target_sev_rank
            
            # Risk Gate check
            risk_threshold = getattr(args, "risk_threshold", None)
            risk_fail = True # Default if flag not provided
            if risk_threshold:
                target_risk_rank = risk_rank.get(risk_threshold.lower(), 10)
                actual_risk_rank = risk_rank.get(last_risk, 10)
                risk_fail = actual_risk_rank >= target_risk_rank
            
            # If BOTH flags are provided, we only exit 1 if BOTH conditions are met?
            # Or if EITHER? Usually EITHER is safer for CI.
            # However, if user says --fail-on error --risk-threshold high, 
            # they likely want to block on EITHER severe errors OR high risk.
            if fail_on or risk_threshold:
                if (fail_on and not severity_fail) and (risk_threshold and not risk_fail):
                    exit_code = 0
                elif fail_on and not risk_threshold and not severity_fail:
                    exit_code = 0
                elif risk_threshold and not fail_on and not risk_fail:
                    exit_code = 0

        sys.exit(exit_code)

    except Exception as e:
        console.print(f"[bold red]Fatal Error:[/bold red] {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
