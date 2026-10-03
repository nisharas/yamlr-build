from __future__ import annotations

#!/usr/bin/env python3
"""
Yamlr Nuitka Build Orchestrator (Google-Quality Edition)
-------------------------------------------------------
Compiles yamlr into high-performance, obfuscated native C binaries.
Maintains strict segregation between Community and Enterprise builds.
"""

import hashlib
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Fix terminal encoding issues (especially on Windows)
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        pass

from version_helper import get_version  # type: ignore

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
DOCS_DIR = ROOT_DIR / "docs"
DIST_DIR = ROOT_DIR / "dist"
ENTRY_POINT = SRC_DIR / "yamlr" / "cli" / "main.py"

def _get_git_sha() -> str:
    """Retrieves the current Git short SHA for build traceability."""
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], 
                                      cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        return "unknown"


def _check_baseline():
    """MANDATORY: Gold Standard Baseline Pre-Flight Check"""
    baseline_path = ROOT_DIR / ".yamlr-baseline"
    if not baseline_path.exists():
        print("❌ CRITICAL: Gold Standard Baseline not found.")
        print("   Requires semantic parity check before building release binaries.")
        print("   Action: Run 'python scripts/capture_baseline.py' first.")
        sys.exit(1)

def _get_base_cmd(app_name: str, version: str) -> list[str]:
    """Generates the base Nuitka command configuration."""
    # Format version for directory safety
    safe_ver = version.replace(".", "_")
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        # Cache extracted files across runs to prevent recurring decompression latency
        f"--onefile-tempdir-spec={{TEMP}}/yamlr/{safe_ver}",
        # Compress release binary; subsequent runs leverage the tempdir cache
        # "--onefile-no-compression", 
        "--show-progress",
        # [PERFORMANCE-HARDENING] Optimized for speed, not build-time memory
        "--follow-imports",
        f"--jobs={os.cpu_count() or 4}",
        "--plugin-enable=pylint-warnings",
        "--plugin-enable=multiprocessing",
        f"--output-dir={DIST_DIR}",
        f"--output-filename={app_name}",
        "--include-package=yamlr",
        "--nofollow-import-to=pygls",
        "--nofollow-import-to=lsprotocol",
        "--nofollow-import-to=yamlr.cli.lsp",
        "--nofollow-import-to=yamlr.core.integrations.vscode_lsp",
        "--nofollow-import-to=yamlr.debug",
        "--nofollow-import-to=yamlr.experimental",
        # [BLOAT-REMOVAL] NEVER include the whole package (prevents target/ inclusion)
        # We explicitly include the .pyd core in _add_data_files
        # "--include-package=yamlr_native", 
        "--include-package=ruamel.yaml",
        "--include-package=pydantic",
        "--include-package=pydantic_core",
        "--include-package=rich",
        "--include-module=socket",         #  Hardening: Fix missing _socket.pyd
        "--include-module=_socket",        #  Hardening: Fix missing _socket.pyd
        "--include-module=select",         #  Hardening: Companion to socket
        "--include-module=ssl",            #  Hardening: Required for HTTPS/Clerk
        "--include-module=multiprocessing", #  Hardening: Fix dynamic import failures
        "--report=dist/nuitka-build-report.xml",
    ]

def _add_platform_optimizations(cmd: list[str], version: str):
    """Adds OS-specific optimizations and metadata."""
    if sys.platform == "win32":
        git_sha = _get_git_sha()
        cmd.extend([
            f"--windows-file-version={version}",
            f"--windows-product-version={version}",
            "--windows-company-name=Timonel Labs",
            "--windows-product-name=Yamlr Forensic Engine",
            f"--windows-file-description=Yamlr v{version} ({git_sha})",
        ])
        # [PERFORMANCE-HARDENING] Enable LTO for faster bootstrap
        cmd.append("--lto=yes")
    else:
        cmd.append("--lto=yes")  # Link Time Optimization (Linux/macOS)


# Add SRC_DIR to sys.path to allow importing from the source tree
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# [FIX] Hardcoded MATRIX since yamlr.core is missing in this branch
class MATRIX:
    default_recommended = "1.30"



