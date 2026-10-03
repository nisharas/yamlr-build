#!/usr/bin/env python3
"""Capture and verify exact native CLI/Python SDK development source inputs.

This is a reviewable snapshot, not a production release or an ownership attestation.
It includes named test-only signing fixtures needed to compile Rust tests.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

TREES = (
    "native_core/src",
    "native_core/catalog",
    "native_core/tests",
    "native_core/benches",
    "scripts/ci",
    "schemas",
)
FILES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "native_core/Cargo.toml",
    "native_core/Cargo.lock",
    "native_core/about.toml",
    "native_core/about.hbs",
    "native_core/deny.toml",
    "src/yamlr/__init__.py",
    "src/yamlr/__main__.py",
    "src/yamlr/_find_bin.py",
    "src/yamlr/version.py",
    "src/yamlr_native/__init__.py",
    "tests/verify_rust_parity.py",
)
MANIFEST = "SOURCE_MANIFEST.json"
LIMIT = 256 * 1024 * 1024
TEST_KEYS = {
    "native_core/tests/fixtures/licensing_test_private.pem",
    "native_core/tests/fixtures/licensing_test_public.pem",
}
PRODUCT_TREES = (
    "integrations",
    "vscode/src",
    "website/src",
    "website/public",
    "website/docs",
    "website/scripts",
    "infra",
    ".github",
    "actions",
    "python_wrapper",
)
PRODUCT_FILES = (
    "scripts/build_nuitka.py",
    "scripts/clean.py",
    "tools/entrypoint.sh",
    "action.yml",
    "Dockerfile",
    "Dockerfile.argocd-cmp",
    ".dockerignore",
    "Makefile",
    "VERSION",
    "install.sh",
    "install.ps1",
    "scripts/install.sh",
    "vscode/package.json",
    "vscode/package-lock.json",
    "vscode/tsconfig.json",
    "vscode/.vscodeignore",
    "vscode/LICENSE",
    "vscode/README.md",
    "vscode/extension-logo.png",
    "website/package.json",
    "website/package-lock.json",
    "website/next.config.js",
    "website/next-env.d.ts",
    "website/tsconfig.json",
    "website/postcss.config.js",
    "website/tailwind.config.js",
)
NATIVE_SCOPE = "native-cli-python-sdk-development-source"
PRODUCT_SCOPE = "all-product-development-source"
EXCLUDED_DIRS = {
    "__pycache__",
    "target",
    "node_modules",
    ".git",
    ".next",
    ".wrangler",
    "out",
    "dist",
    "bin",
    "audit_vsix",
    ".venv",
    "venv",
    "coverage",
}


def policy(scope: str) -> tuple[tuple, tuple]:
    if scope == NATIVE_SCOPE:
        return FILES, TREES
    if scope == PRODUCT_SCOPE:
        return FILES + PRODUCT_FILES, TREES + PRODUCT_TREES
    raise ValueError("Unsupported source snapshot scope")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def allowed(name: str, scope: str = NATIVE_SCOPE) -> bool:
    files, trees = policy(scope)
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        return False
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix in {
        ".pyc",
        ".log",
        ".exe",
        ".pyd",
        ".so",
        ".key",
        ".vsix",
        ".wasm",
        ".tsbuildinfo",
    }:
        return False
    if path.name == ".env" or path.name.startswith(".env."):
        return False
    if name.startswith("website/public/wasm/"):
        return False
    if path.suffix == ".pem" and name not in TEST_KEYS | {
        "native_core/src/security/public_key.pem"
    }:
        return False
    return name in files or any(name.startswith(tree + "/") for tree in trees)


def capture(root: Path, output: Path, scope: str = NATIVE_SCOPE) -> dict:
    root = root.resolve(strict=True)
    files, trees = policy(scope)
    resolved_output = output.resolve()
    if resolved_output.is_relative_to(root) and allowed(
        resolved_output.relative_to(root).as_posix(), scope
    ):
        raise ValueError("Snapshot output must be outside its selected source inputs")
    paths = [root / name for name in files]
    for tree in trees:
        directory = root / tree
        if not directory.is_dir():
            raise ValueError(f"Required source directory missing: {tree}")
        for current, directories, names in os.walk(directory, followlinks=False):
            for child in directories:
                child_path = Path(current) / child
                if child not in EXCLUDED_DIRS and child_path.is_symlink():
                    raise ValueError(
                        f"Source directory link is forbidden: {child_path.relative_to(root)}"
                    )
            directories[:] = sorted(
                child for child in directories if child not in EXCLUDED_DIRS
            )
            paths.extend(Path(current) / name for name in names)
    contents = {}
    total = 0
    for path in sorted(set(paths)):
        name = path.relative_to(root).as_posix()
        if not allowed(name, scope):
            continue
        if path.is_symlink() or path.resolve().is_relative_to(root) is False:
            raise ValueError(f"Source link escapes snapshot policy: {name}")
        if not path.is_file():
            raise ValueError(f"Required source file missing: {name}")
        data = path.read_bytes()
        if name not in TEST_KEYS and re.search(
            rb"(?m)^-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", data
        ):
            raise ValueError(
                f"Private key material is not an allowed source input: {name}"
            )
        total += len(data)
        if total > LIMIT:
            raise ValueError("Source snapshot exceeds size limit")
        contents[name] = data
    inventory = [
        {"path": name, "size": len(data), "sha256": sha(data)}
        for name, data in sorted(contents.items())
    ]
    manifest = {
        "format_version": 1,
        "scope": scope,
        "source_sha256": sha(canonical(inventory)),
        "files": inventory,
        "limitations": [
            "Not a reviewed Git release revision",
            "Generated packages and local credentials are excluded; external build inputs require separate inventory",
            "Includes named test-only signing fixtures; not a distribution artifact",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted({**contents, MANIFEST: canonical(manifest)}.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, data)
    return manifest


def verify(snapshot: Path | bytes) -> dict:
    if (
        len(snapshot) if isinstance(snapshot, bytes) else snapshot.stat().st_size
    ) > LIMIT:
        raise ValueError("Snapshot archive exceeds size limit")
    source = io.BytesIO(snapshot) if isinstance(snapshot, bytes) else snapshot
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError("Snapshot has duplicate entries or no manifest")
        if sum(member.file_size for member in members) > LIMIT:
            raise ValueError("Snapshot exceeds size limit")
        if archive.getinfo(MANIFEST).file_size > 4 * 1024 * 1024:
            raise ValueError("Snapshot manifest exceeds size limit")
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get("format_version") != 1:
            raise ValueError("Unsupported source snapshot manifest")
        scope = manifest.get("scope")
        files, trees = policy(scope)
        inventory = manifest["files"]
        if sha(canonical(inventory)) != manifest["source_sha256"]:
            raise ValueError("Source inventory digest mismatch")
        expected = [item["path"] for item in inventory]
        if len(expected) != len(set(expected)) or set(names) != set(expected) | {
            MANIFEST
        }:
            raise ValueError("Snapshot file inventory mismatch")
        if not set(files).issubset(expected):
            raise ValueError("Snapshot lacks required build inputs")
        if any(
            not any(name.startswith(tree + "/") for name in expected) for tree in trees
        ):
            raise ValueError("Snapshot lacks a required source tree")
        for item in inventory:
            name = item["path"]
            member = archive.getinfo(name)
            if (
                not allowed(name, scope)
                or member.is_dir()
                or stat.S_ISLNK(member.external_attr >> 16)
            ):
                raise ValueError(f"Forbidden snapshot entry: {name}")
            data = archive.read(member)
            if name not in TEST_KEYS and re.search(
                rb"(?m)^-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", data
            ):
                raise ValueError(
                    f"Private key material is not an allowed source input: {name}"
                )
            if len(data) != item["size"] or sha(data) != item["sha256"]:
                raise ValueError(f"Source content digest mismatch: {name}")
        return manifest


def unpack(snapshot: Path, destination: Path) -> dict:
    if snapshot.stat().st_size > LIMIT:
        raise ValueError("Snapshot archive exceeds size limit")
    snapshot_bytes = snapshot.read_bytes()
    manifest = verify(snapshot_bytes)
    # Use the bytes that were verified rather than reopening a replaceable path.
    with zipfile.ZipFile(io.BytesIO(snapshot_bytes)) as archive:
        destination.mkdir(parents=True, exist_ok=False)
        for name in archive.namelist():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("capture")
    create.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    create.add_argument("--output", type=Path, required=True)
    create.add_argument(
        "--scope", choices=[NATIVE_SCOPE, PRODUCT_SCOPE], default=NATIVE_SCOPE
    )
    check = commands.add_parser("verify")
    check.add_argument("snapshot", type=Path)
    extract = commands.add_parser("unpack")
    extract.add_argument("snapshot", type=Path)
    extract.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        manifest = capture(args.root, args.output, args.scope)
    elif args.command == "unpack":
        manifest = unpack(args.snapshot, args.destination)
    else:
        manifest = verify(args.snapshot)
    print(f"{len(manifest['files'])} source files; SHA256 {manifest['source_sha256']}")


if __name__ == "__main__":
    main()
