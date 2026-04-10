import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from yamlr.pro.opa_adapter import OpaAnalyzer


def test_opa_is_bundle_detection():
    analyzer = OpaAnalyzer()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Directory is a bundle
        assert analyzer._is_bundle(tmp_dir) is True

        # 2. .tar.gz is a bundle
        tar_path = os.path.join(tmp_dir, "bundle.tar.gz")
        with open(tar_path, "w") as f:
            f.write("fake tar")
        assert analyzer._is_bundle(tar_path) is True

        # 3. .rego file is NOT a bundle
        rego_path = os.path.join(tmp_dir, "policy.rego")
        with open(rego_path, "w") as f:
            f.write("package test")
        assert analyzer._is_bundle(rego_path) is False


@patch("shutil.which")
@patch("subprocess.run")
def test_opa_eval_bundle_flag(mock_run, mock_which):
    mock_which.return_value = "/usr/bin/opa"
    mock_run.return_value = MagicMock(returncode=0, stdout='{"result": []}')

    analyzer = OpaAnalyzer()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Force it to treat tmp_dir as policy_path
        analyzer.policy_path = tmp_dir

        analyzer.analyze([])

        # Check that --bundle was used
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "--bundle" in cmd
        assert "--data" not in cmd


@patch("shutil.which")
@patch("subprocess.run")
def test_opa_eval_data_flag_for_single_file(mock_run, mock_which):
    mock_which.return_value = "/usr/bin/opa"
    mock_run.return_value = MagicMock(returncode=0, stdout='{"result": []}')

    analyzer = OpaAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".rego", delete=False) as tmp_file:
        tmp_file.write(b"package test")
        tmp_file_path = tmp_file.name

    try:
        analyzer.policy_path = tmp_file_path
        analyzer.analyze([])

        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "--data" in cmd
        assert "--bundle" not in cmd
    finally:
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
