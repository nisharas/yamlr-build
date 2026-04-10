# Bootstrap Debug
try:
    with open("yamlr_boot.log", "w") as _f:
        _f.write(f"ENTRYPOINT REACHED: {__name__}\n")
except Exception:
    pass

# imports
import multiprocessing
import os
import sys
import time

# 🛡️ MANDATORY: Freeze support for native binaries
multiprocessing.freeze_support()

PROCESS_START = time.perf_counter()

# Ensure main is exported
__all__ = ["main"]


def main():
    """Primary orchestration logic for the CLI.

    Why: Coordinates bootstrapping, argument parsing, and command execution
         with full GitOps and Platform compatibility.
    """
    try:
        _main_exec()
    except Exception as e:
        import time
        import traceback

        with open("yamlr_fatal.log", "a") as f:
            f.write(f"\n[{time.ctime()}] FATAL BOOTSTRAP ERROR: {e}\n")
            f.write(traceback.format_exc())
            f.write("-" * 40 + "\n")
        sys.stderr.write(f"\n❌ FATAL BOOTSTRAP ERROR: {e}\nSee yamlr_fatal.log for details.\n")
        sys.exit(1)


def _bootstrap_environment():
    """Environment Initialization: Stdout Protection & Platform Shims."""
    from yamlr.cli.orchestrator import activate_clinical_redirection, setup_global_logging
    from yamlr.core.platform_compat import setup_platform
    from yamlr.cli.context import setup_gitops_env

    if "lsp" not in sys.argv:
        activate_clinical_redirection()

    setup_platform()

    env_log_level = setup_gitops_env()
    if env_log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        setup_global_logging(env_log_level)


def _handle_early_exits(invoked_as: str, is_pro: bool):
    """Handles early-exit operations (LSP, Version, Fast Completion)."""
    raw_args = set(sys.argv[1:])

    # 1. LSP Protocol Redirect
    if len(sys.argv) > 1 and sys.argv[1] == "lsp":
        from yamlr.cli.lsp import main as lsp_main
        lsp_main()
        sys.exit(0)

    # 2. Version Information (Bit-for-Bit parity)
    is_version = "--version" in raw_args or "-v" in raw_args or (len(sys.argv) == 2 and sys.argv[1] == "version")
    if is_version:
        from yamlr.core.engine.version_utils import get_default_cluster_version
        from yamlr.core.entrypoints.display import print_version
        print_version(invoked_as, is_pro, cluster_version=get_default_cluster_version())
        sys.exit(0)

    # 3. Ultra-Fast Completion Path
    if len(sys.argv) > 1 and "completion" in sys.argv:
        from yamlr.core.entrypoints.completion import handle_fast_completion
        if handle_fast_completion():
            sys.exit(0)


def _init_cli_context(invoked_as: str):
    """Step 1: Parser Setup, GitOps Overrides, and Console Initialization."""
    from yamlr.cli.parser_factory import create_parser
    from yamlr.cli.context import is_argocd, is_gitops, CliContext
    import yamlr.core.entrypoints.base as cli_base

    raw_args = set(sys.argv[1:])
    show_all = "--all" in raw_args
    parser = create_parser(invoked_as, show_all=show_all)
    args, unknown = parser.parse_known_args()

    # [Supplier Pivot] GitOps Defaults
    is_gitops_active = is_gitops()
    if is_argocd() or is_gitops_active:
        args.quiet = True
        args.plain = True
        if getattr(args, "command", None) == "heal":
            args.yes_all = True
            if not getattr(args, "output", None):
                args.output = "text"

    # Console Setup
    cli_base._console = None
    target_stream = (sys.stderr if (is_gitops_active or getattr(args, "quiet", False) or getattr(args, "output", "text") != "text") else None)
    console = CliContext.get_console(plain=getattr(args, "plain", False) or is_gitops_active, target_file=target_stream)

    if is_gitops_active or getattr(args, "quiet", False):
        console._yamlr_quiet = True

    if unknown:
        from yamlr.cli.help_formatter import print_kubectl_help
        console.print(f"[red]Error: Unrecognized arguments: {unknown}[/red]")
        print_kubectl_help(console, invoked_as, show_all=getattr(args, "all", False))
        sys.exit(1)

    return args, console, parser, is_gitops_active


def _configure_logging_and_paths(args):
    """Step 2: Logging levels and Path normalization."""
    from yamlr.core.logging_config import YamlrLoggingConfig
    from yamlr.core.entrypoints.base import normalize_paths

    # Verbose / JSON Log Handling
    if getattr(args, "verbose", False) or getattr(args, "log_format", "text") == "json":
        fmt = getattr(args, "log_format", "text")
        level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
        YamlrLoggingConfig.setup(level=level, json_mode=(fmt == "json"))

    # Path Normalization
    if hasattr(args, "path") and args.path:
        args.path = normalize_paths(args.path)


