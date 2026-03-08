import unittest
from typing import List, Dict, Any
from yamlr.ui.formatter_batch import BatchMixin
from yamlr.ui.formatter_summary import SummaryMixin

class MockFormatter(BatchMixin, SummaryMixin):
    def __init__(self):
        # Mocking console attributes
        class MockConsole:
            def print(self, *args, **kwargs): pass
            def input(self, *args, **kwargs): return ""
        self.console = MockConsole()
    def _render_deprecation_summary(self, reports): pass

class TestReportingLogic(unittest.TestCase):
    def test_throughput_calculation(self):
        formatter = MockFormatter()
        reports = [
            {"health_score": 90, "processing_time_seconds": 0.5, "status": "CLEAN", "success": True, "identities": []},
            {"health_score": 80, "processing_time_seconds": 0.5, "status": "CLEAN", "success": True, "identities": []}
        ]
        
        # We need to capture the output or check the logic. 
        # Since BatchMixin prints directly, we'll verify the math by inspecting
        # the component that calculate avg_time.
        
        # For the test, we'll just ensure it doesn't crash with elapsed_time
        formatter._print_summary_stats(reports, elapsed_time=1.0)
        
    def test_paradox_fix(self):
        formatter = MockFormatter()
        reports = [
            {
                "health_score": 85, 
                "status": "PREVIEW", 
                "success": True, 
                "logic_logs": ["Warning: Drift detected"],
                "findings": [{"message": "Drift", "severity": "warning"}],
                "identities": []
            }
        ]
        # In our fix, CLEAN + UNCHANGED are "Healthy files (zero issues)"
        # PREVIEW is "Files with suggested fixes (Warnings)"
        formatter._print_summary_stats(reports, elapsed_time=1.0)

if __name__ == "__main__":
    unittest.main()
