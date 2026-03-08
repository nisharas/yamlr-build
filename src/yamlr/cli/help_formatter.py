"""
Help Formatter for Yamlr CLI — Dispatcher.

Why: Keeps cli/main.py lean by externalizing help text. The monolithic
     print_subcommand_help() was decomposed into per-command modules
     in cli/help/ to enforce the 500-line modularity limit and prevent
     duplicate elif entries.

Architecture:
    - print_kubectl_help(): Main help menu (unchanged, lives here).
    - print_subcommand_help(): Thin dispatcher to per-command modules.
    - Per-command help lives in cli/help/help_scan.py, help_heal.py,
      help_toolbox.py, help_utils.py.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""
from rich.table import Table
from rich.panel import Panel


def print_kubectl_help(console, invoked_as: str):
    """
    Displays the main help menu in a 'kubectl' inspired format.

    Why: The main help screen is the first impression for new users.
         It must clearly show all commands, global options, and
         high-value capabilities in a scannable format.
    """
    console.print("\n[bold cyan]┌─ PRIMARY COMMANDS[/bold cyan]")
    cmd_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    cmd_table.add_column(style="bold green", width=14)
    cmd_table.add_column(style="white")

    # Core Logic
    cmd_table.add_row("scan", "Audit manifests for issues (Read-Only, Local Analysis)")
    cmd_table.add_row("check", "Fast syntax & schema validation (CI-ready)")
    cmd_table.add_row("heal", "Propose repairs (Dry-run by default, no auto-write)")
    cmd_table.add_row("secure", "Analyze & suggest security hardening (Pro)")
    cmd_table.add_row("upgrade", "Migrate APIs to target version")

    # Aliases
    cmd_table.add_row("audit", "Alias for 'scan' (Compliance focus)")
    cmd_table.add_row("migrate", "Alias for 'upgrade' (Versioning focus)")

    console.print(cmd_table)

    console.print("\n[bold cyan]┌─ TOOLBOX[/bold cyan]")
    tool_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    tool_table.add_column(style="bold blue", width=14)
    tool_table.add_column(style="white")

    tool_table.add_row("init", "Initialize a new project with .yamlr.yaml")
    tool_table.add_row("restore", "Restore files from backups")
    tool_table.add_row("diagnose", "Run deep-dive analysis with debug logs")
    tool_table.add_row("explain", "Get detail on a specific rule or rule ID")
    tool_table.add_row("rules", "Dashboard of all available protections")
    tool_table.add_row("status", "SRE Dashboard: System health & backups")
    tool_table.add_row("stats", "ROI Dashboard: Cumulative project impact & mastery")
    tool_table.add_row("dna", "Calculate/Verify Semantic SHA-256 DNA")
    tool_table.add_row("evidence", "Generate Auditor-Ready PDF Compliance Reports")
    tool_table.add_row("manual", "Read the complete User Guide offline")
    tool_table.add_row("catalog", "Manage Kubernetes schema definitions")
    tool_table.add_row("demo", "Magic Moment: Scaffold a learning environment")
    tool_table.add_row("welcome", "Onboarding: Quick start & branding")
    tool_table.add_row("completion", "Generate shell autocompletion scripts")
    tool_table.add_row("version", "Display version info and license status")
    tool_table.add_row("auth", "Manage yamlr enterprise authentication")

    console.print(tool_table)

    console.print("\n[bold cyan]┌─ GLOBAL OPTIONS & FILTERS[/bold cyan]")
    opt_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    opt_table.add_column(style="yellow", width=24)
    opt_table.add_column(style="dim white")
    opt_table.add_row("-h, --help", "Display usage information")
    opt_table.add_row("-v, --version", "Display version information")
    opt_table.add_row("--kube-version VERSION", "Target K8s version (e.g., 1.28, v1.31)")
    opt_table.add_row("--k8s-version VERSION", "Alias for --kube-version")
    opt_table.add_row("--catalog PATH", "Specify a custom K8s schema catalog (default: bundled)")
    opt_table.add_row("--max-depth N", "Limit directory recursion depth (Default: 10)")
    opt_table.add_row("--ext LIST", "Extensions to process (Default: .yaml,.yml)")
    opt_table.add_row("--concurrency N", "Number of parallel worker processes (Default: CPU count)")
    opt_table.add_row("-s, --summary-only", "Show aggregate stats (recommended for 100+ files)")
    opt_table.add_row("--verbose", "Show full engine audit logs and execution stages")
    opt_table.add_row("--fail-on CHOICE", "CI/CD Gate: Exit 1 if issues found (any, warning, error)")
    opt_table.add_row("--stream-to FILE", "ULTRA-SCALE: Stream results to NDJSON (10k+ files)")
    opt_table.add_row("-p, --plain", "ASCII-only output mode (Recommended for Log redirection)")
    opt_table.add_row("-q, --quiet", "Minimal output for CI/CD pipelines (errors + exit code only)")
    opt_table.add_row("--identity-mode MODE", "Identity detection style: 'infer' (default) or 'strict'")
    console.print(opt_table)

    console.print("\n[bold magenta]┌─ QUICK START[/bold magenta]")
    qs_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    qs_table.add_column(style="cyan", width=24)
    qs_table.add_column(style="dim white")
    qs_table.add_row("yamlr scan .", "Audit all YAML files in the current directory")
    qs_table.add_row("yamlr heal <file>", "Interactive repair with visual diff preview")
    qs_table.add_row("yamlr explain <id>", "Get detailed remediation for a rule violation")
    console.print(qs_table)

    tip_content = (
        f"Use [cyan bold]{invoked_as} <command> --help[/cyan bold] for subcommand specific flags.\n"
        "Documentation: [link=https://yamlr.dev]https://yamlr.dev[/link]"
    )

    capability_content = (
        "✨ [bold green]Ghost Services:[/bold green] Detect dangling services with no Pods.\n"
        "✨ [bold green]Cross-Resource:[/bold green] Find port mismatches, broken Ingress, and orphans.\n"
        "✨ [bold green]Security Hardening:[/bold green] Enforce PSS Restricted baseline.\n"
        "✨ [bold green]SARIF Reporting:[/bold green] Native GitHub Code Scanning integration."
    )

    console.print("\n[bold cyan]┌─ HIGH-VALUE CAPABILITIES[/bold cyan]")
    console.print(Panel(capability_content, border_style="green", expand=False))

    security_tip = (
        "🔒 [bold green]Security & Privacy:[/bold green] Yamlr performs manifest analysis locally\n"
        "and does not transmit your YAML to external servers."
    )
    console.print(Panel(security_tip, title="[bold green]🛡 TRUST GUARANTEE[/bold green]", border_style="green", expand=False))

    console.print(Panel(tip_content, title="[bold magenta]💡 TIP[/bold magenta]", border_style="magenta", expand=False))


def print_subcommand_help(console, command: str, invoked_as: str):
    """Dispatches to per-command help modules.

    Why: Replaced the monolithic 260-line elif chain that had 6
         duplicate entries. Each command group now lives in its own
         module under cli/help/.
    """
    # Lazy imports to avoid circular dependencies
    from yamlr.cli.help.help_scan import help_scan, help_check, help_audit
    from yamlr.cli.help.help_heal import help_heal
    from yamlr.cli.help.help_toolbox import (
        help_diagnose, help_secure, help_upgrade, help_dna, help_evidence,
    )
    from yamlr.cli.help.help_utils import (
        help_catalog, help_version, help_explain, help_auth, help_init,
        help_restore, help_demo, help_welcome, help_completion,
        help_status, help_rules, help_stats, help_manual,
    )

    # Dispatch table — deterministic, no duplicate elif entries
    dispatch = {
        "scan": lambda: help_scan(console, invoked_as),
        "check": lambda: help_check(console, invoked_as),
        "audit": lambda: help_audit(console, invoked_as),
        "heal": lambda: help_heal(console, invoked_as),
        "diagnose": lambda: help_diagnose(console, invoked_as),
        "secure": lambda: help_secure(console, invoked_as),
        "upgrade": lambda: help_upgrade(console, "upgrade", invoked_as),
        "migrate": lambda: help_upgrade(console, "migrate", invoked_as),
        "dna": lambda: help_dna(console, invoked_as),
        "evidence": lambda: help_evidence(console, invoked_as),
        "catalog": lambda: help_catalog(console, invoked_as),
        "version": lambda: help_version(console, invoked_as),
        "explain": lambda: help_explain(console, invoked_as),
        "auth": lambda: help_auth(console, invoked_as),
        "init": lambda: help_init(console, invoked_as),
        "restore": lambda: help_restore(console, invoked_as),
        "demo": lambda: help_demo(console, invoked_as),
        "welcome": lambda: help_welcome(console, invoked_as),
        "completion": lambda: help_completion(console, invoked_as),
        "status": lambda: help_status(console, invoked_as),
        "rules": lambda: help_rules(console, invoked_as),
        "stats": lambda: help_stats(console, invoked_as),
        "manual": lambda: help_manual(console, invoked_as),
    }

    handler = dispatch.get(command)
    if handler:
        handler()
