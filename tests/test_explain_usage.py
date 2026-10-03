from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_explain_universal


def test_cmd_explain_usage():
    """Verify explain usage message."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_explain_universal(topic=None)
        assert any("Usage:" in str(call) for call in mock_print.call_args_list)
