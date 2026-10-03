"""Pipeline execution for scanning, healing, and report generation."""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, List

from yamlr.cli.formatters import render_report
from yamlr.cli.signing import cmd_sign, cmd_verify
from yamlr.ui.theme import (
    COLOR_ACCENT,
    COLOR_ERROR,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    ICON_PRO,
    ICON_SUCCESS,
    console,
)

logger = logging.getLogger(__name__)

STYLE_BOLD_CYAN = "bold cyan"

def detect_version() -> str:
    """Detects target Kubernetes version from environment or defaults to 1.30."""
    version = os.getenv("YAMLR_K8S_VERSION")
    if version:
        return version

    if not shutil.which("kubectl"):
        return "1.30"

    try:
        # Try kubectl as the authoritative source for the developer's environment
        result = subprocess.run(
            ["kubectl", "version", "--client", "-o", "json"],
            capture_output=True, text=True, timeout=1
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # Support both old and new kubectl version output formats
            client_version = data.get("clientVersion") or data
            major = client_version.get("major", "1")
            minor = client_version.get("minor", "30")
            # Clean up minor version (sometimes contains '+' or other chars)
            minor = re.sub(r'\D', '', minor)
            return f"{major}.{minor}"
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as e:
        logger.debug("kubectl version detection fallback: %s", e)
    except Exception as e:
        logger.debug("Unexpected error during kubectl version detection: %s", e)

    return "1.30" # Universal stable fallback

def initialize_engine(k8s_version: str) -> List[Any]:
    """Loads core schemas for the specified K8s version."""
    import yamlr_native
    console.print(f"[{STYLE_BOLD_CYAN}][!] Engine Intelligence: K8s v{k8s_version}[/{STYLE_BOLD_CYAN}]")
    try:
        schemas = yamlr_native.native_get_schema_for_version(k8s_version)
        schema_dir = os.getenv("YAMLR_SCHEMA_DIR", ".yamlr/schemas")
        if os.path.isdir(schema_dir):
            for f_name in os.listdir(schema_dir):
                if f_name.endswith(".yaml") or f_name.endswith(".yml"):
                    try:
                        ingest_crds(os.path.join(schema_dir, f_name), schemas)
                    except Exception:
                        pass
        return schemas
    except Exception as e:
        console.print(f"[bold red]FAILED[/bold red] to load schema for v{k8s_version}: {e}")
        sys.exit(1)

def ingest_crds(crd_path: str, schemas: List[Any]):
    """Ingests dynamic CRD schemas."""
    import yamlr_native
    try:
        with open(crd_path, 'r') as f:
            crd_content = f.read()
            dynamic_schemas = yamlr_native.native_extract_schema_from_crd(crd_content)
            schemas.extend(dynamic_schemas)
            console.print(f"[{STYLE_BOLD_CYAN}][!] Ingested Dynamic CRD: {crd_path}[/{STYLE_BOLD_CYAN}]")
    except Exception as e:
        console.print(f"[bold red]FAILED[/bold red] to ingest CRD: {e}")
        sys.exit(1)

def execute_pipeline(path: str, schemas: List[Any], quiet: bool = False, helm: bool = False, kustomize: bool = False) -> Any:
    """Run the scan and heal pipeline."""
    import yamlr_native

    from yamlr.core.scanner import scan_helm_chart, scan_kustomize_dir
    from yamlr.core_logic import streaming_scan
    
    target = os.path.abspath(path)
    if not quiet and sys.stdin.isatty() and not os.path.isfile(target):
        mode_str = " (Helm)" if helm else (" (Kustomize)" if kustomize else "")
        console.print(f"[{STYLE_BOLD_CYAN}][!] Pipeline active: {target}{mode_str}[/{STYLE_BOLD_CYAN}]")
    
    start_time = time.perf_counter()
    results = []
    
    def _get_scanner():
        if helm:
            return scan_helm_chart(target, schemas)
        elif kustomize:
            return scan_kustomize_dir(target, schemas)
        return streaming_scan(target, schemas)

    # Fast path for non-TTY, quiet mode, single files, or pre-commit hooks (<15ms per-file speed gate)
    if quiet or not sys.stdin.isatty() or os.path.isfile(target):
        for res in _get_scanner():
            results.append(res)
    else:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True
        ) as progress:
            scan_task = progress.add_task("[cyan]Scanning manifests...", total=None)
            
            for res in _get_scanner():
                results.append(res)
                progress.advance(scan_task)
                progress.update(scan_task, description=f"[cyan]Audit active: [bold]{os.path.basename(res.file_path)}[/bold]")
    
    end_time = time.perf_counter()
    return yamlr_native.NativeReport(
        results=results,
        total_files=len(results),
        total_time_ms=int((end_time - start_time) * 1000)
    )

