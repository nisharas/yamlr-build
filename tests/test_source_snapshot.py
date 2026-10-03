"""Source snapshot integrity and safe unpacking acceptance."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/ci/source_snapshot.py"
spec = importlib.util.spec_from_file_location("source_snapshot", MODULE)
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / "source"
    (root / "native_core/src").mkdir(parents=True)
    (root / "LICENSE").write_text("development fixture", encoding="utf-8")
    (root / "native_core/src/lib.rs").write_text("pub fn sample() {}", encoding="utf-8")
    monkeypatch.setattr(snapshot, "FILES", ("LICENSE",))
    monkeypatch.setattr(snapshot, "TREES", ("native_core/src",))
    return root


def rewrite(path, contents):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)


def test_same_source_produces_identical_archives(source, tmp_path):
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    manifest = snapshot.capture(source, first)
    snapshot.capture(source, second)
    assert first.read_bytes() == second.read_bytes()
    assert snapshot.verify(first) == manifest


def test_modified_content_fails_verification(source, tmp_path):
    path = tmp_path / "candidate.zip"
    snapshot.capture(source, path)
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["native_core/src/lib.rs"] = b"modified"
    rewrite(path, contents)
    with pytest.raises(ValueError, match="content digest mismatch"):
        snapshot.verify(path)


def test_traversal_rejected_before_destination_created(source, tmp_path):
    path = tmp_path / "candidate.zip"
    manifest = snapshot.capture(source, path)
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["../escape.rs"] = b"escape"
    manifest["files"].append(
        {"path": "../escape.rs", "size": 6, "sha256": snapshot.sha(b"escape")}
    )
    manifest["source_sha256"] = snapshot.sha(snapshot.canonical(manifest["files"]))
    contents[snapshot.MANIFEST] = json.dumps(manifest).encode()
    rewrite(path, contents)
    destination = tmp_path / "unpacked"
    with pytest.raises(ValueError, match="Forbidden snapshot entry"):
        snapshot.unpack(path, destination)
    assert not destination.exists()


def test_unpack_never_overwrites_existing_directory(source, tmp_path):
    path = tmp_path / "candidate.zip"
    snapshot.capture(source, path)
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        snapshot.unpack(path, destination)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_embedded_private_key_rejected(source, tmp_path):
    (source / "native_core/src/key.rs").write_text(
        'const KEY: &str = r#"\n-----BEGIN PRIVATE KEY-----\nfixture\n"#;',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Private key material"):
        snapshot.capture(source, tmp_path / "candidate.zip")


def test_all_product_policy_includes_sources_and_prunes_generated(
    source, tmp_path, monkeypatch
):
    monkeypatch.setattr(snapshot, "PRODUCT_FILES", ())
    monkeypatch.setattr(snapshot, "PRODUCT_TREES", ("website", "infra"))
    for name in ("website/src/page.tsx", "infra/gateway/index.ts"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source", encoding="utf-8")
    for name in (
        "website/node_modules/pkg/index.js",
        "website/.next/output.js",
        "infra/.env",
        "website/public/wasm/generated.js",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("excluded", encoding="utf-8")
    path = tmp_path / "all.zip"
    manifest = snapshot.capture(source, path, snapshot.PRODUCT_SCOPE)
    names = {item["path"] for item in manifest["files"]}
    assert names == {
        "LICENSE",
        "native_core/src/lib.rs",
        "website/src/page.tsx",
        "infra/gateway/index.ts",
    }
    assert snapshot.verify(path) == manifest


def test_verify_rejects_private_key_even_with_recomputed_inventory(source, tmp_path):
    path = tmp_path / "candidate.zip"
    manifest = snapshot.capture(source, path)
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    name = "native_core/src/lib.rs"
    contents[name] = b"-----BEGIN PRIVATE KEY-----\nfixture\n"
    for item in manifest["files"]:
        if item["path"] == name:
            item.update(size=len(contents[name]), sha256=snapshot.sha(contents[name]))
    manifest["source_sha256"] = snapshot.sha(snapshot.canonical(manifest["files"]))
    contents[snapshot.MANIFEST] = snapshot.canonical(manifest)
    rewrite(path, contents)
    with pytest.raises(ValueError, match="Private key material"):
        snapshot.verify(path)


def test_required_tree_cannot_be_removed_from_inventory(source, tmp_path):
    path = tmp_path / "candidate.zip"
    manifest = snapshot.capture(source, path)
    manifest["files"] = [
        item for item in manifest["files"] if item["path"] == "LICENSE"
    ]
    manifest["source_sha256"] = snapshot.sha(snapshot.canonical(manifest["files"]))
    rewrite(
        path,
        {
            "LICENSE": b"development fixture",
            snapshot.MANIFEST: snapshot.canonical(manifest),
        },
    )
    with pytest.raises(ValueError, match="required source tree"):
        snapshot.verify(path)
