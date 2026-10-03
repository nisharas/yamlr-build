import json
import os
import shutil
from pathlib import Path

import pytest

from yamlr.core.backups import BackupManager


def test_backup_manager_init(temp_workspace):
    """Verify infrastructure initialization."""
    bm = BackupManager(temp_workspace)
    assert (Path(temp_workspace) / ".yamlr" / "backups").exists()
    assert (Path(temp_workspace) / ".yamlr" / "backups" / "index.json").exists()

def test_create_checkpoint(temp_workspace):
    """Verify checkpoint creation and indexing."""
    bm = BackupManager(temp_workspace)
    
    # Create a dummy file
    file_path = os.path.join(temp_workspace, "test.yaml")
    with open(file_path, 'w') as f:
        f.write("test content")
        
    session_id = bm.create_checkpoint([file_path])
    
    assert session_id.startswith("session_")
    session_dir = Path(temp_workspace) / ".yamlr" / "backups" / session_id
    assert (session_dir / "test.yaml").exists()
    
    with open(bm.index_path, 'r') as f:
        data = json.load(f)
        assert len(data['sessions']) == 1
        assert data['sessions'][0]['id'] == session_id

def test_restore_last_session(temp_workspace):
    """Verify restoration of files from backup."""
    bm = BackupManager(temp_workspace)
    file_path = os.path.join(temp_workspace, "test.yaml")
    
    # Version 1
    with open(file_path, 'w') as f:
        f.write("version 1")
    
    bm.create_checkpoint([file_path])
    
    # Version 2 (corrupted)
    with open(file_path, 'w') as f:
        f.write("version 2 (corrupted)")
        
    # Restore
    success = bm.restore_last_session()
    assert success is True
    
    with open(file_path, 'r') as f:
        assert f.read() == "version 1"
        
    # Verify session removed from index
    with open(bm.index_path, 'r') as f:
        data = json.load(f)
        assert len(data['sessions']) == 0
