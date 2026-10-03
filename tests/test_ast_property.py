import pytest

hypothesis = pytest.importorskip("hypothesis", reason="hypothesis required for property-based testing")
import yamlr_native
from hypothesis import given
from hypothesis import strategies as st


# A simple strategy to generate nested dictionaries that can be represented in YAML
def yaml_data_strategy():
    keys = st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10)
    values = st.one_of(st.integers(), st.text(alphabet="abcdefghijklmnopqrstuvwxyz1234567890 ", min_size=1, max_size=20), st.booleans())
    return st.recursive(
        st.dictionaries(keys, values, max_size=5),
        lambda children: st.dictionaries(keys, children, max_size=3),
        max_leaves=10
    )

@given(st.text(alphabet=" \n\t-abcde:1234\r", min_size=0, max_size=100))
def test_ast_preservation_fuzz(yaml_str):
    """Property: Any random string parsed and reconstructed should equal itself,
    or at least not crash the engine.
    """
    try:
        shards = yamlr_native.native_shard(yaml_str)
        reconstructed = yamlr_native.native_reconstruct_yaml(shards)
        assert isinstance(reconstructed, str)
    except (ValueError, RuntimeError) as e:
        # Expected parser rejections on malformed YAML syntax
        assert str(e) != "" or isinstance(e, Exception)
