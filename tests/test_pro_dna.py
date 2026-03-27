import pytest
from yamlr.core.pipeline import HealingPipeline
from yamlr.models import HealConfig
from yamlr.core.utils import get_hardened_yaml

def test_pro_width_constraint():
    """Verify that serialization width is 4096 (Pro DNA)."""
    long_string = "a" * 1000
    doc = {"metadata": {"annotations": {"long": long_string}}}
    pipeline = HealingPipeline({})
    content = pipeline.structurer.serialize([doc])
    # If it was wrapped at 80, the long string wouldn't be contiguous
    assert long_string in content


def test_first_doc_boundary_preservation():
    """Verify that leading --- is preserved (Pro DNA)."""
    raw = "---\napiVersion: v1\nkind: Pod\nmetadata: {name: test}"
    pipeline = HealingPipeline({})
    config = HealConfig(file_path="test.yaml")
    result = pipeline.heal(raw, config)
    # The reconstruction might have added a newline after ---
    assert result.content.strip().startswith("---")


def test_validation_sampling():
    """Verify that validation sampling works (Pro DNA)."""
    # Create a manifest with 50 containers (should be sampled to 1)
    containers = [{"name": f"c{i}", "image": "nginx"} for i in range(50)]
    doc = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "massive"},
        "spec": {
            "selector": {"matchLabels": {"app": "web"}},
            "template": {
                "metadata": {"labels": {"app": "web"}},
                "spec": {"containers": containers}
            }
        }
    }
    from yamlr.validators.schema_validator import SchemaValidator
    validator = SchemaValidator()
    # Deep check should catch the 50 if we had a validator (just check logic here)
    sampled = validator._sample_document(doc)
    assert len(sampled["spec"]["template"]["spec"]["containers"]) == 1

def test_dna_integrity_score_renaming():
    """Verify DNA Integrity Score calculation and naming."""
    raw = "apiVersion: v1\nkind: Pod\nmetadata: {name: test}"
    pipeline = HealingPipeline({})
    config = HealConfig(file_path="test.yaml")
    result = pipeline.heal(raw, config)
    assert result.dna_integrity_score > 0
    # Score is a number, not a string with "DNA Integrity"
    assert 0 <= result.dna_integrity_score <= 100


def test_dynamic_resource_profiles():
    """Verify dynamic resource injection with profiles."""
    raw = "apiVersion: v1\nkind: Pod\nmetadata: {name: test}\nspec: {containers: [{name: app, image: nginx}]}"
    profiles = {
        "app": {
            "requests": {"cpu": "777m", "memory": "777Mi"},
            "limits": {"cpu": "888m", "memory": "888Mi"}
        }
    }
    pipeline = HealingPipeline({})
    config = HealConfig(file_path="test.yaml", enforce_limits=True, resource_profiles=profiles)
    result = pipeline.heal(raw, config)
    assert "777m" in result.content
