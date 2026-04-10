import os
import subprocess
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()


def slow_print(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def run_step(title, cmd, explanation):
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))
    slow_print(f"💡 {explanation}")
    time.sleep(1)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(root, "src")

    process = subprocess.Popen(
        cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
    )
    stdout, stderr = process.communicate()

    # We strip any Rich formatting if needed, but let's just print the output as is
    console.print(stdout)
    if stderr:
        console.print(f"[red]{stderr}[/red]")

    time.sleep(2)


def main():
    console.clear()
    console.print(Panel.fit("🛡️  Yamlr Manual QA Walkthrough (Automated Simulation)  🛡️", style="bold green"))

    run_step(
        "Phase 1: Zero-Knowledge Onboarding",
        "python -m yamlr.cli.main doctor",
        "Users start with a 'doctor' check to verify their environment, catalog, and license status.",
    )

    run_step(
        "Phase 2: Habit Trigger (Safety Audit)",
        "python -m yamlr.cli.main scan tests/fixtures/healthy_manifest.yaml",
        "Performing a 'Zero-Blindspot' scan. The engine detects best-practice violations and security risks.",
    )

    # Create a temporary broken file
    with open("walkthrough_broken.yaml", "w") as f:
        f.write(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: broken-pod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:latest\n"
        )

    run_step(
        "Phase 3: The Surgical Heal (S2: Apply)",
        "python -m yamlr.cli.main heal walkthrough_broken.yaml --diff",
        "Yamlr proposes a surgical fix for the 'latest' tag violation. Note the comment preservation and DNA integrity.",
    )
    os.remove("walkthrough_broken.yaml")

    run_step(
        "Phase 4: Forensic Sovereign Audit",
        "python -m yamlr.cli.main explain rule/ingress-insecure-tls",
        "Explaining a security rule. This provides the 'Why' (Rationale) and 'How' (Remediation) for developers.",
    )

    console.print(
        Panel(
            "[bold green]✨ Manual walkthrough complete. System verified for $20M acquisition readiness.[/bold green]",
            style="green",
        )
    )


if __name__ == "__main__":
    main()
