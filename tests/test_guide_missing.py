from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_guide_rich


def test_cmd_guide_not_found():
    """Verify guide command handles missing topics."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        with patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup', return_value=None):
            cmd_guide_rich(topic="unknown")
            assert any("not found" in str(call) for call in mock_print.call_args_list)
