#!/usr/bin/env python3
"""Prepare an offline Rust dependency inventory and notice texts for review.

Input is cargo metadata --locked --offline --format-version 1. The resolved graph
includes development and target-specific dependencies; it is not an artifact SBOM
and does not establish redistribution clearance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_release_artifacts import PRIVATE_KEY_MARKERS


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(metadata: Path, output: Path) -> dict:
    raw = metadata.read_bytes()
    data = json.loads(raw)
    packages = data.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("Cargo metadata contains no dependency packages")
    records = []
    notices = {}
    members = set(data.get("workspace_members", []))
    for package in sorted(
        packages, key=lambda item: (item["name"], item["version"], item["id"])
    ):
        manifest = Path(package["manifest_path"])
        if manifest.name != "Cargo.toml" or not manifest.is_file():
            raise ValueError("Dependency manifest path is invalid")
        directory = manifest.parent.resolve()
        texts = []
        declared = package.get("license_file")
        candidates = list(directory.iterdir())
        if declared:
            candidate = (directory / declared).resolve()
            if not candidate.is_relative_to(directory):
                raise ValueError("Declared dependency license file escapes its package")
            candidates.append(candidate)
        for path in sorted(set(candidates)):
            name = path.name.upper()
            if not path.is_file() or not (
                name.startswith(("LICENSE", "COPYING", "NOTICE"))
                or declared
                and path == candidate
            ):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(directory):
                raise ValueError("Dependency notice path escapes its package")
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Dependency notice exceeds size limit")
            content = path.read_bytes()
            if any(marker in content for marker in PRIVATE_KEY_MARKERS):
                raise ValueError("Private key material in dependency notice")
            notice_id = digest(
                (package["id"] + str(path.relative_to(directory))).encode()
            )
            destination = f"notices/{notice_id}.txt"
            notices[destination] = content
            texts.append(
                {
                    "source_path": path.relative_to(directory).as_posix(),
                    "file": destination,
                    "sha256": digest(content),
                }
            )
        records.append(
            {
                "name": package["name"],
                "version": package["version"],
                "source": package.get("source"),
                "repository": package.get("repository"),
                "declared_license": package.get("license"),
                "workspace_package": package["id"] in members,
                "notice_texts": texts,
                "review_status": "unreviewed",
            }
        )
    result = {
        "format_version": 1,
        "scope": "cargo-resolved-graph-including-dev-and-target-dependencies",
        "metadata_sha256": digest(raw),
        "packages": records,
        "review_status": "unreviewed",
        "limitations": [
            "Not a shipped-artifact SBOM",
            "Does not cover Python/JavaScript packages or embedded assets",
            "License declarations and collected texts require redistribution review",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, content in notices.items():
        destination = output / name
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(content)
    (output / "inventory.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.metadata, args.output)
    missing = sum(not package["notice_texts"] for package in result["packages"])
    print(
        f"Prepared {len(result['packages'])} package records; {missing} have no collected notice text; all remain unreviewed"
    )


if __name__ == "__main__":
    main()
