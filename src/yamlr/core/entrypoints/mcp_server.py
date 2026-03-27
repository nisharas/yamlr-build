"""
Yamlr MCP SERVER (Model Context Protocol)
-----------------------------------------
Exposes Yamlr's Safety Engine as precision surgical tools for AI Agents.

Architecture:
- Protocol: MCP (Model Context Protocol)
- Transport: JSON-RPC over stdio
- SDK: mcp-python-sdk (FastMCP)

Author: Nishar A Sunkesala / Yamlr Team
"""

from __future__ import annotations
import os
import sys
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Yamlr Safety Engine")

__all__ = ["mcp", "scan_manifest", "heal_manifest", "why", "handle_mcp_command"]

# Configure logging to stderr to avoid corrupting stdio transport
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("yamlr.mcp")

def _get_engine(safe_mode: bool = True):
    """Lazy-load the Yamlr Engine to avoid circular imports during bootstrap."""
    from yamlr.core.engine import YamlrEngine
    return YamlrEngine(workspace_path=".", default_namespace="default", safe_mode=safe_mode)

@mcp.tool()
def scan_manifest(path: str) -> str:
    """
    Perform a safety scan on a Kubernetes manifest file or directory.
    Returns a list of findings with rationale and impact analysis.
    
    Args:
        path: The file path or directory to scan.
    """
    logger.info(f"MCP Tool: scan_manifest(path='{path}')")
    try:
        engine = _get_engine(safe_mode=True)
        if os.path.isfile(path):
            result = engine.audit_and_heal_file(path, dry_run=True) # dry_run=True for scan
            results = [result]
        elif os.path.isdir(path):
            results = engine.batch_heal(root_path=path, dry_run=True)
        else:
            return f"Error: Path not found: {path}"

        # Format findings for the agent
        findings_summary = []
        for r in results:
            for f in getattr(r, "findings", []):
                findings_summary.append({
                    "file": r.file_path,
                    "kind": r.kind,
                    "severity": f.get("severity"),
                    "rule_id": f.get("rule_id"),
                    "message": f.get("message"),
                    "rationale": f.get("rationale"),
                    "impact_description": f.get("impact_description"),
                    "risk_level": f.get("risk_level"),
                    "suggestion": f.get("suggestion")
                })
        
        if not findings_summary:
            return "✅ No safety issues found."
        
        # Return as a formatted markdown list for the agent
        report = [f"### Safety Scan Results for `{path}`"]
        for f in findings_summary:
            report.append(f"- **[{f['severity']}]** `{f['rule_id']}` in {f['file']} ({f['kind']})")
            report.append(f"  - *Message*: {f['message']}")
            report.append(f"  - *Rationale*: {f['rationale']}")
            report.append(f"  - *Impact*: {f['impact_description']}")
            report.append(f"  - *Risk Level*: {f['risk_level']}")
            report.append(f"  - *Suggestion*: {f['suggestion']}")
            report.append("")
            
        return "\n".join(report)
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return f"Error during scan: {str(e)}"

@mcp.tool()
def heal_manifest(path: str, rule_filter: Optional[str] = None, allow_unsafe: bool = False) -> str:
    """
    Apply automated safety repairs to a Kubernetes manifest.
    
    Args:
        path: The file path or directory to heal.
        rule_filter: Optional comma-separated list of rule IDs to fix (fix all if omitted).
        allow_unsafe: If True, permits mutation of sensitive resources (Secrets, RBAC) even in SafeMode.
    """
    logger.info(f"MCP Tool: heal_manifest(path='{path}', filter='{rule_filter}', allow_unsafe={allow_unsafe})")
    try:
        # Pass allow_unsafe to the engine config
        engine = _get_engine()
        engine.config.allow_unsafe = allow_unsafe
        
        fix_tags = rule_filter.split(",") if rule_filter else None
        
        if os.path.isfile(path):
            result = engine.audit_and_heal_file(path, dry_run=False, fix_tags=fix_tags)
            results = [result]
        elif os.path.isdir(path):
            results = engine.batch_heal(root_path=path, dry_run=False, fix_tags=fix_tags)
        else:
            return f"Error: Path not found: {path}"

        healed_count = sum(1 for r in results if r.status == "HEALED" or (hasattr(r, "written") and r.written))
        if healed_count == 0:
            # Check for SafeMode blocks to provide better feedback
            for r in results:
                if getattr(r, "status", "") == "SAFE_MODE_BLOCK":
                    return f"🛑 Blocked: Mutation of {r.kind} is restricted for AI Agents in SafeMode. Set 'allow_unsafe=True' if this was intended."
            return "No repairs were necessary or possible."
            
        return f"Successfully applied repairs to {healed_count} file(s)."
        
    except Exception as e:
        logger.error(f"Heal failed: {e}")
        return f"Error during heal: {str(e)}"

@mcp.tool()
def why(rule_id: str) -> str:
    """
    Get a deep architectural explanation for a specific safety rule.
    
    Args:
        rule_id: The rule ID (e.g., 'rule/ghost-service').
    """
    logger.info(f"MCP Tool: why(rule_id='{rule_id}')")
    try:
        from yamlr.core.entrypoints.explain import RULE_DB
        rule_data = RULE_DB.get(rule_id)
        
        if not rule_data:
            # Try fuzzy match
            from yamlr.core.entrypoints.explain import _resolve_rule_data
            rule_data, resolved_id = _resolve_rule_data(rule_id)
            if not rule_data:
                return f"Error: No such rule found: {rule_id}"
            rule_id = resolved_id

        name = rule_data.get("name", "Unknown Rule")
        description = rule_data.get("description", "No description available.")
        rationale = rule_data.get("rationale", "No rationale available.")
        remediation = rule_data.get("remediation", "No remediation steps provided.")
        
        return f"### {name} ({rule_id})\n\n**Rationale**: {rationale}\n\n**Description**: {description}\n\n**Remediation**: {remediation}"
    except Exception as e:
        return f"Error: {str(e)}"

def handle_mcp_command(_args):
    """Entry point for the 'yamlr mcp' CLI command."""
    from yamlr.core.license_manager import LicenseManager
    status, _ = LicenseManager.check_pro_status()
    capabilities = LicenseManager.resolve_capabilities()
    
    if not status.is_usable() or not capabilities.can_run_mcp:
        LicenseManager.notify_pro_required("Agentic Safety Engine (MCP)")
        return 1

    logger.info("Starting Yamlr MCP Server...")
    # FastMCP run() handles transport detection (stdio by default)
    mcp.run()
    return 0

if __name__ == "__main__":
    mcp.run()
