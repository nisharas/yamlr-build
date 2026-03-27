"""
CLI SHARED UTILITIES
--------------------
Common logic used across multiple CLI commands.
(Moved to Core for Public Safety)
"""

from __future__ import annotations
import platform
import sys
import os
from pathlib import Path

# Selective imports for typing only
from typing import Any, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    pass

# Global UI Controller
_console = None

from yamlr.core.entrypoints.cli_options import CliOptions, extract_cli_options
from yamlr.core.k8s_versions import MATRIX

__all__ = [
    "get_console", 
    "set_console",
    "add_standard_flags", 
    "CliOptions", 
    "extract_cli_options", 
    "validate_required_arg", 
    "normalize_paths",
    "verify_stability_consent"
]

def get_console(plain: bool = False, target_file: Optional[Any] = None):
    """
    Returns a configured Rich console.
    
    Why: To centralize UI settings and allow for ASCII-only fallback modes
         required for professional CI/CD and certain Windows environments.
    """
    global _console
    
    # [Supplier Pivot] GitOps Stdout Protection
    # If in quiet mode, Argo CD, or explicit clinical mode, we MUST use stderr 
    # for UI to keep stdout pure for YAML
    force_stderr = (
        "--clinical" in sys.argv or
        os.getenv("YAMLR_QUIET") == "true" or 
        os.getenv("ARGOCD_APP_NAME") is not None or 
        os.getenv("IS_ARGOCD") == "1" or
        os.getenv("IS_GITOPS") == "1"
    )
    if target_file is None:
        target_file = sys.stderr if force_stderr else sys.stdout
    
    # If explicitly requested plain, or if we haven't initialized yet
    if plain or _console is None:
        from rich.console import Console
        from rich import box
        
        # Check environment for NO_COLOR
        no_color = os.getenv("NO_COLOR") is not None
        
        # If redirected to a file, we should be conservative
        try:
            is_terminal = target_file.isatty()
        except (AttributeError, ValueError):
            is_terminal = False
        
        # Determine box style
        box_style = box.ASCII if plain or not is_terminal else box.ROUNDED
        
        # Check environment for terminal width override
        env_width = os.getenv("Yamlr_TERMINAL_WIDTH")
        width = None
        if env_width and env_width.isdigit():
            width = int(env_width)

        new_console = Console(
            width=width,
            force_terminal=is_terminal and not plain,
            legacy_windows=False,
            highlight=False,
            file=target_file,
            color_system=None if plain or no_color else "auto",
            safe_box=plain or not is_terminal
        )
        
        # Attach box style preference to the console object for mixins to use
        new_console._yamlr_box = box_style
        new_console._yamlr_plain = plain or not is_terminal
        _console = new_console
        
    return _console


def set_console(console: Optional[Any]):
    """
    Overrides the global console instance. Useful for testing.
    """
    global _console
    _console = console


if platform.system() == "Windows":
    # Proactive encoding fix for Windows environments.
    # We only wrap if not already wrapped or if we suspect encoding mismatch.
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
    except (ImportError, OSError, IOError):
        pass # Fallback to default if wrapping fails

formatter = None  # Lazy loaded to avoid circular imports if needed

# Constants
CATALOG_VERSION = f"k8s-{MATRIX.default_recommended}-distilled"

def __getattr__(name):
    if name == "CORE_VERSION":
        from scripts.version_helper import get_version
        return f"{get_version()}-stable"
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")



