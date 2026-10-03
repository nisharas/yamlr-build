import os
from pathlib import Path

# Use project-relative paths
ROOT = Path(__file__).resolve().parent.parent
batch_file = str(ROOT / "src/yamlr/ui/formatter_batch.py")
summary_file = str(ROOT / "src/yamlr/ui/formatter_summary.py")
formatter_file = str(ROOT / "src/yamlr/ui/formatter.py")

# Split formatter_batch.py
with open(batch_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if "def _print_summary_stats(" in line:
        start_idx = i
        break

if start_idx != -1:
    batch_lines = lines[:start_idx]
    summary_lines = lines[start_idx:]

    with open(batch_file, "w", encoding="utf-8") as f:
        f.writelines(batch_lines)

    summary_content = '''#!/usr/bin/env python3
"""
Formatter SUMMARY Mixin
-----------------------
Extracted to enforce <500 line modularity rule.
"""
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from yamlr.cli.commands.base import get_console

console = get_console()

class SummaryMixin:
    PRO_FIXABLE_RULES = {
        "rule/resource-requests", "rule/resource-limits",
        "rule/run-as-non-root", "rule/no-privileged", "rule/allow-privilege-escalation",
        "rule/unsafe-hostpath", "rule/host-network", "rule/read-only-root-fs",
        "rule/missing-liveness", "rule/missing-readiness",
        "rule/no-latest-tag",
        "rule/ghost-service", "rule/port-mismatch", "rule/service-no-selector",
        "rule/missing-configmap-target", "rule/broken-volume", "rule/ingress-broken",
        "rule/network-policy-missing", "rule/untrusted-registry"
    }

'''
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_content)
        f.writelines(summary_lines)

    with open(formatter_file, "r", encoding="utf-8") as f:
        fmt = f.read()

    if "SummaryMixin" not in fmt:
        fmt = fmt.replace(
            "from yamlr.ui.formatter_batch import BatchMixin",
            "from yamlr.ui.formatter_batch import BatchMixin\nfrom yamlr.ui.formatter_summary import SummaryMixin",
        )
        fmt = fmt.replace("ReportMixin, BatchMixin", "ReportMixin, BatchMixin, SummaryMixin")
        with open(formatter_file, "w", encoding="utf-8") as f:
            f.write(fmt)

# Split entrypoints/base.py
base_file = str(ROOT / "src/yamlr/core/entrypoints/base.py")
display_file = str(ROOT / "src/yamlr/core/entrypoints/display.py")

with open(base_file, "r", encoding="utf-8") as f:
    blines = f.readlines()

header_idx = -1
for i, line in enumerate(blines):
    if "def print_custom_header(" in line:
        header_idx = i
        break

if header_idx != -1:
    base_content = "".join(blines[:header_idx])
    display_content = "".join(blines[header_idx:])

    with open(base_file, "w", encoding="utf-8") as f:
        f.write(base_content)

    d_content = (
        """import platform
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.console import Group
from yamlr.core.bridge import YamlrBridge
from yamlr.core.context import HealContext
from .base import get_console, CORE_VERSION, CATALOG_VERSION

"""
        + display_content
    )

    with open(display_file, "w", encoding="utf-8") as f:
        f.write(d_content)

    for root, _, files in os.walk(str(ROOT / "src/yamlr/cli/commands")):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as cf:
                    content = cf.read()

                if "print_custom_header" in content or "print_version" in content:
                    if "from yamlr.core.entrypoints.display import" not in content:
                        content = content.replace(
                            "from yamlr.core.entrypoints.base import",
                            "from yamlr.core.entrypoints.display import print_custom_header, print_version\nfrom yamlr.core.entrypoints.base import",
                        )
                        with open(path, "w", encoding="utf-8") as cf:
                            cf.write(content)

print("Split complete.")
