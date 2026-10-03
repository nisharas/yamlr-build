#!/usr/bin/env python3
"""Package and verify signed native artifacts without a hosting provider.

Requires cryptography. Verification trusts only an explicitly supplied public key;
it does not discover a key from the artifact or its download location.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

TARGETS = {
    "linux-x86_64",
    "linux-aarch64",
    "macos-x86_64",
    "macos-aarch64",
    "windows-x86_64",
}
VERSION = re.compile(
    r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?\Z"
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def load_small(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Metadata exceeds size limit: {path.name}")
    return data


def validate_manifest(data: dict) -> None:
    required = {
        "format_version",
        "version",
        "target",
        "profile",
        "source_revision",
        "source_dirty",
        "artifact",
        "sha256",
        "size_bytes",
    }
    if (
        not isinstance(data, dict)
        or set(data) != required
        or data["format_version"] != 1
    ):
        raise ValueError("Invalid offline release manifest")
    if not isinstance(data["version"], str) or not VERSION.fullmatch(data["version"]):
        raise ValueError("Release version must be a pinned semantic version")
    if data["target"] not in TARGETS or data["profile"] not in {"debug", "release"}:
        raise ValueError("Unsupported release target or profile")
    if not isinstance(data["source_revision"], str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", data["source_revision"]
    ):
        raise ValueError("A source revision hash is required")
    if type(data["source_dirty"]) is not bool:
        raise ValueError("Source dirty state must be explicit")
    expected = f"yamlr-{data['version']}-{data['target']}.zip"
    if (
        data["artifact"] != expected
        or not isinstance(data["sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", data["sha256"])
    ):
        raise ValueError("Invalid artifact name or digest")
    if type(data["size_bytes"]) is not int or data["size_bytes"] <= 0:
        raise ValueError("Invalid artifact size")


def package(
    binary: Path,
    notices: Path,
    sbom: Path,
    license_file: Path,
    signing_key: Path,
    output: Path,
    *,
    version: str,
    target: str,
    revision: str,
    profile: str = "release",
    dirty: bool = False,
) -> Path:
    name = f"yamlr-{version}-{target}.zip"
    manifest = dict(
        format_version=1,
        version=version,
        target=target,
        profile=profile,
        source_revision=revision,
        source_dirty=dirty,
        artifact=name,
        sha256="0" * 64,
        size_bytes=1,
    )
    validate_manifest(manifest)
    if profile == "release" and dirty:
        raise ValueError(
            "Production packaging requires a reviewed clean source revision"
        )
    key = serialization.load_pem_private_key(
        load_small(signing_key, 16384), password=None
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Offline release signing requires a dedicated Ed25519 key")
    bill = json.loads(load_small(sbom, 16 * 1024 * 1024))
    if (
        not isinstance(bill, dict)
        or bill.get("bomFormat") != "CycloneDX"
        or not bill.get("specVersion")
    ):
        raise ValueError("A CycloneDX SBOM is required")
    if (
        not notices.is_file()
        or notices.stat().st_size == 0
        or not license_file.is_file()
        or license_file.stat().st_size == 0
    ):
        raise ValueError("Nonempty license and third-party notices are required")
    if not binary.is_file() or binary.stat().st_size == 0:
        raise ValueError("A built native binary is required")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / name
    metadata = archive.with_suffix(".manifest.json")
    signature = archive.with_suffix(".manifest.sig")
    if any(path.exists() for path in (archive, metadata, signature)):
        raise ValueError("Refusing to overwrite an existing release candidate")
    executable = "yamlr.exe" if target.startswith("windows-") else "yamlr"
    created: list[Path] = []
    try:
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            created.append(archive)
            for member, path, mode in [
                (executable, binary, 0o755),
                ("LICENSE", license_file, 0o644),
                ("THIRD_PARTY_NOTICES.txt", notices, 0o644),
                ("sbom.cdx.json", sbom, 0o644),
            ]:
                info = zipfile.ZipInfo(member, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100000 | mode) << 16
                with path.open("rb") as source, bundle.open(info, "w") as dest:
                    while block := source.read(1024 * 1024):
                        dest.write(block)
        # Reuse the release private-key guard before signing any candidate.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from check_release_artifacts import scan_path

        failures: list[str] = []
        scan_path(archive, failures)
        if failures:
            raise ValueError("Private-key policy rejected the packaged artifact")
        manifest.update(sha256=digest(archive), size_bytes=archive.stat().st_size)
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        with metadata.open("xb") as stream:
            created.append(metadata)
            stream.write(payload)
        with signature.open("xb") as stream:
            created.append(signature)
            stream.write(key.sign(payload))
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return archive


def verify(
    archive: Path,
    metadata: Path,
    signature: Path,
    trusted_key: Path,
    *,
    version: str,
    target: str,
    allow_development: bool = False,
) -> dict:
    public = serialization.load_pem_public_key(load_small(trusted_key, 16384))
    if not isinstance(public, Ed25519PublicKey):
        raise ValueError("An explicitly trusted Ed25519 public key is required")
    payload = load_small(metadata, 16384)
    signed = load_small(signature, 64)
    try:
        public.verify(signed, payload)
    except InvalidSignature as error:
        raise ValueError("Release manifest signature is invalid") from error
    data = json.loads(payload)
    validate_manifest(data)
    if data["version"] != version or data["target"] != target:
        raise ValueError(
            "Release version or target does not match the pinned expectation"
        )
    if not allow_development and (data["profile"] != "release" or data["source_dirty"]):
        raise ValueError("Development artifacts are not production releases")
    if (
        archive.name != data["artifact"]
        or archive.stat().st_size != data["size_bytes"]
        or digest(archive) != data["sha256"]
    ):
        raise ValueError("Artifact does not match the signed manifest")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("package")
    for name in ["binary", "notices", "sbom", "license-file", "signing-key", "output"]:
        pack.add_argument("--" + name, type=Path, required=True)
    pack.add_argument("--revision", required=True)
    pack.add_argument("--profile", choices=["debug", "release"], default="release")
    pack.add_argument("--source-dirty", action="store_true")
    check = commands.add_parser("verify")
    for name in ["archive", "manifest", "signature", "trusted-key"]:
        check.add_argument("--" + name, type=Path, required=True)
    check.add_argument("--allow-development", action="store_true")
    for command in [pack, check]:
        command.add_argument("--version", required=True)
        command.add_argument("--target", choices=sorted(TARGETS), required=True)
    args = parser.parse_args()
    try:
        if args.command == "package":
            if args.profile == "release":
                repository = Path(__file__).resolve().parents[2]
                head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repository,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout.strip()
                status = subprocess.run(
                    ["git", "status", "--porcelain", "--untracked-files=all"],
                    cwd=repository,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout
                if head != args.revision or status.strip() or args.source_dirty:
                    raise ValueError(
                        "Production packaging requires the exact clean current Git revision"
                    )
            archive = package(
                args.binary,
                args.notices,
                args.sbom,
                args.license_file,
                args.signing_key,
                args.output,
                version=args.version,
                target=args.target,
                revision=args.revision,
                profile=args.profile,
                dirty=args.source_dirty,
            )
            print(f"Packaged signed artifact: {archive}")
        else:
            verify(
                args.archive,
                args.manifest,
                args.signature,
                args.trusted_key,
                version=args.version,
                target=args.target,
                allow_development=args.allow_development,
            )
            print(f"Verified pinned artifact: {args.archive}")
    except (
        OSError,
        ValueError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as error:
        print(f"Offline release failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
