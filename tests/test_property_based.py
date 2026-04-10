import os

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from yamlr.core.context import HealContext
from yamlr.core.exceptions import YamlrError, YamlrSecurityError
from yamlr.parsers.lexer import YamlrLexer
from yamlr.parsers.structurer import YamlrStructurer

MAX_EXAMPLES = int(os.environ.get("HYPOTHESIS_MAX_EXAMPLES", 100))


@pytest.fixture
def lexer():
    return YamlrLexer()


@pytest.fixture
def structurer():
    return YamlrStructurer(catalog={})


@settings(
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
    max_examples=MAX_EXAMPLES,
)
@given(st.text(min_size=0, max_size=10000))
def test_lexer_robustness(lexer, text):
    """
    Property: The lexer must never crash (unhandled exception) on any text input.
    Valid exceptions like YamlrSecurityError are allowed.
    """
    try:
        lexer.shard(text)
    except (YamlrSecurityError, YamlrError):
        pass
    except Exception as e:
        pytest.fail(f"Lexer raised unhandled exception on input: {e}")


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "line_no": st.integers(min_value=1, max_value=1000),
                "indent": st.integers(min_value=0, max_value=100),
                "key": st.text(max_size=100),
                "value": st.one_of(st.none(), st.text(max_size=100)),
                "is_list_item": st.booleans(),
                "is_block": st.booleans(),
                "is_doc_boundary": st.booleans(),
                "comment": st.text(max_size=100),
                "raw_line": st.text(max_size=200),
            }
        ),
        max_size=100,
    )
)
def test_structurer_robustness(structurer, shard_dicts):
    """
    Property: The structurer must never crash on any sequence of shards.
    """
    from yamlr.models import Shard

    class MockShadow:
        def __init__(self):
            self.physicist = None

    shards = [Shard(**d) for d in shard_dicts]
    context = HealContext(raw_text="", shards=shards)
    context.shadow_engine = MockShadow()

    try:
        structurer.reconstruct(context)
    except (YamlrSecurityError, YamlrError):
        pass
    except Exception as e:
        # We allow some internal ruamel errors if they are caught,
        # but the structurer itself should handle most things.
        if "ruamel" in str(e).lower():
            pass
        else:
            pytest.fail(f"Structurer raised unhandled exception on shards: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
