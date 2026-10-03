import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core.backups import BackupManager


def test_backup_cleanup(temp_workspace):
    """Verify that old backups are cleaned up based on index."""
    bm = BackupManager(temp_workspace)
    
    # Create 15 dummy sessions in index
    sessions = []
    for i in range(15):
        session_id = f"session_{i}"
        os.makedirs(os.path.join(bm.backup_dir, session_id), exist_ok=True)
        sessions.append({"id": session_id, "timestamp": "now", "files": []})
        
    with open(bm.index_path, "w") as f:
        json.dump({"sessions": sessions}, f)
    
    # Trigger cleanup
    bm._cleanup_old_backups()
    
    # Should keep only 10
    with open(bm.index_path, "r") as f:
        data = json.load(f)
        assert len(data["sessions"]) == 10
        assert data["sessions"][0]["id"] == "session_5" # Oldest kept
    
    # Check filesystem
    dirs = [d for d in os.listdir(bm.backup_dir) if d.startswith("session_")]
    assert len(dirs) == 10
