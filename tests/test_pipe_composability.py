"""Tests for POSIX / Unix pipe composability (stdin / stdout)."""
import io
import sys

from yamlr.cli.fmt_handler import cmd_fix_dispatch, cmd_fmt_dispatch

INPUT_UNORDERED = """kind: Service
metadata:
  name: pipe-svc
apiVersion: v1
spec:
  ports:
    - port: 443
"""

INPUT_DEPRECATED = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: pipe-deployment
spec:
  replicas: 2
"""


def test_fmt_stdin_stdout(monkeypatch):
    """Verify yamlr fmt - reads from stdin and outputs formatted YAML to stdout."""
    monkeypatch.setattr('sys.stdin', io.StringIO(INPUT_UNORDERED))
    out_capture = io.StringIO()
    monkeypatch.setattr('sys.stdout', out_capture)

    class Args:
        path = "-"
        write = False
        w = False

    res = cmd_fmt_dispatch(Args())
    assert res == 0

    output = out_capture.getvalue()
    lines = [l.split(":")[0].strip() for l in output.strip().splitlines() if not l.startswith(" ") and not l.startswith("-")]
    assert lines == ["apiVersion", "kind", "metadata", "spec"]


def test_fix_stdin_stdout(monkeypatch):
    """Verify yamlr fix - reads from stdin and outputs healed YAML to stdout."""
    monkeypatch.setattr('sys.stdin', io.StringIO(INPUT_DEPRECATED))
    out_capture = io.StringIO()
    monkeypatch.setattr('sys.stdout', out_capture)

    class Args:
        path = "-"

    res = cmd_fix_dispatch(Args())
    assert res == 0

    output = out_capture.getvalue()
    assert "apiVersion: apps/v1" in output
    assert "kind: Deployment" in output
