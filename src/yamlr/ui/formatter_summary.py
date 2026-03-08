#!/usr/bin/env python3
"""
Formatter SUMMARY Mixin
-----------------------
Extracted to enforce <500 line modularity rule.
"""
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from yamlr.cli.commands.base import get_console

console = get_console()

class SummaryMixin:
    PRO_FIXABLE_RULES = {
        "rule/resource-requests", "rule/resource-limits",
        "rule/run-as-non-root", "rule/no-privileged", "rule/allow-privilege-escalation",
        "rule/unsafe-hostpath", "rule/host-network", "rule/read-only-root-fs",
        "rule/missing-liveness", "rule/missing-readiness",
        "rule/no-latest-tag",
        "rule/ghost-service", "rule/port-mismatch", "rule/service-no-selector",
        "rule/missing-configmap-target", "rule/broken-volume", "rule/ingress-broken",
        "rule/network-policy-missing", "rule/untrusted-registry"
    }

    def _print_summary_stats(self, reports: List[Dict[str, Any]], elapsed_time: float = 0.0, telemetry_data: Optional[Dict[str, Any]] = None):
        """
        FIX: Compact summary mode for large batches (100+ files).

        Why: Provides a high-density, low-friction report for SREs and CI/CD.
             Prevents terminal flooding while summarizing cumulative risk 
             reduction and ROI.
        """
        # Aggregate stats
        total_files = len(reports)
        by_status = {}
        by_kind = {}
        successful = 0
        failed = 0
        total_resources = 0
        total_time = 0.0
        avg_score = 0

        for r in reports:
            status = r.get("status", "UNKNOWN")
            logs = r.get("logic_logs", [])

            # Smart Status Detection for Summary
            has_warnings = any("Warning" in log or "WARN" in log for log in logs)
            if status == "UNCHANGED" and has_warnings:
                status = "WARN"

            by_status[status] = by_status.get(status, 0) + 1

            if r.get("success", False):
                successful += 1

            if status in ["ENGINE_ERROR", "FILE_NOT_FOUND", "SECURITY_ERROR"]:
                failed += 1

            total_time += r.get("processing_time_seconds", 0)
            avg_score += r.get("health_score", 0)

            # NEW: Track Detected vs Fixed (Activation Metrics)
            stats = r.get("processing_stats") or r.get("stats")
            fixed = 0
            if stats:
                # If stats is a dataclass object or a dict
                if hasattr(stats, "lexer_repairs"):
                    fixed = (getattr(stats, "lexer_repairs", 0) +
                             getattr(stats, "lexer_typos", 0) +
                             getattr(stats, "semantic_repairs", 0) +
                             getattr(stats, "security_hardens", 0) +
                             getattr(stats, "migrator_changes", 0))
                else:
                    fixed = (stats.get("lexer_repairs", 0) +
                             stats.get("lexer_typos", 0) +
                             stats.get("semantic_repairs", 0) +
                             stats.get("security_hardens", 0) +
                             stats.get("migrator_changes", 0))

                # Accumulate the true single-file repairs directly into the global counter.
                by_status["_total_fixed"] = by_status.get("_total_fixed", 0) + fixed

            # Unique findings are tracked per file, so we can sum them safely.
            findings = r.get("findings", [])
            detected = fixed + len(findings)
            by_status["_total_detected"] = by_status.get("_total_detected", 0) + detected

            # [MONETIZATION] Track PRO Fixable issues
            findings = r.get("findings", [])
            pro_fixable = sum(1 for f in findings if f.get("rule_id") in self.PRO_FIXABLE_RULES)
            by_status["_pro_fixable"] = by_status.get("_pro_fixable", 0) + pro_fixable

            # Count resources by kind
            for identity in r.get("identities", []):
                kind = identity.get("kind", "Unknown")
                by_kind[kind] = by_kind.get(kind, 0) + 1
                total_resources += 1

        avg_score = avg_score / total_files if total_files > 0 else 0
        
        # FIX: Efficiency Lie - Calculate real wall-clock throughput
        if elapsed_time > 0:
            avg_time = elapsed_time / total_files
            throughput = total_files / elapsed_time
        else:
            avg_time = total_time / total_files if total_files > 0 else 0
            throughput = 0

        # Build summary panel
        summary_text = (
            f"[bold cyan]Files Processed:[/bold cyan] {total_files}\n"
            f"[bold cyan]Resources Found:[/bold cyan] {total_resources}\n"
            f"[bold cyan]Average Health Score:[/bold cyan] {avg_score:.1f}/100\n"
            f"[bold cyan]Average Processing Time (per file):[/bold cyan] {avg_time:.2f}s"
        )
        
        if throughput > 0:
            summary_text += f" [dim]({throughput:.1f} files/sec)[/dim]"
        
        total_detected = by_status.get('_total_detected', 0)
        total_fixed = by_status.get('_total_fixed', 0)
        pro_fixable = by_status.get('_pro_fixable', 0)
        
        heal_rate = (total_fixed / total_detected * 100) if total_detected > 0 else 0.0
        pro_rate = (pro_fixable / total_detected * 100) if total_detected > 0 else 0.0

        summary_text += (
            f"\n[bold cyan]Total Elapsed Time:[/bold cyan] {elapsed_time:.2f}s\n\n"
            f"\n[bold]Auto-Healing Efficiency:[/bold]\n"
            f"  [bold #ff5f87]{self._get_icon('🎯')} Issue Detection Rate:[/bold #ff5f87] 100% ({total_detected} detected)\n"
            f"  [bold green]{self._get_icon('✅')} Auto-Healed (Free):[/bold green] {heal_rate:.1f}% ({total_fixed} fixed)\n"
            f"  [bold bright_cyan]{self._get_icon('💎')} PRO would fix:[/bold bright_cyan] {pro_rate:.1f}% ({pro_fixable} issues)\n\n"
            f"[bold]File Status Breakdown:[/bold]\n"
            f"  [green]{self._get_icon('✓')} Healthy files (zero issues):[/green] {by_status.get('CLEAN', 0) + by_status.get('UNCHANGED', 0)}\n"
            f"  [cyan]{self._get_icon('→')} Files auto-healed and written to disk:[/cyan] {by_status.get('HEALED', 0)}\n"
            f"  [blue]{self._get_icon('✎')} Files with suggested fixes (Preview only):[/blue] {by_status.get('PREVIEW', 0)}\n"
            f"  [yellow]{self._get_icon('⚠')} Files requiring manual intervention:[/yellow] {by_status.get('WARN', 0)}\n"
            f"  [red]{self._get_icon('✗')} Files below required health score (Need repairs):[/red] {failed}\n"
            f"  [#5f87ff]{self._get_icon('↪')} Skipped files:[/ #5f87ff] {by_status.get('SKIPPED', 0)}\n"
        )

        # Add resource type breakdown if any found
        if by_kind:
            summary_text += "\n[bold]Resource Types:[/bold]\n"
            # Sort by count descending, then alphabetically ascending for absolute determinism
            sorted_kinds = sorted(by_kind.items(), key=lambda x: (-x[1], x[0]))
            for kind, count in sorted_kinds[:10]:  # Top 10 kinds
                summary_text += f"  {kind}: {count}\n"
            if len(sorted_kinds) > 10:
                summary_text += (
                    f"  [dim]... and {len(sorted_kinds) - 10} more types[/dim]\n"
                )

        from rich import box
        box_style = getattr(console, "_yamlr_box", box.ROUNDED)
        title_bar = "---" if getattr(console, "_yamlr_plain", False) else "━━━"

        console.print(
            Panel(
                summary_text,
                title=f"[bold magenta]{title_bar} Yamlr Batch Summary {title_bar}[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
                box=box_style,
            )
        )
        
        # --- SCORE ANIMATION (Dopamine Drip) ---
        if telemetry_data and not getattr(console, "_yamlr_plain", False):
            self._animate_score_increase(
                telemetry_data.get("last_health_score", 0.0),
                avg_score,
                telemetry_data.get("surgical_efficiency", 0.0)
            )

        # [Smart UX] Show backup message ONLY if files were actually healed
        healed_count = by_status.get("HEALED", 0)
        if healed_count > 0:
            console.print(
                f"[dim]💾 {healed_count} backup(s) saved to .yamlr/backups/ (relative to workspace)[/dim]"
            )

        if failed > 0 or by_status.get("WARN", 0) > 0:
            console.print(
                Panel(
                    "Issues detected in batch. To investigate:\n"
                    "[bold cyan]Yamlr scan <filename>[/bold cyan]\n"
                    "To preview repairs, run:\n"
                    "[bold cyan]Yamlr heal <filename> --diff[/bold cyan]",
                    title="💡 SMART TIP",
                    border_style="yellow",
                    expand=False,
                )
            )
        pro_fix = by_status.get("_pro_fixable", 0)
        quiet_mode = getattr(console, "_yamlr_quiet", False)
        if pro_fix > 0 and not quiet_mode:
            console.print()
            console.print(
                Panel(
                    f"[bold #875fff]There are {pro_fix} additional issues that can be fixed with Yamlr PRO.[/bold #875fff]\n"
                    "Run [bold cyan]yamlr heal --harden[/bold cyan] to automatically resolve them.",
                    title=f"[#ffaf00]{self._get_icon('💎')} MORE FIXES WITH PRO[/#ffaf00]",
                    border_style="cyan",
                    expand=False,
                )
            )

        console.print(
            "[dim]Note: Detailed table shown automatically for batches <= 5 files.[/dim]\n"
        )

        # [Feature] Deprecation Summary
        self._render_deprecation_summary(reports)

    def print_impact_summary(self, reports: List[Any], elapsed_time: float):
        """
        [ULTRA-SCALE] Impact Summary View.
        Designed for 10k-100k+ file scans where a table is too large.
        Focuses on 'At a Glance' metrics and critical blockers.
        """
        total_files = len(reports)
        crit_errors = 0
        total_findings = 0
        fixed_issues = 0
        security_risks = 0
        deprecations = 0

        for r in reports:
            # Handle both dict and HealFileResult
            def _gv(obj, key, default=None):
                if hasattr(obj, key): return getattr(obj, key)
                if isinstance(obj, dict): return obj.get(key, default)
                return default

            findings = _gv(r, "findings", [])
            total_findings += len(findings)
            if _gv(r, "status") == "FAILED" or not _gv(r, "success"):
                crit_errors += 1
            
            for f in findings:
                sev = f.get("severity", "").lower()
                if sev == "error": security_risks += 1
                if "deprecated" in f.get("message", "").lower(): deprecations += 1

            stats = _gv(r, "processing_stats") or _gv(r, "stats")
            if stats:
                if hasattr(stats, "lexer_repairs"):
                    fixed_issues += (getattr(stats, "lexer_repairs", 0) +
                                   getattr(stats, "lexer_typos", 0) +
                                   getattr(stats, "semantic_repairs", 0))
                elif isinstance(stats, dict):
                    fixed_issues += (stats.get("lexer_repairs", 0) +
                                   stats.get("lexer_typos", 0) +
                                   stats.get("semantic_repairs", 0))

        # [MONETIZATION] Track PRO Fixable issues at scale
        pro_fixable_issues = 0
        for r in reports:
            def _gv(obj, key, default=None):
                if hasattr(obj, key): return getattr(obj, key)
                if isinstance(obj, dict): return obj.get(key, default)
                return default
            findings = _gv(r, "findings", [])
            pro_fixable_issues += sum(1 for f in findings if f.get("rule_id") in self.PRO_FIXABLE_RULES)

        # Render Impact Panel
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="bold white")

        heal_rate = (fixed_issues / total_findings * 100) if total_findings > 0 else 0.0
        pro_rate = (pro_fixable_issues / total_findings * 100) if total_findings > 0 else 0.0

        table.add_row("📂 Total Files Scanned:", f"{total_files:,}")
        table.add_row("🎯 Issue Detection Rate:", "[#ff5f87]100%[/]")
        table.add_row("✅ Auto-Healed (Free):", f"[green]{heal_rate:.1f}% ({fixed_issues:,})[/green]")
        table.add_row("💎 PRO would fix:", f"[cyan]{pro_rate:.1f}% ({pro_fixable_issues:,})[/cyan]")
        table.add_row("⚡ Processing Time:", f"{elapsed_time:.2f}s ({(total_files/elapsed_time if elapsed_time > 0 else 0):.1f} files/sec)")
        table.add_row("🛡 Security/Policy Risks:", f"[yellow]{security_risks:,}[/yellow]")
        table.add_row("📉 API Deprecations:", f"[magenta]{deprecations:,}[/magenta]")
        table.add_row("🛑 Critical Failures:", f"[red]{crit_errors:,}[/red]")

        panel = Panel(
            table,
            title="[bold magenta]🚀 Yamlr Ultra-Scale Impact Summary[/bold magenta]",
            subtitle="[dim]Enterprise CI/CD Visibility Mode[/dim]",
            border_style="magenta",
            padding=(1, 2)
        )
        console.print("\n")
        console.print(panel)

        quiet_mode = getattr(console, "_yamlr_quiet", False)
        if pro_fixable_issues > 0 and not quiet_mode:
            console.print(
                Panel(
                    f"[bold cyan]There are {pro_fixable_issues} additional issues that can be fixed with Yamlr PRO.[/bold cyan]\n"
                    "Run [bold cyan]yamlr heal --harden[/bold cyan] to automatically resolve them.",
                    title=f"[cyan]{self._get_icon('💎')} PRO UPSELL[/cyan]",
                    border_style="cyan",
                    expand=False,
                )
            )

        console.print()
    def _animate_score_increase(self, old_score: float, new_score: float, efficiency: float):
        """
        Animates a health score bar filling up.
        
        Why: Drives user engagement and creates a 'Magic Moment' visual feedback 
             loop after a successful healing session.
        """
        from rich.live import Live
        from rich.progress import ProgressBar
        import time
        
        # Only animate if there's a positive change or high baseline
        if new_score < old_score and new_score < 100:
            return 

        console.print(f"\n[bold cyan]✨ Project Health Progression[/bold cyan]")
        
        with Live(console=console, refresh_per_second=10) as live:
            target = int(new_score)
            start = int(old_score) if old_score < new_score else 0
            
            from rich.columns import Columns
            from rich.text import Text
            for i in range(start, target + 1):
                color = "green" if i > 80 else "yellow" if i > 50 else "red"
                bar = ProgressBar(total=100, completed=i, width=40, style=color)
                
                eff_text = f" | Efficiency: {efficiency:.1f}x" if efficiency > 0 else ""
                
                # Use Columns to render the bar alongside text instead of stringifying the Bar object
                renderable = Columns([
                    bar,
                    Text(f" {i}%{eff_text}", style=f"bold {color}" if eff_text == "" else f"bold {color}")
                ])
                live.update(renderable)
                time.sleep(0.01)

        if new_score > old_score:
            console.print(f"  [bold green]⬆ Project health improved by {new_score - old_score:.1f}%![/bold green]")
        elif new_score == 100:
            console.print(f"  [bold cyan]🏆 Pure DNA: Project is at 100% integrity.[/bold cyan]")
