"""
Help text for the 'heal' command.

Why: Heal is the most flag-heavy command in Yamlr. Extracted to its own
     module to keep help_formatter.py under 500 lines and enable
     independent updates for Safety Engine output framing.
"""


def help_heal(console, invoked_as: str) -> None:
    """Display help for the 'heal' command.

    Why: Heal is the core product command. Help must cover all flags
         including Pro features, output control, and semantic protection.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} heal <target...>[/bold white] [options]"
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to heal")
    console.print("  --opa-bundle URL    Path or URL to OPA bundle (Supports Gatekeeper)")
    console.print("  --kyverno-report P  Path to Kyverno PolicyReport JSON for Auto-Fix ingestion")
    console.print("  --evidence-dir DIR  Generate cryptographic DNA evidence receipts")
    console.print("  --adapters-dir DIR  Execute custom Python/Bash remediation scripts")
    console.print("  --identity-mode MODE Identity detection: 'infer' (default) or 'strict'")
    console.print("  --dry-run           Show proposed changes without writing")
    console.print("  --pro-preview       [PRO Demo] Simulate PRO healing features without writing to disk")
    console.print("  -y, --yes           Auto-confirm single file healing")
    console.print("  --yes-all           Auto-confirm batch healing (Use with caution)")
    console.print("  --harden            Apply security hardening (Pro feature)")
    console.print("  --check-deprecations Audit for deprecated APIs")
    console.print("  --output FORMAT     Output formatting (text, json)")
    console.print("  --ext LIST          Extensions to scan (default: .yaml,.yml)")
    console.print("  --max-depth N       Recursion depth (default: 10)")
    console.print("  --kube-version V    Force target K8s version (alias: --k8s-version)")
    console.print("  -s, --summary-only  Show aggregate stats for batches")
    console.print("  --concurrency N     Number of parallel worker processes")
    console.print("  --verbose           Show detailed execution logs")
    console.print("  --strict            Enable strict schema validation")
    console.print("  --compact           Output with minimal whitespace")
    console.print("  --fail-on CHOICE    CI/CD Gate: Exit 1 if issues found (any/warning/error)")
    console.print("  --risk-threshold R  Exit 1 if finding meets/exceeds risk (high/medium/low)")
    console.print("  --catalog PATH      Path to custom K8s schema catalog (bundled by default)")
    console.print("  --stream-to FILE    ULTRA-SCALE: Stream incremental results to NDJSON")

    console.print("\n[bold cyan]SEMANTIC & PROTECTION[/bold cyan]")
    console.print("  --harden            Apply security hardening (Pro)")
    console.print("  --enforce-limits    Auto-inject CPU/Memory limits")
    console.print("  --fix-tags          Auto-fix :latest or missing image tags")
    console.print("  --enforce-probes    Auto-inject Liveness/Readiness probes")
    console.print("  --stub-refs [TYPE]  Generate missing resources via filter")
    console.print("  --unsafe [TYPE]     Allow healing of sensitive resources")
    console.print("  --cpu-limit L       Default CPU for new containers (e.g. 500m)")
    console.print("  --mem-limit L       Default Memory for new containers (e.g. 512Mi)")
    console.print("  --namespace NS      Default namespace for generated resources")
    console.print("  --health-threshold N Min score to consider 'Healthy' (default: 70)")
    console.print("  --enforce-namespace  Auto-inject default namespace if missing")
    console.print("  --fix-refs           [PRO] Cross-Resource Auto-Fix selector/port/stubs")

    console.print("\n[bold cyan]OUTPUT CONTROL[/bold cyan]")
    console.print("  -p, --plain         ASCII-only output mode")
    console.print("  -q, --quiet         Minimal output (CI/CD mode: errors + exit code)")
    console.print("  --no-backup         Skip backup creation (use with caution)")
