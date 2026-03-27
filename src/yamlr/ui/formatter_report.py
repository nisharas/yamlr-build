from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from yamlr.models import HealFileResult, HealAction

from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from yamlr.cli.commands.base import get_console
from yamlr.ui.formatter_report_shared import get_icon_fallback, get_score_emoji
from yamlr.ui.formatter_report_base import ReportBaseMixin


__all__ = ['ReportMixin']


class ReportMixin(ReportBaseMixin):
    """
    Surgical report rendering methods for YamlrFormatter.
    [MODULARIZED] Inherits base rendering from ReportBaseMixin.
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
        return get_icon_fallback(icon)

    def display_report(self, result: HealFileResult, verbose: bool = False):
        """Renders the full surgical details for a single file."""
        try:
            status = result.status
            file_path = result.file_path

            if self._handle_early_exits(status, file_path, result):
                return

            # 1. Render Header Panel (from ReportBaseMixin)
            self._render_header_panel(result, file_path, status)

            # 2. Render Issues & Audit logs
            logs = result.logic_logs
            self._render_issues_summary(logs, status)
            if verbose and logs:
                self._render_staged_logs(logs, file_path)

            # 3. Render Findings & Deprecations
            self._render_findings_table(result.findings, status)
            self._render_resource_deprecations(result.identities, file_path)

            # 4. Render Footer (Backups & Remediation)
            self._render_remediation_footer(result, status)

            # 5. [Feature] Single-file Deprecation Summary
            if hasattr(self, "_render_deprecation_summary"):
                self._render_deprecation_summary([result])

            get_console().print("[dim]💡 Run with --verbose for full audit trail[/dim]\n")
        except Exception:
            import traceback
            traceback.print_exc()
            raise

    def _render_findings_table(self, findings: List[HealAction], status: str) -> None:
        """Renders the detailed findings table."""
        if not findings: return

        table = Table(
            title="[bold magenta]Findings[/bold magenta]",
            show_header=True, header_style="bold white",
        )
        table.add_column("Severity", width=10)
        table.add_column("Risk", width=10)
        table.add_column("Rule ID", width=30)
        table.add_column("Message")

        pro_fixable_count = 0
        quiet_mode = getattr(get_console(), "_yamlr_quiet", False)
        
        for f in findings:
            rule_id = getattr(f, "rule_id", "") if not isinstance(f, dict) else f.get("rule_id", "")
            if rule_id in self.PRO_FIXABLE_MAPPING and status != "HEALED":
                pro_fixable_count += 1
            self._add_finding_row(table, f, status)

        get_console().print(table)
        
        if pro_fixable_count > 0 and not quiet_mode:
            get_console().print(f"[bold yellow]⚠️  {pro_fixable_count} more issues are fixable with Yamlr Enterprise (Pro).[/bold yellow]")
        
        get_console().print()

    def _add_finding_row(self, table: Table, f: Union[HealAction, Dict[str, Any]], status: str) -> None:
        """Helper to format and add a single finding row."""
        def get_val(obj, key, default=None):
            if isinstance(obj, dict): return obj.get(key, default)
            return getattr(obj, key, default)

        sev = str(get_val(f, "severity", "WARNING")).upper()
        rule_id = get_val(f, "rule_id", "")
        
        icon = self._get_icon("❌") if sev == "ERROR" else self._get_icon("⚠️")
        sev_style = "bold red" if sev == "ERROR" else "bold yellow"

        msg = get_val(f, "message", "")
        rationale = get_val(f, "rationale")
        suggestion = get_val(f, "suggestion")

        full_msg = msg or ""
        if rationale:
            full_msg += f"\n[dim white]{self._get_icon('💡')} Rationale: {rationale}[/dim white]"
        if suggestion:
            full_msg += f"\n[dim italic]{self._get_icon('💡')} {suggestion}[/dim italic]"

        risk_l = str(get_val(f, "risk_level", "LOW")).upper()
        risk_style = "bold red" if risk_l == "HIGH" else "bold yellow" if risk_l == "MEDIUM" else "green"
        
        impact = get_val(f, "impact_description")
        if impact: full_msg = f"[bold white]{impact}[/bold white]\n" + full_msg

        quiet_mode = getattr(get_console(), "_yamlr_quiet", False)
        if not quiet_mode and rule_id in self.PRO_FIXABLE_MAPPING and status != "HEALED":
            pro_cmd = self.PRO_FIXABLE_MAPPING[rule_id]
            full_msg += f"\n[bold cyan]{self._get_icon('💎')} PRO: yamlr heal {pro_cmd} would fix this[/bold cyan]"

        table.add_row(
            f"[{sev_style}]{icon} {sev}[/{sev_style}]",
            f"[{risk_style}]{risk_l}[/{risk_style}]",
            f"[cyan]{rule_id}[/cyan]",
            full_msg,
        )

    def _render_resource_deprecations(self, identities: List[Dict[str, Any]], file_path: str) -> None:
        """Renders deprecation warnings."""
        found_dep = False
        for identity in identities:
            dep = identity.get("deprecation_info")
            if dep:
                found_dep = True
                self._render_deprecation_panel(identity, dep)

        if found_dep:
            get_console().print(Panel(
                f"This resource is using an API that has been removed or deprecated.\n"
                f"Run [bold cyan]yamlr migrate {file_path}[/bold cyan] to automatically upgrade it.",
                title=f"{self._get_icon('💡')} QUICK FIX", border_style="green", expand=False,
            ))

    def _render_deprecation_panel(self, identity: Dict[str, Any], dep: Dict[str, Any]) -> None:
        """Helper to render a specific deprecation warning panel."""
        deprecated = dep.get('deprecated_api', '?')
        replacement = dep.get('replacement_api', '?')
        removed = dep.get('removed_in_version', '?')
        kind = identity.get('kind')
        name = identity.get('name', 'unnamed')
        
        diff_text = f"[bold red]- apiVersion: {deprecated}[/bold red]\n"
        diff_text += f"[bold green]+ apiVersion: {replacement}[/bold green]\n"
        
        get_console().print(Panel(
            f"[bold yellow]⚠️  DEPRECATED API DETECTED[/bold yellow]\n\n"
            f"[bold]Resource:[/bold] {kind}/{name}\n"
            f"[bold]Status:[/bold] Removed in K8s {removed}\n\n"
            f"{diff_text}\n"
            f"[dim]{dep.get('migration_notes', '')}[/dim]",
            title=f"{self._get_icon('⚠️')} Deprecation Warning",
            border_style="yellow", padding=(1, 2),
        ))

    def _render_remediation_footer(self, result: Dict[str, Any], status: str) -> None:
        """Renders backup paths and remediation commands."""
        backup_path = result.get("backup_created")
        if status == "HEALED" and backup_path:
            get_console().print(f"[dim]💾 Backup: {backup_path}[/dim]")

        remediation = result.get("remediation_command")
        if remediation:
            get_console().print(Panel(
                f"To fix detected issues, run:\n[bold cyan]{remediation}[/bold cyan]",
                title=f"{self._get_icon('⚔️')} REMEDIATION", border_style="cyan", expand=False,
            ))

    def _render_issues_summary(self, logs: List[str], status: str):
        """Renders a clean table of Warnings and Errors from logs."""
        issues = self._extract_issues_from_logs(logs)
        if not issues: return

        table = Table(
            title="[bold red]ISSUES FOUND[/bold red]", show_header=True, 
            header_style="bold white", expand=True, box=None,
        )
        table.add_column("Severity", width=10)
        table.add_column("Rule", width=20)
        table.add_column("Message")

        for i in issues:
            sev_style = "bold red" if i["severity"] == "ERROR" else "bold yellow"
            icon = self._get_icon("❌") if i["severity"] == "ERROR" else self._get_icon("⚠️")
            table.add_row(f"[{sev_style}]{icon} {i['severity']}[/{sev_style}]", f"[cyan]{i['rule']}[/cyan]", i["msg"])

        get_console().print(table)
        get_console().print()
        self._render_issue_recommendations(issues, status)

    def _extract_issues_from_logs(self, logs: List[str]) -> List[Dict[str, str]]:
        issues = []
        for log in logs:
            issue = self._parse_log_line(log)
            if issue and not any(i["msg"] == issue["msg"] for i in issues):
                issues.append(issue)
        return issues

    def _parse_log_line(self, log: str) -> Optional[Dict[str, str]]:
        if "Ghost Service detected" in log: return self._parse_ghost_service_log(log)
        if "Warning" in log or "WARNING" in log:
            if any(x in log for x in ["Semantic Warnings", "Stage 2", "layout preservation"]): return None
            rule = "DeprecatedAPI" if "Deprecation" in log else "MissingReference" if "Missing" in log else "UnsafeReference" if "Skipping unsafe" in log else "General"
            return {"severity": "WARNING", "rule": rule, "msg": log.replace("[WARNING]", "").strip()}
        if "Error" in log or "CRITICAL" in log:
            return {"severity": "ERROR", "rule": "General", "msg": log.replace("[ERROR]", "").strip()}
        return None

    def _parse_ghost_service_log(self, log: str) -> Dict[str, str]:
        msg = f"Ghost Service detected: {log.split('Hint:')[0].replace('Ghost Service detected:', '').strip()}"
        if "Hint:" in log: msg += f"\n[dim italic]Hint: {log.split('Hint:')[1].strip()}[/dim italic]"
        return {"severity": "WARNING", "rule": "GhostService", "msg": msg}

    def _render_issue_recommendations(self, issues: List[Dict[str, str]], status: str) -> None:
        """Renders context-aware suggestion panels."""
        if any(i["rule"] == "GhostService" for i in issues):
            self._render_ghost_service_suggestion(status)
        if any(i["rule"] == "MissingReference" for i in issues):
            get_console().print(Panel("Detected missing resources. Run: [bold cyan]yamlr heal <file> --stub-refs[/bold cyan]", title="💡 SMART TIP", border_style="green", expand=False))
        if any(i["rule"] == "UnsafeReference" for i in issues):
            get_console().print(Panel("Detected sensitive missing resources. Run: [bold cyan]yamlr heal <file> --stub-refs --unsafe[/bold cyan]", title="🛡 SECURITY NOTICE", border_style="red", expand=False))

    def _render_ghost_service_suggestion(self, status: str) -> None:
        msg = "Run [white]yamlr heal <file>[/white] to fix." if status == "PREVIEW" else "Manual intervention required."
        get_console().print(Panel(msg, title="💡 SUGGESTION", border_style="green" if status == "PREVIEW" else "yellow", expand=False))

    def _render_staged_logs(self, logs: List[str], file_path: Optional[str] = None):
        """Groups logs by 'Stage X:' prefixes with visual hierarchy."""
        tree = Tree(f"[bold cyan]📋 Audit Trail{f': {file_path}' if file_path else ''}[/bold cyan]")
        current_branch = None
        for log in logs:
            if log.startswith("Stage "): current_branch = tree.add(f"[bold magenta]{log}[/bold magenta]")
            else:
                target = current_branch or tree
                if "Warning" in log: target.add(f"[bold yellow]⚠️  {log}[/bold yellow]")
                elif any(x in log for x in ["Error", "CRITICAL"]): target.add(f"[bold red]❌ {log}[/bold red]")
                elif "Shield" in log: target.add(f"[cyan]🛡  {log}[/cyan]")
                elif "Passed" in log: target.add(f"[green]✅ {log}[/green]")
                else: target.add(f"[dim]└─ {log}[/dim]")
        get_console().print(tree)
        get_console().print()
