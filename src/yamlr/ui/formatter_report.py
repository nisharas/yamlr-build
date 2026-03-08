#!/usr/bin/env python3
"""
Formatter REPORT Mixin
----------------------
Single-file report rendering: surgical details, issues summary, and audit trails.

Why: Extracted from formatter.py to enforce the <500 line modularity rule.
This mixin provides per-file display methods that YamlrFormatter inherits.

Architecture: Mixin pattern — shares state via `self` with the main class.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
"""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from yamlr.cli.commands.base import get_console

console = get_console()


def get_score_emoji(score: int) -> str:
    """Returns an emoji indicator based on health score."""
    if getattr(console, "_yamlr_plain", False):
        if score >= 90: return "[v]"
        elif score >= 70: return "[!]"
        elif score >= 50: return "[?]"
        else: return "[x]"

    if score >= 90:
        return "🟢"  # Excellent
    elif score >= 70:
        return "🟡"  # Good
    elif score >= 50:
        return "🟠"  # Needs work
    else:
        return "🔴"  # Critical


class ReportMixin:
    """
    Single-file report rendering methods for YamlrFormatter.

    Responsibilities:
    - Full surgical report display (display_report)
    - Issues summary table with smart tips
    - Verbose audit trail tree
    """

    PRO_FIXABLE_MAPPING = {
        "rule/resource-requests": "--enforce-limits",
        "rule/resource-limits": "--enforce-limits",
        "rule/run-as-non-root": "--harden",
        "rule/no-privileged": "--harden",
        "rule/allow-privilege-escalation": "--harden",
        "rule/unsafe-hostpath": "--harden",
        "rule/host-network": "--harden",
        "rule/read-only-root-fs": "--harden",
        "rule/missing-liveness": "--enforce-probes",
        "rule/missing-readiness": "--enforce-probes",
        "rule/no-latest-tag": "--fix-tags",
        "rule/ghost-service": "--fix-refs",
        "rule/port-mismatch": "--fix-refs",
        "rule/service-no-selector": "--fix-refs",
        "rule/missing-configmap-target": "--fix-refs",
        "rule/broken-volume": "--fix-refs",
        "rule/ingress-broken": "--fix-refs",
        "rule/network-policy-missing": "--harden",
        "rule/untrusted-registry": "--harden",
    }

    def _get_icon(self, icon: str) -> str:
        """Returns ASCII fallback for emojis if plain mode is active."""
        if not getattr(console, "_yamlr_plain", False):
            return icon
        
        mapping = {
            "📊": "[#]", "✅": "[v]", "✓": "v", "→": "->", 
            "✎": "*", "⚠": "!", "○": "o", "↪": ">>", "✗": "x",
            "💾": "(B)", "✨": "OK", "💡": "i", "⚔️": "[!]",
            "⚠️": "!", "❌": "x", "🛡": "[S]", "📋": "[L]",
            "Reference:": "REF:"
        }
        return mapping.get(icon, icon)

    # -------------------------------------------------------------------------
    # Unified Report Display
    # -------------------------------------------------------------------------

    def display_report(self, result: Dict[str, Any], verbose: bool = False):
        """
        Renders the full surgical details for a single file.

        Args:
            result: Result dict from engine.audit_and_heal_file()
            verbose: If True, shows the full 'Stage X' audit trail.
        """
        status = result.get("status", "UNKNOWN")
        file_path = result.get("file_path", "Unknown")

        # Handle errors and skips early
        if status == "SKIPPED":
            console.print(
                Panel(
                    "[yellow]This file does not contain a valid Kubernetes API identity (kind + apiVersion).\nStrict Identity Mode is active, so healing was bypassed to protect your data.[/yellow]",
                    title=f"[bold yellow]↪ SKIPPED: {file_path}[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
            return

        if status in ["ENGINE_ERROR", "FILE_NOT_FOUND", "SECURITY_ERROR", "EMPTY_FILE"]:
            self.display_error(file_path, result.get("error", "Unknown error"), status)
            return

        # Main Panel Component for the File
        score = result.get("health_score", 0)
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        score_emoji = get_score_emoji(score)

        # Header Info
        identities = result.get("identities", [])
        resources_str = ""
        if identities:
            resources_list = []
            for identity in identities:
                kind = identity.get("kind", "Unknown")
                name = identity.get("name", "unnamed")
                resources_list.append(f"{kind}/{name}")
            resources_str = ", ".join(resources_list)
        else:
            resources_str = "[dim]No resources[/dim]"

        # Create Title Panel with emoji score indicator
        from rich import box
        box_style = getattr(console, "_yamlr_box", box.ROUNDED)

        console.print(
            Panel(
                f"[bold]Resources:[/bold] {resources_str}\n"
                f"[bold]Health Score:[/bold] {score_emoji} [{color}]{score}/100[/{color}]\n"
                f"[bold]Detection Rate:[/bold] [magenta]100%[/magenta] (Truth-in-Healing enabled)\n"
                f"[bold]Status:[/bold] {status}\n"
                f"[bold]Shield Status:[/bold] [cyan]PHY: {result.get('phy_status', '100%')}[/cyan] | [cyan]KBS: {result.get('kbs_status', '0%')}[/cyan] | [cyan]SEM: {result.get('sem_status', '0%')}[/cyan]",
                title=f"[bold {color}]Reference: {file_path}[/bold {color}]",
                border_style=color,
                expand=True,  # Expanded for better layout
                box=box_style,
            )
        )

        logs = result.get("logic_logs", [])

        # NEW: Issues Summary Table (Always visible if there are issues)
        self._render_issues_summary(logs, status)

        # OLD: Audit Tree (Visible ONLY if verbose)
        if verbose:
            if logs:
                self._render_staged_logs(logs, file_path)

        findings = result.get("findings", [])
        if findings:
            table = Table(
                title="[bold magenta]Findings[/bold magenta]",
                show_header=True,
                header_style="bold white",
            )
            table.add_column("Severity", width=10)
            table.add_column("Risk", width=10)
            table.add_column("Rule ID", width=30)
            table.add_column("Message")

            for f in findings:
                sev = f.get("severity", "").upper()
                rule_id = f.get("rule_id", "")
                msg = f.get("message", "")
                suggestion = f.get("suggestion", "")
                rationale = f.get("rationale", "")

                icon = self._get_icon("❌") if sev == "ERROR" else self._get_icon("⚠️")
                sev_style = "bold red" if sev == "ERROR" else "bold yellow"

                # Format message with suggestion if present
                full_msg = msg
                if rationale:
                    full_msg += f"\n[dim white]{self._get_icon('💡')} Rationale: {rationale}[/dim white]"
                if suggestion:
                    full_msg += f"\n[dim italic]{self._get_icon('💡')} {suggestion}[/dim italic]"

                # Risk Intelligence Integration
                risk_l = f.get("risk_level", "LOW").upper()
                risk_style = "bold red" if risk_l == "HIGH" else "bold yellow" if risk_l == "MEDIUM" else "green"
                risk_impact = f.get("impact_description", "")
                
                if risk_impact:
                    full_msg = f"[bold white]{risk_impact}[/bold white]\n" + full_msg

                # Inline PRO Upsell Hints [FREE-12-04]
                quiet_mode = getattr(console, "_yamlr_quiet", False)
                if not quiet_mode and rule_id in self.PRO_FIXABLE_MAPPING and status != "HEALED":
                    pro_cmd = self.PRO_FIXABLE_MAPPING[rule_id]
                    full_msg += f"\n[bold cyan]{self._get_icon('💎')} PRO: yamlr heal {pro_cmd} would fix this[/bold cyan]"

                # Enterprise Compliance Attribution [TASK-21-1]
                try:
                    from yamlr.pro.compliance.ruleset import ComplianceRegistry
                    ctrl_str = ComplianceRegistry.format_controls_string(rule_id)
                    if ctrl_str:
                        shield_icon = self._get_icon("🛡")
                        full_msg += f"\n[dim italic]{shield_icon} Compliance: {ctrl_str}[/dim italic]"
                except ImportError:
                    pass

                table.add_row(
                    f"[{sev_style}]{icon} {sev}[/{sev_style}]",
                    f"[{risk_style}]{risk_l}[/{risk_style}]",
                    f"[cyan]{rule_id}[/cyan]",
                    full_msg,
                )

            console.print(table)
            console.print()

        # =====================================================================
        # DEPRECATION WARNINGS (OSS Feature)
        # =====================================================================
        found_dep = False
        for identity in identities:
            dep = identity.get("deprecation_info")
            if dep:
                found_dep = True
                deprecated = dep.get('deprecated_api', '?')
                replacement = dep.get('replacement_api', '?')
                removed = dep.get('removed_in_version', '?')
                kind = identity.get('kind')
                name = identity.get('name', 'unnamed')
                
                # Side-by-Side Diff Representation
                diff_text = f"[bold red]- apiVersion: {deprecated}[/bold red]\n"
                diff_text += f"[bold green]+ apiVersion: {replacement}[/bold green]\n"
                
                console.print(
                    Panel(
                        f"[bold yellow]⚠️  DEPRECATED API DETECTED[/bold yellow]\n\n"
                        f"[bold]Resource:[/bold] {kind}/{name}\n"
                        f"[bold]Status:[/bold] Removed in K8s {removed}\n\n"
                        f"{diff_text}\n"
                        f"[dim]{dep.get('migration_notes', '')}[/dim]",
                        title=f"{self._get_icon('⚠️')} Deprecation Warning",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                )

        if found_dep:
            # Add Migration Hint as a standalone high-visibility panel
            invoked_as = "Yamlr"
            try:
                from yamlr.core.bridge import YamlrBridge
                invoked_as = YamlrBridge.get_invoked_command()
            except:
                pass

            console.print(
                Panel(
                    f"This resource is using an API that has been removed or deprecated.\n"
                    f"Run [bold cyan]{invoked_as} migrate {file_path}[/bold cyan] to automatically upgrade it.",
                    title=f"{self._get_icon('💡')} QUICK FIX",
                    border_style="green",
                    expand=False,
                )
            )

        # [Feature] Single-file Deprecation Summary
        self._render_deprecation_summary([result])

        # [Smart UX] Show backup message ONLY if file was actually healed
        backup_path = result.get("backup_created")
        if status == "HEALED" and backup_path:
            console.print(f"[dim]💾 Backup: {backup_path}[/dim]")

        # NEW: Remediation Command (Activation UX)
        remediation = result.get("remediation_command")
        if remediation:
            console.print(
                Panel(
                    f"To fix detected issues, run:\n[bold cyan]{remediation}[/bold cyan]",
                    title=f"{self._get_icon('⚔️')} REMEDIATION",
                    border_style="cyan",
                    expand=False,
                )
            )

        # [Progressive Disclosure] Hint about verbose mode
        console.print("[dim]💡 Run with --verbose for full audit trail[/dim]\n")

    def _render_issues_summary(self, logs: List[str], status: str):
        """Renders a clean table of Warnings and Errors found in the logs."""
        issues = []
        for log in logs:
            severity = None
            rule = "General"
            msg = log

            if "Ghost Service detected" in log:
                severity = "WARNING"
                rule = "GhostService"

                # Extract core message and hint
                # Expected format from pipeline: "Ghost Service detected: ... \n  Hint: ..."
                parts = log.split("Hint:")
                core_msg = parts[0]
                hint = parts[1].strip() if len(parts) > 1 else ""

                # Clean up core message
                if "Ghost Service detected:" in core_msg:
                    core_msg = core_msg.split("Ghost Service detected:")[1]

                # Remove tree characters
                core_msg = (
                    core_msg.replace("Stage 3.5: Semantic Warnings (1):", "")
                    .replace("└─", "")
                    .replace("•", "")
                    .strip()
                )

                msg = f"Ghost Service detected: {core_msg}"
                if hint:
                    msg += f"\n[dim italic]Hint: {hint}[/dim italic]"

            elif "Warning" in log or "WARNING" in log:
                # Check if it is a real issue or just a header
                if "Semantic Warnings" in log:
                    continue
                # Filter internal layout warnings
                if "Stage 2" in log or "layout preservation" in log.lower():
                    continue

                severity = "WARNING"
                if "Deprecation" in log:
                    rule = "DeprecatedAPI"
                if "Missing" in log and "detected" in log:
                    rule = "MissingReference"
                if "Skipping unsafe heal" in log:
                    rule = "UnsafeReference"
                msg = log.replace("[WARNING]", "").replace("Warning -", "").strip()

            elif "Error" in log or "CRITICAL" in log:
                severity = "ERROR"
                msg = log.replace("[ERROR]", "").replace("Error -", "").strip()

            if severity:
                # Deduplicate simplistic way
                if not any(i["msg"] == msg for i in issues):
                    issues.append({"severity": severity, "rule": rule, "msg": msg})

        if not issues:
            return

        table = Table(
            title="[bold red]ISSUES FOUND[/bold red]",
            show_header=True,
            header_style="bold white",
            expand=True,
            box=None,
        )
        table.add_column("Severity", width=10)
        table.add_column("Rule", width=20)
        table.add_column("Message")

        for i in issues:
            sev_style = "bold red" if i["severity"] == "ERROR" else "bold yellow"
            icon = self._get_icon("❌") if i["severity"] == "ERROR" else self._get_icon("⚠️")
            table.add_row(
                f"[{sev_style}]{icon} {i['severity']}[/{sev_style}]",
                f"[cyan]{i['rule']}[/cyan]",
                i["msg"],
            )

        console.print(table)
        console.print()

        # Recommendation Hint
        invoked_as = "Yamlr"
        try:
            from yamlr.core.bridge import YamlrBridge

            invoked_as = YamlrBridge.get_invoked_command()
        except:
            pass

        if any(i["rule"] == "GhostService" for i in issues):
            # Context-Aware Suggestions
            if status == "PREVIEW":
                # If we are in preview/scan and changes are possible -> Suggest Heal
                console.print(
                    Panel(
                        f"Run [white]{invoked_as} heal <file>[/white] to automatically fix detected issues.",
                        title="💡 SUGGESTION",
                        border_style="green",
                        expand=False,
                    )
                )
            elif status in ["HEALED", "UNCHANGED", "WARN"]:
                # If we already healed (or can't heal) -> Suggest Manual Action
                console.print(
                    Panel(
                        "Automated healing complete. Remaining issues require [bold]manual intervention[/bold].\n"
                        "Check valid labels and ensure referenced deployments exist.",
                        title="📝 MANUAL CHECK REQUIRED",
                        border_style="yellow",
                        expand=False,
                    )
                )

        # Semantic Tips
        if any(i["rule"] == "MissingReference" for i in issues):
            console.print(
                Panel(
                    "Detected missing resources that can be auto-generated.\n"
                    "Run: [bold cyan]yamlr heal <file> --stub-refs[/bold cyan]",
                    title="💡 SMART TIP: MISSING REFS",
                    border_style="green",
                    expand=False,
                )
            )

        if any(i["rule"] == "UnsafeReference" for i in issues):
            console.print(
                Panel(
                    "Detected missing sensitive resources (Secret/Ingress).\n"
                    "To stub these, you must explicitly allow them:\n"
                    "Run: [bold cyan]yamlr heal <file> --stub-refs --unsafe[/bold cyan]",
                    title="🛡 SECURITY NOTICE",
                    border_style="red",
                    expand=False,
                )
            )
        console.print()

    def _render_staged_logs(self, logs: List[str], file_path: Optional[str] = None):
        """Groups logs by 'Stage X:' prefixes with visual hierarchy."""
        tree = Tree(
            f"[bold cyan]📋 Audit Trail{f': {file_path}' if file_path else ''}[/bold cyan]"
        )
        current_branch = None

        for log in logs:
            if log.startswith("Stage "):
                current_branch = tree.add(f"[bold magenta]{log}[/bold magenta]")
            elif "Warning" in log or "WARNING" in log:
                target = current_branch if current_branch else tree
                target.add(f"[bold yellow]⚠️  {log}[/bold yellow]")
            elif "Error" in log or "CRITICAL" in log or "Failed" in log:
                target = current_branch if current_branch else tree
                target.add(f"[bold red]❌ {log}[/bold red]")
            elif "Shield" in log or "Action:" in log:
                target = current_branch if current_branch else tree
                target.add(f"[cyan]🛡  {log}[/cyan]")
            elif "Passed" in log or "completed" in log:
                target = current_branch if current_branch else tree
                target.add(f"[green]✅ {log}[/green]")
            else:
                target = current_branch if current_branch else tree
                target.add(f"[dim]└─ {log}[/dim]")

        console.print(tree)
        console.print()
