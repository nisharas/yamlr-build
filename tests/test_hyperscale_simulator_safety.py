"""Safety tests for the hyperscale fixture generator's output handling."""

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "benchmark" / "simulate_hyperscale.py"
SPEC = importlib.util.spec_from_file_location("simulate_hyperscale", SCRIPT_PATH)
SIMULATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SIMULATOR)


def test_existing_output_is_preserved_without_overwrite_option(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--overwrite"):
        SIMULATOR.prepare_output_directory(output, overwrite=False)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_declined_confirmation_preserves_existing_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(PermissionError, match="not confirmed"):
        SIMULATOR.prepare_output_directory(output, overwrite=True, confirm=lambda _: "no")

    assert marker.read_text(encoding="utf-8") == "keep"


def test_exact_confirmation_replaces_existing_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "old.txt").write_text("old", encoding="utf-8")
    confirmation = f"OVERWRITE {output.resolve()}"

    SIMULATOR.prepare_output_directory(output, overwrite=True, confirm=lambda _: confirmation)

    assert not output.exists()


def test_filesystem_and_repository_roots_are_never_replaced(tmp_path):
    repository_root = Path(SIMULATOR.__file__).resolve().parents[2]
    for protected_path in (Path(repository_root.anchor), repository_root):
        with pytest.raises(ValueError, match="root"):
            SIMULATOR.prepare_output_directory(
                protected_path,
                overwrite=True,
                confirm=lambda _: f"OVERWRITE {protected_path.resolve()}",
            )
