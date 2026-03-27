from __future__ import annotations
from pathlib import Path
from yamlr.core.scoring import ScoringEngine
from yamlr.core.idp_exporter import IDPExporter

__all__ = ["handle_idp_export_command"]

def handle_idp_export_command(args, engine, console) -> int:
    """Handles the 'yamlr idp-export' command.
    
    Why: Enables Yamlr to act as a 'Supplier of Safety Truth' for Backstage/Prometheus.
    """
    action = getattr(args, "action", "export")
    fmt = getattr(args, "format", "json")
    output_file = getattr(args, "output_file", None)
    
    if action == "init":
        return _handle_init_workflow(fmt, output_file, console)
    
    # 1. Run a fresh scan to get findings
    if not getattr(console, "_yamlr_quiet", False):
        console.print("[dim]Collecting safety metrics for export...[/dim]")
    target = args.path if hasattr(args, "path") and args.path else ["."]
    results = engine.batch_heal(target, dry_run=True)
    
    # 2. Generate report
    # Group results by app name (Consistency with stats --apps)
    results_by_app = {}
    for res in results:
        app_name = getattr(res, "app_name", "Infrastructure") or "Infrastructure"
        if app_name not in results_by_app:
            results_by_app[app_name] = []
        results_by_app[app_name].append(res)
        
    scoring = ScoringEngine()
    report = scoring.generate_app_report(results_by_app)
    
    # 3. Export
    exporter = IDPExporter(report)
    
    if fmt == "backstage":
        output = exporter.export_backstage()
    elif fmt == "prometheus":
        output = exporter.export_prometheus()
    else:
        output = exporter.export_json()
        
    if output_file:
        try:
            Path(output_file).write_text(output, encoding="utf-8")
            if not getattr(console, "_yamlr_quiet", False):
                console.print(f"[green]✅ Export saved to: {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error writing export to {output_file}: {e}[/red]")
            return 1
    else:
        # For Prometheus, we want raw text if possible, but Console might add formatting
        # If quiet mode, we print raw output to sys.stdout (via clinical redirection if enabled)
        # But here we just use console for simplicity unless it's prometheus
        if fmt == "prometheus":
            print(output) # Use standard print for raw Prometheus metrics
        else:
            console.print(output)
            
    return 0

def _handle_init_workflow(fmt: str, output_file: Optional[str], console) -> int:
    """Generates opinionated IDP integration templates.
    
    Why: To provide a 'Magic Moment' for platform engineers by showing 
         exactly how to plug Yamlr safety metrics into their IDP.
    """
    if fmt == "backstage":
        template = """# Yamlr Backstage Integration Template
# ------------------------------------
# 1. Copy this into your component's 'catalog-info.yaml'
# 2. Ensure Yamlr CI/CD is pushing metrics to your IDP exporter.

apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: example-service
  description: A service secured by Yamlr
  annotations:
    yamlr.io/safety-score: "pending"  # Updated automatically by Yamlr
    yamlr.io/last-scan: "pending"
    yamlr.io/dna-integrity: "pending"
spec:
  type: service
  owner: platform-team
  lifecycle: production
"""
    elif fmt == "prometheus":
        template = """# Yamlr Prometheus Scrape Config
# ------------------------------
# 1. Add this to your 'prometheus.yml' scrape_configs
# 2. Ensure your Yamlr IDP Exporter is reachable at the target IP.

scrape_configs:
  - job_name: 'yamlr-safety-metrics'
    static_configs:
      - targets: ['localhost:9091'] # Replace with your exporter endpoint
    metrics_path: '/metrics'
"""
    else:
        console.print(f"[yellow]⚠️  'init' is only supported for 'backstage' or 'prometheus' (got: {fmt})[/yellow]")
        return 1

    if output_file:
        Path(output_file).write_text(template, encoding="utf-8")
        console.print(f"[green]✅ Generated {fmt} template at: {output_file}[/green]")
    else:
        console.print(f"\n[bold]Yamlr {fmt.capitalize()} Integration Template:[/bold]\n")
        console.print(template)
        console.print("\n[dim]Tip: Use --output to save this to a file.[/dim]")
    
    return 0
