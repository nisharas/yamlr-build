import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Core components to test for resilience
from yamlr.core.io import FileSystemManager
from yamlr.pro.opa_adapter import OpaAnalyzer

class ChaosSuite(unittest.TestCase):
    """
    Simulates infrastructure-level chaos to verify 'Zero-Failure' Trust.
    """

    def setUp(self):
        # We need a workspace root for FileSystemManager
        self.workspace = Path(".yamlr_chaos_workspace").resolve()
        self.workspace.mkdir(exist_ok=True)
        self.fsm = FileSystemManager(self.workspace)
        self.fsm.ensure_workspace()
        
        self.test_file = self.workspace / "target.yaml"
        self.content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: chaos-target"

    def tearDown(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    def test_disk_full_during_atomic_write(self):
        """
        [QA-010.1] Simulation: Disk Full during fsync.
        Rule: Original file must remain intact if write fails.
        """
        # Create initial file
        with open(self.test_file, "w") as f:
            f.write("ORIGINAL_CONTENT")

        # Mock os.fsync to simulate Disk Full (OSError ENOSPC)
        # Note: we mock os.fsync because that's what FileSystemManager calls
        with patch("os.fsync", side_effect=OSError(28, "No space left on device")):
            try:
                self.fsm.atomic_write(self.test_file, "NEW_CONTENT")
            except (OSError, IOError):
                 pass # Expected failure
            
            # Verify original content is STILL THERE
            with open(self.test_file, "r") as f:
                self.assertEqual(f.read(), "ORIGINAL_CONTENT")
            
            # The tmp file should have been cleaned up by the except block in atomic_write
            # Check state_dir/tmp 
            tmp_dir = self.workspace / ".yamlr" / "tmp"
            self.assertEqual(len(list(tmp_dir.glob("*.tmp"))), 0)

    def test_network_timeout_during_opa_fetch(self):
        """
        [QA-010.2] Simulation: Network Down.
        Rule: OpaAnalyzer must not crash; should handle timeout gracefully.
        """
        import urllib.error
        
        # Mock urllib.request.urlopen to simulate timeout
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
            # Must use a trusted domain to pass domain allowlist check in OpaAnalyzer
            analyzer = OpaAnalyzer(policy_path="https://github.com/yamlr/unreachable.rego")
            
            # If it failed to fetch, it should have returned None for policy_path
            self.assertIsNone(analyzer.policy_path)

    def test_process_interruption_cleanup(self):
        """
        [QA-010.3] Simulation: Incomplete Write Recovery.
        Rule: Next run should clean up stale .tmp files.
        """
        # Manually create a STALE .tmp file in the secure tmp dir
        tmp_dir = self.workspace / ".yamlr" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        stale_tmp = tmp_dir / "stale.1234.tmp"
        
        # We need to make it "old" so cleanup_fragments picks it up
        with open(stale_tmp, "w") as f:
            f.write("STALE_DATA")
        
        # Backdate the file by 2 hours
        past_time = os.path.getmtime(stale_tmp) - 7200
        os.utime(stale_tmp, (past_time, past_time))
            
        # Running ensure_workspace should trigger cleanup_fragments
        self.fsm.ensure_workspace()
        
        # Stale .tmp should be gone
        self.assertFalse(stale_tmp.exists())

if __name__ == "__main__":
    unittest.main()
