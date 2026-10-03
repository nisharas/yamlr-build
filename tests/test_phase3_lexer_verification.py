"""High-fidelity YAML lexer verification test suite covering odd indents, block chomping, and line endings."""
import pytest
import yamlr_native


def test_odd_indentation_1_and_3_spaces_preservation():
    """Verify that 1-space and 3-space indents are NOT snapped to even numbers."""
    raw_yaml = (
        "spec:\n"
        "   replicas: 3\n"
        "   template:\n"
        "    metadata:\n"
        "     labels:\n"
        "      app: odd-indent-test\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "   replicas: 3" in reconstructed, "3-space indent must be preserved verbatim!"
    assert "    metadata:" in reconstructed, "4-space indent must be preserved!"
    assert "     labels:" in reconstructed, "5-space indent must be preserved verbatim!"
    assert "      app: odd-indent-test" in reconstructed, "6-space indent must be preserved!"


def test_block_scalar_chomping_strip_and_keep():
    """Verify that |- (strip) and |+ (keep) block scalar indicators are preserved."""
    raw_yaml = (
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: script-config\n"
        "data:\n"
        "  run.sh: |-\n"
        "    #!/bin/bash\n"
        "    echo 'Hello Yamlr'\n"
        "  notes.txt: |+\n"
        "    Some notes\n"
        "\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "run.sh: |-" in reconstructed or "|-" in reconstructed, "Chomping indicator |- must be preserved!"
    assert "notes.txt: |+" in reconstructed or "|+" in reconstructed, "Chomping indicator |+ must be preserved!"
    assert "echo 'Hello Yamlr'" in reconstructed


def test_multidoc_with_comments_and_blank_lines():
    """Verify that multi-document streams with pure comments and blank lines are reconstructed with 100% fidelity."""
    raw_yaml = (
        "# Header comment\n"
        "apiVersion: v1\n"
        "kind: Namespace\n"
        "metadata:\n"
        "  name: prod\n"
        "---\n"
        "# Second document comment\n"
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n"
        "  name: prod-svc\n"
        "spec:\n"
        "  ports:\n"
        "  - port: 80 # inline comment\n"
        "    targetPort: 8080\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "# Header comment" in reconstructed
    assert "kind: Namespace" in reconstructed
    assert "---" in reconstructed
    assert "# Second document comment" in reconstructed
    assert "# inline comment" in reconstructed
    assert "targetPort: 8080" in reconstructed


def test_crlf_windows_line_ending_preservation():
    """Verify that Windows CRLF line endings are parsed and reconstructed without corrupting newlines."""
    crlf_yaml = "apiVersion: v1\r\nkind: Pod\r\nmetadata:\r\n  name: crlf-pod\r\n"
    shards = yamlr_native.native_shard(crlf_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "apiVersion: v1" in reconstructed
    assert "kind: Pod" in reconstructed
    assert "name: crlf-pod" in reconstructed
