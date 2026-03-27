"""
Yamlr CLI: Doctor Command Handler
---------------------------------
Performs a brutally fast, deterministic health check of the local environment.

Why: To provide a single "Marquee" diagnostic flow that builds trust and simplifies troubleshooting.
"""
from __future__ import annotations
import platform
import sys
from rich.table import Table
from yamlr.core.bridge import YamlrBridge
from yamlr.core.k8s_versions import MATRIX
import hashlib
import datetime


def handle_doctor_command(args, engine, console):
    """
    Executes the 'doctor' health check.
    """
    console.print("\n[bold]🩺 Yamlr Doctor - System Health Check[/bold]\n")
    
    table = Table(box=None, padding=(0, 2))
    table.add_column("COMPONENT", style="cyan", no_wrap=True)
    table.add_column("STATUS", width=10)
    table.add_column("DETAIL", style="dim")

    # 1. Runtime Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Runtime", "[green]PASS[/green]", f"Python {py_ver} ({platform.system()})")
    
    # 2. Engine Check
    from yamlr.core.entrypoints.base import CORE_VERSION
    table.add_row("Engine", "[green]PASS[/green]", f"Yamlr v{CORE_VERSION}")

    # 3. Catalog Check
    if engine and hasattr(engine, "catalog"):
        cat_ver = engine.cluster_version
        res_count = len(engine.catalog.get_all_kinds()) if hasattr(engine.catalog, "get_all_kinds") else "N/A"
        table.add_row("Catalog", "[green]PASS[/green]", f"K8s {cat_ver} ({res_count} resources cached)")
    else:
        table.add_row("Catalog", "[yellow]WARN[/yellow]", "No active catalog loaded")

    # 4. Kube-Version Detection
    if engine and engine.cluster_version:
        status = "[green]PASS[/green]" if engine.cluster_version.lstrip("v") in MATRIX.supported_versions else "[yellow]EXT[/yellow]"
        detail = f"Targeting {engine.cluster_version}"
        if status == "[yellow]EXT[/yellow]":
            detail += " (Best-effort mode)"
        table.add_row("K8s API", status, detail)
    else:
        table.add_row("K8s API", "[red]FAIL[/red]", "Unable to detect target cluster version")

    # 4.5 Matrix Check
    k8s_matrix = getattr(args, "k8s_matrix", False)
    k8s_matrix_strict = getattr(args, "k8s_matrix_strict", False)
    missing_versions = []
    
    if k8s_matrix or k8s_matrix_strict:
        from yamlr.core.catalog_manager import CatalogManager
        catalog_manager = CatalogManager()
        
        installed_versions = [v.lstrip("v") for v in catalog_manager.list_installed_versions()]
        missing_versions = [v for v in MATRIX.supported_versions if v not in installed_versions]
        
        default_version = MATRIX.default_recommended
        default_path = catalog_manager.get_catalog_path(default_version)
        
        if missing_versions:
            status = "[red]FAIL[/red]"
            detail = f"Missing bundles: {', '.join(missing_versions)}"
        else:
            status = "[green]PASS[/green]"
            detail = f"{len(MATRIX.supported_versions)}/{len(MATRIX.supported_versions)} supported versions present."
            
        if default_path.exists():
            mtime = default_path.stat().st_mtime
            timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            
            sha256_hash = hashlib.sha256()
            with open(default_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            actual_sha = sha256_hash.hexdigest()[:8]
            size_kb = default_path.stat().st_size // 1024
            
            detail += f"\nDefault: v{default_version}, {size_kb}KB, sha256:{actual_sha}, updated {timestamp}"
        else:
            detail += f"\nDefault: v{default_version} is missing!"
            status = "[red]FAIL[/red]"
            if default_version not in missing_versions:
                 missing_versions.append(default_version)

        table.add_row("K8s Matrix", status, detail)
    else:
        table.add_row("Matrix", "[green]PASS[/green]", f"Support: {MATRIX.min_supported}–{MATRIX.max_supported} (Default: v{MATRIX.default_recommended})")
    # 5. Pro License Check
    status, message = YamlrBridge.check_pro_status()
    from yamlr.core.license_manager import ProStatus
    
    if status == ProStatus.VALID:
        table.add_row("License", "[green]PASS[/green]", f"Pro Active ({message})")
    elif status in [ProStatus.TRIAL_ACTIVE]:
        table.add_row("License", "[yellow]TRIAL[/yellow]", message)
    else:
        table.add_row("License", "[blue]FREE[/blue]", "Yamlr Free Version active")

    console.print(table)
    
    console.print("\n[dim]Run with [white]--verbose[/white] for deep trace logs.[/dim]")
    
    if k8s_matrix_strict and missing_versions:
        console.print("\n[red]ERROR: Strict matrix validation failed. Missing required catalogs.[/red]")
        sys.exit(1)
        
    return 0
