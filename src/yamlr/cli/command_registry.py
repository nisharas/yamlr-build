"""
Yamlr CLI Command Registry
--------------------------
Centralizes the mapping between CLI commands and their respective 
entrypoint handlers to reduce boilerplate stubs in the source tree.

Why: To eliminate "Skeleton Debt" and maintain a 100% modular, high-signal codebase.
"""

from typing import Dict, Tuple

# Map command name -> (module_path, function_name)
COMMAND_HANDLER_MAP: Dict[str, Tuple[str, str]] = {
    # Core Validation/Healing
    "scan": ("yamlr.core.entrypoints.scan", "handle_scan_command"),
    "heal": ("yamlr.core.entrypoints.heal", "handle_heal_command"),
    "audit": ("yamlr.cli.commands.audit", "handle_audit_command"),
    "upgrade": ("yamlr.core.entrypoints.upgrade", "handle_upgrade_command"),
    "migrate": ("yamlr.core.entrypoints.upgrade", "handle_upgrade_command"),
    "secure": ("yamlr.cli.commands.secure", "handle_secure_command"),
    "diagnose": ("yamlr.cli.commands.diagnose", "handle_diagnose_command"),
    "check": ("yamlr.cli.commands.check", "handle_check_command"),
    
    # Utility/Information
    "explain": ("yamlr.cli.commands.explain", "handle_explain_command"),
    "init": ("yamlr.core.entrypoints.config", "handle_init_command"),
    "restore": ("yamlr.core.entrypoints.restore", "handle_restore_command"),
    "status": ("yamlr.cli.commands.status", "handle_status_command"),
    "welcome": ("yamlr.cli.commands.welcome", "handle_welcome_command"),
    "rules": ("yamlr.cli.commands.rules", "handle_rules_command"),
    "completion": ("yamlr.cli.commands.completion", "handle_completion_command"),
    "catalog": ("yamlr.cli.commands.catalog", "handle_catalog_command"),
    "demo": ("yamlr.cli.commands.demo", "handle_demo_command"),
    "manual": ("yamlr.cli.commands.manual", "handle_manual_command"),
    "dna": ("yamlr.cli.commands.dna", "handle_dna_command"),
    "evidence": ("yamlr.cli.commands.evidence", "handle_evidence_command"),
    "stats": ("yamlr.cli.commands.stats", "handle_stats_command"),
    "roi": ("yamlr.cli.commands.roi", "handle_roi_command"),
    "baseline": ("yamlr.core.entrypoints.baseline", "handle_baseline_command"),
    "pulse": ("yamlr.cli.commands.pulse", "handle_pulse_command"),
    "mcp": ("yamlr.core.entrypoints.mcp_server", "handle_mcp_command"),
    "graph": ("yamlr.core.entrypoints.graph", "handle_graph_command"),
    "idp-export": ("yamlr.cli.commands.idp_export", "handle_idp_export_command"),
    "auth": ("yamlr.cli.commands.auth", "handle_auth_command"),
    "doctor": ("yamlr.cli.commands.doctor", "handle_doctor_command"),
}

def get_handler(command: str) -> Tuple[str, str]:
    """Retrieves the handler module and function for a given command."""
    return COMMAND_HANDLER_MAP.get(command, (None, None))
