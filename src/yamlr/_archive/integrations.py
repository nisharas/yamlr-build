import os
import sys

from yamlr.ui.theme import ICON_SUCCESS, console


def cmd_install_hook():
    """Installs Yamlr as a Git pre-commit hook."""
    git_dir = os.path.join(os.getcwd(), ".git")
    if not os.path.exists(git_dir):
        console.print("[bold red]ERROR:[/bold red] Not a Git repository. Run 'git init' first.")
        return False
    
    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    
    hook_path = os.path.join(hooks_dir, "pre-commit")
    
    hook_content = """#!/bin/sh
# Yamlr pre-commit hook
# Block commits with manifest violations.

echo "[!] Yamlr: Auditing manifests for safety gaps..."
yamlr scan . --fail-on error
if [ $? -ne 0 ]; then
    echo "[X] Yamlr: Commit blocked. Please heal your manifests with 'yamlr heal . --apply'"
    exit 1
fi
"""
    
    with open(hook_path, "w") as f:
        f.write(hook_content)
    
    # Make executable
    if os.name != 'nt':
        os.chmod(hook_path, 0o755)
        
    console.print(f"\n[bold green]{ICON_SUCCESS} Git hook installed![/bold green]")
    console.print("[dim]Yamlr will now protect every commit in this repository.[/dim]")
    return True

def cmd_install_action():
    """Generates a GitHub Action workflow for Yamlr."""
    workflow_dir = os.path.join(os.getcwd(), ".github", "workflows")
    os.makedirs(workflow_dir, exist_ok=True)
    
    action_path = os.path.join(workflow_dir, "yamlr-safety.yml")
    
    action_content = """name: Yamlr Manifest Safety
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Yamlr Engine
        uses: yamlr/action@v1
        with:
          path: '.'
          fail_on: 'error'
          output: 'sarif'
          version: 'v1.2.3'
"""
    
    with open(action_path, "w") as f:
        f.write(action_content)
        
    console.print(f"\n[bold green]{ICON_SUCCESS} GitHub Action generated![/bold green]")
    console.print("[dim]Path: .github/workflows/yamlr-safety.yml[/dim]")
    return True
