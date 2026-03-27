"""
CLI OPTIONS AND EXTRACTION
-------------------------
Standardized data structures and logic for CLI flag extraction.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

@dataclass(slots=True)
class CliOptions:
    """
    Standard container for all common CLI options.
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
    sovereign: bool = False
    plain: bool = False
    evidence_dir: Optional[str] = None
    adapters_dir: Optional[str] = None
    risk_threshold: Optional[str] = None
    scout: bool = False
    use_rust: bool = False
    from_report: Optional[str] = None
    baseline: Optional[str] = None
    pro_preview: bool = False
    export: Optional[str] = None
    timing: bool = False
    timing_file: Optional[str] = None

def extract_cli_options(args, is_pro: bool, console=None) -> CliOptions:
    """
    Extracts and normalizes flags from argparse namespace.
    """
    from yamlr.core.entrypoints.base import get_console
    if console is None:
        console = get_console()

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
        sovereign=getattr(args, "sovereign", False),
        plain=getattr(args, "plain", False),
        evidence_dir=getattr(args, "evidence_dir", None),
        adapters_dir=getattr(args, "adapters_dir", None),
        risk_threshold=getattr(args, "risk_threshold", None),
        scout=getattr(args, "scout", False),
        use_rust=getattr(args, "use_rust", False),
        from_report=getattr(args, "from_report", None),
        baseline=getattr(args, "baseline", None),
        pro_preview=getattr(args, "pro_preview", False),
        export=getattr(args, "export", None),
        timing=getattr(args, "timing", False),
        timing_file=getattr(args, "timing_file", None)
    )

    # [HARDENING] Centralized Pro-Gating (Hardened v1.4 CapabilityShield)
    from yamlr.core.bridge import YamlrBridge
    caps = YamlrBridge.capabilities
    is_pro_effective = is_pro or options.pro_preview

    if options.harden and not is_pro_effective:
        YamlrBridge.notify_pro_required("Security Hardening (--harden)")
        options.harden = False

    if options.enforce_limits and not is_pro_effective:
        YamlrBridge.notify_pro_required("Resource Limit Enforcement (--enforce-limits)")
        options.enforce_limits = False

    if options.enforce_probes and not is_pro_effective:
        YamlrBridge.notify_pro_required("Advanced Probe Injection (--enforce-probes)")
        options.enforce_probes = False

    if options.sovereign and not is_pro_effective:
        YamlrBridge.notify_pro_required("Sovereign Sorting (--sovereign)")
        options.sovereign = False

    if options.fast and not is_pro_effective:
        YamlrBridge.notify_pro_required("Fast Native Scanner (--fast)")
        options.fast = False

    if options.fix_refs and not (caps.can_auto_fix_refs() or options.pro_preview):
        # Specific check for Auto-Repair as it's a Tier 1 wedge
        YamlrBridge.notify_pro_required("Cross-Resource Auto-Repair (--stub-refs)")
        options.fix_refs = False

    if getattr(args, "generate_receipts", False) and not (caps.produces_evidence_receipts() or options.pro_preview):
        YamlrBridge.notify_pro_required("Compliance Receipts (--generate-receipts)")
        # Note: we can't easily unset args.generate_receipts, but consumers check caps or options

    return options
