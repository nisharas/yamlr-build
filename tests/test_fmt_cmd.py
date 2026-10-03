"""Tests for canonical manifest formatting and zero-flag fixing (k8sfmt / yamlfix)."""
import os
import tempfile
from pathlib import Path

from yamlr.cli.fmt_handler import cmd_fix_dispatch, cmd_fmt_dispatch, format_yaml_string

UNORDERED_YAML = """kind: Service
metadata:
  name: test-svc
apiVersion: v1
spec:
  ports:
    - port: 80
"""

DEPRECATED_YAML = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 2
"""


def test_format_yaml_string_orders_keys():
    """Verify official Kubernetes schema key ordering: apiVersion, kind, metadata, spec."""
    formatted = format_yaml_string(UNORDERED_YAML)
    lines = [line.split(":")[0].strip() for line in formatted.strip().splitlines() if not line.startswith(" ") and not line.startswith("-")]
    assert lines == ["apiVersion", "kind", "metadata", "spec"]


def test_cmd_fmt_file_write_in_place():
    """Verify yamlr fmt -w modifies file in place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "service.yaml"
        fpath.write_text(UNORDERED_YAML, encoding="utf-8")

        class Args:
            path = str(fpath)
            write = True
            w = True

        res = cmd_fmt_dispatch(Args())
        assert res == 0

        content = fpath.read_text(encoding="utf-8")
        assert content.startswith("apiVersion: v1")


def test_cmd_fix_file():
    """Verify yamlr fix upgrades deprecated manifests directly without flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "deployment.yaml"
        fpath.write_text(DEPRECATED_YAML, encoding="utf-8")

        class Args:
            path = str(fpath)

        res = cmd_fix_dispatch(Args())
        assert res == 0

        content = fpath.read_text(encoding="utf-8")
        assert "apps/v1" in content