def add_standard_flags(sub):
    """Helper to inject path arguments and search filters into sub-parsers."""
    sub.add_argument(
        "--kube-version",
        "--k8s-version",
        type=str,
        default=None,
        metavar="VERSION",
        dest="kube_version",
        help=f"Target K8s version (e.g., 1.28, v{MATRIX.default_recommended})",
    )
    sub.add_argument(
        "path", nargs="*", metavar="TARGET", help="File(s) or directory(s) to process (supports globbing)"
    )
    sub.add_argument(
        "--yes", "-y", action="store_true", help="Auto-approve Stability Gate for experimental K8s versions"
    )
    sub.add_argument("--max-depth", type=int, default=10, help="Limit directory recursion depth (default: 10)")
    sub.add_argument("--ext", default=".yaml,.yml", help="Extensions to process (default: .yaml,.yml)")
    sub.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Structured logging format for SIEM/SRE integration",
    )
    sub.add_argument(
        "--unrestricted",
        action="store_true",
        help="Bypass security interlocks (DANGEROUS: use with caution)",
    )
    sub.add_argument("-h", "--help", action="store_true")
    sub.add_argument(
        "-s",
        "--summary-only",
        action="store_true",
        help="Show high-level impact summary (recommended for 100+ files)",
    )
    sub.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Parallel worker count (defaults to CPU core count)",
    )
    sub.add_argument(
        "--verbose", action="store_true", help="Show full audit logs and stages"
    )
    sub.add_argument(
        "-p", "--plain", action="store_true", help="ASCII-only output (no colors/emojis)"
    )
    sub.add_argument(
        "--clinical", action="store_true", help="[SUPPLIER PIVOT] Force absolutely silent stdout by redirecting UI to stderr"
    )
    sub.add_argument(
        "--identity-mode",
        choices=["infer", "strict"],
        default="infer",
        help="Identity detection style: 'infer' (default) or 'strict'",
    )
    sub.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output for CI/CD pipelines (errors + exit code only)",
    )

    # Advanced / Feature Parity Flags
    sub.add_argument(
        "--strict", action="store_true", help="Treat all schema warnings as errors"
    )
    sub.add_argument(
        "--compact",
        action="store_true",
        help="Minify output (2-space indent, no extra whitespace)",
    )
    sub.add_argument(
        "--cpu-limit",
        type=str,
        default="500m",
        help="Standard CPU request/limit for auto-injection (e.g. 500m)",
    )
    sub.add_argument(
        "--mem-limit",
        type=str,
        default="512Mi",
        help="Standard Memory request/limit for auto-injection (e.g. 512Mi)",
    )
    sub.add_argument(
        "--namespace",
        type=str,
        default="default",
        help="Default namespace for generated resources",
    )
    sub.add_argument(
        "--health-threshold",
        type=int,
        default=70,
        help="Custom health score penalty threshold (0-100)",
    )
    
    # [POWER HEALING TOGGLES]
    sub.add_argument(
        "--enforce-limits",
        action="store_true",
        help="Inject default CPU/Memory requests/limits if missing.",
    )
    sub.add_argument(
        "--enforce-probes",
        action="store_true",
        help="Inject default Liveness/Readiness probes.",
    )
    sub.add_argument(
        "--enforce-namespace",
        action="store_true",
        help="Inject default namespace for resources missing one.",
    )
    sub.add_argument(
        "--fix-tags",
        action="store_true",
        help="Auto-remediate :latest or missing image tags.",
    )
    sub.add_argument(
        "--harden",
        action="store_true",
        help="Apply enterprise security hardening (Pro features).",
    )
    sub.add_argument(
        "--stream-to",
        type=str,
        default=None,
        metavar="FILE",
        help="ULTRA-SCALE: Stream incremental results to NDJSON (prevents RAM saturation for 10k+ files)",
    )
    sub.add_argument(
        "--fail-on",
        choices=["error", "warning", "any"],
        default=None,
        help="CI/CD GATE: Exit with code 1 if specified severity is found",
    )
    sub.add_argument(
        "--check-deprecations",
        action="store_true",
        help="Explicitly audit for and record deprecated Kubernetes APIs",
    )
    sub.add_argument(
        "--fast",
        action="store_true",
        help="[ACCELERATION] Enable lightning-fast scanning via native Rust extension (Pro)",
    )
    sub.add_argument(
        "--sovereign",
        action="store_true",
        help="[AESTHETICS] Enable high-fidelity sovereign export with schema-aware sorting (Pro)",
    )
    sub.add_argument(
        "--experimental-rust",
        "--rust",
        action="store_true",
        dest="use_rust",
        help="[HYBRID] Enable high-performance Rust scanner (experimental)",
    )
    sub.add_argument(
        "--baseline",
        metavar="PATH",
        help="Path to baseline file (default: .yamlr-baseline.json). Skips findings already in baseline.",
    )
    sub.add_argument(
        "--pro-preview",
        action="store_true",
        help="[SIMULATE] Preview Enterprise-tier fixes in Community edition",
    )
    sub.add_argument(
        "--export",
        type=str,
        default=None,
        metavar="FORMAT:PATH",
        help="[INTERACTIVE] Export report to external format (e.g. html:report.html, pdf:audit.pdf)",
    )
    sub.add_argument(
        "--timing",
        action="store_true",
        help="[PERFORMANCE] Show surgical execution timings and performance breakdown",
    )
    sub.add_argument(
        "--timing-file",
        type=str,
        default=None,
        metavar="FILE",
        help="[PERFORMANCE] Save performance profiling data to a JSON file",
    )



def validate_required_arg(value, arg_name: str, context: str, examples: list):
    """
    Validates that a required argument is present.
    If missing, prints a Smart Error Panel and returns False.
    """
    if value:
        return True

    from rich.align import Align
    from rich.panel import Panel
    console = get_console()

    error_msg = f"[bold red]❌ Missing Required Argument: {arg_name}[/bold red]\n\n"
    error_msg += f"The [bold]{context}[/bold] command requires a specific target.\n"

    if examples:
        error_msg += "\n[dim italic]Try:[/dim italic]\n"
        for ex in examples:
            error_msg += f"  [cyan]{ex}[/cyan]\n"

    console.print(
        Panel(
            Align.center(error_msg),
            border_style="red",
            title="[bold yellow]Input Error[/bold yellow]",
            padding=(0, 2),
            expand=False,
        )
    )
    return False


