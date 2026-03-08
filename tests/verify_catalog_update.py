#!/usr/bin/env python3
"""
VERIFY CATALOG UPDATE
---------------------
Tests the CatalogManager's ability to download and install schemas.
Uses a local 'file://' URL to simulate the upstream server, ensuring
network independence for this test.
"""

import json
import logging
import os
import sys
from pathlib import Path

from rich.console import Console

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.catalog_manager import CatalogManager

# Configure logging
logging.basicConfig(level=logging.WARNING)
console = Console()


def test_catalog_update():
    console.print("[bold cyan]🚀 Starting Catalog Update Verification...[/bold cyan]")

    # 1. Setup Mock Upstream
    base_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    upstream_dir = base_dir / "mock_upstream"
    upstream_dir.mkdir(exist_ok=True)

    dummy_version = "v1.99"
    dummy_file = upstream_dir / f"k8s_{dummy_version}_distilled.json"

    dummy_content = {"MockResource": {"fields": {"spec": {"type": "object"}}}}

    with open(dummy_file, "w") as f:
        json.dump(dummy_content, f)

    console.print(f"Created mock upstream at: {dummy_file}")

    # 2. Setup Manager with Local Storage
    local_storage = base_dir / "local_cache"
    local_storage.mkdir(exist_ok=True)

    mgr = CatalogManager(storage_dir=str(local_storage))

    # IMPORTANT: Override upstream URL to point to local file system
    # file:///path/to/mock_upstream
    mock_url = f"file:///{str(upstream_dir).replace(os.sep, '/')}"
    mgr.UPSTREAM_BASE_URL = mock_url

    console.print(f"Mocking upstream URL: {mock_url}")

    # 3. Perform Update
    success = mgr.fetch_catalog(dummy_version)

    if not success:
        console.print("[bold red]❌ fetch_catalog returned False[/bold red]")
        sys.exit(1)

    # 4. Verify Installation
    installed_path = mgr.get_catalog_path(dummy_version)
    if installed_path.exists():
        console.print(f"[green]Catalog installed at:[/green] {installed_path}")

        # Verify content match
        with open(installed_path, "r") as f:
            installed_content = json.load(f)

        if installed_content == dummy_content:
            console.print(
                "[bold green]✅ SUCCESS: Catalog downloaded and verified![/bold green]"
            )
        else:
            console.print("[bold red]❌ FAILURE: Content mismatch[/bold red]")
            sys.exit(1)
    else:
        console.print(
            f"[bold red]❌ FAILURE: File not found at expected path: {installed_path}[/bold red]"
        )
        sys.exit(1)

    # 5. Verify Resolution
    resolved = mgr.resolve_catalog(dummy_version)
    if str(installed_path) == str(resolved):
        console.print(
            "[bold green]✅ RESOLUTION: Manager correctly resolved local cache.[/bold green]"
        )
    else:
        console.print(
            f"[bold red]❌ RESOLUTION FAILED: Expected {installed_path}, got {resolved}[/bold red]"
        )
        sys.exit(1)

    # Cleanup (Optional, helpful for debugging to leave if failed, but clean on success)
    # shutil.rmtree(upstream_dir)
    # shutil.rmtree(local_storage)


if __name__ == "__main__":
    test_catalog_update()
