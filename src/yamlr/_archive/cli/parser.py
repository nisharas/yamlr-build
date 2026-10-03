import argparse
import os
from typing import Any, List

from yamlr.core_logic import UniversalCommandRegistry
from yamlr.ui.theme import DESC_HEAL, DESC_PATH, DESC_SCAN


def create_parser():
    """Builds the forensic command registry (Lazy Generation)."""
    parser = argparse.ArgumentParser(
        prog="yamlr", 
        description="Yamlr Integrity Engine — The Autonomous Resolution Plane for Kubernetes.",
        epilog="Examples:\n  yamlr scan .                    # Read-only clinical audit\n  yamlr heal . --apply            # Non-destructive auto-repair\n  yamlr scan --helm ./chart       # In-memory Helm chart audit\n  yamlr mcp                       # Start Model Context Protocol (MCP) server\n  yamlr lsp                       # Start Language Server Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show precision help.")
    parser.add_argument("-v", "--version", action="store_true", help="Show engine version.")
    
    parent_parser = _create_parent_parser()
    subparsers = parser.add_subparsers(dest="command", help="Precision Commands")

    _add_core_commands(subparsers, parent_parser)
    _add_discovery_commands(subparsers, parent_parser)
    _add_enterprise_commands(subparsers, parent_parser)
    _add_system_commands(subparsers, parent_parser)

    parser.add_argument("--all", action="store_true", help="Display the full engine registry.")
    return parser

