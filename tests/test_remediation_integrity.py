"""Tests for post-write invariant verification and instant auto-rollback."""
import os
import shutil
import tempfile
from unittest.mock import MagicMock

from yamlr.cli.remediation import apply_remediation


def test_remediation_post_write_auto_rollback(monkeypatch):
    """Verify that if post-write invariant fails, the file is automatically restored from .bak."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = os.path.join(tmpdir, "test.yaml")
        original_content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        mock_fix = MagicMock()
        mock_fix.field_path = "spec.replicas"
        mock_fix.suggested_value = 3
        mock_fix.message = "Set replicas"

        mock_res = MagicMock()
        mock_res.file_path = target_file
        mock_res.suggested_fixes = [mock_fix]
        mock_res.identity = MagicMock(kind="Pod", name="test")

        import yamlr_native
        # Simulate native_apply_fix_atomic writing corrupted unparseable content
        def mock_apply_atomic(path, field, val, kind, name):
            with open(path, "w", encoding="utf-8") as f:
                f.write("corrupted: invalid: [yaml: {unclosed")
            return True

        monkeypatch.setattr(yamlr_native, "native_apply_fix_atomic", mock_apply_atomic)

        # Apply remediation
        apply_remediation(mock_res, telemetry=None, apply=True, dry_run=False, diff=False)

        # Verify that post-write invariant failed and restored original content!
        with open(target_file, "r", encoding="utf-8") as f:
            final_content = f.read()

        assert final_content == original_content, "Corrupted file must be automatically rolled back from .bak!"
