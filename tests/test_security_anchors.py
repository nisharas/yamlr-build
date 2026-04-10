import pytest

from yamlr.core.exceptions import YamlrSecurityError
from yamlr.parsers.lexer import YamlrLexer


def test_anchor_recursion_guard():
    """Verifies that YamlrLexer prevents Billion Laughs attacks via anchor depth."""
    lexer = YamlrLexer()

    # Nested tags/anchors on a single line
    yaml_deep = "a: " + "!!tag " * 60 + "value"

    with pytest.raises(YamlrSecurityError) as excinfo:
        lexer.shard(yaml_deep)
    assert "Maximum anchor/tag nesting depth exceeded" in str(excinfo.value)


def test_alias_count_guard():
    """Verifies that YamlrLexer prevents alias explosion."""
    lexer = YamlrLexer()

    # 2000 aliases (MAX is 1000)
    yaml_explosion = "a: &a root\n"
    for i in range(2000):
        yaml_explosion += f"alias_{i}: *a\n"

    with pytest.raises(YamlrSecurityError) as excinfo:
        lexer.shard(yaml_explosion)
    assert "Maximum alias count exceeded" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__])
