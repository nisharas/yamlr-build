import json
import time
from pathlib import Path
import pytest
import hmac
import hashlib

from yamlr.pro.compliance.evidence import EvidenceEngine

def test_evidence_engine_key_generation(tmp_path, monkeypatch):
    """Test that the engine automatically generates and reuses a deterministic key."""
    # Mock home directory to our temp path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    engine1 = EvidenceEngine()
    key1 = engine1._key
    assert len(key1) == 32
    
    # Ensure key was written to disk
    key_file = tmp_path / EvidenceEngine.KEY_PATH_RELATIVE
    assert key_file.exists()
    assert key_file.read_bytes() == key1
    
    # Reload engine, should use same key
    engine2 = EvidenceEngine()
    assert engine2._key == key1

def test_evidence_engine_signature_verification(tmp_path, monkeypatch):
    """Test that the generated receipt correctly calculates hashes and signs the payload."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    engine = EvidenceEngine()
    
    original = "apiVersion: v1\nkind: Pod"
    healed = "apiVersion: v1\nkind: Pod\nmetadata:\n  namespace: default"
    findings = [{"rule_id": "MissingNamespace", "severity": "WARNING"}]
    identities = [{"kind": "Pod", "name": "unknown"}]
    
    receipt = engine.generate_receipt(
        file_path="/test/path.yaml",
        original_content=original,
        healed_content=healed,
        findings=findings,
        identities=identities
    )
    
    assert receipt["signature_method"] == "HMAC-SHA256"
    
    payload = receipt["payload"]
    assert payload["file_path"] == "/test/path.yaml"
    assert "timestamp" in payload
    
    # Verify SHA-256 Hashes
    expected_orig_hash = hashlib.sha256(original.encode('utf-8')).hexdigest()
    expected_healed_hash = hashlib.sha256(healed.encode('utf-8')).hexdigest()
    
    assert payload["original_sha256"] == expected_orig_hash
    assert payload["healed_sha256"] == expected_healed_hash
    
    # Verify HMAC Signature mathematically
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    expected_sig = hmac.new(engine._key, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
    
    assert receipt["signature"] == expected_sig

def test_evidence_engine_null_content(tmp_path, monkeypatch):
    """Ensure engine handles dry-runs or skip paths where healed content might be empty or identical."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    engine = EvidenceEngine()
    
    receipt = engine.generate_receipt(
        file_path="/test/path.yaml",
        original_content="foo",
        healed_content=None,
        findings=[],
        identities=[]
    )
    
    assert receipt["payload"]["healed_sha256"] == ""
