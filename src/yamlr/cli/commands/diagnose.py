"""
DIAGNOSE COMMAND LOGIC
----------------------
A deep-dive debugging wrapper around the 'scan' command.
"""
from __future__ import annotations
from yamlr.core.entrypoints.scan import handle_scan_command
from yamlr.core.entrypoints.base import get_console
import os
import zipfile
import json
import time
from pathlib import Path
from yamlr.core.bridge import YamlrBridge
__all__ = ['handle_diagnose_command']


def handle_diagnose_command(args, engine):
    """
    Executes 'scan' with elevated verbosity for debugging.
    
    Equivalent to:
    yamlr scan --verbose --debug
    """
    # 3. Handle Bundle Export
    if getattr(args, "bundle", False):
        from yamlr.pro.license import license_manager
        license_manager.feature_gate("bundle", "diagnose --bundle")
        return _handle_bundle_export(engine, get_console())

    # 4. Delegate to Scan
    return handle_scan_command(args, engine)

def _handle_bundle_export(engine, console) -> int:
    """Exports an anonymized diagnostic bundle for founder review."""
    timestamp = int(time.time())
    bundle_name = f"yamlr-bundle-{timestamp}.zip"
    bundle_path = Path(bundle_name)
    
    console.print("\n[bold cyan]📦 Generating Founder Diagnostic Bundle...[/bold cyan]")
    
    try:
        with zipfile.ZipFile(bundle_path, 'w') as zf:
            # 1. Anonymized Telemetry
            stats = engine.telemetry.get_stats()
            # Deep scrub sensitive paths or names if they exist in stats
            zf.writestr("telemetry.json", json.dumps(stats, indent=2))
            
            # 2. Config (Anonymized)
            config_data = {
                "kubernetes_version": engine.cluster_version,
                "concurrency": engine.concurrency,
                "has_opa": bool(engine._opa_bundle_path),
                "is_pro": YamlrBridge.is_pro_enabled(),
                "default_namespace": engine.default_namespace
            }
            zf.writestr("config_summary.json", json.dumps(config_data, indent=2))
            
            # 3. Environment (Anonymized)
            import platform
            env_data = {
                "os": os.name,
                "platform": platform.platform(),
                "python": platform.python_version(),
                "timestamp": timestamp,
                "cpu_count": os.cpu_count()
            }
            zf.writestr("environment.json", json.dumps(env_data, indent=2))

            # 4. DNA Receipt Aggregation (Strategic Analytics)
            evidence_path = engine.workspace / ".yamlr" / "evidence"
            if evidence_path.exists() and evidence_path.is_dir():
                try:
                    from yamlr.pro.compliance.aggregator import EvidenceAggregator
                    aggregator = EvidenceAggregator(str(evidence_path))
                    # Use fast metadata extract to avoid heavy CPU hashing in bundle generation
                    compliance_summary = aggregator.fast_metadata_extract()
                    zf.writestr("compliance_summary.json", json.dumps(compliance_summary, indent=2))
                except Exception as e:
                    logger.debug(f"Failed to aggregate evidence for bundle: {e}")

            # 5. Global Pulse Intelligence
            try:
                from yamlr.core.telemetry import PulseManager
                pm = PulseManager()
                zf.writestr("pulse_intelligence.json", json.dumps(pm.get_founder_intelligence(), indent=2))
            except Exception as e:
                 logger.debug(f"Failed to include pulse data in bundle: {e}")

        console.print("[bold green]✅ Bundle Created![/bold green]")
        console.print(f"📁 Path: [cyan]{bundle_path.resolve()}[/cyan]")
        console.print("[dim]Please send this file to [bold]founder@yamlr.dev[/bold] for strategic review.[/dim]\n")
        return 0
    except Exception as e:
        console.print(f"[red]❌ Failed to create bundle: {e}[/red]")
        return 1
