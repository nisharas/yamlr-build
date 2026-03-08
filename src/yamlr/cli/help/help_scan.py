"""
Help text for the 'scan', 'check', and 'audit' commands.

Why: Extracted from monolithic help_formatter.py to enforce the
     500-line modularity limit and enable independent updates
     when Safety Engine output framing is added.
"""


def help_scan(console, invoked_as: str) -> None:
    """Display help for the 'scan' command.

    Why: Scan is the primary entry-point for safety analysis.
         This help must guide users to all analysis and CI flags.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} scan <target...>[/bold white] [options]"
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s), directory(s), or '-' for stdin")
    console.print("  --output FORMAT     Report format (text, json, sarif)")
    console.print("  --opa-bundle URL    Path or URL to OPA bundle (Supports Gatekeeper)")
    console.print("  --kyverno-report P  Path to Kyverno PolicyReport JSON for Auto-Fix ingestion")
    console.print("  --evidence-dir DIR  Generate cryptographic DNA evidence receipts")
    console.print("  --adapters-dir DIR  Execute custom Python/Bash remediation scripts")
    console.print("  --identity-mode MODE Identity detection: 'infer' (default) or 'strict'")
    console.print("  --diff              Show visual diff of proposed fixes")
    console.print("  --fast              Skip deep semantic analysis for speed")
    _print_shared_analysis_options(console)
    _print_semantic_protection_options(console)


def help_check(console, invoked_as: str) -> None:
    """Display help for the 'check' command.

    Why: Check is the lightweight CI gate. Users need to know
         it defaults to --strict --summary-only.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} check <target...>[/bold white] [options]"
    )
    console.print(
        "\nFast syntax and schema validation. Logic-checks only (no network)."
    )
    console.print(
        "[dim]Optimized for CI/CD: Defaults to --strict --summary-only.[/dim]"
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to check")
    console.print("  --fast              Always enabled for check")
    console.print("  --output FORMAT     Report format (text, json, sarif)")
    _print_shared_analysis_options(console)


def help_audit(console, invoked_as: str) -> None:
    """Display help for the 'audit' command (alias for scan).

    Why: Compliance-focused alias. Shows HAS score and benchmark options.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} audit <target...>[/bold white] [options]"
    )
    console.print(
        "\nAlias for [bold]scan[/bold]. Performs a deep read-only "
        "compliance audit. Calculates Healing Accuracy Score (HAS)."
    )
    console.print("\n[bold cyan]EXTRA AUDIT OPTIONS[/bold cyan]")
    console.print("  --bench             Run in 'Scientific Mode' against a labeled corpus")
    console.print("  --stats             Show summary stats only for the benchmark")
    console.print("\n[bold cyan]GLOBAL OPTIONS[/bold cyan]")
    console.print("  (See 'yamlr scan --help' for full options)")


# =====================================================================
# SHARED HELPERS (within this module)
# =====================================================================


def _print_shared_analysis_options(console) -> None:
    """Print the standard analysis flags shared by scan/check/audit.

    Why: Eliminates duplication across scan, check, and audit help blocks.
    """
    console.print("  --ext LIST          Extensions to scan (default: .yaml,.yml)")
    console.print("  --max-depth N       Recursion depth (default: 10)")
    console.print("  --kube-version V    Force target K8s version (alias: --k8s-version)")
    console.print("  -s, --summary-only  Show aggregate stats for batches")
    console.print("  --concurrency N     Number of parallel worker processes")
    console.print("  --catalog PATH      Path to custom K8s schema catalog (bundled by default)")
    console.print("  --identity-mode M   Identity: 'infer' (default) or 'strict'")
    console.print("  --verbose           Show detailed execution logs")
    console.print("  --strict            Enable strict schema validation")
    console.print("  --compact           Output with minimal whitespace")
    console.print("  --fail-on CHOICE    CI/CD Gate: Exit 1 if issues found (any/warning/error)")
    console.print("  --risk-threshold R  Exit 1 if finding meets/exceeds risk (high/medium/low)")
    console.print("  --stream-to FILE    ULTRA-SCALE: Stream incremental results to NDJSON")
    console.print("  -p, --plain         ASCII-only output mode")
    console.print("  -q, --quiet         Minimal output (CI/CD mode: errors + exit code)")


def _print_semantic_protection_options(console) -> None:
    """Print semantic & protection flags shared by scan and heal.

    Why: These flags appear in both scan and heal commands. Extracted
         to prevent drift between the two help blocks.
    """
    console.print("\n[bold cyan]SEMANTIC & PROTECTION[/bold cyan]")
    console.print("  --harden            Audit with security best practices & Pod Security Standards (Pro)")
    console.print("  --enforce-limits    Verify that all containers have resource requests & limits defined")
    console.print("  --fix-tags          Detect and remediate mutable image tags (e.g., :latest)")
    console.print("  --enforce-probes    Ensure all service-oriented containers have Liveness/Readiness probes")
    console.print("  --cpu-limit L       Override default CPU limit (e.g. 500m)")
    console.print("  --mem-limit L       Override default Memory limit (e.g. 512Mi)")
    console.print("  --namespace NS      Default namespace for generated resources")
    console.print("  --health-threshold N Min score to consider 'Healthy' (default: 70)")
    console.print("  --check-deprecations Audit for deprecated APIs")
    console.print("  --enforce-namespace  Auto-inject default namespace if missing")
