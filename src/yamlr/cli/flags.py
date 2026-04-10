from __future__ import annotations

"""
CLI FLAGS - Global and Standard Argument Definitions
----------------------------------------------------
Centralizes all global and reusable flags for the Yamlr CLI.

Why: Extracted from parser_factory.py to ensure the factory remains 
     under 500 lines and is "AI-Ingestible".
"""

import argparse
from typing import TYPE_CHECKING, Any, Dict, Optional

from yamlr.core.k8s_versions import MATRIX



def add_global_flags(parser: argparse.ArgumentParser):
    """Adds the parent-level global flags used across most commands."""
    parser.add_argument(
        "--kube-version",
        "--k8s-version",
        type=str,
        default=None,
        metavar="VERSION",
        dest="kube_version",
        help=f"Target Kubernetes version (default: v{MATRIX.default_recommended}). Supports v1.21-v1.31 and beyond.",
    )
    parser.add_argument("--catalog", default=None, help="Path to custom catalog (default: bundled)")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("-s", "--summary-only", action="store_true", help="Show aggregate stats for batches")
    parser.add_argument("-p", "--plain", action="store_true", help="ASCII-only output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output for CI/CD pipelines")
    parser.add_argument("--all", action="store_true", help="Show all commands including hidden Meta commands")
    parser.add_argument("--sequential", action="store_true", help="Force single-threaded execution")
    parser.add_argument("--verbose", action="store_true", help="Show full engine audit logs")
    parser.add_argument("--expert", action="store_true", help="Unlock advanced UI details and deep forensic insights")
    parser.add_argument("--max-depth", type=int, default=10, help="Limit directory recursion depth (default: 10)")
    parser.add_argument(
        "--ext",
        default=".yaml,.yml",
        help="Extensions to process (default: .yaml,.yml).",
    )
    parser.add_argument("--concurrency", type=int, default=None, help="Parallel worker count")
    parser.add_argument(
        "--fail-on", choices=["error", "warning", "any"], default=None, help="CI/CD Gate: Exit 1 if issues found"
    )
    parser.add_argument(
        "--stream-to",
        type=str,
        default=None,
        metavar="FILE",
        help="ULTRA-SCALE: Stream results to NDJSON for constant-memory processing",
    )
    parser.add_argument(
        "--identity-mode",
        choices=["infer", "strict"],
        default="infer",
        help="Identity detection style: 'infer' (default) or 'strict'",
    )
    parser.add_argument(
        "--risk-threshold",
        choices=["high", "medium", "low"],
        help="Exit 1 if any finding meets or exceeds this risk level",
    )
    parser.add_argument("--clinical", action="store_true", help="Force silent stdout (UI to stderr)")
    parser.add_argument("--compact", action="store_true", help="Minify output")
    parser.add_argument("--pro-preview", action="store_true", help="[SIMULATE] Preview Enterprise fixes")
    parser.add_argument("--experimental-rust", "--rust", action="store_true", help="Enable Rust scanner")
    parser.add_argument("--fast", action="store_true", help="Enable high-speed structural audit (Pro)")
    parser.add_argument("--sovereign", action="store_true", help="Enable sovereign export (Pro)")
    parser.add_argument(
        "--engine",
        choices=["python", "native", "rust"],
        default="python",
        help="Select healing engine tier: 'python', 'native', or 'rust'",
    )
    parser.add_argument(
        "--debug-stages",
        action="store_true",
        help="Display detailed execution timing for every pipeline stage",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="[PERFORMANCE] Output breakdown of bootstrap vs. execution time",
    )
    parser.add_argument(
        "--forensic-debug",
        action="store_true",
        help="[EXPERT] Enable sensitive forensic logs (PII Redacted)",
    )
    parser.add_argument(
        "--timing-file",
        type=str,
        default=None,
        metavar="FILE",
        help="[PERFORMANCE] Save performance profiling data to a JSON file",
    )


def add_standard_flags(parser: argparse.ArgumentParser):
    """
    Delegates to the core standard flag adder.
    Redirected via this module to maintain centralized flag management.
    """
    from yamlr.core.entrypoints.base import add_standard_flags as core_add_std
    core_add_std(parser)