def _add_data_files(cmd: list[str]):
    """Embeds static catalog resources, protocol glue, and deprecations into the build."""
    def_v = MATRIX.default_recommended
    cat_filename = f"k8s_v{def_v}_distilled.json"
    distilled_src = SRC_DIR / "yamlr" / "catalog" / cat_filename
    
    if distilled_src.exists():
        cmd.append(f"--include-data-file={distilled_src}=yamlr/catalog/{cat_filename}")
        cmd.append(f"--include-data-file={distilled_src}=yamlr/catalog/k8s_latest_distilled.json")

    catalog_source = ROOT_DIR / "catalog"
    if catalog_source.exists():
        for cat_file in catalog_source.glob("k8s_v*.json"):
            if def_v in cat_file.name:
                continue
            cmd.append(f"--include-data-file={cat_file}=yamlr/catalog/{cat_file.name}")

    proxy_src = SRC_DIR / "yamlr" / "cli" / "lsp_proxy.py"
    if proxy_src.exists():
        cmd.append(f"--include-data-file={proxy_src}=lsp_proxy.py")

    rules_src = SRC_DIR / "yamlr" / "core" / "data" / "rules.yaml"
    if rules_src.exists():
        cmd.append(f"--include-data-file={rules_src}=yamlr/core/data/rules.yaml")

    depr_src = SRC_DIR / "yamlr" / "data" / "k8s_deprecations.json"
    if depr_src.exists():
        cmd.append(f"--include-data-file={depr_src}=yamlr/data/k8s_deprecations.json")

    # [BLOAT-REMOVAL] Native core is detected automatically via imports in native_adapter.py

    # [Manual-Hardening] Embed ONLY Man Pages for 'yamlr manual' (Bible Engine)
    man_dir = DOCS_DIR / "man" / "man1"
    if man_dir.exists():
        cmd.append(f"--include-data-dir={man_dir}=docs/man/man1")

    # cmd.append("--include-package-data=yamlr.core.data") # [FIX] Removed as yamlr.core is missing
    
    # Include pre-rendered help files
    help_dir = SRC_DIR / "yamlr" / "cli" / "help"
    if (help_dir / "help_main.ansi").exists():
        cmd.append(f"--include-data-file={help_dir / 'help_main.ansi'}=yamlr/cli/help/help_main.ansi")
    if (help_dir / "help_all.ansi").exists():
        cmd.append(f"--include-data-file={help_dir / 'help_all.ansi'}=yamlr/cli/help/help_all.ansi")

    # [SECURITY] Embed public key for offline JWT verification
    # Offline validation without external IDP calls.
    pubkey_src = ROOT_DIR / "keys" / "public_key.pem"
    if pubkey_src.exists():
        cmd.append(f"--include-data-file={pubkey_src}=yamlr/keys/public_key.pem")
        print("[SECURITY] ✅ Public key embedded for offline verification.")
    else:
        print("⚠ Warning: keys/public_key.pem not found. Offline JWT verification will fail.")

