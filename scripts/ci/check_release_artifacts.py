#!/usr/bin/env python3
"""Reject private-key files or PEM material from release artifacts."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import BinaryIO


PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN DSA PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
)
PRIVATE_KEY_NAMES = (
    "private_key",
    "private-key",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_xmss",
)
CHUNK_SIZE = 1024 * 1024
OVERLAP = max(map(len, PRIVATE_KEY_MARKERS)) - 1


def has_private_key_name(name: str) -> bool:
    normalized = name.replace("\\", "/").casefold()
    basename = normalized.rsplit("/", 1)[-1]
    return any(fragment in basename for fragment in PRIVATE_KEY_NAMES) or basename.endswith(".key")


def stream_contains_private_key(stream: BinaryIO) -> bool:
    tail = b""
    while chunk := stream.read(CHUNK_SIZE):
        data = tail + chunk
        if any(marker in data for marker in PRIVATE_KEY_MARKERS):
            return True
        tail = data[-OVERLAP:]
    return False


def scan_path(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"Artifact path does not exist: {path}")
        return

    files = sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]
    if not files:
        failures.append(f"Artifact path contains no files: {path}")
        return

    for artifact in files:
        if has_private_key_name(artifact.name):
            failures.append(f"Private-key-like filename in artifact: {artifact}")
            continue

        try:
            if zipfile.is_zipfile(artifact):
                with zipfile.ZipFile(artifact) as archive:
                    for member in archive.infolist():
                        if member.is_dir():
                            continue
                        if has_private_key_name(member.filename):
                            failures.append(f"Private-key-like filename in archive: {artifact}!{member.filename}")
                        else:
                            with archive.open(member) as stream:
                                if stream_contains_private_key(stream):
                                    failures.append(f"Private-key PEM material in archive: {artifact}!{member.filename}")
            elif tarfile.is_tarfile(artifact):
                with tarfile.open(artifact, "r:*") as archive:
                    for member in archive.getmembers():
                        if not member.isfile():
                            continue
                        if has_private_key_name(member.name):
                            failures.append(f"Private-key-like filename in archive: {artifact}!{member.name}")
                            continue
                        stream = archive.extractfile(member)
                        if stream is not None:
                            with stream:
                                if stream_contains_private_key(stream):
                                    failures.append(f"Private-key PEM material in archive: {artifact}!{member.name}")
            else:
                with artifact.open("rb") as stream:
                    if stream_contains_private_key(stream):
                        failures.append(f"Private-key PEM material in artifact: {artifact}")
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
            failures.append(f"Unable to inspect artifact '{artifact}': {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Artifact files or directories to inspect")
    args = parser.parse_args()

    failures: list[str] = []
    for path in args.paths:
        scan_path(path, failures)

    if failures:
        for failure in failures:
            print(f"[ERROR] {failure}", file=sys.stderr)
        return 1

    print("[OK] No private-key filenames or PEM private-key material found in release artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
