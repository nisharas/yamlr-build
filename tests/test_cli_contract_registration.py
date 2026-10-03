"""Every command routed by the native dispatcher must appear in parity checks."""

import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_every_dispatch_name_has_help_and_unknown_argument_parity():
    source = (ROOT / "native_core/src/cli/dispatch.rs").read_text(encoding="utf-8")
    routing = source.split("match command.as_str() {", 1)[1].split("        _ => {", 1)[
        0
    ]
    arms = re.findall(r'^\s*("[^"]+"(?:\s*\|\s*"[^"]+")*)\s*=>', routing, re.MULTILINE)
    names = {name for arm in arms for name in re.findall(r'"([^"]+)"', arm)}
    tree = ast.parse((ROOT / "tests/verify_rust_parity.py").read_text(encoding="utf-8"))
    declarations = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "SUPPORTED_COMMANDS"
            for target in node.targets
        )
    ]
    assert len(declarations) == 1
    cases = ast.literal_eval(declarations[0].value)
    assert len(cases) == len(set(cases))
    assert names == set(
        cases
    ), f"Dispatch/parity mismatch: {names.symmetric_difference(cases)}"
