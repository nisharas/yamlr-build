"""End-to-End Tests for Atomic Backup and Restore Lifecycle."""
import os
import shutil
import tempfile
from pathlib import Path

from yamlr.core.backups import BackupManager


def test_e2e_backup_and_restore_cycle():
    """E2E: Verifies complete checkpointing and restoration lifecycle."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_backup_test_")
    try:
        manifest_path = os.path.join(temp_dir, "deployment.yaml")
        original_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 2
"""
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(original_content)

        bm = BackupManager(temp_dir)
        session_id = bm.create_checkpoint([manifest_path])
        assert session_id is not None

        # Mutate the file
        mutated_content = original_content + "\n# Modified by test"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(mutated_content)

        assert open(manifest_path, "r", encoding="utf-8").read() == mutated_content

        # Execute restore
        bm.restore_last_session()

        # Assert byte-for-byte original restoration
        restored_content = open(manifest_path, "r", encoding="utf-8").read()
        assert restored_content == original_content

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
