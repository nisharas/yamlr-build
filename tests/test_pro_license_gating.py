"""
PRO LICENSE GATING TESTS
------------------------
Verifies that Pro flags (--harden, --enforce-limits, --enforce-probes,
--fix-tags) are blocked for unlicensed users and allowed for licensed users.

Why: PRO-BUG-01 — Pro flags had zero license checks, meaning any free
user could access all Pro features without paying.
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _make_heal_args(**overrides):
    """Build a minimal args namespace for handle_heal_command."""
    defaults = {
        "path": [os.path.join(os.path.dirname(__file__), "fixtures", "healthy_manifest.yaml")],
        "ext": ".yaml,.yml",
        "max_depth": 10,
        "dry_run": True,
        "identity_mode": "infer",
        "yes": False,
        "yes_all": False,
        "output": "text",
        "stub_refs": False,
        "unsafe": False,
        "enforce_limits": False,
        "fix_tags": False,
        "harden": False,
        "enforce_probes": False,
        "strict": False,
        "compact": False,
        "quiet": True,       # Suppress rich output in tests
        "no_backup": True,
        "verbose": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_scan_args(**overrides):
    """Build a minimal args namespace for handle_scan_command."""
    defaults = {
        "path": [os.path.join(os.path.dirname(__file__), "fixtures", "healthy_manifest.yaml")],
        "ext": ".yaml,.yml",
        "max_depth": 10,
        "identity_mode": "infer",
        "output": "text",
        "enforce_limits": False,
        "fix_tags": False,
        "harden": False,
        "enforce_probes": False,
        "strict": False,
        "compact": False,
        "diff": False,
        "summary_only": False,
        "verbose": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestProLicenseGating(unittest.TestCase):
    """Ensure Pro flags are blocked without a valid license."""

    # ── HEAL COMMAND ──────────────────────────────────────────────────

    @patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled")
    @patch("yamlr.core.bridge.YamlrBridge.notify_pro_required")
    def test_heal_pro_flags_blocked_without_license(self, mock_notify, mock_is_pro):
        """Free user + --harden → notify_pro_required called, flag zeroed."""
        mock_is_pro.return_value = False

        from yamlr.core.entrypoints.heal import handle_heal_command

        engine = MagicMock()
        engine.audit_and_heal_file.return_value = {
            "success": True, "file_path": "test.yaml", "status": "HEALTHY",
            "healed_content": None, "raw_content": "", "findings": [], "actions": [],
        }
        formatter = MagicMock()

        args = _make_heal_args(harden=True, enforce_limits=True)
        handle_heal_command(args, engine, formatter, is_pro=False)

        # Gate must have fired
        mock_notify.assert_called_once()
        call_arg = mock_notify.call_args[0][0]
        self.assertIn("--harden", call_arg)
        self.assertIn("--enforce-limits", call_arg)

        # Engine must have been called with zeroed-out Pro flags
        call_kwargs = engine.audit_and_heal_file.call_args
        self.assertFalse(call_kwargs.kwargs.get("harden", call_kwargs[1].get("harden", False)))
        self.assertFalse(call_kwargs.kwargs.get("enforce_limits", call_kwargs[1].get("enforce_limits", False)))

    @patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled")
    @patch("yamlr.core.bridge.YamlrBridge.notify_pro_required")
    def test_heal_pro_flags_pass_with_license(self, mock_notify, mock_is_pro):
        """Licensed user + --harden → flags pass through, no notification."""
        mock_is_pro.return_value = True

        from yamlr.core.entrypoints.heal import handle_heal_command

        engine = MagicMock()
        engine.audit_and_heal_file.return_value = {
            "success": True, "file_path": "test.yaml", "status": "HEALTHY",
            "healed_content": None, "raw_content": "", "findings": [], "actions": [],
        }
        formatter = MagicMock()

        args = _make_heal_args(harden=True)
        handle_heal_command(args, engine, formatter, is_pro=True)

        # Gate must NOT have fired
        mock_notify.assert_not_called()

        # Engine called with harden=True
        call_kwargs = engine.audit_and_heal_file.call_args
        self.assertTrue(call_kwargs.kwargs.get("harden", call_kwargs[1].get("harden", False)))

    @patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled")
    def test_heal_no_pro_flags_skips_gate(self, mock_is_pro):
        """No Pro flags → gate never checked (avoid unnecessary license lookups)."""
        from yamlr.core.entrypoints.heal import handle_heal_command

        engine = MagicMock()
        engine.audit_and_heal_file.return_value = {
            "success": True, "file_path": "test.yaml", "status": "HEALTHY",
            "healed_content": None, "raw_content": "", "findings": [], "actions": [],
        }
        formatter = MagicMock()

        args = _make_heal_args()  # No Pro flags
        handle_heal_command(args, engine, formatter, is_pro=False)

        # is_pro_enabled should NOT have been called at all
        mock_is_pro.assert_not_called()

    # ── SCAN COMMAND ──────────────────────────────────────────────────

    @patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled")
    @patch("yamlr.core.bridge.YamlrBridge.notify_pro_required")
    def test_scan_pro_flags_blocked_without_license(self, mock_notify, mock_is_pro):
        """Free user + --enforce-probes in scan → blocked with notification."""
        mock_is_pro.return_value = False

        from yamlr.core.entrypoints.scan import handle_scan_command

        engine = MagicMock()
        engine.audit_and_heal_file.return_value = {
            "success": True, "file_path": "test.yaml", "status": "HEALTHY",
            "healed_content": None, "raw_content": "", "findings": [],
        }
        formatter = MagicMock()

        args = _make_scan_args(enforce_probes=True, fix_tags=True)
        handle_scan_command(args, engine, formatter)

        # Gate fired
        mock_notify.assert_called_once()
        call_arg = mock_notify.call_args[0][0]
        self.assertIn("--enforce-probes", call_arg)
        self.assertIn("--fix-tags", call_arg)

    @patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled")
    @patch("yamlr.core.bridge.YamlrBridge.notify_pro_required")
    def test_scan_pro_flags_pass_with_license(self, mock_notify, mock_is_pro):
        """Licensed user + --harden in scan → flags pass through."""
        mock_is_pro.return_value = True

        from yamlr.core.entrypoints.scan import handle_scan_command

        engine = MagicMock()
        engine.audit_and_heal_file.return_value = {
            "success": True, "file_path": "test.yaml", "status": "HEALTHY",
            "healed_content": None, "raw_content": "", "findings": [],
        }
        formatter = MagicMock()

        args = _make_scan_args(harden=True)
        handle_scan_command(args, engine, formatter)

        mock_notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
