"""
Help text for toolbox commands: diagnose, secure, upgrade, migrate, dna, evidence.

Why: Groups the medium-complexity subcommand help texts that share
     a common pattern (USAGE + OPTIONS + standard flags). Keeps the
     main help_formatter.py lean.
"""


def help_diagnose(console, invoked_as: str) -> None:
    """Display help for the 'diagnose' command.

    Why: Diagnose is the debug-mode entry point. Users need to know
         it enables DEBUG-level logging for engine tracing.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} diagnose <target...>[/bold white] [options]"
    )
    console.print(
        "\nRuns a deep audit with [bold yellow]DEBUG[/bold yellow] "
        "logging enabled.\nUse this to trace engine decisions or report bugs."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to analyze")
    console.print("  --output FORMAT     Report format (text, json)")
    _print_standard_options(console)


def help_secure(console, invoked_as: str) -> None:
    """Display help for the 'secure' command.

    Why: Secure is a Pro feature. Help text must clearly state
         what it enforces and that it requires a Pro license.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} secure <target...>[/bold white] [options]"
    )
    console.print(
        "\nApplies enterprise security hardening (Pro feature)."
    )
    console.print(
        "Enforces: [dim]runAsNonRoot, readOnlyRootFilesystem, "
        "drop capabilities, logic limits.[/dim]"
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to harden")
    console.print("  --dry-run           Show proposed changes without writing")
    console.print("  --diff              Show visual diff")
    console.print("  -y, --yes           Auto-confirm changes")
    console.print("  --output FORMAT     Report format (text, json)")
    _print_standard_options(console)


def help_upgrade(console, command: str, invoked_as: str) -> None:
    """Display help for the 'upgrade' or 'migrate' commands.

    Why: Upgrade is the version-migration tool. The --to flag is
         REQUIRED and must be prominent in the help output.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} {command} <target...>[/bold white] [options]"
    )
    console.print(
        "\nMigrates deprecated Kubernetes APIs to their modern replacements."
    )
    console.print("Example: [dim]extensions/v1beta1 Deployment -> apps/v1[/dim]")
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to upgrade")
    console.print("  --to VERSION        Target K8s version (e.g. 1.30). Defaults to cluster/latest.")
    console.print("  --dry-run           Show proposed changes without writing")
    console.print("  --diff              Show visual diff")
    console.print("  -y, --yes           Auto-confirm changes")
    console.print("  --output FORMAT     Report format (text, json)")
    _print_standard_options(console)


def help_dna(console, invoked_as: str) -> None:
    """Display help for the 'dna' command.

    Why: DNA is the semantic integrity feature. Users must
         understand hash-based verification for CI pipelines.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} dna <path>[/bold white] [options]"
    )
    console.print(
        "\nCalculates or verifies the Semantic SHA-256 DNA of a manifest."
    )
    console.print(
        "The DNA is invariant to formatting, comments, and field ordering."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  path                Path to the YAML manifest file")
    console.print("  --hash HASH         Expected hash for verification (returns exit 1 if mismatch)")
    console.print("  --output json       Export DNA as structured JSON")


def help_evidence(console, invoked_as: str) -> None:
    """Display help for the 'evidence' command.

    Why: Evidence is the compliance reporting tool. Users must know
         it aggregates DNA receipts into auditor-ready PDFs.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} evidence <dir>[/bold white] [options]"
    )
    console.print(
        "\nAggregates cryptographic DNA receipts into a unified "
        "PDF Compliance Report."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  dir                 Directory containing JSON receipts (e.g., from --evidence-dir)")
    console.print("  --format FORMAT     Output format: pdf (default) or json")
    console.print("  --output FILE       Path to save the generated report")


# =====================================================================
# SHARED HELPER
# =====================================================================


def _print_standard_options(console) -> None:
    """Print standard options shared across diagnose, secure, upgrade.

    Why: Eliminates duplication. These flags are identical across
         several subcommands.
    """
    console.print("  --kube-version V    Target K8s version (alias: --k8s-version)")
    console.print("  --max-depth N       Recursion depth (default: 10)")
    console.print("  --ext LIST          Extensions to scan (default: .yaml,.yml)")
    console.print("  --concurrency N     Number of parallel worker processes")
    console.print("  --strict            Enable strict schema validation")
    console.print("  --compact           Output with minimal whitespace")
    console.print("  --verbose           Show detailed execution logs")
    console.print("  -s, --summary-only  Show aggregate stats for batches")
    console.print("  --fail-on CHOICE    CI/CD Gate: Exit 1 if found (any/warning/error)")
    console.print("  --risk-threshold R  Exit 1 if finding meets/exceeds risk (high/medium/low)")
    console.print("  --catalog PATH      Path to custom K8s schema catalog (bundled by default)")
    console.print("  --identity-mode M   Identity: 'infer' (default) or 'strict'")
    console.print("  --stream-to FILE    ULTRA-SCALE: Stream results to NDJSON")
    console.print("  -p, --plain         ASCII-only output mode")
    console.print("\n[dim]Advanced & Semantic Controls:[/dim]")
    console.print("  --check-deprecations Audit for deprecated APIs")
    console.print("  --cpu-limit L       Override default CPU limit (e.g. 500m)")
    console.print("  --mem-limit L       Override default Memory limit (e.g. 512Mi)")
    console.print("  --namespace NS      Default namespace for generated resources")
    console.print("  --health-threshold N Min score to consider 'Healthy' (default: 70)")
