"""
Shared Help Blocks for Yamlr CLI.

Why: Prevents drift between scan, heal, and toolbox help modules.
     Ensures 'Universal Expert Flags' are documented identically.
"""

from __future__ import annotations

__all__ = ["print_shared_analysis_options", "print_semantic_protection_options"]

def print_shared_analysis_options(console, show_all: bool = False):
    """Prints standard analysis flags (kube-version, max-depth, etc.)."""
    console.print("  --kube-version V    Force target K8s version (alias: --k8s-version)")
    console.print("  --output FORMAT     Report format (text, json, sarif)")
    console.print("  --fail-on CHOICE    CI/CD Gate: Exit 1 if found (any/warning/error)")
    console.print("  -q, --quiet         Minimal output (CI/CD mode: errors + exit code)")
    
    if show_all:
        console.print("  --max-depth N       Recursion depth (default: 10)")
        console.print("  --ext LIST          Extensions (default: .yaml,.yml). Supports .tf")
        console.print("  -s, --summary-only  Show aggregate stats for batches")
        console.print("  --concurrency N     Number of parallel worker processes")
        console.print("  --catalog PATH      Path to custom K8s schema catalog (bundled by default)")
        console.print("  --identity-mode M   Identity Style: 'infer' (default) or 'strict'")
        console.print("  --verbose           Show detailed execution logs and engine stages")
        console.print("  --strict            Enable strict schema validation")
        console.print("  --compact           Output with minimal whitespace")
        console.print("  --risk-threshold R  Exit 1 if finding meets/exceeds risk (high/medium/low)")
        console.print("  --stream-to FILE    ULTRA-SCALE: Stream incremental results to NDJSON")
        console.print("  -p, --plain         ASCII-only output mode (Recommended for Logs)")

def print_semantic_protection_options(console, is_heal: bool = False, show_all: bool = False):
    """Prints semantic & protection flags (harden, limits, etc.)."""
    if not show_all:
        return

    console.print("\n[bold cyan]SEMANTIC & PROTECTION[/bold cyan]")
    verb = "Apply" if is_heal else "Audit for"
    console.print(f"  --harden            {verb} security hardening & PSS baseline (Pro)")
    console.print(f"  --enforce-limits    {verb} CPU/Memory requests & limits defined")
    console.print(f"  --fix-tags          {verb} and remediate mutable image tags (e.g. :latest)")
    console.print(f"  --enforce-probes    {verb} Liveness/Readiness probes")
    console.print("  --check-deprecations Audit for and record deprecated Kubernetes APIs")
    console.print("  --enforce-namespace  Auto-inject default namespace if missing")
    console.print("  --cpu-limit L       Override default CPU limit (e.g. 500m)")
    console.print("  --mem-limit L       Override default Memory limit (e.g. 512Mi)")
    console.print("  --namespace NS      Default namespace for generated resources")
    console.print("  --health-threshold N Min score to consider 'Healthy' (default: 70)")
    
    if is_heal:
        console.print("  --stub-refs [TYPE]  Generate missing resources via filter")
        console.print("  --fix-refs           [PRO] Cross-Resource Auto-Fix selector/port/stubs")
        console.print("  --unsafe [TYPE]     Allow healing of sensitive resources (e.g. Secret)")

    console.print("  --sovereign          [AESTHETICS] Enable high-fidelity sovereign export (Pro)")
    console.print("  --fast               [ACCELERATION] Enable lightning-fast scanning via Rust (Pro)")
