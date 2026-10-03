import io
import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from yamlr.cli.main import cmd_sign, cmd_verify


def test_cmd_sign_success(temp_workspace):
    """Verify that cmd_sign correctly injects a signature."""
    manifest_path = os.path.join(temp_workspace, "test.yaml")
    with open(manifest_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Service\nmetadata:\n  name: test\n")
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_sign_manifest', return_value="mock-signature"):
        with patch('os.getenv', return_value="fake-key"):
            with patch('yamlr.core_logic.LicenseManager') as mock_lm_class:
                mock_lm_class.return_value.is_pro = True
                cmd_sign(args)
    
    # Check if signature was added
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert "yamlr.dev/signature: mock-signature" in content

def test_cmd_verify_success(temp_workspace):
    """Verify that cmd_verify correctly validates a signed manifest."""
    manifest_path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: Service
metadata:
  name: test
  annotations:
    yamlr.dev/signature: mock-sig
"""
    with open(manifest_path, 'w') as f:
        f.write(content)
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_verify_manifest', return_value=True):
        with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-pubkey"):
            # Should not exit
            cmd_verify(args)

def test_cmd_verify_fail(temp_workspace):
    """Verify that cmd_verify exits on failure."""
    manifest_path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: Service
metadata:
  name: test
  annotations:
    yamlr.dev/signature: bad-sig
"""
    with open(manifest_path, 'w') as f:
        f.write(content)
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_verify_manifest', return_value=False):
        with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-pubkey"):
            with pytest.raises(SystemExit):
                cmd_verify(args)
