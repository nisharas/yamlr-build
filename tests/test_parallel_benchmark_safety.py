"""Safety tests for the parallel benchmark corpus generator."""

import importlib.util
import sys
from types import ModuleType
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "benchmark" / "benchmark_parallel.py"
SPEC = importlib.util.spec_from_file_location("benchmark_parallel", SCRIPT_PATH)
BENCHMARK = importlib.util.module_from_spec(SPEC)
ENGINE_MODULE = ModuleType("yamlr.core.engine")
ENGINE_MODULE.YamlrEngine = object
CORE_MODULE = ModuleType("yamlr.core")
CORE_MODULE.engine = ENGINE_MODULE
YAMLR_MODULE = ModuleType("yamlr")
YAMLR_MODULE.core = CORE_MODULE
with patch.dict(
    sys.modules,
    {
        "yamlr": YAMLR_MODULE,
        "yamlr.core": CORE_MODULE,
        "yamlr.core.engine": ENGINE_MODULE,
    },
):
    SPEC.loader.exec_module(BENCHMARK)


def test_missing_corpus_requires_no_overwrite_or_confirmation(tmp_path):
    corpus = tmp_path / "new"

    BENCHMARK.prepare_corpus_directory(
        corpus,
        overwrite=False,
        confirm=lambda _: pytest.fail("confirmation must not be requested for a missing path"),
    )

    assert not corpus.exists()


def test_existing_corpus_is_preserved_without_overwrite_option(tmp_path):
    corpus = tmp_path / "existing"
    corpus.mkdir()
    marker = corpus / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--overwrite"):
        BENCHMARK.prepare_corpus_directory(corpus, overwrite=False)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_existing_file_is_not_treated_as_a_corpus_directory(tmp_path):
    corpus = tmp_path / "existing-file"
    corpus.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        BENCHMARK.prepare_corpus_directory(corpus, overwrite=True, confirm=lambda _: "")

    assert corpus.read_text(encoding="utf-8") == "keep"


def test_declined_confirmation_preserves_existing_corpus(tmp_path):
    corpus = tmp_path / "existing"
    corpus.mkdir()
    marker = corpus / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(PermissionError, match="not confirmed"):
        BENCHMARK.prepare_corpus_directory(corpus, overwrite=True, confirm=lambda _: "no")

    assert marker.read_text(encoding="utf-8") == "keep"


def test_unavailable_confirmation_preserves_existing_corpus(tmp_path):
    corpus = tmp_path / "existing"
    corpus.mkdir()
    marker = corpus / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    def unavailable_confirmation(_):
        raise EOFError

    with pytest.raises(PermissionError, match="not confirmed"):
        BENCHMARK.prepare_corpus_directory(corpus, overwrite=True, confirm=unavailable_confirmation)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_exact_confirmation_replaces_existing_corpus(tmp_path):
    corpus = tmp_path / "existing"
    corpus.mkdir()
    (corpus / "old.txt").write_text("old", encoding="utf-8")
    confirmation = f"OVERWRITE {corpus.resolve()}"

    BENCHMARK.prepare_corpus_directory(corpus, overwrite=True, confirm=lambda _: confirmation)

    assert not corpus.exists()


def test_repository_and_filesystem_roots_are_never_replaced(tmp_path):
    repository_root = Path(BENCHMARK.__file__).resolve().parents[2]
    for protected_path in (Path(repository_root.anchor), repository_root):
        with pytest.raises(ValueError, match="root"):
            BENCHMARK.prepare_corpus_directory(
                protected_path,
                overwrite=True,
                confirm=lambda _: f"OVERWRITE {protected_path.resolve()}",
            )
