import pytest

from yamlr.core.engine import YamlrEngine
from yamlr.models import HealConfig


def test_indentation_parity_multi_doc():
    """
    Verifies that Yamlr preserves per-document indentation in a multi-document manifest.
    Doc 1: 2-space indent
    Doc 2: 4-space indent
    """
    yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: doc-two-space
spec:
  selector:
    app: foo
---
apiVersion: apps/v1
kind: Deployment
metadata:
    name: doc-four-space
spec:
    replicas: 1
    selector:
        matchLabels:
            app: bar
"""
    engine = YamlrEngine.quick()
    config = HealConfig(skip_repair=False)

    # Process the multi-doc text
    results = engine.heal(yaml_text, config=config)
    healed_text = results.healed_content

    print("HEALED TEXT:\n" + healed_text)

    docs = healed_text.split("---")
    # Filter out empty strings if any
    docs = [d.strip() for d in docs if d.strip()]

    assert len(docs) == 2

    # Doc 1: Should have 2-space indent for 'selector'
    assert "  selector:" in docs[0]
    assert "    app: foo" in docs[0]

    # Doc 2: Should have 4-space indent for 'spec' and 'replicas'
    assert "    replicas: 1" in docs[1]
    assert "        matchLabels:" in docs[1]


if __name__ == "__main__":
    pytest.main([__file__])
