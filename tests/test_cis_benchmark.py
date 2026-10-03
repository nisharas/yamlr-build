"""Tests for CIS Kubernetes Benchmark v1.8 catalog mapping."""
import pytest

from yamlr.knowledge.cis_benchmark import get_cis_mapping, get_cis_tag, list_cis_rules


def test_cis_mapping_lookup_sec006():
    """Verify SEC-006 maps to CIS-5.1.1 (Privileged containers)."""
    mapping = get_cis_mapping("SEC-006")
    assert mapping is not None
    assert mapping["cis_id"] == "CIS-5.1.1"
    assert "privileged" in mapping["title"].lower()
    assert mapping["profile"] == "Level 1"


def test_cis_mapping_lookup_sec001():
    """Verify SEC-001 maps to CIS-5.7.3 (Security context)."""
    tag = get_cis_tag("SEC-001")
    assert tag == "CIS-5.7.3"


def test_list_cis_rules():
    """Verify all mapped CIS rules are returned."""
    rules = list_cis_rules()
    assert len(rules) >= 10
    cis_ids = [r["cis_id"] for r in rules]
    assert "CIS-5.1.1" in cis_ids
    assert "CIS-5.1.4" in cis_ids
    assert "CIS-5.3.1" in cis_ids
