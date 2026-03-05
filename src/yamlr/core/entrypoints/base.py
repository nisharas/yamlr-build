"""
CLI SHARED UTILITIES
--------------------
Common logic used across multiple CLI commands.
(Moved to Core for Public Safety)
"""

import platform
import sys
import os

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import box
from rich.text import Text

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from yamlr.core.bridge import YamlrBridge
from yamlr.core.context import HealContext

# Global UI Controller
_console = None

def get_console(plain: bool = False):
    """
    Returns a configured Rich console.
    
    Why: To centralize UI settings and allow for ASCII-only fallback modes
         required for professional CI/CD and certain Windows environments.
    """
    global _console
    
    # If explicitly requested plain, or if we haven't initialized yet
    if plain or _console is None:
        from rich import box
        
        # Check environment for NO_COLOR
        no_color = os.getenv("NO_COLOR") is not None
        
        # If redirected to a file, we should be conservative
        is_terminal = sys.stdout.isatty()
        
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
            color_system=None if plain or no_color else "auto",
            safe_box=plain or not is_terminal
        )
        
        # Attach box style preference to the console object for mixins to use
        new_console._yamlr_box = box_style
        new_console._yamlr_plain = plain or not is_terminal
        
        if plain or _console is None:
            _console = new_console
            _console._yamlr_quiet = False  # Set later by main.py if arg is present
            
    return _console


if platform.system() == "Windows":
    # Proactive encoding fix for Windows environments.
    # We only wrap if not already wrapped or if we suspect encoding mismatch.
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
    except Exception:
        pass # Fallback to default if wrapping fails

formatter = None  # Lazy loaded to avoid circular imports if needed

# Constants
CORE_VERSION = "0.1.0-stable"
CATALOG_VERSION = "k8s-01.31-distilled"



def add_standard_flags(sub):
    """Helper to inject path arguments and search filters into sub-parsers."""
    sub.add_argument(
        "--kube-version",
        "--k8s-version",
        type=str,
        default=None,
        metavar="VERSION",
        dest="kube_version",
        help="Target K8s version (e.g., 1.28, v1.31)",
    )
    sub.add_argument(
        "path", nargs="*", metavar="TARGET", help="File(s) or directory(s) to process (supports globbing)"
    )
    sub.add_argument("--max-depth", type=int, default=10, help="Limit directory recursion depth (default: 10)")
    sub.add_argument("--ext", default=".yaml,.yml", help="Extensions to process (default: .yaml,.yml)")
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


@dataclass(slots=True)
class CliOptions:
    """
    Standard container for all common CLI options.

    Why: To provide a type-safe, centralized structure for handling flags
         across scan, heal, and check commands.
    """
    targets: List[str] = field(default_factory=list)
    kube_version: Optional[str] = None
    max_depth: int = 10
    extensions: List[str] = field(default_factory=list)
    concurrency: Optional[int] = None
    strict: bool = False
    compact: bool = False
    identity_mode: str = "infer"
    summary_only: bool = False
    verbose: bool = False
    cpu_limit: str = "500m"
    mem_limit: str = "512Mi"
    namespace: str = "default"
    health_threshold: int = 70
    enforce_limits: bool = False
    enforce_probes: bool = False
    enforce_namespace: bool = False
    fix_tags: bool = False
    harden: bool = False
    fix_refs: bool = False
    stream_to: Optional[str] = None
    fail_on: Optional[str] = None
    check_deprecations: bool = False
    is_pro: bool = False
    fast: bool = False
    plain: bool = False
    pro_preview: bool = False
    evidence_dir: Optional[str] = None
    adapters_dir: Optional[str] = None
    risk_threshold: Optional[str] = None


def extract_cli_options(args, is_pro: bool, console=None) -> CliOptions:
    """
    Extracts and normalizes flags from argparse namespace into a CliOptions object.

    Why: To centralize Pro-license gating and flag normalization, ensuring
         consistent behavior and reducing code duplication in command handlers.
    """
    if console is None:
        console = get_console()

    # 1. Extraction
    options = CliOptions(
        targets=args.path if hasattr(args, "path") else [],
        kube_version=getattr(args, "kube_version", None),
        max_depth=getattr(args, "max_depth", 10),
        extensions=[e.strip() for e in getattr(args, "ext", ".yaml,.yml").split(",")],
        concurrency=getattr(args, "concurrency", None),
        strict=getattr(args, "strict", False),
        compact=getattr(args, "compact", False),
        identity_mode=getattr(args, "identity_mode", "infer"),
        summary_only=getattr(args, "summary_only", False),
        verbose=getattr(args, "verbose", False),
        cpu_limit=getattr(args, "cpu_limit", "500m"),
        mem_limit=getattr(args, "mem_limit", "512Mi"),
        namespace=getattr(args, "namespace", "default"),
        health_threshold=getattr(args, "health_threshold", 70),
        enforce_limits=getattr(args, "enforce_limits", False),
        enforce_probes=getattr(args, "enforce_probes", False),
        enforce_namespace=getattr(args, "enforce_namespace", False),
        fix_tags=getattr(args, "fix_tags", False),
        harden=getattr(args, "harden", False),
        fix_refs=getattr(args, "fix_refs", False),
        stream_to=getattr(args, "stream_to", None),
        fail_on=getattr(args, "fail_on", None),
        check_deprecations=getattr(args, "check_deprecations", False),
        is_pro=is_pro,
        fast=getattr(args, "fast", False),
        plain=getattr(args, "plain", False),
        pro_preview=getattr(args, "pro_preview", False),
        evidence_dir=getattr(args, "evidence_dir", None),
        adapters_dir=getattr(args, "adapters_dir", None),
        risk_threshold=getattr(args, "risk_threshold", None)
    )

    # 2. Pro License Gating
    # If unlicensed, show upgrade panel and zero out Pro features for graceful degradation.
    # [PRO-12-06] Bypass zero-out if pro-preview is active to allow demo diff generation.
    pro_flags = {
        "harden": options.harden,
        "enforce_limits": options.enforce_limits,
        "enforce_probes": options.enforce_probes,
        "fix_tags": options.fix_tags,
        "enforce_namespace": options.enforce_namespace,
        "check_deprecations": options.check_deprecations,
        "fix_refs": options.fix_refs,
    }
    
    active_pro = [k for k, v in pro_flags.items() if v]
    if active_pro and not is_pro and not options.pro_preview:
        flag_names = ", ".join(f"--{f.replace('_', '-')}" for f in active_pro)
        YamlrBridge.notify_pro_required(f"Flags: {flag_names}")
        console.print(
            "[dim]Continuing with OSS features only. "
            "Pro flags have been disabled for this run.[/dim]\n"
        )
        # Disable the flags in the options object
        options.harden = False
        options.enforce_limits = False
        options.enforce_probes = False
        options.fix_tags = False
        options.enforce_namespace = False
        options.check_deprecations = False
        options.fix_refs = False
        options.evidence_dir = None
        options.adapters_dir = None

    return options


def validate_required_arg(value, arg_name: str, context: str, examples: list):
    """
    Validates that a required argument is present.
    If missing, prints a Smart Error Panel and returns False.
    """
    if value:
        return True

    from rich.align import Align
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
    Flattens separate path arguments or comma-separated lists into a clean list.
    Handles both single strings (from argparse) and lists (from nargs="*").
    """
    if not raw_paths:
        return []

    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]

    normalized = []
    for p in raw_paths:
        for sub in p.split(","):
            clean = sub.strip()
            if clean:
                normalized.append(clean)
    return normalized