def normalize_paths(raw_paths):
    """
    Standardizes a list of paths (directories or files) or a single path.
    Also enforces length limits to prevent DoS via extremely long arguments. [CRITICAL-3]
    """
    MAX_PATH_LENGTH = 4096
    if not raw_paths:
        return []

    # Handle single path case
    if isinstance(raw_paths, (str, Path)):
        raw_paths = [str(raw_paths)]

    normalized = []
    for p in raw_paths:
        ps = str(p).strip()
        if len(ps) > MAX_PATH_LENGTH:
            from yamlr.core.exceptions import YamlrSecurityError
            raise YamlrSecurityError(
                f"CLI argument too long: {len(ps)} bytes (Max: {MAX_PATH_LENGTH})",
                remediation="Ensure path arguments are reasonably sized and do not contain excessive garbage."
            )
        normalized.append(ps)
    return normalized


def handle_interactive_export(job_results: List[Any], export_str: str):
    """Handles the --export FORMAT:PATH flag for interactive reporting.
    
    Why: To provide rich HTML/PDF reports for stakeholders and audits.
    """
    console = get_console()
    # Support FORMAT:PATH where PATH might contain a drive colon (e.g. html:d:\report.html)
    if ":" in export_str:
        # Check if the first part is a known format
        parts = export_str.split(":", 1)
        potential_fmt = parts[0].lower()
        if potential_fmt in ["html", "pdf", "sarif"]:
            fmt = potential_fmt
            path = parts[1]
        else:
            # Maybe it's just a path without a format? Or an unknown format.
            # Default to HTML if it looks like a file path? 
            # No, requirement is FORMAT:PATH.
            console.print(f"[red]❌ Unknown export format: {potential_fmt}. Use html: path.html, pdf: path.pdf, or sarif: path.json[/red]")
            return
    else:
        console.print(f"[red]❌ Invalid export format: {export_str}. Use FORMAT:PATH (e.g. html:report.html)[/red]")
        return

    # Ensure path is absolute for internal consistency
    path = str(Path(path).absolute())
    
    # [DEBUG] Trace path resolution
    console.print(f"[dim]DEBUG: Exporting to format={fmt}, path={path}[/dim]")
    from yamlr.pro.exporter import Exporter
    exporter = Exporter()
    
    # Convert results to pure dicts for exporter, ensuring we preserve DNA enriched metrics
    serializable = []
    for r in job_results:
        # job_results can be list of HealFileResult or dicts
        if hasattr(r, "to_dict"):
            r_dict = r.to_dict()
            # Ensure findings are also fully serialized
            r_dict["findings"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in getattr(r, "findings", [])]
            serializable.append(r_dict)
        elif hasattr(r, "__dict__"):
            # Fallback for dataclasses without to_dict
            serializable.append(vars(r))
        elif isinstance(r, dict):
             serializable.append(r)

    success = False
    if fmt == "html":
        success = exporter.export_html(serializable, path)
    elif fmt == "pdf":
        success = exporter.export_pdf(serializable, path)
    elif fmt == "sarif":
        success = exporter.export_sarif(serializable, path)
    else:
        console.print(f"[red]❌ Unsupported export format: {fmt}[/red]")
        return

    if success:
        console.print(f"[green]✅ Exported {fmt.upper()} report to: [cyan]{path}[/cyan][/green]")
    else:
        console.print(f"[red]❌ Failed to export {fmt.upper()} report to: {path}[/red]")


def verify_stability_consent(version: str, args: Any) -> bool:
    """Verifies user consent for using unstable or experimental K8s versions.
    
    Why: To prevent accidental usage of Alpha/Beta catalogs in production 
         and ensure users are aware when they exit the 'Tested Range'.
    """
    from yamlr.core.k8s_versions import is_stable, is_supported, MATRIX
    import sys
    
    if not version:
        return True
        
    # If it's stable AND supported, no consent needed
    if is_stable(version) and is_supported(version):
        return True
        
    # If it's stable but NOT supported, we still proceed with best-effort 
    # (The CatalogManager warning will handle this)
    if is_stable(version):
        return True
        
    # UNSTABLE VERSION detected (Alpha/Beta/RC)
    console = get_console()
    
    # Check for implicit consent (-y / --yes)
    if getattr(args, "yes", False) or getattr(args, "dry_run", False):
        return True
        
    # Check for interactivity
    if not sys.stdin.isatty():
        console.print(f"[yellow]⚠️  Warning: K8s {version} is unstable and outside the tested range.[/yellow]")
        console.print("[dim]Proceeding in non-interactive mode. Use --yes to suppress this warning.[/dim]")
        return True
        
    # INTERACTIVE PROMPT
    console.print("\n[bold yellow]🧪 EXPERIMENTAL VERSION DETECTED[/bold yellow]")
    console.print(f"Kubernetes [cyan]{version}[/cyan] is an unstable release (Alpha/Beta/RC).")
    console.print(f"Yamlr's tested range is [green]{MATRIX.min_supported}–{MATRIX.max_supported}[/green].")
    
    try:
        response = input(f"\nDo you want to proceed with {version}? [y/N]: ").strip().lower()
        if response == 'y':
            return True
    except EOFError:
        return True
        
    console.print("[red]Aborted by user.[/red]")
    return False

