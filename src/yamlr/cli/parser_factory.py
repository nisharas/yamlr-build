"""
Parser Factory for Yamlr CLI.
-----------------------------
Centralizes and modularize the definition of CLI commands and flags.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-03-10: Decoupled Command Registries**
   - **Context**: The main parser function was becoming a "God Function".
   - **Decision**: Refactor into specialized command adders (e.g., `add_heal_command`).
   - **Consequence**: CLI extension is now modular; new commands are easy to add.

2. **2026-03-23: CI Safety by Default**
   - **Context**: Automated healing in CI without human review is risky.
   - **Decision**: Default the `heal` command to dry-run when `CI=true`.
   - **Consequence**: Zero-failure trust pillar upheld in automated workloads.
"""

import argparse
from typing import TYPE_CHECKING, Any, Dict, Optional

from yamlr.cli.flags import add_global_flags, add_standard_flags
from yamlr.cli.constants import COMMAND_TIER_MAP, CommandTier
from yamlr.core.k8s_versions import MATRIX
from yamlr.cli.command_registry import COMMAND_REGISTRY, CLICommand

__all__ = ["create_parser"]

OUTPUT_FORMAT = "Output format"
ALIAS_DRY_RUN = "Alias for --dry-run"

def create_parser(invoked_as: str, show_all: bool = False) -> argparse.ArgumentParser:
    """Creates the main argument parser from the declarative registry."""
    parser = argparse.ArgumentParser(
        prog=invoked_as,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="High-Performance Kubernetes Safety Engine.",
        add_help=False,
    )

    add_global_flags(parser)
    subparsers = parser.add_subparsers(dest="command")

    # SCAN (Core Detection Engine)
    scan_parser = subparsers.add_parser(
        "scan", add_help=False, help="Identify Kubernetes safety issues and compliance violations"
    )
    add_standard_flags(scan_parser)
    scan_parser.add_argument("--dry-run", action="store_true", help="Perform a read-only audit (Default)")
    scan_parser.add_argument("--diff", dest="dry_run", action="store_true", help=ALIAS_DRY_RUN)
    scan_parser.add_argument(
        "--output", 
        choices=["text", "json", "sarif", "sbom"], 
        default="text", 
        help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    scan_parser.add_argument("--emulate", nargs="+", help="Simulate sidecars offline (e.g. istiod, linkerd)")
    scan_parser.add_argument("--shadow", action="store_true", help="Capture dynamic mutations via server-side dry-run")
    scan_parser.add_argument("--patch", action="store_true", help="[Plan 1B] Generate yamlr-patches.yaml instead of direct output")

    # AUDIT (Alias for SCAN)
    audit_parser = subparsers.add_parser(
        "audit", add_help=False, help="Identify Kubernetes safety issues (alias for 'scan')"
    )
    # Copy ALL flags from scan
    for action in scan_parser._actions:
        if not any(opt in audit_parser._option_string_actions for opt in action.option_strings):
            audit_parser._add_action(action)

    diagnose_parser = subparsers.add_parser(
        "diagnose", add_help=False, help="[PRO] Deep-dive analysis: Path masking, forensics & environment audit"
    )
    add_standard_flags(diagnose_parser)
    diagnose_parser.add_argument("--output", choices=["text", "json"], default="text")
    diagnose_parser.add_argument(
        "--bundle", action="store_true", help="[PRO] Export an anonymized, founder-ready support zip"
    )
    
    # DRIFT (Strategic Reconciliation)
    drift_parser = subparsers.add_parser(
        "drift", add_help=False, help="Reconcile live cluster state against local manifests (Pro)"
    )
    add_standard_flags(drift_parser)
    drift_parser.add_argument("--context", help="Kubeconfig context to use")

    # DOCTOR (Marquee Health Check)
    doctor_parser = subparsers.add_parser(
        "doctor", add_help=False, help="Brutally fast health check: Runtime, Catalog, Cluster & Pro status"
    )
    add_standard_flags(doctor_parser)
    doctor_parser.add_argument("--output", choices=["text", "json"], default="text")
    doctor_parser.add_argument(
        "--k8s-matrix",
        "--k8s",
        action="store_true",
        help="Validate K8s matrix support externally and deterministically",
    )
    doctor_parser.add_argument(
        "--k8s-matrix-strict",
        action="store_true",
        help="Validate K8s matrix and exit non-zero if any claimed bundle is missing",
    )

    # CHECK (Scan Wrapper)
    check_parser = subparsers.add_parser(
        "check", add_help=False, help="Fast syntax & schema validation (wraps: scan --fast --strict)"
    )
    add_standard_flags(check_parser)
    check_parser.add_argument("--output", choices=["text", "json", "sarif"], default="text")

    # SECURE (Heal Wrapper)
    secure_parser = subparsers.add_parser(
        "secure", add_help=False, help="Analyze & suggest security hardening automatically (Pro feature)"
    )
    add_standard_flags(secure_parser)
    secure_parser.add_argument("--dry-run", action="store_true", help="Show proposed hardening without writing")
    secure_parser.add_argument("--diff", dest="dry_run", action="store_true", help=ALIAS_DRY_RUN)
    secure_parser.add_argument(
        "--output", choices=["text", "json", "sarif"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )

    # UPGRADE (Heal Wrapper)
    upgrade_parser = subparsers.add_parser(
        "upgrade", add_help=False, help="Migrate deprecated APIs to target version (wraps: heal --to <version>)"
    )
    add_standard_flags(upgrade_parser)
    upgrade_parser.add_argument(
        "--to",
        dest="kube_version",
        metavar="VERSION",
        help=f"Target Kubernetes version (e.g. 1.30). Defaults to the latest stable ({MATRIX.default_recommended}).",
    )
    upgrade_parser.add_argument("--dry-run", action="store_true")
    upgrade_parser.add_argument("--diff", dest="dry_run", action="store_true")
    upgrade_parser.add_argument(
        "--output", choices=["text", "json", "sarif"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )

    # MIGRATE (Alias for UPGRADE)
    migrate_parser = subparsers.add_parser(
        "migrate",
        add_help=False,
        help=f"Migrate APIs to newer versions (Alias for 'upgrade'). Example: yamlr migrate --to {MATRIX.default_recommended}",
    )
    # Copy ALL flags from upgrade
    for action in upgrade_parser._actions:
        if not any(opt in migrate_parser._option_string_actions for opt in action.option_strings):
            migrate_parser._add_action(action)

    # HEAL
    heal_parser = subparsers.add_parser("heal", add_help=False)
    add_standard_flags(heal_parser)
    heal_parser.add_argument("--dry-run", action="store_true")
    heal_parser.add_argument("--diff", dest="dry_run", action="store_true", help=ALIAS_DRY_RUN)
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
    heal_parser.add_argument(
        "--from-report",
        metavar="PATH",
        help="Automated Remediation: Ingest a Kyverno PolicyReport or OPA JSON violation file and apply fixes.",
    )
    heal_parser.add_argument("--yes-all", action="store_true", help="Auto-confirm all in batch")
    heal_parser.add_argument(
        "--output",
        choices=["text", "json", "sarif"],
        default="text",
        help=f"{OUTPUT_FORMAT} (default: %(default)s)",
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
    heal_parser.add_argument("--no-backup", action="store_true", help="Skip backup creation. ⚠️ DANGEROUS")
    heal_parser.add_argument("--patch", action="store_true", help="[Plan 1B] Surgical Persistence: write patches to yamlr-patches.yaml")
    heal_parser.add_argument("--emulate", nargs="+", help="Sidecar Bridge: simulate ghost containers during audit")
    heal_parser.add_argument("--shadow", action="store_true", help="Server-Side Shadowing: sync with cluster-injected sidecars")
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
    heal_parser.add_argument(
        "--adapter-shadow-mode",
        action="store_true",
        help="[PRO] Run adapters in shadow mode (record receipts but do not modify files).",
    )
    heal_parser.add_argument(
        "--allow-break-glass-adapters",
        action="store_true",
        help="[PRO] Explicitly allow adapters with BREAK_GLASS contract to run.",
    )
    heal_parser.add_argument(
        "--receipt",
        action="store_true",
        dest="generate_receipts",
        help="Generate a cryptographic DNA receipt for this healing session.",
    )
    heal_parser.add_argument(
        "--complement-mode",
        nargs="+",
        dest="complement",
        metavar="TOOL:PATH",
        help="[PRO] Complement Mode: Ingest findings from Checkov/Kubeconform for auto-fix (format: tool:path)",
    )

    # EXPLAIN
    explain_parser = subparsers.add_parser("explain", add_help=False)
    explain_parser.add_argument("rule_id", nargs="?", help="Rule ID to explain (e.g., rules/no-latest-tag)")
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
    catalog_parser.add_argument("-h", "--help", action="store_true")
    catalog_parser.add_argument("--verbose", action="store_true", help="Show detailed sync logs")
    catalog_parser.add_argument("action", choices=["update", "list", "status", "sync"], nargs="?", default="status")

    # RULES
    rules_parser = subparsers.add_parser("rules", add_help=False)
    rules_parser.add_argument("-h", "--help", action="store_true")
    rules_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    rules_parser.add_argument("-v", "--verbose", action="store_true", help="Show full rationale for every rule")

    # STATUS
    status_parser = subparsers.add_parser("status", add_help=False)
    add_standard_flags(status_parser)
    status_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )

    # STATS (Engineering Efficiency)
    stats_parser = subparsers.add_parser(
        "stats", add_help=False, help="[PRO] Engineering Efficiency: Surgical impact & project mastery metrics"
    )
    add_standard_flags(stats_parser)
    stats_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    stats_parser.add_argument(
        "--badge", action="store_true", help="Generate a shareable Markdown ROI badge (Shields.io)"
    )
    stats_parser.add_argument(
        "--org", action="store_true", help="[PRO] Show organization-wide surgical impact across all projects"
    )
    stats_parser.add_argument(
        "--apps", action="store_true", help="Show safety scores and top risks grouped by application"
    )

    # GRAPH (Visual Observability)
    graph_parser = subparsers.add_parser(
        "graph", add_help=False, help="Visual Observability: Relational topology & blast-radius analysis"
    )
    # No standard flags at parent level to avoid path swallowing subcommands
    graph_sub = graph_parser.add_subparsers(dest="action")

    topo_sub = graph_sub.add_parser("topo", help="Display ASCII tree of resource relationships", add_help=False)
    add_standard_flags(topo_sub)

    export_sub = graph_sub.add_parser("export", help="Export graph in Mermaid or DOT format", add_help=False)
    add_standard_flags(export_sub)
    export_sub.add_argument("--format", choices=["mermaid", "dot", "json"], default="mermaid")

    blast_sub = graph_sub.add_parser("blast-radius", help="Analyze the impact of a specific resource", add_help=False)
    add_standard_flags(blast_sub)
    blast_sub.add_argument("--resource", required=True, help="Resource key (kind/name or kind/ns/name)")

    # IDP-EXPORT (Supplier Pivot)
    idp_parser = subparsers.add_parser(
        "idp-export", add_help=False, help="[PRO] Platform Integration: Export safety truth to Backstage or Prometheus"
    )

    idp_sub = idp_parser.add_subparsers(dest="action")

    # Action: EXPORT
    export_sub = idp_sub.add_parser("export", help="Send metrics to target platform (Default)", add_help=False)
    export_sub.add_argument(
        "--format",
        choices=["backstage", "prometheus", "json"],
        default="json",
        help="Target platform format (default: json)",
    )
    export_sub.add_argument("--output-file", metavar="PATH", help="Write export to file instead of stdout")
    add_standard_flags(export_sub)

    # Action: INIT (Magic Moment)
    init_sub = idp_sub.add_parser("init", help="Generate opinionated integration templates", add_help=False)
    init_sub.add_argument(
        "--format",
        choices=["backstage", "prometheus"],
        default="backstage",
        help="Target platform format for template (default: backstage)",
    )
    init_sub.add_argument("--output-file", metavar="PATH", help="Path to save the generated template")
    add_standard_flags(init_sub)

    # ROI (Executive Dashboard)
    roi_parser = subparsers.add_parser(
        "roi", add_help=False, help="[PRO] Executive Portfolio: Financial value & engineering budget justification"
    )
    add_standard_flags(roi_parser)
    roi_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    roi_parser.add_argument("--badge", action="store_true", help="Generate a shareable Markdown ROI badge (Shields.io)")

    welcome_parser = subparsers.add_parser("welcome", add_help=False)
    welcome_parser.add_argument("-h", "--help", action="store_true")

    # MANUAL
    manual_parser = subparsers.add_parser(
        "manual", add_help=False, help="View the complete Yamlr User Guide or specific command manuals in your terminal"
    )
    manual_parser.add_argument("topic", nargs="?", help="Specific command or topic to view (e.g., scan, heal, rules)")
    manual_parser.add_argument("-h", "--help", action="store_true")

    # PULSE (Founder Intelligence)
    pulse_parser = subparsers.add_parser(
        "pulse", add_help=False, help="[STRATEGIC] Founder Intelligence: View aggregate rule efficacy and ecosystem ROI"
    )
    pulse_parser.add_argument("--output", choices=["text", "json"], default="text")
    pulse_parser.add_argument("-h", "--help", action="store_true")

    # DEMO
    demo_parser = subparsers.add_parser("demo", add_help=False)
    demo_parser.add_argument("-h", "--help", action="store_true")

    # INIT
    init_parser = subparsers.add_parser("init", add_help=False)
    init_parser.add_argument("-h", "--help", action="store_true")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration")
    init_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )

    # RESTORE
    restore_parser = subparsers.add_parser("restore", add_help=False)
    restore_parser.add_argument("path", nargs="*", help="File to restore from backup")
    restore_parser.add_argument("-h", "--help", action="store_true")

    # ROLLBACK (Global Atomic Transaction Reversal)
    rollback_parser = subparsers.add_parser(
        "rollback",
        add_help=False,
        help="Roll back the last atomic healing session (Omega)",
    )
    rollback_parser.add_argument("session_id", nargs="?", help="Specific session ID to roll back (default: latest)")
    rollback_parser.add_argument("-h", "--help", action="store_true")

    # DNA
    dna_parser = subparsers.add_parser(
        "dna", add_help=False, help="[PRO] Calculate or verify the Semantic SHA-256 DNA of a manifest"
    )
    dna_parser.add_argument("path", help="Path to manifest file")
    dna_parser.add_argument("--hash", dest="expected_hash", help="Expected hash for verification")
    dna_parser.add_argument(
        "--output", choices=["text", "json"], default="text", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    dna_parser.add_argument("-h", "--help", action="store_true")

    # EVIDENCE (Auditor-Ready Export)
    evidence_parser = subparsers.add_parser(
        "evidence",
        add_help=False,
        help="[PRO] Compile mathematical DNA receipts into Auditor-Ready Compliance PDF/JSON reports",
    )
    evidence_parser.add_argument("dir", help="Directory containing Yamlr evidence-*.json receipts")
    evidence_parser.add_argument(
        "--format", choices=["pdf", "json"], default="pdf", help=f"{OUTPUT_FORMAT} (default: %(default)s)"
    )
    evidence_parser.add_argument("--output", dest="output_file", help="Explicit file path to save the report to")
    evidence_parser.add_argument("-h", "--help", action="store_true")

    # BASELINE (GitOps Guard)
    baseline_parser = subparsers.add_parser(
        "baseline",
        add_help=False,
        help="Snapshot current violations to .yamlr-baseline.json to ignore them in future scans",
    )
    add_standard_flags(baseline_parser)
    baseline_sub = baseline_parser.add_subparsers(dest="action")

    gen_sub = baseline_sub.add_parser("generate", help="Create a new baseline snapshot", add_help=False)
    add_standard_flags(gen_sub)
    gen_sub.add_argument("--output", help="Custom path for the baseline file")

    # Keep top-level flags for backwards compatibility if needed, but primarily use 'generate'
    baseline_parser.add_argument("--output", help="Custom path for the baseline file")

    subparsers.add_parser("version", add_help=False)
    auth_parser = subparsers.add_parser("auth", add_help=False)
    auth_sub = auth_parser.add_subparsers(dest="auth_action")
    auth_sub.add_parser("login", help="Authenticate with Yamlr Enterprise (Pro)")
    auth_sub.add_parser("logout", help="Clear local credentials")
    auth_sub.add_parser("status", help="Check authentication status")
    auth_sub.add_parser("whoami", help="Alias for status")

    # [AGENTIC] MCP Server
    mcp_parser = subparsers.add_parser(
        "mcp", add_help=False, help="[PRO] Start the Yamlr MCP (Model Context Protocol) server for AI Agents"
    )
    mcp_parser.add_argument(
        "--transport", choices=["stdio"], default="stdio", help="Transport layer to use (default: stdio)"
    )
    mcp_parser.add_argument("-h", "--help", action="store_true")

    # LSP Server
    lsp_parser = subparsers.add_parser(
        "lsp", add_help=False, help="Start the Protocol (LSP) Server for VS Code (Pro)"
    )
    lsp_parser.add_argument("-h", "--help", action="store_true")

    # Final Pruning: Apply SUPPRESS to all non-PRIMARY commands if not show_all
    for cmd, tier in COMMAND_TIER_MAP.items():
        if tier == CommandTier.ADVANCED and not show_all:
            if cmd in subparsers.choices:
                # Override help with SUPPRESS
                subparsers.choices[cmd].help = argparse.SUPPRESS

    return parser
