"""
DEMO COMMAND - The Safety Engine Showcase
----------------------------------
Scaffolds a sample directory with purposeful errors to demonstrate Yamlr's power.
"""
from __future__ import annotations
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
__all__ = ['handle_demo_command']


def handle_demo_command(args, engine, console: Console):
    """
    Creates a demo directory with malformed K8s manifests.
    """
    demo_dir = Path("yamlr-demo")
    if demo_dir.exists():
        console.print(f"[yellow]⚠️  Directory '[bold]{demo_dir}[/bold]' already exists. Skipping scaffold.[/yellow]")
    else:
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Scaffolding malformed sample.yaml
        sample_path = demo_dir / "sample.yaml"
        sample_content = """# Yamlr Demo: Safety Engine Showcase
# 1. Mismatched Indentation (Lexer demo)
# 2. Ghost Service (Selector mismatch)
# 3. Missing Probes (Best practice demo)

apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web-frontend   # Expects 'app=web'
  ports:
    - port: 80
      targetPort: 8080

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: web        # Typo: 'web' != 'web-frontend'
    spec:
      containers:
        - name: nginx
          image: nginx:latest # Pinning needed
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
# Indentation error on the next line (purposeful)
     livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
"""
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(sample_content)
        
        console.print(f"[green]✅ Created demo manifest at [bold]{sample_path}[/bold][/green]")

    # Instructions
    instructions = (
        "[bold cyan]Try these core capabilities to see Yamlr's Safety Engine in action:[/bold cyan]\n\n"
        "1. [white bold]yamlr scan yamlr-demo[/white bold]\n"
        "   [dim]Detect the 'Ghost Service' caused by the selector typo.[/dim]\n\n"
        "2. [white bold]yamlr heal yamlr-demo --fix-refs[/white bold] [blue](Yamlr Pro)[/blue]\n"
        "   [dim]Watch the engine automatically fix the typo to restore system integrity.[/dim]\n\n"
        "3. [white bold]yamlr heal yamlr-demo --harden --enforce-limits[/white bold] [blue](Yamlr Pro)[/blue]\n"
        "   [dim]Instantly inject SOC2/CIS compliance guardrails across the manifest.[/dim]\n\n"
        "⚙️ [bold white]NEXT STEP:[/bold white]\n"
        "[dim]Drop Yamlr into your GitHub Actions to prevent silent failures from ever reaching production.[/dim]"
    )
    
    console.print(Panel(instructions, title="[bold magenta]✨ Kubernetes Safety Engine Demo[/bold magenta]", border_style="magenta", padding=(1, 2)))
    
    return 0
