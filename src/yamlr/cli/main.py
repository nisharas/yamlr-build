#!/usr/bin/env python3
from __future__ import annotations
import time
PROCESS_START = time.perf_counter()
"""
Yamlr UNIFIED CLI - The Entry Point
------------------------------------
Coordinates argument parsing and command dispatch.
"""

import sys
import os
from typing import TYPE_CHECKING

# 0. Global Stdout Protection for GitOps [Supplier Pivot]
import yamlr.cli.orchestrator as _orch
_orch.activate_clinical_redirection()
_orig_stdout_fd = _orch._orig_stdout_fd

# Type-hint friendly imports
if TYPE_CHECKING:
    pass

# Ensure main is exported
__all__ = ['main']

def main():
    """Primary orchestration logic for the CLI."""
    
    # 0. Surgical Timing Instrumentation (Bootstrap Anchor)
    from yamlr.core.measurement import SurgicalTimer
    root_timer = SurgicalTimer("yamlr", bootstrap_start=PROCESS_START)
    if "--timing" in sys.argv:
        root_timer.__enter__()

    # 0. Apply Platform Shims (Multiprocessing & Encoding)
    from yamlr.core.platform_compat import setup_platform
    setup_platform()
    
    exit_code = 0
    try:
        # 0. Handle Global Log Level & GitOps Detection
        from yamlr.cli.context import setup_gitops_env, is_gitops, is_argocd
        from yamlr.cli.orchestrator import setup_global_logging
        env_log_level = setup_gitops_env()
        if env_log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            setup_global_logging(env_log_level)
            
        raw_args = set(sys.argv[1:])
        is_version = "--version" in raw_args or "-v" in raw_args or (len(sys.argv) == 2 and sys.argv[1] == "version")
        
        from yamlr.core.bridge import YamlrBridge
        from yamlr.core.entrypoints.display import print_version, print_custom_header
        from yamlr.core.engine.version_utils import get_default_cluster_version

        invoked_as = YamlrBridge.get_invoked_command()
        is_pro = YamlrBridge.get_identity() == "PRO"

        if is_version:
            print_version(invoked_as, is_pro, cluster_version=get_default_cluster_version())
            sys.exit(0)

        # 0. ULTRA-FAST COMPLETION PATH
        if len(sys.argv) > 1 and "completion" in sys.argv:
            from yamlr.cli.commands.completion import handle_fast_completion
            if handle_fast_completion(): sys.exit(0)

        # 1. Setup Parser & Args
        from yamlr.cli.parser_factory import create_parser
        show_all = "--all" in raw_args # Fast-path show_all for help suppression
        parser = create_parser(invoked_as, show_all=show_all)
        args, unknown = parser.parse_known_args()

        # [Supplier Pivot] GitOps Defaults
        is_gitops_active = is_gitops()
        if is_argocd() or is_gitops_active:
            setattr(args, "quiet", True)
            setattr(args, "plain", True)
            if getattr(args, "command", None) == "heal":
                setattr(args, "yes_all", True)
                if not getattr(args, "output", None): setattr(args, "output", "text")

        # 2. Setup Console
        from yamlr.cli.context import CliContext
        import yamlr.core.entrypoints.base as cli_base
        cli_base._console = None # Force re-init to pick up redirected stdout
        
        target_stream = sys.stderr if (is_gitops_active or getattr(args, "quiet", False) or getattr(args, "output", "text") != "text") else None
        console = CliContext.get_console(plain=getattr(args, "plain", False) or is_gitops_active, target_file=target_stream)
        
        if is_gitops_active or getattr(args, "quiet", False):
            console._yamlr_quiet = True

        if unknown:
            console.print(f"[red]Error: Unrecognized arguments: {unknown}[/red]")
            from yamlr.cli.help_formatter import print_kubectl_help
            print_kubectl_help(console, invoked_as, show_all=getattr(args, "all", False))
            sys.exit(1)

        # 5. Version Handling
        if getattr(args, "version", False):
            from yamlr.core.entrypoints.base import handle_version_command
            handle_version_command(console)
            # [Conversion Hook] Show Pro hint if not pro
            if not YamlrBridge.is_pro_enabled():
                checkout_url = YamlrBridge.get_checkout_url()
                console.print("\n[bold gold1]💎 Unlock high-gravity healing & compliance with Yamlr Pro.[/bold gold1]")
                console.print(f"[dim]Upgrade at: [link={checkout_url}]yamlr.dev/pro[/link][/dim]")
            sys.exit(0)

        if getattr(args, "verbose", False) or getattr(args, "log_format", "text") == "json":
            from yamlr.core.logging_config import YamlrLoggingConfig
            fmt = getattr(args, "log_format", "text")
            level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
            YamlrLoggingConfig.setup(level=level, json_mode=(fmt == "json"))

        from yamlr.core.entrypoints.base import normalize_paths
        if hasattr(args, "path") and args.path:
            args.path = normalize_paths(args.path)

        # 3. Handle Workspace Target Version
        target_cluster_version = getattr(args, "kube_version_target", None) or args.kube_version or os.getenv("YAMLR_KUBE_VERSION")
        from yamlr.core.context import HealContext
        if target_cluster_version:
            try:
                target_cluster_version = HealContext.set_cluster_version(target_cluster_version)
            except ValueError as e:
                if getattr(args, "output", None) != "json": console.print(f"[bold red]❌ Invalid K8s version:[/bold red] {e}")
                sys.exit(1)

        # 4. Help Dispatch & Smart Prompt
        if args.help or not args.command:
            if args.command:
                from yamlr.cli.help_formatter import print_subcommand_help
                print_subcommand_help(console, args.command, invoked_as, show_all=show_all)
                sys.exit(0)
            else:
                is_explicit_help = args.help or "-h" in sys.argv or "--help" in sys.argv
                
                if not is_explicit_help and not is_gitops_active and sys.stdout.isatty() and not os.getenv("YAMLR_CLASSIC"):
                    from yamlr.core.config import ConfigManager
                    config_mgr = ConfigManager(os.getcwd(), app_name="yamlr")
                    from yamlr.core.engine.discovery import fast_manifest_scan
                    from yamlr.cli.interactor import render_workspace_context, run_smart_prompt
                    manifest_count = fast_manifest_scan(os.getcwd())
                    target_kb = target_cluster_version or config_mgr.kubernetes_version or HealContext._get_default_cluster_version()
                    render_workspace_context(console, manifest_count, config_mgr.has_local_config(), target_kb)
                    
                    cmd_tuple = run_smart_prompt(console, manifest_count, config_mgr.has_local_config(), is_pro)
                    if not cmd_tuple: sys.exit(0)
                    cmd, remaining = cmd_tuple
                    
                    if cmd == "help":
                        from yamlr.cli.help_formatter import print_kubectl_help
                        print_kubectl_help(console, invoked_as, show_all=getattr(args, "all", False)); sys.exit(0)
                    args.command = cmd
                    if remaining: args.path = remaining
                else:
                    from yamlr.cli.help_formatter import print_kubectl_help
                    print_custom_header(invoked_as, is_pro)
                    print_kubectl_help(console, invoked_as, show_all=show_all)
                    sys.exit(0)

        # 5. Engine & Command Dispatch
        from yamlr.cli.command_registry import get_handler
        mod_name, func_name = get_handler(args.command)
        
        if not mod_name:
            console.print(f"[red]Error: Unknown command '{args.command}'[/red]")
            sys.exit(1)

        # Load engine if the command expects it
        engine = None
        if args.command in ["scan", "heal", "upgrade", "migrate", "secure", "diagnose", "check", "audit", "dna", "status", "welcome", "demo", "stats", "roi", "baseline", "pulse", "graph", "idp-export", "doctor"]:
            from yamlr.core.engine import YamlrEngine
            engine = YamlrEngine(
                workspace_path=".", catalog_path=args.catalog, cluster_version=target_cluster_version,
                opa_bundle_path=getattr(args, "opa_bundle", None), kyverno_report_path=getattr(args, "kyverno_report", None),
                from_report_path=getattr(args, "from_report", None), concurrency=getattr(args, "concurrency", None),
                default_namespace=getattr(args, "namespace", "default"), health_threshold=getattr(args, "health_threshold", 70),
                unrestricted=getattr(args, "unrestricted", False),
            )
            if not is_gitops_active and not getattr(console, "_yamlr_quiet", False) and getattr(args, "output", "text") == "text":
                console.print(f"🎯 Target K8s: [bold green]{engine.cluster_version}[/bold green]")

        # Run Handler
        import importlib
        handler_mod = importlib.import_module(mod_name)
        handler_func = getattr(handler_mod, func_name)
        
        # Validation for path-based commands
        if args.command in ["scan", "heal", "migrate", "secure", "diagnose", "check", "audit"]:
            from yamlr.core.entrypoints.base import validate_required_arg

            if not (args.command == "audit" and getattr(args, "verify", None)) and not validate_required_arg(args.path, "path", args.command, [f"{invoked_as} {args.command} ."]):
                sys.exit(1)

        # Pass the timing report if requested
        timing_report = root_timer.get_report() if "--timing" in sys.argv else None

        # [REFACTOR] Signature-Aware Dispatch Mapping (Hardening v1.4)
        SIG_MAP = {
            "CONSOLE_ONLY": ["init", "auth"],
            "ENGINE_CONTEXT": ["status", "stats", "roi", "dna", "demo", "welcome", "pulse", "graph", "idp-export", "doctor", "upgrade", "migrate"],
            "ENGINE_ONLY": ["baseline", "heal", "fix", "secure", "scan", "audit"],
            "PARSER_CONTEXT": ["completion"],
            "PATH_CONTEXT": ["restore"],
            "VERSION_CONTEXT": ["catalog"],
            "NO_ARGS": ["manual", "mcp"],
            "CONSOLE_ARGS": ["explain", "rules", "evidence"]
        }
        
        INV_SIG_MAP = {cmd: sig for sig, cmds in SIG_MAP.items() for cmd in cmds}
        sig = INV_SIG_MAP.get(args.command)

        if sig == "CONSOLE_ONLY":
            exit_code = handler_func(console, force=getattr(args, "force", False)) if args.command == "init" else handler_func(args, console)
        elif sig == "ENGINE_CONTEXT":
            exit_code = handler_func(args, engine, console)
        elif sig == "ENGINE_ONLY":
            if args.command in ["heal", "fix", "secure"]:
                exit_code = handler_func(args, engine, is_pro=is_pro)
            elif args.command in ["scan", "audit"]:
                exit_code = handler_func(args, engine, timing_report=timing_report)
            elif args.command == "baseline":
                exit_code = handler_func(args, engine, is_pro)
            else:
                exit_code = handler_func(args, engine)
        elif sig == "PARSER_CONTEXT":
            exit_code = handler_func(args, parser, console)
        elif sig == "PATH_CONTEXT":
            exit_code = handler_func(args, ".")
        elif sig == "VERSION_CONTEXT":
            exit_code = handler_func(args, target_cluster_version)
        elif sig == "CONSOLE_ARGS":
            exit_code = handler_func(args, console)
        elif sig == "NO_ARGS":
            exit_code = handler_func(args)
        else:
            exit_code = handler_func(args, engine) if engine else handler_func(args)
            
    except SystemExit as se:
        exit_code = se.code
    except Exception as e:
        import traceback
        if os.getenv("YAMLR_DEBUG"):
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        exit_code = 1
    finally:
        if engine:
            try:
                engine.close()
            except Exception:
                pass

        if "--timing" in sys.argv:
            root_timer.__exit__(None, None, None)
            
            # Use local variables if they exist
            locs = locals()
            current_args = locs.get("args")
            current_console = locs.get("console")
            
            # Determine if we should print the report (suppress for machine-readable scan output)
            cmd = getattr(current_args, "command", None) if current_args else None
            out = getattr(current_args, "output", "text") if current_args else "text"
            
            if not (cmd == "scan" and out in ["json", "sarif"]):
                if not current_console:
                    from yamlr.cli.context import CliContext
                    current_console = CliContext.get_console()
                
                current_console.rule("[bold]Surgical Performance Breakdown[/bold]")
                SurgicalTimer.print_timing_report(root_timer.get_report(), current_console)
            
            timing_file = getattr(current_args, "timing_file", None) if current_args else None
            if timing_file:
                try:
                    from pathlib import Path
                    import json
                    Path(timing_file).write_text(json.dumps(root_timer.get_report(), indent=2), encoding="utf-8")
                    if current_console:
                        current_console.print(f"\n[dim]Performance profile saved to: {timing_file}[/dim]")
                except Exception:
                    pass

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
