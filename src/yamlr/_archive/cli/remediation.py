"""Remediation logic for applying automated fixes to Kubernetes manifests."""
import logging
import os
import shutil
import sys
from typing import Any

from yamlr.ui.theme import console

logger = logging.getLogger(__name__)

def apply_remediation(res: Any, telemetry: Any, apply: bool, dry_run: bool = False, diff: bool = False, create_stubs: bool = False):
    """Handles remediation with 'Environment Intelligence' (TTY vs CI/CD)."""
    if not res.suggested_fixes:
        return

    is_interactive = sys.stdin.isatty() and not dry_run
    for fix in res.suggested_fixes:
        # Task 2: Safety Gate for auto-generated stub synthesis
        is_stub_fix = "generate_stub" in getattr(fix, "field_path", "").lower() or "REL-005" in getattr(fix, "rule_id", "")
        if is_stub_fix and not create_stubs:
            console.print(f"    [bold yellow][STUB PREVIEW][/bold yellow] Proposed placeholder stub for {fix.field_path}. (Opt-in with --create-stubs or yamlr.dev/create-stubs)")
            continue

        proceed = True
        if dry_run:
            console.print(f"    [bold cyan][DRY-RUN][/bold cyan] Would apply fix: [dim]{fix.field_path} -> {fix.suggested_value}[/dim]")
            continue

        if is_interactive:
            proceed = _handle_interactive_remediation(fix, apply, diff)
        else:
            _handle_cicd_remediation(res, fix, apply)
        
        if proceed:
            _apply_atomic_fix(res, fix, telemetry)

def _handle_interactive_remediation(fix, apply, diff):
    """Interactive mode logic."""
    if not diff:
        console.print(f"\n    [bold yellow][?] Proposed Remediation:[/bold yellow] {fix.field_path}")
        console.print(f"        [dim]Rationale: {fix.message}[/dim]")
    
    if not apply:
        confirm = console.input("    [bold cyan][?] Apply this surgical fix? [y/N]: [/bold cyan]")
        if confirm.lower() != 'y':
            console.print("    [dim]Remediation deferred.[/dim]")
            return False
    return True

def _handle_cicd_remediation(res, fix, apply):
    """CI/CD mode logic."""
    if not apply:
        console.print(f"\n    [bold red][!] CI/CD SAFETY GATE:[/bold red] Remediation required for {res.file_path}")
        console.print(f"    [dim]Error: Fix '{fix.field_path}' must be applied. Run with --apply to auto-heal.[/dim]")
        sys.exit(1)

def _apply_atomic_fix(res, fix, telemetry):
    """Internal logic for atomic manifest modification."""
    import yamlr_native
    try:
        if telemetry is not None and type(telemetry).__name__ == "NativeTelemetry":
            try:
                yamlr_native.native_record_telemetry(telemetry, "HEAL", 10.0, 100, "WARNING")
            except Exception:
                pass
        # Create a simple .bak for the test and extra safety
        bak_path = res.file_path + ".bak"
        if not os.path.exists(bak_path):
            shutil.copy2(res.file_path, bak_path)
            
        success = yamlr_native.native_apply_fix_atomic(
            res.file_path, fix.field_path, fix.suggested_value,
            getattr(res.identity, 'kind', None), getattr(res.identity, 'name', None)
        )
        if success:
            # Post-write invariant verification: ensure the healed file remains valid YAML
            try:
                with open(res.file_path, "r", encoding="utf-8") as f:
                    repaired_content = f.read()

                # 1. Guarantee valid YAML syntax
                try:
                    import yaml
                    list(yaml.safe_load_all(repaired_content))
                except Exception as yaml_err:
                    raise ValueError(f"Invalid YAML syntax: {yaml_err}") from yaml_err

                # 2. Guarantee non-empty AST shards in native core
                shards = yamlr_native.native_shard(repaired_content)
                if not shards:
                    raise ValueError("Repaired manifest produced empty AST shards")

                console.print(f"    [bold green][OK] Successfully Healed:[/bold green] {res.file_path} [dim](Rollback: yamlr rollback)[/dim]")
            except Exception as verify_err:
                # Automated instant rollback to guarantee zero manifest corruption
                if os.path.exists(bak_path):
                    shutil.copy2(bak_path, res.file_path)
                console.print(f"    [bold red][!] Invariant check failed:[/bold red] {verify_err}. Restored from backup.")
        else:
            console.print("    [bold red][!] FAILED:[/bold red] Resource layout mismatch.")
    except Exception as e:
        console.print(f"    [bold red][ERROR] Healing failed: {e}[/bold red]")
        sys.exit(1)
