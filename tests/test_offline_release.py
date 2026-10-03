"""Offline release trust and packaging regression tests."""

from __future__ import annotations
import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

spec = importlib.util.spec_from_file_location(
    "offline_release",
    Path(__file__).resolve().parents[1] / "scripts/ci/offline_release.py",
)
release = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release)


@pytest.fixture
def candidate(tmp_path):
    key = Ed25519PrivateKey.generate()
    private = tmp_path / "signing.pem"
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public = tmp_path / "trusted.pem"
    public.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    binary = tmp_path / "yamlr.exe"
    binary.write_bytes(b"development binary fixture")
    notices = tmp_path / "notices.txt"
    notices.write_text("Development test notices only", encoding="utf-8")
    license_file = tmp_path / "license.txt"
    license_file.write_text("Development test license only", encoding="utf-8")
    sbom = tmp_path / "sbom.json"
    sbom.write_text(
        json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "components": []}),
        encoding="utf-8",
    )
    archive = release.package(
        binary,
        notices,
        sbom,
        license_file,
        private,
        tmp_path / "out",
        version="v0.1.0",
        target="windows-x86_64",
        revision="a" * 40,
        profile="debug",
        dirty=True,
    )
    return (
        archive,
        archive.with_suffix(".manifest.json"),
        archive.with_suffix(".manifest.sig"),
        public,
    )


def verify(candidate, **kwargs):
    return release.verify(
        *candidate,
        version="v0.1.0",
        target="windows-x86_64",
        allow_development=True,
        **kwargs,
    )


def test_valid_development_candidate_requires_explicit_development_mode(candidate):
    assert verify(candidate)["source_dirty"] is True
    with pytest.raises(ValueError, match="Development artifacts"):
        release.verify(*candidate, version="v0.1.0", target="windows-x86_64")


def test_tampered_archive_is_rejected(candidate):
    archive = candidate[0]
    with archive.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="signed manifest"):
        verify(candidate)


def test_tampered_manifest_is_rejected(candidate):
    candidate[1].write_bytes(candidate[1].read_bytes() + b" ")
    with pytest.raises(ValueError, match="signature"):
        verify(candidate)


def test_wrong_trusted_key_is_rejected(candidate):
    candidate[3].write_bytes(
        Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    with pytest.raises(ValueError, match="signature"):
        verify(candidate)


def test_wrong_pinned_version_and_target_are_rejected(candidate):
    for version, target in [("v0.2.0", "windows-x86_64"), ("v0.1.0", "linux-x86_64")]:
        with pytest.raises(ValueError, match="pinned expectation"):
            release.verify(
                *candidate, version=version, target=target, allow_development=True
            )


def test_existing_candidate_is_not_overwritten(candidate):
    parent = candidate[0].parent.parent
    before = candidate[0].read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        release.package(
            parent / "yamlr.exe",
            parent / "notices.txt",
            parent / "sbom.json",
            parent / "license.txt",
            parent / "signing.pem",
            candidate[0].parent,
            version="v0.1.0",
            target="windows-x86_64",
            revision="a" * 40,
            profile="debug",
            dirty=True,
        )
    assert candidate[0].read_bytes() == before


def test_private_key_material_is_never_signed_or_packaged(candidate):
    parent = candidate[0].parent.parent
    (parent / "yamlr.exe").write_bytes((parent / "signing.pem").read_bytes())
    output = parent / "rejected"
    with pytest.raises(ValueError, match="Private-key policy"):
        release.package(
            parent / "yamlr.exe",
            parent / "notices.txt",
            parent / "sbom.json",
            parent / "license.txt",
            parent / "signing.pem",
            output,
            version="v0.1.0",
            target="windows-x86_64",
            revision="a" * 40,
            profile="debug",
            dirty=True,
        )
    assert list(output.iterdir()) == []


def test_packaging_is_deterministic(candidate):
    parent = candidate[0].parent.parent
    second = release.package(
        parent / "yamlr.exe",
        parent / "notices.txt",
        parent / "sbom.json",
        parent / "license.txt",
        parent / "signing.pem",
        parent / "second",
        version="v0.1.0",
        target="windows-x86_64",
        revision="a" * 40,
        profile="debug",
        dirty=True,
    )
    assert second.read_bytes() == candidate[0].read_bytes()
    assert (
        second.with_suffix(".manifest.json").read_bytes() == candidate[1].read_bytes()
    )
    assert second.with_suffix(".manifest.sig").read_bytes() == candidate[2].read_bytes()


def test_production_package_rejects_dirty_declarations(candidate):
    parent = candidate[0].parent.parent
    with pytest.raises(ValueError, match="clean source revision"):
        release.package(
            parent / "yamlr.exe",
            parent / "notices.txt",
            parent / "sbom.json",
            parent / "license.txt",
            parent / "signing.pem",
            parent / "production",
            version="v0.1.0",
            target="windows-x86_64",
            revision="a" * 40,
            profile="release",
            dirty=True,
        )
    assert not (parent / "production").exists()


def test_oversized_signature_is_rejected(candidate):
    candidate[2].write_bytes(b"x" * 65)
    with pytest.raises(ValueError, match="size limit"):
        verify(candidate)
