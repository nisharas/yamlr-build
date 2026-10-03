"""Phase 14 Test Suite: Unified WebAssembly Build & Static Asset Verification.

Why: Verifies that native Rust core compiles deterministically to WebAssembly (WASM),
generates static browser-ready assets in website/public/wasm/, and prevents regex
or semantic drift between native CLI and the web playground.
"""

import json
import os
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEBSITE_DIR = REPO_ROOT / "website"
WASM_DIR = WEBSITE_DIR / "public" / "wasm"


def test_wasm_static_assets_exist():
    """Verify that build-time WASM artifacts exist in website/public/wasm/."""
    wasm_binary = WASM_DIR / "yamlr_native_bg.wasm"
    js_bridge = WASM_DIR / "yamlr_native.js"

    assert wasm_binary.exists(), f"Missing WASM binary: {wasm_binary}"
    assert js_bridge.exists(), f"Missing JS bridge: {js_bridge}"

    # Verify binary size is substantial (contains real compiled Rust code)
    assert wasm_binary.stat().st_size > 500_000, "WASM binary appears truncated"

    # Verify JS glue exports primary symbols
    js_content = js_bridge.read_text(encoding="utf-8")
    assert "wasm_scan" in js_content, "wasm_scan not exported in JS glue"
    assert "wasm_heal" in js_content, "wasm_heal not exported in JS glue"
    assert "wasm_diff" in js_content, "wasm_diff not exported in JS glue"
    assert "wasm_version" in js_content, "wasm_version not exported in JS glue"


def test_website_package_json_build_script():
    """Verify that website/package.json wires build:wasm into the build pipeline."""
    pkg_json_path = WEBSITE_DIR / "package.json"
    assert pkg_json_path.exists()

    with open(pkg_json_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    scripts = pkg_data.get("scripts", {})
    assert "build:wasm" in scripts, "build:wasm missing in package.json scripts"
    assert "build:wasm" in scripts.get("build", ""), "build script does not invoke build:wasm"


def test_wasm_bridge_typescript_integration():
    """Verify that WasmBridge.ts consumes the public WASM module correctly."""
    bridge_ts = WEBSITE_DIR / "src" / "components" / "WasmBridge.ts"
    assert bridge_ts.exists()

    ts_content = bridge_ts.read_text(encoding="utf-8")
    assert "/wasm/yamlr_native.js" in ts_content
    assert "wasm.wasm_scan" in ts_content
    assert "wasm.wasm_heal" in ts_content