def _execute_scan_heal_pipeline(args):
    import yamlr_native

    from yamlr.ui.renderer import RichRenderer
    target_path = os.path.abspath(args.path)
    
    if args.command == "graph":
        discovery = yamlr_native.native_discover_resources(target_path)
        edges = yamlr_native.native_build_topology_graph(discovery)
        blast = yamlr_native.native_calculate_blast_radius(args.focus, edges) if getattr(args, "focus", None) else None
        RichRenderer.render_graph(edges, blast)
        return

    if args.command == "drift":
        discovery = yamlr_native.native_discover_resources(target_path)
        drifts = yamlr_native.native_detect_version_drift(discovery)
        RichRenderer.render_drift_report(drifts)
        return

    if args.command == "audit":
        from yamlr.core_logic import audit_topology_outages
        version = args.k8s_version or detect_version()
        schemas = initialize_engine(version)
        report = execute_pipeline(
            target_path, schemas,
            quiet=getattr(args, "quiet", False),
            helm=getattr(args, "helm", False),
            kustomize=getattr(args, "kustomize", False)
        )
        
        findings = audit_topology_outages(report.results)
        RichRenderer.render_audit_report(findings)
        return

    version = args.k8s_version or detect_version()
    schemas = initialize_engine(version)
    if isinstance(getattr(args, "crd", None), str) and getattr(args, "crd", None):
        ingest_crds(args.crd, schemas)

    ingest_opa = getattr(args, "ingest_opa", None)
    ingest_kyverno = getattr(args, "ingest_kyverno", None)
    if (isinstance(ingest_opa, str) and ingest_opa) or (isinstance(ingest_kyverno, str) and ingest_kyverno):
        from yamlr.core.stages.policy_ingestion_stage import PolicyIngestionStage
        report_path = ingest_opa if (isinstance(ingest_opa, str) and ingest_opa) else ingest_kyverno
        report_type = "opa" if (isinstance(ingest_opa, str) and ingest_opa) else "kyverno"
        PolicyIngestionStage.ingest_and_heal(
            report_path,
            target_dir=target_path,
            report_type=report_type,
            apply=getattr(args, "apply", False) is True
        )
        return
        
    def _output(report):
        output_format = getattr(args, "output", "text")
        user_output_file = getattr(args, "output_file", None)
        
        if output_format == "sarif":
            from yamlr.sarif_reporter import SarifReporter
            output_file = user_output_file or "yamlr-report.sarif"
            SarifReporter.generate_sarif(report.results, output_file)
            console.print(f"[bold green][OK] SARIF Report generated: {output_file}[/bold green]")
        elif output_format == "json":
            output_file = user_output_file or "yamlr-report.json"
            _export_json_report(report, output_file)
            console.print(f"[bold green][OK] JSON Report generated: {output_file}[/bold green]")
        else:
            is_diff_cmd = args.command == "diff"
            render_report(
                report, yamlr_native.NativeTelemetry(), 
                "heal" if is_diff_cmd else args.command, 
                False if is_diff_cmd else getattr(args, "apply", False), 
                dry_run=True if is_diff_cmd else getattr(args, "dry_run", False),
                diff=True if is_diff_cmd else getattr(args, "diff", False),
                push=getattr(args, "push_telemetry", False),
                create_stubs=getattr(args, "create_stubs", False)
            )

        exit_zero = getattr(args, "exit_zero", False)
        fail_on = getattr(args, "fail_on", None)
        if fail_on is None and (os.getenv("CI") or os.getenv("GITHUB_ACTIONS")):
            fail_on = "error"
        if getattr(args, "watch", False) is not True:
            _handle_exit_code(report, fail_on, exit_zero=exit_zero)

    if getattr(args, "watch", False) is True:
        import time

        from yamlr.core.scanner import _discover_manifests
        
        def get_mtimes():
            files = _discover_manifests(target_path)
            return {f: os.stat(f).st_mtime for f in files if os.path.exists(f)}
            
        last_mtimes = get_mtimes()
        console.clear()
        console.print(f"[bold cyan][*] Watch mode enabled. Polling for file changes in {target_path}...[/bold cyan]")
        report = execute_pipeline(target_path, schemas)
        _output(report)

        try:
            while True:
                time.sleep(2.0)
                current_mtimes = get_mtimes()
                if current_mtimes != last_mtimes:
                    last_mtimes = current_mtimes
                    console.clear()
                    console.print(f"[bold blue]Change detected at {time.strftime('%X')}, re-scanning...[/bold blue]\n")
                    report = execute_pipeline(target_path, schemas)
                    _output(report)
        except KeyboardInterrupt:
            console.print("\n[dim]Watch mode terminated.[/dim]")
    else:
        report = execute_pipeline(
            target_path, schemas,
            quiet=getattr(args, "quiet", False),
            helm=getattr(args, "helm", False),
            kustomize=getattr(args, "kustomize", False)
        )
        _output(report)

def _export_json_report(report, output_file):
    data = {
        "total_files": report.total_files,
        "total_time_ms": report.total_time_ms,
        "results": []
    }
    for res in report.results:
        res_data = {
            "file": res.file_path,
            "health_score": res.health_score,
            "violations": [{"field": v.field_path, "msg": v.message, "sev": v.severity} for v in res.violations],
            "integrity_violations": [{"check": v.check_name, "msg": v.message, "sev": v.severity} for v in res.integrity_violations]
        }
        data["results"].append(res_data)
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

def _handle_exit_code(report, fail_level, exit_zero=False):
    if exit_zero:
        return

    sev_map = {"error": 3, "warning": 2, "note": 1, "any": 1}
    target_sev = sev_map.get(str(fail_level).lower(), 3) if fail_level else 0
    if not fail_level:
        return

    max_found = 0
    for res in report.results:
        for v in list(res.violations) + list(res.integrity_violations):
            v_sev = str(getattr(v, "severity", "error")).lower()
            if "critical" in v_sev or "high" in v_sev or "error" in v_sev:
                max_found = max(max_found, 3)
            elif "medium" in v_sev or "warning" in v_sev:
                max_found = max(max_found, 2)
            else:
                max_found = max(max_found, 1)

    if max_found >= target_sev:
        console.print(f"\n[bold red][!] Failure threshold met ({fail_level}). Exiting with code 1.[/bold red]")
        sys.exit(1)
