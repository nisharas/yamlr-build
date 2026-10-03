"""CLI handler for canonical manifest formatting and instant repair (k8sfmt / yamlfix).

Why: Separates formatting and zero-flag fixing logic from core orchestration,
ensuring strict adherence to the 500-line modularity limit while enabling
seamless POSIX Unix pipe composability.
"""
import os
import sys
from pathlib import Path
from typing import Any

from yamlr import heal_yaml
from yamlr.core.scanner import _discover_manifests

GOLDEN_ORDER = ["apiVersion", "kind", "metadata", "spec", "data", "status"]


def cmd_fmt_dispatch(args: Any) -> int:
    """Dispatches yamlr fmt command (reordering keys, formatting layout)."""
    target = getattr(args, "path", ".") or "."
    write_in_place = getattr(args, "write", False) or getattr(args, "w", False)

    # POSIX / Unix Pipe Composability
    if target == "-" or not sys.stdin.isatty() and not os.path.exists(target):
        content = sys.stdin.read()
        formatted = format_yaml_string(content)
        sys.stdout.write(formatted)
        return 0

    target_path = Path(target).resolve()
    if target_path.is_file():
        content = target_path.read_text(encoding="utf-8", errors="ignore")
        formatted = format_yaml_string(content)
        if write_in_place:
            if formatted != content:
                target_path.write_text(formatted, encoding="utf-8")
                print(str(target_path))
        else:
            sys.stdout.write(formatted)
        return 0

    if target_path.is_dir():
        files = _discover_manifests(str(target_path))
        diff_count = 0
        for fpath in files:
            p = Path(fpath)
            content = p.read_text(encoding="utf-8", errors="ignore")
            formatted = format_yaml_string(content)
            if formatted != content:
                diff_count += 1
                if write_in_place:
                    p.write_text(formatted, encoding="utf-8")
                    print(str(p))
                else:
                    print(str(p))
        return 1 if not write_in_place and diff_count > 0 else 0

    print(f"[ERROR] Target path '{target}' does not exist.", file=sys.stderr)
    return 2


def cmd_fix_dispatch(args: Any) -> int:
    """Dispatches yamlr fix command (zero-flag non-destructive auto-repair)."""
    target = getattr(args, "path", ".") or "."

    # POSIX / Unix Pipe Composability
    if target == "-" or not sys.stdin.isatty() and not os.path.exists(target):
        content = sys.stdin.read()
        heal_res = heal_yaml(content)
        sys.stdout.write(heal_res.healed_yaml)
        return 0

    target_path = Path(target).resolve()
    if target_path.is_file():
        content = target_path.read_text(encoding="utf-8", errors="ignore")
        heal_res = heal_yaml(content)
        if heal_res.had_changes:
            target_path.write_text(heal_res.healed_yaml, encoding="utf-8")
            print(f"[FIXED] {target_path}")
        return 0

    if target_path.is_dir():
        files = _discover_manifests(str(target_path))
        fixed_count = 0
        for fpath in files:
            p = Path(fpath)
            content = p.read_text(encoding="utf-8", errors="ignore")
            heal_res = heal_yaml(content)
            if heal_res.had_changes:
                fixed_count += 1
                p.write_text(heal_res.healed_yaml, encoding="utf-8")
                print(f"[FIXED] {p}")
        return 0

    print(f"[ERROR] Target path '{target}' does not exist.", file=sys.stderr)
    return 2


def format_yaml_string(content: str) -> str:
    """Formats YAML string with official Kubernetes schema key ordering."""
    try:
        import yamlr_native
        if hasattr(yamlr_native, "native_format_yaml"):
            return yamlr_native.native_format_yaml(content)
        return content
    except Exception:
        return content
