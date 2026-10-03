"""Informational commands — user-facing info, documentation, and utility commands."""
import json
import os
from typing import Optional

from yamlr.ui.theme import console


def cmd_welcome():
    """Displays the Yamlr welcome dashboard and workspace status."""
    from yamlr.ui.renderer import RichRenderer
    workspace = os.getcwd()
    version = _detect_k8s_version_safe()
    RichRenderer.render_welcome(workspace, version)


def cmd_version():
    """Displays the Yamlr engine version and native core build info."""
    from yamlr.version import __version__
    console.print(f"\n[bold white]Yamlr[/bold white] [dim]v{__version__}[/dim]")

    try:
        import yamlr_native
        native_info = getattr(yamlr_native, 'native_get_build_info', None)
        if native_info:
            console.print(f"[dim]Native Core:[/dim] {native_info()}")
        else:
            console.print("[dim]Native Core:[/dim] Linked (PyO3)")
    except ImportError:
        console.print("[dim]Native Core:[/dim] [yellow]Not available[/yellow]")

    console.print(f"[dim]Python:[/dim] {os.sys.version.split()[0]}")
    console.print()


def cmd_guide_rich(topic: Optional[str] = None):
    """Interactive documentation guide powered by the Knowledge Registry.

    Args:
        topic: Optional topic key to look up (e.g., "HEAL", "DNA", "Y-101").
    """
    from yamlr.knowledge.registry import KnowledgeRegistry
    from yamlr.ui.renderer import RichRenderer

    if topic:
        data = KnowledgeRegistry.lookup(topic)
        if data:
            RichRenderer.render_explain(topic, data)
        else:
            console.print(f"\n[yellow][!] Topic '{topic}' not found in the Knowledge Registry.[/yellow]")
            _print_available_topics(KnowledgeRegistry)
    else:
        console.print("\n[bold white]Yamlr Knowledge Guide[/bold white]\n")
        _print_available_topics(KnowledgeRegistry)


def cmd_explain_universal(topic: Optional[str] = None, flag: Optional[str] = None):
    """Universal technical concept lookup across rules and flags.

    Args:
        topic: The concept or rule ID to explain.
        flag: Optional flag context for lookup.
    """
    from yamlr.knowledge.registry import KnowledgeRegistry
    from yamlr.ui.renderer import RichRenderer

    if not topic:
        console.print("\n[yellow]Usage: yamlr explain <topic> [--flag <flag>][/yellow]")
        return

    # Try Bible first (flag-level documentation)
    try:
        from yamlr.knowledge.bible import BIBLE
        bible_data = BIBLE.lookup(topic, flag) if flag else BIBLE.lookup(topic)
        if bible_data:
            RichRenderer.render_explain(topic, bible_data)
            return
    except (ImportError, AttributeError):
        pass

    # Fallback 1: Knowledge Registry
    data = KnowledgeRegistry.lookup(topic)
    if data:
        RichRenderer.render_explain(topic, data)
        return

    # Fallback 2: Forensic Catalog (Rule-level deep dives)
    try:
        catalog_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog", "forensic_catalog.json")
        if os.path.exists(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
                detectors = catalog.get("detectors", [])
                for detector in detectors:
                    if detector.get("id") == topic:
                        RichRenderer.render_explain(topic, {
                            "title": detector.get("name", topic),
                            "definition": detector.get("rationale", "No definition provided."),
                            "rationale": f"Rule ID: {topic} | Severity: {detector.get('severity', 'UNKNOWN')}",
                            "impact": "Forensic Remediation Recommended",
                            "example": f"Category: {detector.get('category', 'General')}"
                        })
                        return
    except Exception:
        pass

    console.print(f"\n[yellow][!] No documentation found for '{topic}'.[/yellow]")
    console.print("[dim]Try: yamlr guide (to browse all topics)[/dim]\n")


def cmd_completion(shell: str):
    """Generate shell completion scripts.

    Args:
        shell: Target shell type ("bash" or "zsh").
    """
    from yamlr.core.command_registry import UniversalCommandRegistry

    commands = sorted(UniversalCommandRegistry.COMMANDS.keys())
    cmd_list = " ".join(commands)

    if shell == "bash":
        script = f"""# Yamlr bash completion — add to ~/.bashrc
_yamlr_completions() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    COMPREPLY=($(compgen -W "{cmd_list}" -- "$cur"))
}}
complete -F _yamlr_completions yamlr
"""
    elif shell == "zsh":
        script = f"""# Yamlr zsh completion — add to ~/.zshrc
_yamlr() {{
    local commands=({cmd_list})
    _describe 'command' commands
}}
compdef _yamlr yamlr
"""
    else:
        console.print(f"[yellow]Unsupported shell: {shell}. Use 'bash' or 'zsh'.[/yellow]")
        return

    print(script)
    console.print(f"[dim]# Paste the above into your ~/.{shell}rc and restart your shell.[/dim]")


# --- Private Helper Functions ---

def _detect_k8s_version_safe() -> str:
    """Safely detects Kubernetes version with fallback to 1.30."""
    version = os.getenv("YAMLR_K8S_VERSION")
    if version:
        return version

    try:
        import yamlr_native
        if hasattr(yamlr_native, "native_detect_cluster_version"):
            return yamlr_native.native_detect_cluster_version()
    except Exception:
        pass

    try:
        import subprocess
        result = subprocess.run(
            ["kubectl", "version", "--client", "-o", "json"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            major = data.get("clientVersion", {}).get("major", "1")
            minor = data.get("clientVersion", {}).get("minor", "30")
            return f"{major}.{minor}"
    except Exception:
        pass

    return "1.30"




def _print_available_topics(registry_class):
    """Prints all available topics in the Knowledge Registry."""
    from rich.table import Table
    table = Table(show_header=True, title="Available Topics")
    table.add_column("Key", style="cyan")
    table.add_column("Title", style="white")
    for key, data in registry_class.DATA.items():
        table.add_row(key, data.get("title", ""))
    console.print(table)
    console.print("\n[dim]Usage: yamlr guide <topic>[/dim]\n")