def _main_exec():
    """Internal execution logic wrapped in fatal error handler."""
    from yamlr.core.measurement import SurgicalTimer
    from yamlr.core.bridge import YamlrBridge
    from yamlr.core.context import HealContext

    # [Baseline-Lock] Process Metadata
    root_timer = SurgicalTimer("yamlr", bootstrap_start=PROCESS_START)
    if "--timing" in sys.argv:
        root_timer.__enter__()

    # Thread-Safe Dispatch Constraint
    if "--sequential" in sys.argv:
        os.environ["YAMLR_SEQUENTIAL"] = "1"
        os.environ["YAMLR_CONCURRENCY"] = "1"

    invoked_as = YamlrBridge.get_invoked_command()
    is_pro = YamlrBridge.get_identity() == "PRO"

    # [Logic-Parity] Workflow Phases
    _bootstrap_environment()
    _handle_early_exits(invoked_as, is_pro)

    try:
        # Context Initialization
        args, console, parser, is_gitops_active = _init_cli_context(invoked_as)
        _configure_logging_and_paths(args)

        # 5. Version Flag Handling
        if getattr(args, "version", False):
            from yamlr.core.entrypoints.base import handle_version_command
            handle_version_command(console)
            if not YamlrBridge.is_pro_enabled():
                checkout_url = YamlrBridge.get_checkout_url()
                console.print("\n[bold gold1]💎 Unlock high-gravity healing & compliance with Yamlr Pro.[/bold gold1]")
                console.print(f"[dim]Upgrade at: [link={checkout_url}]yamlr.dev/pro[/link][/dim]")
            sys.exit(0)

        # 3. Handle Workspace Target Version
        target_cluster_version = (getattr(args, "kube_version_target", None) or args.kube_version or os.getenv("YAMLR_KUBE_VERSION"))
        if target_cluster_version:
            try:
                target_cluster_version = HealContext.set_cluster_version(target_cluster_version)
            except ValueError as e:
                if getattr(args, "output", None) != "json":
                    console.print(f"[bold red]❌ Invalid K8s version:[/bold red] {e}")
                sys.exit(1)

        # 4. Help Dispatch & Smart Prompt
        if args.help or not args.command:
            from yamlr.cli.help_formatter import print_subcommand_help, print_kubectl_help
            from yamlr.core.entrypoints.display import print_custom_header

            if args.command:
                print_subcommand_help(console, args.command, invoked_as, show_all="--all" in set(sys.argv[1:]))
                sys.exit(0)
            else:
                is_explicit_help = args.help or "-h" in sys.argv or "--help" in sys.argv
                if not is_explicit_help and not is_gitops_active and sys.stdout.isatty() and not os.getenv("YAMLR_CLASSIC"):
                    from yamlr.core.config import ConfigManager
                    from yamlr.cli.interactor import render_workspace_context, run_smart_prompt
                    from yamlr.core.engine.discovery import fast_manifest_scan

                    config_mgr = ConfigManager(os.getcwd(), app_name="yamlr")
                    manifest_count = fast_manifest_scan(os.getcwd())
                    target_kb = (target_cluster_version or config_mgr.kubernetes_version or HealContext._get_default_cluster_version())
                    render_workspace_context(console, manifest_count, config_mgr.has_local_config(), target_kb)
                    cmd_tuple = run_smart_prompt(console, manifest_count, config_mgr.has_local_config(), is_pro)
                    if not cmd_tuple:
                        sys.exit(0)
                    args.command, remaining = cmd_tuple
                    if args.command == "help":
                        print_kubectl_help(console, invoked_as, show_all=getattr(args, "all", False))
                        sys.exit(0)
                    if remaining:
                        args.path = remaining
                else:
                    print_custom_header(invoked_as, is_pro)
                    print_kubectl_help(console, invoked_as, show_all="--all" in set(sys.argv[1:]))
                    sys.exit(0)

        # 5. Engine & Command Dispatch
        from yamlr.cli.command_registry import get_handler
        mod_name, func_name = get_handler(args.command)
        if not mod_name:
            console.print(f"[red]Error: Unknown command '{args.command}'[/red]")
            sys.exit(1)

        engine = None
        if args.command in ["scan", "heal", "upgrade", "migrate", "secure", "diagnose", "check", "audit", "dna", "status", "welcome", "demo", "stats", "roi", "baseline", "pulse", "graph", "idp-export", "doctor"]:
            from yamlr.core.engine import YamlrEngine
            engine = YamlrEngine(
                workspace_path=".", catalog_path=args.catalog, cluster_version=target_cluster_version,
                opa_bundle_path=getattr(args, "opa_bundle", None), kyverno_report_path=getattr(args, "kyverno_report", None),
                from_report_path=getattr(args, "from_report", None), concurrency=getattr(args, "concurrency", None),
                complement=getattr(args, "complement", []), default_namespace=getattr(args, "namespace", "default"),
                health_threshold=getattr(args, "health_threshold", 70), unrestricted=getattr(args, "unrestricted", False),
                debug_forensics=getattr(args, "forensic_debug", False),
            )
            if not is_gitops_active and not getattr(console, "_yamlr_quiet", False) and getattr(args, "output", "text") == "text":
                console.print(f"🎯 Target K8s: [bold green]{engine.cluster_version}[/bold green]")

        # Run Handler
        import importlib
        handler_mod = importlib.import_module(mod_name)
        handler_func = getattr(handler_mod, func_name)

        if args.command in ["scan", "heal", "migrate", "secure", "diagnose", "check", "audit"]:
            from yamlr.core.entrypoints.base import validate_required_arg
            if not (args.command == "audit" and getattr(args, "verify", None)) and not validate_required_arg(args.path, "path", args.command, [f"{invoked_as} {args.command} ."]):
                sys.exit(1)

        timing_report = root_timer.get_report() if "--timing" in sys.argv else None

        # [REFACTOR] Signature-Aware Dispatch Mapping
        SIG_MAP = {
            "CONSOLE_ONLY": ["init", "auth"],
            "ENGINE_CONTEXT": ["status", "stats", "roi", "dna", "demo", "welcome", "pulse", "graph", "idp-export", "doctor", "drift", "upgrade", "migrate"],
            "ENGINE_ONLY": ["baseline", "heal", "fix", "secure", "scan", "audit", "rollback"],
            "PARSER_CONTEXT": ["completion"],
            "PATH_CONTEXT": ["restore"],
            "VERSION_CONTEXT": ["catalog"],
            "NO_ARGS": ["manual", "mcp", "lsp"],
            "CONSOLE_ARGS": ["explain", "rules", "evidence"],
        }
        INV_SIG_MAP = {cmd: sig for sig, cmds in SIG_MAP.items() for cmd in cmds}
        sig = INV_SIG_MAP.get(args.command)

        if sig == "CONSOLE_ONLY":
            exit_code = handler_func(console, force=getattr(args, "force", False)) if args.command == "init" else handler_func(args, console)
        elif sig == "ENGINE_CONTEXT":
            exit_code = handler_func(args, engine, console)
        elif sig == "ENGINE_ONLY":
            if args.command in ["heal", "fix", "secure"]: exit_code = handler_func(args, engine, is_pro=is_pro)
            elif args.command in ["scan", "audit"]: exit_code = handler_func(args, engine, timing_report=timing_report)
            elif args.command == "baseline": exit_code = handler_func(args, engine, is_pro)
            else: exit_code = handler_func(args, engine)
        elif sig == "PARSER_CONTEXT": exit_code = handler_func(args, parser, console)
        elif sig == "PATH_CONTEXT": exit_code = handler_func(args, ".")
        elif sig == "VERSION_CONTEXT": exit_code = handler_func(args, target_cluster_version)
        elif sig == "CONSOLE_ARGS": exit_code = handler_func(args, console)
        elif sig == "NO_ARGS": exit_code = handler_func(args)
        else: exit_code = handler_func(args, engine) if engine else handler_func(args)

    except SystemExit as se:
        exit_code = se.code
        raise se
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if "--timing" in sys.argv:
            root_timer.__exit__(None, None, None)
            from yamlr.core.measurement import SurgicalTimer
            locs = locals()
            cur_args = locs.get("args")
            cur_console = locs.get("console")
            cmd = getattr(cur_args, "command", None) if cur_args else None
            out = getattr(cur_args, "output", "text") if cur_args else "text"

            if not (cmd == "scan" and out in ["json", "sarif"]):
                if not cur_console:
                    from yamlr.cli.context import CliContext
                    cur_console = CliContext.get_console()
                cur_console.rule("[bold]Surgical Performance Breakdown[/bold]")
                SurgicalTimer.print_timing_report(root_timer.get_report(), cur_console)

            timing_file = getattr(cur_args, "timing_file", None) if cur_args else None
            if timing_file:
                try:
                    import json
                    from pathlib import Path
                    Path(timing_file).write_text(json.dumps(root_timer.get_report(), indent=2), encoding="utf-8")
                except Exception: pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
