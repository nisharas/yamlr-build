from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_roi


def test_cmd_roi_no_native():
    """Verify ROI command handles missing native core."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        # Force ImportError when importing yamlr_native in cmd_roi
        # We need to ensure it's not already in sys.modules or mock it
        with patch.dict('sys.modules', {'yamlr_native': MagicMock()}):
            # Patch the import inside the function
            with patch('builtins.__import__', side_effect=ImportError):
                try:
                    cmd_roi(".")
                except ImportError:
                    pass
                assert any("Native core required" in str(call) for call in mock_print.call_args_list)
