import pytest

from yamlr.ui.diff_engine import SideBySideDiff


def test_diff_unchanged():
    old = "line1\nline2"
    new = "line1\nline2"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert all(d[2] == "UNCHANGED" for d in diff)
    assert diff[0][0] == "line1"
    assert diff[0][1] == "line1"

def test_diff_added():
    old = "line1"
    new = "line1\nline2"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[0][2] == "UNCHANGED"
    assert diff[1][2] == "ADDED"
    assert diff[1][0] is None
    assert diff[1][1] == "line2"

def test_diff_removed():
    old = "line1\nline2"
    new = "line1"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[1][2] == "REMOVED"
    assert diff[1][0] == "line2"
    assert diff[1][1] is None

def test_diff_changed():
    old = "line1\nold_val"
    new = "line1\nnew_val"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[1][2] == "CHANGED"
    assert diff[1][0] == "old_val"
    assert diff[1][1] == "new_val"

def test_diff_replace_mismatch():
    old = "line1\nold1\nold2"
    new = "line1\nnew1"
    diff = SideBySideDiff.calculate(old, new)
    # tag will be 'replace' for old1,old2 -> new1
    # max_len = 2
    # k=0: left=old1, right=new1, status=CHANGED
    # k=1: left=old2, right=None, status=CHANGED
    assert any(d[2] == "CHANGED" for d in diff)


def test_cli_diff_subcommand_registered():
    """Verify that 'diff' is registered as a Core CLI command."""
    from yamlr.cli.parser import create_parser
    parser = create_parser()
    args = parser.parse_args(["diff", "some/path.yaml", "-u"])
    assert args.command == "diff"
    assert args.path == "some/path.yaml"
    assert args.unified is True