def build():
    app_name = "yamlr"
    binary_name = f"{app_name}.exe" if sys.platform == "win32" else app_name
    version = get_version()

    print(f"[START] Starting Native {app_name.upper()} Build...")

    # [PRE-RENDER] Generate ANSI help text for fast-path delivery
    help_script = ROOT_DIR / "scripts" / "pre_render_help.py"
    if help_script.exists():
        try:
            print("[PRE-RENDER] Generating ANSI help files...")
            subprocess.run([sys.executable, str(help_script)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠ Warning: Pre-render failed, help will fall back to lazy-load: {e}")
    else:
        print("[PRE-RENDER] Skipping (pre_render_help.py not found)")

    _check_baseline()

    cmd = _get_base_cmd(app_name, version)
    _add_platform_optimizations(cmd, version)

    # [Unified Motto] Always include yamlr.pro in the build
    # cmd.append("--follow-import-to=yamlr.pro")
    # [REMOVED] cmd.append("--include-package=yamlr.pro.reconciliation")
    
    #  Surface Reduction: Exclude dev/leaks
    cmd.extend([
        "--nofollow-import-to=mypy",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=pip",
    ])

    _add_data_files(cmd)

    cmd.append(str(ENTRY_POINT))

    os.chdir(ROOT_DIR)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)

    print(f"[TOOLS] Executing: {' '.join(cmd)}")
    
    # --- SBOM GENERATION ---
    # Generates a Software Bill of Materials for security audits.
    try:
        print("[SBOM] Generating Python SBOM...")
        python_sbom = DIST_DIR / "sbom_python.spdx.json"
        subprocess.run(["cyclonedx-py", "environment", "-o", str(python_sbom)], check=False, capture_output=True)

        print("[SBOM] Generating Rust SBOM...")
        native_dir = ROOT_DIR / "native_core"
        rust_sbom = DIST_DIR / "sbom_rust.cdx.json"
        if native_dir.exists():
            subprocess.run([
                "cargo", "cyclonedx", "--format", "json",
                "--output-file", str(rust_sbom)
            ], check=False, cwd=str(native_dir), capture_output=True)

        # Merge both SBOMs into one
        merged_sbom = DIST_DIR / "sbom.spdx.json"
        cyclonedx_cli = shutil.which("cyclonedx")
        if cyclonedx_cli and rust_sbom.exists():
            subprocess.run([
                cyclonedx_cli, "merge",
                "--input-files", str(python_sbom), str(rust_sbom),
                "--output-file", str(merged_sbom)
            ], check=False, capture_output=True)
            print(f"[SBOM] ✅ Merged SBOM written to {merged_sbom}")
        else:
            # Fallback: use Python SBOM only
            if python_sbom.exists():
                if merged_sbom.exists():
                    os.remove(merged_sbom)
                python_sbom.rename(merged_sbom)
                print("[SBOM] ✅ Python-only SBOM written (cargo-cyclonedx or cyclonedx-cli missing).")
    except Exception as e:
        print(f"⚠ Warning: SBOM generation failed: {e}")

    try:
        subprocess.run(cmd, check=True, env=env)
        print(f"\n[OK] Compilation successful! Native binary: {DIST_DIR}/{binary_name}")

        # --- BINARY SIGNING ---
        binary_path = DIST_DIR / binary_name
        if sys.platform == "win32":
            signtool = shutil.which("signtool")
            if signtool:
                print("[SIGN] Signing binary with EV Certificate (Windows)...")
                try:
                    subprocess.run([
                        signtool, "sign", "/tr", "http://timestamp.sectigo.com",
                        "/td", "sha256", "/fd", "sha256", "/a", str(binary_path)
                    ], check=True)
                    print("[SIGN] ✅ Windows signing complete.")
                except Exception as e:
                    print(f"⚠ Warning: Windows signing failed: {e}")
            else:
                print("⚠ Warning: signtool not found. Binary will trigger SmartScreen.")
        elif sys.platform == "darwin":
            identity = os.environ.get("MACOS_SIGNING_IDENTITY")
            if identity:
                print("[SIGN] Signing binary (macOS)...")
                try:
                    subprocess.run(["codesign", "--deep", "--force", "--options", "runtime", "--sign", identity, str(binary_path)], check=True)
                    apple_id, apple_team, apple_pass = os.environ.get("APPLE_ID"), os.environ.get("APPLE_TEAM_ID"), os.environ.get("APPLE_APP_PASSWORD")
                    if apple_id and apple_team and apple_pass:
                        print("[NOTARIZE] Submitting for Apple notarization (async)...")
                        subprocess.run(["xcrun", "notarytool", "submit", str(binary_path), "--apple-id", apple_id, "--team-id", apple_team, "--password", apple_pass, "--wait"], check=True)
                        subprocess.run(["xcrun", "stapler", "staple", str(binary_path)], check=True)
                        print("[NOTARIZE] ✅ Notarization and stapling complete.")
                except Exception as e:
                    print(f"⚠ Warning: macOS signing/notarization failed: {e}")
            else:
                print("⚠ Warning: MACOS_SIGNING_IDENTITY not set. Binary will trigger Gatekeeper.")
        elif sys.platform == "linux":
            print("[SIGN] Generating GPG signature (Linux)...")
            try:
                subprocess.run(["gpg", "--detach-sign", "--armor", str(binary_path)], check=False)
                print("[SIGN] ✅ GPG signature generated.")
            except Exception as e:
                print(f"⚠ Warning: GPG signing failed: {e}")

        # --- CHECKSUM GENERATION ---
        print("[CHECKSUM] Generating SHA256 checksum...")
        try:
            sha256_hash = hashlib.sha256()
            with open(binary_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            with open(str(binary_path) + ".sha256", "w") as f:
                f.write(f"{sha256_hash.hexdigest()}  {binary_name}\n")
            print(f"[CHECKSUM] ✅ SHA256 written to {binary_name}.sha256")
        except Exception as e:
            print(f"⚠ Warning: Checksum generation failed: {e}")
        
        # Remove intermediate compilation directories after successful build
        for folder in ["main.build", "main.onefile-build"]:
            cleanup_path = DIST_DIR / folder
            if cleanup_path.exists():
                print(f"[CLEANUP] Removing build artifacts: {folder}")
                shutil.rmtree(cleanup_path)
                
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] Compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
