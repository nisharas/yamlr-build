from __future__ import annotations

from pathlib import Path

from yamlr.core.context import HealContext

__all__ = ["handle_init_command"]

DEFAULT_CONFIG_TEMPLATE = """# Yamlr Configuration File
# Documentation: https://yamlr.dev/config

kubernetes:
  # Auto-detected from your environment at init time
  version: "{cluster_version}"

rules:
  # Minimum health score (0-100) to fail the pipeline
  threshold: 80

  # Ignore specific rules globally
  # ignore:
  #   - "rules/no-latest-tag"
  #   - "rules/resource-limits"

ignore:
  # Paths to exclude from scanning (glob patterns)
  files:
    - "test/*"
    - "vendor/**"

output:
  # Default output format (text, json, sarif)
  format: text
"""


def handle_init_command(console, force: bool = False):
    """Generates the .yamlr.yaml file with smart defaults."""
    target = Path(".yamlr.yaml")

    if target.exists() and not force:
        console.print("[yellow]⚠️  Configuration file .yamlr.yaml already exists.[/yellow]")
        console.print("[dim]Use --force to overwrite.[/dim]")
        return 1

    try:
        if target.exists() and force:
            console.print("[yellow]Overwriting existing configuration...[/yellow]")

        # Smart Detect: Get Connected Cluster Version
        # This prevents the "Mismatched Version" warning for day-1 users
        detected_version = HealContext._get_default_cluster_version() or "v1.31"
        console.print(f"[dim]Auto-detected Kubernetes version: {detected_version}[/dim]")

        # Hydrate Template
        config_content = DEFAULT_CONFIG_TEMPLATE.format(cluster_version=detected_version)

        target.write_text(config_content, encoding="utf-8")
        console.print(f"[green]✅ Created configuration file: [bold]{target.absolute()}[/bold][/green]")
        console.print("[dim]Tip: Edit this file to customize rule thresholds and file ignores.[/dim]")
        console.print(
            "[bold magenta]🚀 Ready to go![/bold magenta] Run [cyan]yamlr demo[/cyan] to test your setup with samples."
        )

        # 3. Smart Onboarding Suggestions
        _suggest_integrations(console)

    except Exception as e:
        console.print(f"[red]❌ Failed to create config file: {e}[/red]")
        return 1

    return 0


def _suggest_integrations(console):
    """
    Detects the environment and suggests high-value integrations.
    """
    cwd = Path.cwd()

    # 1. Pre-Commit
    if (cwd / ".pre-commit-config.yaml").exists():
        console.print("\n[bold cyan]⚡ Detected pre-commit configuration[/bold cyan]")
        console.print("Add this hook to your [bold].pre-commit-config.yaml[/bold] to auto-fix YAML on commit:")
        console.print(
            "[dim]"
            "  - repo: https://github.com/yamlr/yamlr\n"
            "    rev: v0.1.0\n"
            "    hooks:\n"
            "      - id: yamlr-check\n"
            "[/dim]"
        )

    # 2. VS Code
    if (cwd / ".vscode").is_dir():
        console.print("\n[bold blue]📝 Detected VS Code project[/bold blue]")
        console.print("Enable real-time validation by adding this to [bold].vscode/settings.json[/bold]:")
        console.print(
            "[dim]"
            '  "yaml.schemas": {\n'
            '    "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.31.0-standalone-strict/all.json": "/*.yaml"\n'
            "  }\n"
            "[/dim]"
        )

    # 3. GitHub Actions
    if (cwd / ".github" / "workflows").is_dir():
        console.print("\n[bold white]🤖 Detected GitHub Actions[/bold white]")
        console.print("Run Yamlr in CI with the official action:")
        console.print("[dim]  - name: Run Yamlr Guardrails\n    uses: yamlr/yamlr-action@v1\n[/dim]")
