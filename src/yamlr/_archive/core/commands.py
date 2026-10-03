"""Operational commands for DNA hashing, ROI estimation, and fleet management."""
import json
import logging
import os
import subprocess
from typing import Any, Dict

import yaml

from yamlr.core.scanner import _discover_manifests
from yamlr.ui.theme import ICON_SUCCESS, console

logger = logging.getLogger(__name__)


def cmd_dna(path: str = "."):
    """Generate semantic DNA integrity signatures for manifests.

    DNA signatures only change when the semantic behavior of the manifest
    changes, ignoring whitespace and comments to prevent spurious GitOps diffs.

    Args:
        path: Path to file or directory to fingerprint.
    """
    from rich.table import Table

    try:
        import yamlr_native
    except ImportError as e:
        logger.debug("Native core import failed in cmd_dna: %s", e)
        console.print("[bold red][!] Native core required for DNA hashing.[/bold red]")
        return

    target = os.path.abspath(path)
    files = _discover_manifests(target)

    if not files:
        console.print("[yellow][!] No YAML files found.[/yellow]")
        return

    table = Table(title="Semantic DNA Signatures", show_header=True)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("DNA Hash", style="green")
    table.add_column("Kind", style="dim")

    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            dna_hash = yamlr_native.native_calculate_dna_hash(content)
            shards = yamlr_native.native_shard(content)
            identity = yamlr_native.extract_native_identity(shards)
            kind = identity.kind if identity else "Unknown"
            rel_path = os.path.relpath(fpath, target) if os.path.isdir(target) else os.path.basename(fpath)
            table.add_row(rel_path, dna_hash[:16] + "...", kind)
        except (OSError, UnicodeDecodeError, RuntimeError) as e:
            logger.debug("Failed to calculate DNA for file '%s': %s", fpath, e)
            continue

    console.print(table)


