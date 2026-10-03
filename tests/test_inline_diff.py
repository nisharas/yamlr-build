import pytest

from yamlr.ui.diff_engine import (
    InlineWordDiff,
    SideBySideDiff,
    render_inline_diff,
    render_side_by_side_diff,
    render_unified_diff,
)
from yamlr.ui.renderer import RichRenderer


def test_inline_word_diff_tokenization():
    """Verify line tokenization isolates identifiers, punctuation, and spaces."""
    line = "  apiVersion: extensions/v1beta1 # legacy"
    tokens = InlineWordDiff.tokenize_line(line)
    assert "  " in tokens
    assert "apiVersion" in tokens
    assert ":" in tokens
    assert "extensions" in tokens
    assert "/" in tokens
    assert "v1beta1" in tokens
    assert "legacy" in tokens

def test_inline_word_diff_computation():
    """Verify word-level diff highlights exact replacements."""
    old_line = "  apiVersion: extensions/v1beta1"
    new_line = "  apiVersion: apps/v1"
    old_text, new_text = InlineWordDiff.compute_inline_words(old_line, new_line)
    
    assert "extensions/v1beta1" in old_text.plain
    assert "apps/v1" in new_text.plain
    assert "apiVersion:" in old_text.plain
    assert "apiVersion:" in new_text.plain

def test_render_diff_methods_execute_cleanly():
    """Verify that all RichRenderer diff methods execute without raising exceptions."""
    old = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: old-app\n"
    new = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: new-app\n"
    
    # Should execute without throwing any exception
    RichRenderer.render_inline_word_diff(old, new, title="Test Diff")
    RichRenderer.render_unified_diff(old, new, title="Test Unified")
    RichRenderer.render_side_by_side_diff(old, new, title="Test Side-by-Side")

def test_render_diff_identical_content():
    """Verify diff methods handle identical content gracefully."""
    content = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-svc\n"
    RichRenderer.render_inline_word_diff(content, content)
    RichRenderer.render_unified_diff(content, content)
    RichRenderer.render_side_by_side_diff(content, content)
