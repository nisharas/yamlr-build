"""
Yamlr ADVISORY ENGINE
---------------------
Decouples rich UI, rendering, and strategic advice from core logic.

Why: To separate data-processing (scanning/healing) from presentation,
     enabling better testability and programmatic usage of findings.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, List

from pydantic import BaseModel, Field
from rich.panel import Panel

from yamlr.core.gatekeeper import ProGate

if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine
    from yamlr.core.scoring import AppSafetyReport
    from yamlr.models import HealFileResult

logger = logging.getLogger("yamlr.advisory")


class AdvisoryData(BaseModel):
    """Structured container for scan/heal findings and ROI metrics."""

    results: List[Any] = Field(default_factory=list)  # HealFileResult
    duration: float = 0.0
    is_pro: bool = False
    is_dry_run: bool = True
    workspace_root: str = "."
    license_tier: str = "OSS"
    summary_only: bool = False
    verbose: bool = False
    pro_preview: bool = False

    class Config:
        arbitrary_types_allowed = True


class AdvisoryRenderer:
    """Orchestrates the visual presentation of Yamlr findings."""

    def __init__(self, console):
        self.console = console

    def render_scan_report(self, data: AdvisoryData, args: Any):
        """Renders the main scan/audit report."""
        job_results = data.results

        if data.pro_preview:
            self.console.print(
                Panel(
                    f"[bold gold1]{ProGate.get_pro_title('preview')}[/bold gold1]\n"
                    "[dim]Simulating Enterprise healing depth. Manifests will NOT be modified.[/dim]",
                    border_style="gold1",
                    expand=False,
                )
            )
        if len(job_results) == 1:
            result = job_results[0]
            # [QA-12-10] Use centralized formatter for consistency
            from yamlr.ui.formatter import YamlrFormatter

            YamlrFormatter().display_report(result, verbose=data.verbose)

            if getattr(args, "diff", False):
                self._render_single_diff(result)
        else:
            from yamlr.ui.formatter import YamlrFormatter

            YamlrFormatter().print_final_table(job_results, show_summary=True, compact=getattr(args, "quiet", False))

        # 2. Render Conversion Surface (if not Pro)
        from yamlr.core.bridge import YamlrBridge

        if not YamlrBridge.is_pro_enabled() and job_results:
            try:
                # Use the first result as a representative for the DNA score advisory
                representative_result = job_results[0]
                score_val = int(getattr(representative_result, "dna_integrity_score", 100))
            except (TypeError, ValueError):
                score_val = 100

            if score_val < 70:
                self.render_safety_score_advisory(score_val)

        # 3. Render Pro Preview (Dopamine Drip)
        if data.pro_preview:
            self.render_pro_preview(job_results)

        # 4. Render Reconciliation Summary [TASK-24-3]
        reconciled_total = sum(getattr(r, "reconciled_count", 0) for r in job_results)
        if reconciled_total > 0:
            self.render_reconciliation_panel(reconciled_total, len(job_results))

    def _render_single_diff(self, result: "HealFileResult"):
        from yamlr.ui.diff import DiffEngine

        raw = getattr(result, "raw_content", "")
        healed = getattr(result, "healed_content", "")
        if healed and raw != healed:
            DiffEngine.render_diff(raw, healed, getattr(result, "file_path", "Unknown"))

    def _render_batch_diffs(self, results: List["HealFileResult"]):
        from yamlr.ui.diff import DiffEngine

        changed_jobs = [
            j
            for j in results
            if getattr(j, "healed_content", None) and getattr(j, "raw_content", "") != getattr(j, "healed_content", "")
        ]
        if changed_jobs:
            self.console.print(f"\n[bold yellow]Found {len(changed_jobs)} files with proposed repairs:[/bold yellow]")
            for job in changed_jobs:
                DiffEngine.render_diff(
                    getattr(job, "raw_content", "") or "",
                    getattr(job, "healed_content", "") or "",
                    getattr(job, "file_path", "Unknown"),
                )

    def render_pro_preview(self, results: List["HealFileResult"]):
        """Renders colorized 'Before -> After' diffs for simulated Pro fixes.

        Why: To create the 'Dopamine Drip' conversion experience by showing
             users the exact surgical repairs they would get with Yamlr Pro.
        """
        pro_jobs = [
            j for j in results if getattr(j, "pro_features_triggered", False) and getattr(j, "healed_content", None)
        ]

        if not pro_jobs:
            self.console.print("\n[dim]No high-gravity Pro repairs were identified in this preview run.[/dim]")
            return

        self.console.print(f"\n[bold gold1]{ProGate.get_pro_title('repairs')} ({len(pro_jobs)} files):[/bold gold1]")
        from yamlr.ui.diff import DiffEngine

        for job in pro_jobs:
            # Highlight the Pro advantage
            self.console.print(
                Panel(
                    f"[bold cyan]Yamlr Pro Feature:[/bold cyan] {self._infer_pro_value_prop(job)}",
                    border_style="gold1",
                    padding=(0, 1),
                )
            )
            DiffEngine.render_diff(
                getattr(job, "raw_content", "") or "",
                getattr(job, "healed_content", "") or "",
                getattr(job, "file_path", "Unknown"),
            )

    def _infer_pro_value_prop(self, job: "HealFileResult") -> str:
        """Infers the most relevant Pro value proposition for a given result."""
        findings = getattr(job, "findings", [])
        if any(f.get("analyzer") == "cross-resource" for f in findings):
            return "Cross-Resource Auto-Repair (Relational Surgery)"
        if any(f.get("severity") == "critical" for f in findings):
            return "Enterprise Security Hardening (--harden)"
        return "Advanced Schema Optimization & DNA Integrity"

    def render_safety_score_advisory(self, score: Any):
        """Renders a conversion-focused panel for high-gravity issues based on safety score."""
        try:
            score_val = int(score)
        except (TypeError, ValueError):
            score_val = 0

        if score_val < 40:
            color = "red"
        elif score_val < 70:
            color = "yellow"
        else:
            color = "green"

        self.console.print(
            Panel(
                f"[bold {color}]High-Gravity Performance & Security Gap Detected[/bold {color}]\n"
                f"Your DNA Integrity Score of [bold]{score_val}/100[/bold] indicates significant technical debt.\n\n"
                f"Yamlr Enterprise (Pro) provides automated surgery for these issues.",
                title=ProGate.get_pro_title("advisory"),
                border_style=color,
            )
        )

    def render_api_upgrade_advisory(self, engine: Any, results: List[Any]):
        """Renders a dashboard showing identified API deprecations and available upgrades."""
        # This is where we show "K8s 1.25 -> 1.28 migration available"
        deprecated = [r for r in results if getattr(r, "deprecations_found", False)]
        if not deprecated:
            return

        self.console.print(
            Panel(
                f"[bold yellow]🚀 API Upgrade Path Identified[/bold yellow]\n"
                f"Found [cyan]{len(deprecated)}[/cyan] manifests using deprecated or removed K8s APIs.\n\n"
                f"Run [bold green]yamlr upgrade --to {engine.cluster_version}[/bold green] to automatically align these resources.",
                title="UPGRADE ADVISORY",
                border_style="yellow",
                expand=False,
            )
        )

    def render_pro_cta(self):
        """Displays call-to-action for Enterprise features."""
        self.console.print("\n")
        self.console.print(
            Panel(
                "[bold white]This run was a 💎 PRO PREVIEW simulation.[/bold white]\n"
                "None of the changes above were written to disk.\n\n"
                "To unlock these Enterprise security and compliance features for real: \n"
                "▶ [cyan bold]https://yamlr.dev/pro[/cyan bold]",
                title="[bold red]Unlock Yamlr Enterprise (Pro)[/bold red]",
                border_style="red",
                expand=False,
            )
        )

    def render_trial_usage(self, is_pro: bool):
        """Displays trial consumption metrics."""
        if not is_pro:
            return

        from yamlr.core.bridge import ProStatus, YamlrBridge

        pro_license = YamlrBridge.get_license_module()
        status, _ = YamlrBridge.check_pro_status()

        if pro_license and status == ProStatus.TRIAL_ACTIVE and hasattr(pro_license, "get_usage_summary"):
            try:
                summary = pro_license.get_usage_summary()
                high_usage = [
                    f"{f.replace('_', ' ').title()}: {d['used']}/{d['limit']}"
                    for f, d in summary.items()
                    if d["percentage"] >= 80
                ]

                if high_usage:
                    self.console.print("\n[yellow]⚠️  Trial Usage Alert:[/yellow]")
                    for feat in high_usage:
                        self.console.print(f"  {feat}")

                if any(d["percentage"] >= 100 for d in summary.values()):
                    self.console.print(
                        Panel(
                            "[bold yellow]🎉 Trial Limit Reached![/bold yellow]\n\n"
                            "Upgrade now for unlimited features:\n"
                            "  • [cyan]https://yamlr.dev/upgrade[/cyan]",
                            border_style="yellow",
                            expand=False,
                        )
                    )
            except Exception as e:
                logger.debug(f"Failed to render trial usage: {e}")

    def render_heal_results(self, data: AdvisoryData, engine: "YamlrEngine"):
        """Renders final heal summary, aggregate tables, and Enterprise CTAs."""
        job_results = data.results
        if data.is_dry_run:
            self._render_dry_run_summary(job_results, engine, data.verbose)

        # [TASK-24-3] Reconciliation Summary
        reconciled_total = sum(getattr(r, "reconciled_count", 0) for r in job_results)
        if reconciled_total > 0:
            self.render_reconciliation_panel(reconciled_total, len(job_results))

        # Trial/CTA
        self.render_trial_usage(data.is_pro)

        # Pro Preview CTA
        if data.is_dry_run or data.pro_preview:
            self._render_pro_preview_cta(job_results, data.pro_preview)

    def _render_dry_run_summary(self, job_results: List[Any], engine: "YamlrEngine", verbose: bool):
        changed = [
            j
            for j in job_results
            if getattr(j, "healed_content", None) and getattr(j, "raw_content", "") != getattr(j, "healed_content", "")
        ]
        if not changed:
            if not verbose:
                self.console.print("[green]All files are healthy! No changes needed.[/green]")
        else:
            from yamlr.ui.formatter import YamlrFormatter

            YamlrFormatter().print_final_table(
                job_results, summary_only=True, telemetry_data=engine.telemetry.get_stats()
            )
            self.console.print(f"\n[bold yellow]Dry Run: Found {len(changed)} files to heal.[/bold yellow]")

    def _render_pro_preview_cta(self, job_results: List[Any], pro_preview: bool):
        pro_triggered = any(getattr(r, "pro_features_triggered", False) for r in job_results)
        if pro_triggered or pro_preview:
            if pro_triggered:
                self.render_pro_preview(job_results)
            self.render_pro_cta()

    def render_json_results(self, all_results: List["HealFileResult"], is_dry: bool):
        """Generates a structured JSON summary of healing actions.

        Why: To support programmatic review of repair outcomes in
             automation scripts and custom dashboards.
        """
        import json

        output = {
            "summary": {
                "total_files": len(all_results),
                "healed": sum(
                    1
                    for r in all_results
                    if getattr(r, "status", "") in ("HEALED", "MODIFIED")
                    or (getattr(r, "actions", None) and len(r.actions) > 0)
                ),
                "mode": "dry-run" if is_dry else "live",
            },
            "results": [],
        }

        for r in all_results:
            output["results"].append(
                {
                    "file": getattr(r, "file_path", "Unknown"),
                    "status": getattr(r, "status", "Unknown"),
                    "findings": [f.message for f in getattr(r, "findings", [])] if hasattr(r, "findings") else [],
                    "repairs": getattr(r, "logic_logs", []),
                }
            )
        sys.stdout.write(json.dumps(output, indent=2) + "\n")

    def render_sarif_results(self, all_results: List["HealFileResult"]):
        """Generates a standardized SARIF v2.1.0 report for CI security integration."""
        from yamlr.ui.reporters import SARIFReporter

        duration = getattr(self, "_last_duration", 0.0)
        report = SARIFReporter().format(all_results, timing={"total_seconds": duration})
        sys.stdout.write(report + "\n")

    def render_next_steps(self, command: str, results: List["HealFileResult"]):
        """Suggests the next logical CLI command based on current findings."""
        if command == "scan":
            fixable = sum(
                1
                for r in results
                if getattr(r, "healed_content", None)
                and getattr(r, "raw_content", "") != getattr(r, "healed_content", "")
            )
            if fixable > 0:
                self.console.print(
                    f"\n[bold cyan]💡 Next Step:[/bold cyan] Run [bold green]yamlr heal .[/bold green] to apply {fixable} repairs."
                )
        elif command == "heal":
            healed = sum(1 for r in results if getattr(r, "status", "") in ("HEALED", "MODIFIED"))
            if healed > 0:
                self.console.print(
                    "\n[bold cyan]💡 Next Step:[/bold cyan] Run [bold green]yamlr status .[/bold green] to verify your repository's health."
                )

    def render_app_stats(self, report: "AppSafetyReport"):
        """Displays per-application safety scores with top categories and rules.

        Why: To provide the 'Why' behind the score in an explainable,
             terminal-first visualization.
        """
        if not report.apps:
            self.console.print("\n[dim]No application-level entities identified in this scan.[/dim]")
            return

        self.console.print(
            f"\n[bold cyan]📊 Application Safety Summary (Scoring v{report.scoring_version})[/bold cyan]"
        )

        for app in report.apps:
            if app.score < 50:
                score_color = "red"
            elif app.score < 80:
                score_color = "yellow"
            else:
                score_color = "green"

            # Category display with colors
            cat_list = [f"[bold yellow]{c}[/bold yellow]" for c in app.top_categories]
            cat_str = ", ".join(cat_list)

            rule_list = [f"[dim]{r}[/dim]" for r in app.top_rules]
            rule_str = ", ".join(rule_list)

            panel_content = (
                f"[bold]App ID:[/bold] {app.app_name}\n"
                f"[bold]Status:[/bold] [{score_color}]{app.score:.1f}/100[/{score_color}]\n"
                f"[bold]Top Issues:[/bold] {cat_str if cat_str else '[dim]None[/dim]'}\n"
                f"[bold]Top Rules:[/bold] {rule_str if rule_str else '[dim]None[/dim]'}"
            )

            self.console.print(Panel(panel_content, border_style=score_color, expand=False, padding=(0, 1)))

        self.console.print(f"\n[bold]Total Apps Scanned:[/bold] {len(report.apps)}")
        self.console.print(f"[bold]Overall Fleet Safety:[/bold] [bold cyan]{report.overall_score:.1f}/100[/bold cyan]")

    def render_reconciliation_panel(self, reconciled_count: int, file_count: int):
        """Displays a high-fidelity summary of findings reconciled from external tools."""
        self.console.print(
            Panel(
                f"Successfully reconciled [bold magenta]{reconciled_count}[/bold magenta] findings from external policy engines\n"
                f"across [bold]{file_count}[/bold] involved manifests. [dim](Complement Mode Active)[/dim]\n\n"
                f"[bold green]✓ Integrated auto-healing mapped and verified.[/bold green]",
                title="[bold magenta]🔌 Reconciliation Report[/bold magenta]",
                border_style="magenta",
                expand=False,
            )
        )


class GitHubAdvisoryRenderer:
    """
    Generates a high-fidelity Markdown report for GitHub PR comments.

    Why: To provide a 'Visual UI' experience within the PR context,
         making findings and repairs immediately actionable for developers.
    """

    def render_comment(self, results: List[HealFileResult], is_dry_run: bool = True) -> str:
        """
        Orchestrates the Markdown generation for a PR comment.
        """
        total_files = len(results)
        fixable = [r for r in results if r.findings]
        healed = [r for r in results if r.status in ("HEALED", "MODIFIED") or (hasattr(r, "written") and r.written)]

        status_emoji = "✅" if not fixable else "⚠️"
        title = "Yamlr Scan Report" if is_dry_run else "Yamlr Healing Report"

        lines = [
            f"## {status_emoji} {title}",
            "",
            f"Yamlr has completed its surgical audit of **{total_files}** manifests.",
            "",
        ]

        # 1. Summary Stats
        lines.extend(self._render_summary(total_files, len(fixable), len(healed), is_dry_run))

        # 2. Detailed Findings (Collapsible)
        if fixable:
            lines.extend(self._render_findings(fixable))

        # 3. Footer / CTA
        lines.append("---")
        lines.append("[Yamlr](https://yamlr.dev) — The Autonomous Manifest Control Plane")

        return "\n".join(lines)

    def _render_summary(self, total: int, issues: int, healed: int, is_dry: bool) -> List[str]:
        lines = [
            "| Metric | Status |",
            "| :--- | :--- |",
            f"| **Files Scanned** | {total} |",
            f"| **Issues Detected** | {issues} |",
        ]
        if not is_dry:
            lines.append(f"| **Auto-Healed** | {healed} |")
        lines.append("")
        return lines

    def _render_findings(self, fixable: List[HealFileResult]) -> List[str]:
        lines = ["### 🔍 Finding Details", "<details>", "<summary>Click to view anatomical findings</summary>", ""]

        for res in fixable[:50]:  # Limit to 50 for safety
            lines.append(f"#### 📄 `{res.file_path}` ({res.kind})")
            for f in res.findings:
                severity_badge = self._get_severity_badge(f.get("severity", "info"))
                lines.append(f"- {severity_badge} **{f.get('rule_id', 'General')}**: {f.get('message')}")
                if f.get("rationale"):
                    lines.append(f"  - *Rationale*: {f.get('rationale')}")
            lines.append("")

        if len(fixable) > 50:
            lines.append(f"*...and {len(fixable) - 50} more files. Download the full SARIF report for details.*")

        lines.extend(["</details>", ""])
        return lines

    def _get_severity_badge(self, severity: str) -> str:
        """Maps severity to an appropriate GitHub badge/emoji."""
        badges = {
            "critical": "🔴 **CRITICAL**",
            "error": "❌ **ERROR**",
            "warning": "⚠️ **WARNING**",
            "info": "ℹ️ **INFO**",
            "success": "✅ **SUCCESS**",
        }
        return badges.get((severity or "").lower(), "⚪ **NOTICE**")