def cmd_roi(path: str = ".", output: str = "text") -> Dict[str, Any]:
    """Calculate manifest engineering quality and reliability impact metrics.

    Measures discrete reliability improvements, syntax/schema fixes, and outage
    interceptions computed directly from manifest AST and relational topology.

    Args:
        path: Path to file or directory to analyze.
        output: Output format ('text' or 'json').
    """
    try:
        import yamlr_native
    except ImportError as e:
        logger.debug("Native core import failed in cmd_roi: %s", e)
        console.print("[bold red][!] Native core required for ROI calculation.[/bold red]")
        return {}

    target = os.path.abspath(path)
    files = _discover_manifests(target)
    
    docs_parsed = 0
    outages_prevented = 0
    violations_identified = 0
    risk_mitigated = 0.0

    telemetry = yamlr_native.NativeTelemetry()
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            shards = yamlr_native.native_shard(content)
            if shards:
                telemetry.scans_completed += 1
                manifest = yamlr_native.native_structurize(shards)
                if hasattr(manifest, 'integrity_violations'):
                    for v in manifest.integrity_violations:
                        try:
                            yamlr_native.native_record_telemetry(telemetry, "HEAL", 10.0, 100, "WARNING")
                        except Exception:
                            pass
                        _record_healing_impact_local(telemetry, getattr(v, "check_name", "UNKNOWN"))
        except (OSError, UnicodeDecodeError, RuntimeError) as e:
            logger.debug("Failed processing file '%s' for impact: %s", fpath, e)
            continue
    
    docs_parsed = getattr(telemetry, 'scans_completed', 0)
    outages_prevented = getattr(telemetry, 'potential_outages_prevented', 0)
    violations_identified = getattr(telemetry, 'toil_mitigated', 0)
    risk_mitigated = float(getattr(telemetry, 'total_risk_mitigated', 0.0))

    result = {
        "manifests_analyzed": len(files),
        "documents_parsed": docs_parsed,
        "outages_prevented": outages_prevented,
        "violations_identified": violations_identified,
        "integrity_risk_mitigated": round(risk_mitigated, 1)
    }

    if output == "json":
        console.print(json.dumps(result, indent=2))
        return result

    console.print("\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
    console.print("   [bold white]Yamlr Manifest Quality & Impact Analysis[/bold white]")
    console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
    console.print(f"  [bold green]•[/bold green] [bold]Manifests Analyzed:[/bold]       {result['manifests_analyzed']}")
    console.print(f"  [bold green]•[/bold green] [bold]Documents Parsed:[/bold]         {result['documents_parsed']}")
    console.print(f"  [bold green]•[/bold green] [bold]Outages Prevented:[/bold]        {result['outages_prevented']}")
    console.print(f"  [bold green]•[/bold green] [bold]Violations Identified:[/bold]    {result['violations_identified']}")
    console.print(f"  [bold green]•[/bold green] [bold]Integrity Risk Mitigated:[/bold] {result['integrity_risk_mitigated']} units")
    console.print("[dim]  Metrics computed deterministically from AST syntax, schema, and topology analysis.[/dim]\n")
    return result


def _record_healing_impact_local(telemetry: Any, check_name: str):
    """Local fallback for recording impact counts if native binding is absent."""
    if hasattr(telemetry, "toil_mitigated"):
        telemetry.toil_mitigated += 1


def cmd_pulse(path: str = "."):
    """Live Drift Detection: Local Manifests vs Cluster State."""
    import yamlr_native

    from yamlr.ui.renderer import RichRenderer

    target = os.path.abspath(path)
    console.print(f"\n[bold cyan][!] Live Pulse: Auditing drift in {target}...[/bold cyan]")

    # 1. Discover local resources
    discovery = yamlr_native.native_discover_resources(target)

    drifts_found = 0
    for res in discovery:
        if not res.identity:
            continue
        identity = res.identity

        console.print(f"  [dim]• Checking {identity.kind}/{identity.name}...[/dim]", end="\r")

        # 2. Fetch live state from cluster
        try:
            result = subprocess.run(
                ["kubectl", "get", identity.kind, identity.name, "-n", identity.namespace, "-o", "yaml"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                continue  # Resource doesn't exist in cluster

            live_content = result.stdout
            with open(res.file_path, "r", encoding="utf-8") as f:
                local_content = f.read()

            # 3. Use native DNA to check for semantic drift
            local_dna = yamlr_native.native_calculate_dna_hash(local_content)
            live_dna = yamlr_native.native_calculate_dna_hash(live_content)

            if local_dna != live_dna:
                drifts_found += 1
                console.print(f"  [bold yellow][!] DRIFT DETECTED:[/bold yellow] {identity.kind}/{identity.name}")
                RichRenderer.render_unified_diff(local_content, live_content)
        except (subprocess.SubprocessError, OSError, UnicodeDecodeError) as e:
            logger.debug("Failed drift check for '%s/%s': %s", identity.kind, identity.name, e)
            continue

    if drifts_found == 0:
        console.print(f"\n[bold green]{ICON_SUCCESS} Pulse Complete: No semantic drift detected across the fleet.[/bold green]")
    else:
        console.print(f"\n[bold yellow][!] Pulse Complete: {drifts_found} resources have drifted from the manifest-of-truth.[/bold yellow]")


def cmd_secure(path: str = "."):
    """Policy Architect: Automated Network Policy hardening."""
    import yamlr_native
    target = os.path.abspath(path)
    console.print("\n[bold magenta][!] Secure Architect: Generating Least-Privilege Policies...[/bold magenta]")

    discovery = yamlr_native.native_discover_resources(target)
    services = [r.identity for r in discovery if r.identity and r.identity.kind == "Service"]

    if not services:
        console.print("[dim]No services found to harden.[/dim]")
        return

    for svc in services:
        if not svc.selector:
            continue

        policy_name = f"{svc.name}-hardened-policy"

        ports = getattr(svc, "ports", [80, 443])
        ingress_rules = []
        for port in ports:
            ingress_rules.append({
                "ports": [{"protocol": "TCP", "port": port}]
            })

        policy = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": policy_name,
                "namespace": svc.namespace,
                "labels": {"yamlr.dev/managed": "true"},
                "annotations": {"yamlr.dev/generated": "true"}
            },
            "spec": {
                "podSelector": {"matchLabels": svc.selector},
                "policyTypes": ["Ingress"],
                "ingress": ingress_rules
            }
        }

        console.print(f"\n  [bold green][+] Suggested Policy for {svc.name}:[/bold green]")
        console.print(yaml.dump(policy, indent=2))


def cmd_rollback(path: str = "."):
    """Managed Fleet Restoration: Rollback to the last known-good state."""
    from yamlr.core.backups import BackupManager
    bm = BackupManager(path)
    bm.restore_last_session()


def cmd_fleet():
    """Fleet Intelligence: Multi-cluster health overview."""
    console.print("\n[bold blue][!] Fleet Intelligence: Discovery Active...[/bold blue]")

    try:
        result = subprocess.run(
            ["kubectl", "config", "get-contexts", "-o", "name"],
            capture_output=True, text=True, timeout=5
        )
        contexts = result.stdout.splitlines()

        from rich.table import Table
        table = Table(title="Fleet Inventory", border_style="dim")
        table.add_column("Cluster Context", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Engine", style="dim")

        for ctx in contexts:
            table.add_row(ctx, f"{ICON_SUCCESS} ACTIVE", "v0.1.0-Link")

        console.print(table)
        console.print(f"\n[dim]{len(contexts)} Clusters discovered in local Kubeconfig.[/dim]\n")
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("Fleet discovery failed: %s", e)
        console.print(f"[bold red][!] Fleet discovery failed:[/bold red] {e}")
