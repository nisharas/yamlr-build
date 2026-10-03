#!/usr/bin/env python3
"""Prepare JavaScript dependency and asset provenance records from a verified snapshot.

Declared metadata is evidence for review, not license clearance or an artifact SBOM.
No dependency installation, registry calls, or notice-text substitution is performed.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

from source_snapshot import PRODUCT_SCOPE, LIMIT, sha, verify


def prepare(snapshot: Path, output: Path) -> dict:
    if snapshot.stat().st_size > LIMIT:
        raise ValueError("Source snapshot exceeds size limit")
    raw = snapshot.read_bytes()
    manifest = verify(raw)
    if manifest["scope"] != PRODUCT_SCOPE:
        raise ValueError("Product review requires the all-product source scope")
    packages = []
    assets = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for item in manifest["files"]:
            name = item["path"]
            if name.endswith("/package-lock.json"):
                lock = json.loads(archive.read(name))
                if lock.get("lockfileVersion") not in (2, 3) or not isinstance(
                    lock.get("packages"), dict
                ):
                    raise ValueError(f"Unsupported npm lockfile structure: {name}")
                for location, entry in sorted(lock["packages"].items()):
                    if not location:
                        continue
                    if not isinstance(entry, dict):
                        raise ValueError(f"Invalid npm package entry: {name}")
                    packages.append(
                        {
                            "lockfile": name,
                            "lockfile_sha256": item["sha256"],
                            "location": location,
                            "name": entry.get("name")
                            or location.rsplit("node_modules/", 1)[-1],
                            "version": entry.get("version"),
                            "resolved": entry.get("resolved"),
                            "integrity": entry.get("integrity"),
                            "declared_license": entry.get("license"),
                            "development_only": entry.get("dev", False),
                            "optional": entry.get("optional", False),
                            "local_link": entry.get("link", False),
                            "review_status": "unreviewed",
                            "notice_texts": [],
                        }
                    )
            path = Path(name)
            if (
                "catalog" in path.parts
                or name.startswith("schemas/")
                or name.startswith("website/public/")
                or path.suffix.lower()
                in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".svg",
                    ".ico",
                    ".woff",
                    ".woff2",
                    ".ttf",
                    ".otf",
                }
            ):
                assets.append(
                    {
                        **item,
                        "source": None,
                        "license": None,
                        "review_status": "provenance-unconfirmed",
                    }
                )
    result = {
        "format_version": 1,
        "source_sha256": manifest["source_sha256"],
        "snapshot_sha256": sha(raw),
        "scope": "source-lockfiles-and-candidate-assets",
        "javascript_packages": packages,
        "assets": assets,
        "limitations": [
            "Includes development/optional dependencies; not an artifact SBOM",
            "Lockfile license declarations are not reviewed license or notice texts",
            "Python/Rust dependency evidence is collected separately",
            "Inline or adapted material outside candidate asset paths requires manual provenance review",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.snapshot, args.output)
    print(
        f"Prepared {len(result['javascript_packages'])} npm records and {len(result['assets'])} asset records; all unreviewed"
    )


if __name__ == "__main__":
    main()
