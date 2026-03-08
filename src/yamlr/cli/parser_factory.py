"""
Parser Factory for Yamlr CLI.

Why: To centralize and modularize the definition of CLI commands and flags,
reducing the complexity of the main entry point.
"""
import argparse
from yamlr.cli.commands.base import add_standard_flags

def create_parser(invoked_as: str) -> argparse.ArgumentParser:
    """
    Creates the main argument parser with all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog=invoked_as,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Yamlr: The Autonomous Manifest Control Plane.\n"
                    "Local-first, privacy-preserving manifest surgery.\n"
                    "Fixes what others miss: from malformed YAML to deprecated APIs and security risks.\n\n"
                    "🚀 NEW USER? Start here:\n"
                    "  yamlr welcome   - Guided visual tour & feature dashboard\n"
                    "  yamlr manual    - Read the complete User Guide offline\n"
                    "  yamlr status    - SRE Dashboard for your repository health\n"
                    "  yamlr demo      - Instant play-zone with intentional errors\n\n"
                    "🏗️ ULTRA-SCALE & CI/CD:\n"
                    "  yamlr check     - Fast syntax & schema gate (Perfect for PRs)\n"
                    "  yamlr scan      - Deep audit with SARIF support (Read-Only)\n"
                    "  yamlr audit     - Scientific benchmark & compliance audit (Alias for scan)\n"
                    "  yamlr dna       - Calculate/Verify Semantic SHA-256 DNA\n"
                    "  yamlr heal      - Propose repairs (Dry-run by default)\n",
        add_help=False
    )

    # Global flags
    parser.add_argument(
        "--kube-version", "--k8s-version", type=str, default=None, metavar="VERSION", dest="kube_version",
        help="Target K8s version (e.g., 1.28, v1.31)"
    )
    parser.add_argument(
        "--catalog", default=None, help="Path to custom catalog (default: bundled)"
    )
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("-s", "--summary-only", action="store_true", help="Show aggregate stats for batches")
    parser.add_argument("-p", "--plain", action="store_true", help="ASCII-only output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output for CI/CD pipelines")
    parser.add_argument("--verbose", action="store_true", help="Show full engine audit logs and execution stages")
    parser.add_argument("--max-depth", type=int, default=10, help="Limit directory recursion depth (default: 10)")
    parser.add_argument("--ext", default=".yaml,.yml", help="Extensions to process (default: .yaml,.yml)")
    parser.add_argument("--concurrency", type=int, default=None, help="Parallel worker count")
    parser.add_argument("--fail-on", choices=["error", "warning", "any"], default=None, help="CI/CD Gate: Exit 1 if issues found")
    parser.add_argument("--stream-to", type=str, default=None, metavar="FILE", help="ULTRA-SCALE: Stream results to NDJSON")
    parser.add_argument(
        "--identity-mode",
        choices=["infer", "strict"],
        default="infer",
        help="Identity detection style: 'infer' (default) or 'strict'",
    )
    parser.add_argument(
        "--risk-threshold",
        choices=["high", "medium", "low"],
        help="Exit 1 if any finding meets or exceeds this risk level",
    )

    subparsers = parser.add_subparsers(dest="command")

    # SCAN
    scan_parser = subparsers.add_parser("scan", add_help=False)
    add_standard_flags(scan_parser)
    scan_parser.add_argument(
        "--opa-bundle",
        metavar="PATH|URL",
        help="Path or URL to OPA bundle (Supports Gatekeeper Templates)",
    )
    scan_parser.add_argument(
        "--kyverno-report",
        metavar="PATH",
        help="[PRO] Path to Kyverno PolicyReport JSON for Auto-Fix ingestion",
    )
    scan_parser.add_argument(
        "--output",
        choices=["text", "json", "sarif"],
        default="text",
        help="Output format",
    )
    scan_parser.add_argument(
        "--diff", action="store_true", help="Show proposed fixes (like heal --dry-run)"
    )
    scan_parser.add_argument(
        "--fast", action="store_true", help="Skip deep semantic analysis for speed"
    )
    scan_parser.add_argument(
        "--dry-run", dest="diff", action="store_true", help="Alias for --diff"
    )

    # AUDIT (Alias for SCAN)
    audit_parser = subparsers.add_parser("audit", add_help=False, 
        help="Deep compliance audit (Alias for 'scan')")
    # Copy ALL flags from scan (including standard ones)
    for action in scan_parser._actions:
        if not any(opt in audit_parser._option_string_actions for opt in action.option_strings):
            audit_parser._add_action(action)
    
    audit_parser.add_argument("--bench", action="store_true", 
                             help="Run in 'Scientific Mode' against a labeled corpus")
    audit_parser.add_argument("--stats", action="store_true", 
                             help="Show summary stats only for the benchmark")

    # DIAGNOSE (Scan Wrapper)
    diagnose_parser = subparsers.add_parser("diagnose", add_help=False, 
        help="Deep-dive analysis with debug logs (runs scan with DEBUG logging)")
    add_standard_flags(diagnose_parser)
    diagnose_parser.add_argument("--output", choices=["text", "json"], default="text")

    # CHECK (Scan Wrapper)
    check_parser = subparsers.add_parser("check", add_help=False,
        help="Fast syntax & schema validation (wraps: scan --fast --strict)")
    add_standard_flags(check_parser)
    check_parser.add_argument("--output", choices=["text", "json", "sarif"], default="text")
    check_parser.add_argument("--fast", action="store_true", default=True, help="Alias for --fast (always on for check)")

    # SECURE (Heal Wrapper)
    secure_parser = subparsers.add_parser("secure", add_help=False,
        help="Analyze & suggest security hardening automatically (Pro feature)")
    add_standard_flags(secure_parser)
    secure_parser.add_argument("--dry-run", action="store_true")
    secure_parser.add_argument("--diff", dest="dry_run", action="store_true")
    secure_parser.add_argument("-y", "--yes", action="store_true")
    secure_parser.add_argument("--output", choices=["text", "json"], default="text")

    # UPGRADE (Heal Wrapper)
    upgrade_parser = subparsers.add_parser("upgrade", add_help=False,
        help="Migrate deprecated APIs to target version (wraps: heal --to <version>)")
    add_standard_flags(upgrade_parser)
    upgrade_parser.add_argument("--to", dest="kube_version", metavar="VERSION",
        help="Target Kubernetes version (e.g. 1.30). Defaults to cluster version.")
    upgrade_parser.add_argument("--dry-run", action="store_true")
    upgrade_parser.add_argument("--diff", dest="dry_run", action="store_true")
    upgrade_parser.add_argument("-y", "--yes", action="store_true")
    upgrade_parser.add_argument("--output", choices=["text", "json"], default="text")

    # MIGRATE (Alias for UPGRADE)
    migrate_parser = subparsers.add_parser("migrate", add_help=False,
        help="Migrate APIs to newer versions (Alias for 'upgrade'). Example: yamlr migrate --to 1.31")
    # Copy ALL flags from upgrade
    for action in upgrade_parser._actions:
         if not any(opt in migrate_parser._option_string_actions for opt in action.option_strings):
            migrate_parser._add_action(action)

    # HEAL
    heal_parser = subparsers.add_parser("heal", add_help=False)
    add_standard_flags(heal_parser)
    heal_parser.add_argument("--dry-run", action="store_true")
    heal_parser.add_argument(
        "--diff", dest="dry_run", action="store_true", help="Alias for --dry-run"
    )
    heal_parser.add_argument(
        "--pro-preview", action="store_true", help="[PRO Demo] Simulate PRO healing features without writing to disk"
    )
    heal_parser.add_argument(
        "--opa-bundle",
        metavar="PATH|URL",
        help="Path or URL to OPA bundle (Supports Gatekeeper Templates)",
    )
    heal_parser.add_argument(
        "--kyverno-report",
        metavar="PATH",
        help="[PRO] Path to Kyverno PolicyReport JSON for Auto-Fix ingestion",
    )
    heal_parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm")
    heal_parser.add_argument(
        "--yes-all", action="store_true", help="Auto-confirm all in batch"
    )
    heal_parser.add_argument(
        "--output",
        choices=["text", "json", "sarif"],
        default="text",
        help="Output format (text, json, or sarif)",
    )
    heal_parser.add_argument(
        "--stub-refs",
        nargs="?",
        const="*",
        default=False,
        help="Generate missing resources. Default: Safe kinds only. Use --stub-refs=Kind for filter.",
    )
    heal_parser.add_argument(
        "--fix-refs",
        action="store_true",
        default=False,
        dest="fix_refs",
        help="[PRO] Cross-Resource Auto-Fix: correct selector typos, fix port mismatches, and stub missing ConfigMaps/Secrets.",
    )
    heal_parser.add_argument(
        "--unsafe",
        nargs="?",
        const="*",
        default=False,
        help="Allow healing of sensitive resources. Use --unsafe or --unsafe=Secret.",
    )
    heal_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation. ⚠️ DANGEROUS: No way to revert changes!",
    )
    heal_parser.add_argument(
        "--evidence-dir",
        metavar="DIR",
        help="[PRO] Generate DNA-signed cryptographic receipts for compliance audits in the specified directory.",
    )
    heal_parser.add_argument(
        "--adapters-dir",
        metavar="DIR",
        help="[PRO] Directory containing custom Python/Shell remediation adapters for compliance violations.",
    )

    # EXPLAIN
    explain_parser = subparsers.add_parser("explain", add_help=False)
    explain_parser.add_argument(
        "rule_id", nargs="?", help="Rule ID to explain (e.g., rules/no-latest-tag)"
    )
    explain_parser.add_argument("-h", "--help", action="store_true")

    # COMPLETION
    completion_parser = subparsers.add_parser("completion", add_help=False)
    completion_parser.add_argument(
        "shell", choices=["powershell", "bash", "zsh", "fish"], nargs="?", help="Target shell"
    )
    completion_parser.add_argument(
        "--install", action="store_true", help="Automatically install completion to user profile"
    )
    completion_parser.add_argument("--word", type=str, help="Word being completed (Runtime callback)")
    completion_parser.add_argument("--position", type=int, help="Cursor position (Runtime callback)")
    completion_parser.add_argument("-h", "--help", action="store_true")

    # CATALOG
    catalog_parser = subparsers.add_parser("catalog", add_help=False)
    catalog_parser.add_argument(
        "action", choices=["update", "list", "status"], nargs="?", default="status"
    )
    catalog_parser.add_argument("--kube-version", "--k8s-version", type=str, metavar="VERSION", dest="kube_version")
    catalog_parser.add_argument("-h", "--help", action="store_true")

    # RULES
    rules_parser = subparsers.add_parser("rules", add_help=False)
    rules_parser.add_argument("-h", "--help", action="store_true")
    rules_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    rules_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show full rationale for every rule"
    )

    # STATUS
    status_parser = subparsers.add_parser("status", add_help=False)
    status_parser.add_argument("-h", "--help", action="store_true")
    status_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    status_parser.add_argument("--kube-version", "--k8s-version", type=str, metavar="VERSION", dest="kube_version")

    # STATS (ROI Calculator)
    stats_parser = subparsers.add_parser("stats", add_help=False,
        help="Display surgical ROI and time saved metrics")
    stats_parser.add_argument("-h", "--help", action="store_true")
    stats_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )

    welcome_parser = subparsers.add_parser("welcome", add_help=False)
    welcome_parser.add_argument("-h", "--help", action="store_true")

    # MANUAL
    manual_parser = subparsers.add_parser("manual", add_help=False,
        help="View the complete Yamlr User Guide or specific command manuals in your terminal")
    manual_parser.add_argument(
        "topic", nargs="?", help="Specific command or topic to view (e.g., scan, heal, rules)"
    )
    manual_parser.add_argument("-h", "--help", action="store_true")

    # DEMO
    demo_parser = subparsers.add_parser("demo", add_help=False)
    demo_parser.add_argument("-h", "--help", action="store_true")

    # INIT
    init_parser = subparsers.add_parser("init", add_help=False)
    init_parser.add_argument("-h", "--help", action="store_true")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing configuration"
    )
    init_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )

    # RESTORE
    restore_parser = subparsers.add_parser("restore", add_help=False)
    restore_parser.add_argument("path", nargs="*", help="File to restore from backup")
    restore_parser.add_argument("-h", "--help", action="store_true")

    # DNA
    dna_parser = subparsers.add_parser("dna", add_help=False, 
        help="Calculate or verify the Semantic SHA-256 DNA of a manifest")
    dna_parser.add_argument("path", help="Path to manifest file")
    dna_parser.add_argument("--hash", dest="expected_hash", help="Expected hash for verification")
    dna_parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    dna_parser.add_argument("-h", "--help", action="store_true")

    # EVIDENCE (Auditor-Ready Export)
    evidence_parser = subparsers.add_parser("evidence", add_help=False,
        help="[PRO] Compile mathematical DNA receipts into Auditor-Ready Compliance PDF/JSON reports")
    evidence_parser.add_argument("dir", help="Directory containing Yamlr evidence-*.json receipts")
    evidence_parser.add_argument("--format", choices=["pdf", "json"], default="pdf", help="Output format (default: pdf)")
    evidence_parser.add_argument("--output", dest="output_file", help="Explicit file path to save the report to")
    evidence_parser.add_argument("-h", "--help", action="store_true")

    subparsers.add_parser("version", add_help=False)
    auth_parser = subparsers.add_parser("auth", add_help=False)
    auth_sub = auth_parser.add_subparsers(dest="auth_action")
    auth_sub.add_parser("login", help="Authenticate with Yamlr Enterprise")
    auth_sub.add_parser("logout", help="Clear local credentials")
    auth_sub.add_parser("status", help="Check authentication status")
    auth_sub.add_parser("whoami", help="Alias for status")

    return parser
