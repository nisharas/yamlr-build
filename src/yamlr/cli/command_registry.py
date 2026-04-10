"""
Yamlr CLI Command Registry
--------------------------
Centralizes the mapping between CLI commands and their respective
entrypoint handlers to reduce boilerplate stubs in the source tree.

Why: To eliminate "Skeleton Debt" and maintain a 100% modular, high-signal codebase.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

class CLIArgument(BaseModel):
    """Metadata for a CLI flag/argument."""
    name: str # e.g., "--output"
    help: str
    choices: Optional[List[str]] = None
    default: Any = None
    action: Optional[str] = None # e.g., "store_true"
    dest: Optional[str] = None
    metavar: Optional[str] = None
    nargs: Optional[Any] = None

class CLICommand(BaseModel):
    """Declarative definition of a CLI command."""
    name: str
    help: str
    handler_module: str
    handler_func: str
    aliases: List[str] = Field(default_factory=list)
    args: List[CLIArgument] = Field(default_factory=list)
    tier: str = "Free" # OSS vs PRO

# The "One True Registry" for CLI operations
COMMAND_REGISTRY: List[CLICommand] = [
    CLICommand(
        name="scan",
        help="Audit manifests and validate schema compliance",
        handler_module="yamlr.core.entrypoints.scan",
        handler_func="handle_scan_command",
        aliases=["check", "audit"],
        args=[
            CLIArgument(name="--output", choices=["text", "json", "sarif", "sbom"], default="text", help="Output format"),
            CLIArgument(name="--diff", action="store_true", help="Show proposed fixes"),
            CLIArgument(name="--opa-bundle", metavar="PATH|URL", help="Path to OPA bundle"),
            CLIArgument(name="--kyverno-report", metavar="PATH", help="Path to Kyverno PolicyReport"),
        ]
    ),
    CLICommand(
        name="heal",
        help="Visual repair & semantic anchor generation",
        handler_module="yamlr.core.entrypoints.heal",
        handler_func="handle_heal_command",
        args=[
            CLIArgument(name="--diff", action="store_true", help="Show diff before applying"),
            CLIArgument(name="--force", action="store_true", help="Apply fixes without confirmation"),
        ]
    ),
    CLICommand(
        name="features",
        help="Show comprehensive list of engine capabilities and their status",
        handler_module="yamlr.core.entrypoints.features",
        handler_func="handle_features_command",
    ),
    CLICommand(
        name="baseline",
        help="Capture or compare against a resource fingerprint baseline",
        handler_module="yamlr.core.entrypoints.baseline",
        handler_func="handle_baseline_command",
    ),
    CLICommand(
        name="graph",
        help="Visualize or query the Kubernetes resource relationship graph",
        handler_module="yamlr.core.graph.engine",
        handler_func="handle_graph_command",
    ),
    CLICommand(
        name="mcp",
        help="Start the Model Context Protocol (MCP) server for AI assistants",
        handler_module="yamlr.core.entrypoints.mcp_server",
        handler_func="handle_mcp_command",
        tier="PRO",
    ),
    CLICommand(
        name="drift",
        help="Reconcile live cluster state against local manifests (Reporting-only)",
        handler_module="yamlr.pro.reconciliation.drift_doctor",
        handler_func="handle_drift_command",
        tier="PRO",
        args=[
            CLIArgument(name="--context", help="Kubeconfig context to use"),
            CLIArgument(name="--namespace", help="Namespace to filter (default: all)"),
        ]
    ),
    CLICommand(
        name="secure",
        help="Analyze & suggest security hardening automatically (Pro)",
        handler_module="yamlr.core.entrypoints.heal",
        handler_func="handle_heal_command",
        tier="PRO",
    ),
    CLICommand(
        name="init",
        help="Initialize a new .yamlr.yaml configuration file with smart defaults",
        handler_module="yamlr.core.entrypoints.config",
        handler_func="handle_init_command",
        args=[
            CLIArgument(name="--force", action="store_true", help="Overwrite existing configuration"),
        ]
    ),
    CLICommand(
        name="explain",
        help="Provide deep technical context and remediation steps for rules",
        handler_module="yamlr.core.entrypoints.explain",
        handler_func="handle_explain_command",
    ),
    CLICommand(
        name="catalog",
        help="Manage local Kubernetes schema catalogs and sync versions",
        handler_module="yamlr.core.entrypoints.catalog",
        handler_func="handle_catalog_command",
    ),
    CLICommand(
        name="demo",
        help="Generate sample manifests and run a guided healing demo",
        handler_module="yamlr.core.entrypoints.demo",
        handler_func="handle_demo_command",
    ),
    CLICommand(
        name="status",
        help="Show localized SRE health dashboard and system state",
        handler_module="yamlr.core.entrypoints.status",
        handler_func="handle_status_command",
    ),
    CLICommand(
        name="dna",
        help="Calculate or verify the SHA-256 Semantic DNA of a manifest",
        handler_module="yamlr.core.entrypoints.dna",
        handler_func="handle_dna_command",
        tier="PRO",
    ),
    CLICommand(
        name="upgrade",
        help="Automatically migrate deprecated APIs to newer versions",
        handler_module="yamlr.core.entrypoints.upgrade",
        handler_func="handle_upgrade_command",
        aliases=["migrate"],
        tier="PRO",
    ),
    CLICommand(
        name="rollback",
        help="Roll back the last atomic healing session (Omega)",
        handler_module="yamlr.core.entrypoints.restore",
        handler_func="handle_restore_command",
    ),
    CLICommand(
        name="idp-export",
        help="Export safety truth to Backstage or Prometheus (Pro)",
        handler_module="yamlr.core.idp_exporter",
        handler_func="handle_idp_command",
        tier="PRO",
    ),
    CLICommand(
        name="lsp",
        help="Start the Protocol (LSP) Server for VS Code (Pro)",
        handler_module="yamlr.cli.lsp",
        handler_func="handle_lsp_command",
        tier="PRO",
    ),
    CLICommand(
        name="completion",
        help="Generate and install shell autocompletion scripts",
        handler_module="yamlr.core.entrypoints.completion",
        handler_func="handle_completion_command",
    ),
    CLICommand(
        name="manual",
        help="View the complete Yamlr User Guide in your terminal",
        handler_module="yamlr.core.entrypoints.manual",
        handler_func="handle_manual_command",
    ),
    CLICommand(
        name="restore",
        help="Restore a manifest from the local backup vault",
        handler_module="yamlr.core.entrypoints.restore",
        handler_func="handle_restore_command",
    ),
    CLICommand(
        name="rules",
        help="List available healing rules and their remediation DNA",
        handler_module="yamlr.core.entrypoints.rules",
        handler_func="handle_rules_command",
    ),
    CLICommand(
        name="evidence",
        help="Manage or verify DNA-signed compliance receipts (Pro)",
        handler_module="yamlr.core.entrypoints.evidence",
        handler_func="handle_evidence_command",
        tier="PRO",
    ),
    CLICommand(
        name="stats",
        help="Show impact analysis & organizational efficiency metrics (Pro)",
        handler_module="yamlr.core.entrypoints.stats",
        handler_func="handle_stats_command",
        tier="PRO",
    ),
    CLICommand(
        name="roi",
        help="Calculate cost savings from automated healing (Pro)",
        handler_module="yamlr.core.entrypoints.roi",
        handler_func="handle_roi_command",
        tier="PRO",
    ),
    CLICommand(
        name="doctor",
        help="Diagnose system configuration and license issues",
        handler_module="yamlr.core.entrypoints.doctor",
        handler_func="handle_doctor_command",
        aliases=["diagnose"],
    ),
    CLICommand(
        name="auth",
        help="Manage Enterprise license keys and authentication",
        handler_module="yamlr.core.entrypoints.auth",
        handler_func="handle_auth_command",
    ),
    CLICommand(
        name="welcome",
        help="Show getting started guide and interactive tutorial",
        handler_module="yamlr.core.entrypoints.welcome",
        handler_func="handle_welcome_command",
    ),
]

# Legacy Compatibility Mapping
COMMAND_HANDLER_MAP: Dict[str, Tuple[str, str]] = {
    c.name: (c.handler_module, c.handler_func) for c in COMMAND_REGISTRY
}
for c in COMMAND_REGISTRY:
    for alias in c.aliases:
        COMMAND_HANDLER_MAP[alias] = (c.handler_module, c.handler_func)

def get_handler(command: str) -> Tuple[Optional[str], Optional[str]]:
    """Retrieves the handler module and function for a given command."""
    return COMMAND_HANDLER_MAP.get(command, (None, None))
