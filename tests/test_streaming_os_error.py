import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_os_error(temp_workspace):
    """Verify streaming scan handles OS errors gracefully."""
    yaml_path = os.path.join(temp_workspace, "error.yaml")
    with open(yaml_path, 'w') as f:
        f.write("content")
    
    # Mock open to raise OSError
    with patch('builtins.open', side_effect=OSError("Permission Denied")):
        results = list(streaming_scan(yaml_path, []))
        # Should yield 0 results but not crash
        assert len(results) == 0