def _create_parent_parser():
    """Defines global arguments shared across all commands."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--k8s-version", "--kube-version", dest="k8s_version", help="Force Kubernetes version (e.g., 1.31).")
    parent.add_argument("--crd", help="Path to CRD manifests to ingest.")
    parent.add_argument("-f", "--output-file", help="Path to write report (SARIF/JSON).")
    parent.add_argument("--exit-zero", action="store_true", default=False, help="Always exit with code 0 (for non-blocking CI warnings).")
    return parent

def _add_targeting_group(parser, helm_help: str, kustomize_help: str):
    """Attaches Kubernetes schema versioning and templating flags.

    Why: Guarantees consistent cluster schema resolution and templating engine
         emulation across audit, diff, and remediation commands.
    """
    group = parser.add_argument_group("Targeting & Environment")
    group.add_argument("--k8s-version", "--kube-version", dest="k8s_version", help="Target Kubernetes schema version (e.g., 1.30, 1.31).")
    group.add_argument("--crd", help="Path to CRD manifests to ingest.")
    group.add_argument("--helm", action="store_true", help=helm_help)
    group.add_argument("--kustomize", action="store_true", help=kustomize_help)
    return group


def _add_cicd_group(parser, include_fail_on: bool = False, include_telemetry: bool = False):
    """Attaches CI/CD pipeline integration, report outputs, and automation flags.

    Why: Standardizes deterministic exit codes, SARIF/JSON reporting, and CI telemetry
         for headless execution in automated continuous integration workflows.
    """
    group = parser.add_argument_group("CI/CD & Pipeline Integration")
    if include_fail_on:
        group.add_argument(
            "--fail-on",
            choices=["error", "warning", "note"],
            help="Exit with non-zero code if violations of this severity or higher are found.",
        )
    group.add_argument("-f", "--output-file", help="Path to write report (SARIF/JSON).")
    group.add_argument(
        "--exit-zero",
        action="store_true",
        default=False,
        help="Always exit with code 0 (for non-blocking CI warnings).",
    )
    if include_telemetry:
        group.add_argument(
            "--push-telemetry",
            action="store_true",
            default=False,
            help="Push anonymous ROI data to global dashboard.",
        )
    return group


def _add_core_commands(subparsers, parent):
    """Tier 0: Critical Integrity Commands."""
    # 1. scan
    p = subparsers.add_parser("scan", help=DESC_SCAN)
    g_scan_pri = p.add_argument_group("Primary Options")
    g_scan_pri.add_argument("path", nargs="?", default=".", help="Path to manifests.")
    g_scan_pri.add_argument("--output", choices=["text", "sarif", "json"], default="text", help="Output format.")
    g_scan_pri.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output.")
    g_scan_pri.add_argument("-w", "--watch", action="store_true", help="Watch for changes and re-scan automatically.")
    _add_targeting_group(
        p,
        helm_help="Audit rendered Helm chart templates in-memory.",
        kustomize_help="Audit rendered Kustomize overlay resources in-memory.",
    )
    _add_cicd_group(p, include_fail_on=True, include_telemetry=True)

    # 2. heal
    h = subparsers.add_parser("heal", help=DESC_HEAL)
    g_heal_pri = h.add_argument_group("Primary Remediation Options")
    g_heal_pri.add_argument("path", nargs="?", default=".", help="Path to manifests.")
    g_heal_pri.add_argument("--apply", action="store_true", help="Apply fixes directly to manifests (Default: Preview).")
    g_heal_pri.add_argument("--diff", action="store_true", help="Show side-by-side diff of proposed changes.")
    g_heal_pri.add_argument("--dry-run", action="store_true", help="Show forensic impact without applying changes.")
    g_heal_pri.add_argument("--create-stubs", action="store_true", help="Opt-in to synthesize missing Kubernetes target stubs (ConfigMap, Secret, PVC).")
    _add_targeting_group(
        h,
        helm_help="Audit & heal Helm values in-memory.",
        kustomize_help="Audit & heal Kustomize overlays in-memory.",
    )
    g_heal_policy = h.add_argument_group("Policy & Tool Ingestion")
    g_heal_policy.add_argument("--ingest-opa", help="Path to OPA Gatekeeper JSON report to ingest and auto-repair.")
    g_heal_policy.add_argument("--ingest-kyverno", help="Path to Kyverno PolicyReport JSON to ingest and auto-repair.")
    _add_cicd_group(h, include_fail_on=False, include_telemetry=True)

    # 3. diff
    diff_p = subparsers.add_parser("diff", help="Preview side-by-side or unified diff of proposed auto-remediations.")
    g_diff_pri = diff_p.add_argument_group("Primary Diff Options")
    g_diff_pri.add_argument("path", nargs="?", default=".", help="Path to manifests.")
    g_diff_pri.add_argument("-u", "--unified", action="store_true", help="Display unified diff instead of side-by-side.")
    _add_targeting_group(
        diff_p,
        helm_help="Preview diff for Helm chart templates in-memory.",
        kustomize_help="Preview diff for Kustomize overlays in-memory.",
    )
    _add_cicd_group(diff_p, include_fail_on=False, include_telemetry=False)

    # 4. fmt
    fmt_p = subparsers.add_parser("fmt", parents=[parent], help="Canonical manifest formatter for Unix pipes and files (reorders keys to K8s schema standards).")
    fmt_p.add_argument("path", nargs="?", default=".", help="Path to manifest or directory (or '-' for stdin).")
    fmt_p.add_argument("-w", "--write", action="store_true", help="Write result to source file directly instead of stdout.")

    # 5. fix
    fix_p = subparsers.add_parser("fix", parents=[parent], help="Zero-flag non-destructive auto-repair for Unix pipes and files.")
    fix_p.add_argument("path", nargs="?", default=".", help="Path to manifest or directory (or '-' for stdin).")


def _add_discovery_commands(subparsers, parent):
    """Tier 1: UX & Learning Commands."""
    stat = subparsers.add_parser("status", help="Display engine metadata and licensing.")
    g_stat_pri = stat.add_argument_group("Primary Options")
    g_stat_pri.add_argument("--output", choices=["text", "json"], default="text", help="Output format (text or structured JSON).")
    _add_cicd_group(stat, include_fail_on=False, include_telemetry=False)

    ver = subparsers.add_parser("version", help="Display version metadata.")
    g_ver_pri = ver.add_argument_group("Primary Options")
    g_ver_pri.add_argument("--output", choices=["text", "json"], default="text", help="Output format (text or structured JSON).")
    _add_cicd_group(ver, include_fail_on=False, include_telemetry=False)

    doc = subparsers.add_parser("doctor", help="Perform environment diagnostics.")
    g_doc = doc.add_argument_group("Diagnostic Options")
    g_doc.add_argument("--fix", action="store_true", help="Auto-fix local environment drift (e.g. download schemas).")
    g_doc_env = doc.add_argument_group("Targeting & Environment")
    g_doc_env.add_argument("--k8s-version", "--kube-version", dest="k8s_version", help="Target Kubernetes schema version to diagnose (e.g., 1.30, 1.31).")
    g_doc_env.add_argument("--crd", help="Path to CRD manifests to validate.")
    subparsers.add_parser("welcome", parents=[parent], help="Display entry dashboard.")
    subparsers.add_parser("guide", parents=[parent], help="Open technical guide.")
    
    h = subparsers.add_parser("help", parents=[parent], help="Display precision help and command registry.")
    h.add_argument("topic", nargs="?", help="Target command or concept.")
    h.add_argument("--all", action="store_true", help="Display full registry.")

    ex = subparsers.add_parser("explain", parents=[parent], help="Technical concept lookup.")
    ex.add_argument("path", nargs="?", default=".", help="Concept.")
    ex.add_argument("--flag", help="Flag context.")

def _add_enterprise_commands(subparsers, parent):
    """Tier 2: Pro Capability Discovery."""
    for cmd in ["dna", "drift", "audit", "graph", "pulse", "secure", "rollback", "evidence", "sign"]:
        p = subparsers.add_parser(cmd, parents=[parent], help=f"[PRO] {UniversalCommandRegistry.get_desc(cmd)}")
        p.add_argument("path", nargs="?", default=".", help=DESC_PATH)
        if cmd == "graph":
            p.add_argument("--focus", help="Focus on a specific resource (e.g., Deployment/my-app).")

    fleet_p = subparsers.add_parser("fleet", parents=[parent], help="[PRO] Fleet Intelligence and Multi-Repo GitOps PR Batching.")
    fleet_p.add_argument("fleet_command", nargs="?", choices=["status", "pr-batch"], default="status", help="Fleet subcommand (status or pr-batch).")
    fleet_p.add_argument("--repos", help="Path to repository manifest file, single repo, or directory of repos.")
    fleet_p.add_argument("--branch", default="yamlr/fleet-upgrade", help="Target git branch for fleet PRs.")
    fleet_p.add_argument("--title", default="fix(k8s): automated fleet manifest remediation", help="PR title and commit message.")
    fleet_p.add_argument("--apply", action="store_true", help="Apply fixes directly to repositories.")
    fleet_p.add_argument("--dry-run", action="store_true", help="Simulate fleet upgrades without modifying or committing.")
    fleet_p.add_argument("--create-pr", action="store_true", help="Automatically push and open PRs via gh or glab CLI.")
    fleet_p.add_argument("--report", default="fleet-report.md", help="Path to write markdown fleet audit report.")
    
    r = subparsers.add_parser("roi", parents=[parent], help="Calculate manifest engineering quality and reliability impact metrics.")
    r.add_argument("path", nargs="?", default=".", help=DESC_PATH)
    r.add_argument("--output", choices=["text", "json"], default="text", help="Output format.")

    imp = subparsers.add_parser("impact", parents=[parent], help="Alias of 'roi': Calculate manifest engineering quality and reliability impact metrics.")
    imp.add_argument("path", nargs="?", default=".", help=DESC_PATH)
    imp.add_argument("--output", choices=["text", "json"], default="text", help="Output format.")
    
    subparsers.add_parser("subscribe", parents=[parent], help="Manage or activate Yamlr Pro workspace subscription.")
    
    u = subparsers.add_parser("migrate", parents=[parent], help="Automated Kubernetes API version migration.")
    u.add_argument("path", nargs="?", default=".", help=DESC_PATH)
    u.add_argument("--to-k8s", dest="k8s_version", default="1.30", help="Target Kubernetes version (default: 1.30).")
    u.add_argument("--apply", action="store_true", help="Apply migrations directly to manifests.")

def _add_system_commands(subparsers, parent):
    """Tier 3: Admin & Integration."""
    inst = subparsers.add_parser("install", parents=[parent], help="Install Git hooks/Actions.")
    inst.add_argument("target", choices=["hook", "action"], help="Integration target.")
    subparsers.add_parser("restore", parents=[parent], help="Atomic restoration of last remediation checkpoint.")
    
    v = subparsers.add_parser("verify", parents=[parent], help="Forensic verification of manifest signatures.")
    v.add_argument("path", nargs="?", default=".", help=DESC_PATH)
    
    subparsers.add_parser("lsp", parents=[parent], help="Start LSP interface.")
    
    comp = subparsers.add_parser("completion", parents=[parent], help="Generate shell completions.")
    comp.add_argument("shell", choices=["bash", "zsh"], help="Shell type.")
    subparsers.add_parser("diagnose", parents=[parent], help="Deep diagnostic audit of engine internals.")
    subparsers.add_parser("check", parents=[parent], help="Multi-tier environment and manifest sanity check.")
    subparsers.add_parser("catalog", parents=[parent], help="Inspect forensic rule catalog and schema coverage.")
    upg = subparsers.add_parser("upgrade", parents=[parent], help="Alias of 'migrate': Automated API version migration.")
    upg.add_argument("path", nargs="?", default=".", help=DESC_PATH)
    upg.add_argument("--to-k8s", dest="k8s_version", default="1.30", help="Target Kubernetes version (default: 1.30).")
    upg.add_argument("--apply", action="store_true", help="Apply migrations directly to manifests.")
    init = subparsers.add_parser("init", parents=[parent], help="Initialize a new Yamlr workspace.")
    init.add_argument("path", nargs="?", default=".", help="Path to initialize.")
    subparsers.add_parser("rules", parents=[parent], help="Alias of 'catalog': Inspect forensic rule catalog.")
    subparsers.add_parser("stats", parents=[parent], help="Alias of 'admin stats': Display engine performance and violation stats.")
    b_p = subparsers.add_parser("baseline", parents=[parent], help="Establish or verify workspace baseline fingerprints.")
    b_p.add_argument("path", nargs="?", default=".", help="Path to workspace.")
    idp = subparsers.add_parser("idp-export", parents=[parent], help="[PRO] Export safety and compliance metrics to Internal Developer Portals.")
    idp.add_argument("--format", choices=["backstage", "prometheus", "json"], default="json", help="Target IDP format.")
    subparsers.add_parser("demo", parents=[parent], help="Generate an interactive sample workspace with broken manifests.")
    subparsers.add_parser("features", parents=[parent], help="Display active engine capabilities and tier support.")
    subparsers.add_parser("legal", parents=[parent], help="Display license and legal metadata.")
    subparsers.add_parser("manual", parents=[parent], help="Open the offline professional reference.")
    subparsers.add_parser("mcp", parents=[parent], help="Model Context Protocol interface for IDE and editor integrations.")
    
    admin = subparsers.add_parser("admin", parents=[parent], help="Internal engine diagnostics and system health.")
    admin.add_argument("sub", choices=["stats", "health", "users"], help="Admin operation.")
    
    auth = subparsers.add_parser("auth", parents=[parent], help="Authenticate and manage Yamlr Pro licensing.")
    auth.add_argument("sub", choices=["activate"], help="Auth operation.")
    auth.add_argument("key", help="The JWT string or path to license file.")

    sch = subparsers.add_parser("schema", parents=[parent], help="Manage and ingest custom Kubernetes schemas and CRDs.")
    sch_sub = sch.add_subparsers(dest="schema_action")
    sch_ingest = sch_sub.add_parser("ingest", help="Ingest and compile CRD YAML manifests into Yamlr schema cache.")
    sch_ingest.add_argument("path", help="Path to CRD YAML file or directory of CRDs.")
    sch_ingest.add_argument("--out", "-o", default=".yamlr/schemas", help="Output directory for compiled schema cache.")
    sch_list = sch_sub.add_parser("list", help="List all active native and custom ingested CRD schemas.")
    sch_list.add_argument("--dir", default=".yamlr/schemas", help="Schema cache directory.")
    sch_clean = sch_sub.add_parser("clean", help="Clear the local CRD schema cache.")
    sch_clean.add_argument("--dir", default=".yamlr/schemas", help="Schema cache directory.")
