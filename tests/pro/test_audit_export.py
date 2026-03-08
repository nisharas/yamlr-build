import json
import pytest
from pathlib import Path
from yamlr.pro.compliance.evidence import EvidenceEngine
from yamlr.pro.compliance.aggregator import EvidenceAggregator

@pytest.fixture
def dummy_evidence_dir(tmp_path):
    engine = EvidenceEngine()
    
    # 1. Generate Valid Receipt A (Maps to SOC2 and CIS internally via MissingNamespace)
    receipt_a = engine.generate_receipt(
        file_path="src/pod.yaml",
        original_content="kind: Pod",
        healed_content="kind: Pod\nmetadata:\n  namespace: default",
        findings=[{"rule_id": "MissingNamespace", "severity": "ERROR"}],
        identities=[{"kind": "Pod"}]
    )
    
    # 2. Generate Valid Receipt B (Maps to something else, or same)
    receipt_b = engine.generate_receipt(
        file_path="src/deployment.yaml",
        original_content="kind: Deployment",
        healed_content="kind: Deployment\nmetadata:\n  namespace: default",
        findings=[{"rule_id": "MissingNamespace", "severity": "ERROR"}],
        identities=[{"kind": "Deployment"}]
    )
    
    # 3. Generate Tampered Receipt C
    receipt_c = engine.generate_receipt(
        file_path="src/secret.yaml",
        original_content="kind: Secret",
        healed_content="kind: Secret\nmetadata:\n  name: my-secret",
        findings=[{"rule_id": "MissingLabel", "severity": "WARN"}],
        identities=[{"kind": "Secret"}]
    )
    receipt_c["payload"]["healed_sha256"] = "tampered_hash_12345" # Inject bad hash
    
    (tmp_path / "evidence-pod.json").write_text(json.dumps(receipt_a))
    (tmp_path / "evidence-deployment.json").write_text(json.dumps(receipt_b))
    (tmp_path / "evidence-secret.json").write_text(json.dumps(receipt_c))
    
    return tmp_path

def test_aggregator_verification(dummy_evidence_dir):
    """Verify aggregator correctly flags tampered receipts."""
    aggregator = EvidenceAggregator(str(dummy_evidence_dir))
    is_clean = aggregator.load_and_verify()
    
    assert is_clean is False
    assert len(aggregator.receipts) == 2 # Only valid receipts made it
    assert len(aggregator.tampered_files) == 1
    assert "evidence-secret.json" in aggregator.tampered_files[0]

def test_aggregator_compliance_mapping(dummy_evidence_dir):
    """Verify aggregator successfully groups findings natively into Framework controls."""
    aggregator = EvidenceAggregator(str(dummy_evidence_dir))
    aggregator.load_and_verify()
    
    mapping = aggregator.aggregate_findings()
    
    # MissingNamespace maps to SOC2: CC6.1 and CIS: 5.2.6
    assert "SOC2: CC6.1" in mapping
    assert "CIS: 5.2.6" in mapping
    
    # Check that both valid files made it under the SOC2 control
    soc2_incidents = mapping["SOC2: CC6.1"]["incidents"]
    assert len(soc2_incidents) == 2
    
    files = [inc["file"] for inc in soc2_incidents]
    assert "src/pod.yaml" in files
    assert "src/deployment.yaml" in files

def test_aggregator_pdf_export(dummy_evidence_dir, tmp_path):
    """Verify aggregator structurally compiles PDF binaries using reportlab."""
    aggregator = EvidenceAggregator(str(dummy_evidence_dir))
    aggregator.load_and_verify()
    
    pdf_path = tmp_path / "compliance-report.pdf"
    output = aggregator.extract_pdf(str(pdf_path))
    
    assert pdf_path.exists()
    assert output == str(pdf_path)
    
    # Check standard PDF magick header block
    content = pdf_path.read_bytes()
    assert content.startswith(b"%PDF-")
