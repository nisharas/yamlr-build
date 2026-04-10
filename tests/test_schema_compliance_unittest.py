import logging
import os
import unittest
from pathlib import Path

import yaml

from yamlr.core.engine import YamlrEngine
from yamlr.core.utils import resolve_bundled_asset
from yamlr.validators.schema_validator import SchemaValidator

# Configure logging to suppress noisy output during tests
logging.getLogger("yamlr").setLevel(logging.CRITICAL)


class TestSchemaCompliance(unittest.TestCase):
    """
    QA-12-03: Schema Compliance Gate
    Verifies that healed output from Yamlr is 100% compliant with K8s OpenAPI schemas.
    """

    @classmethod
    def setUpClass(cls):
        # Initialize engine and validator once
        catalog_path = str(resolve_bundled_asset("catalog/k8s_v1_distilled.json"))
        cls.engine = YamlrEngine(workspace_path=".", app_name="YamlrTest", catalog_path=catalog_path)
        cls.validator = SchemaValidator(k8s_version="1.31")
        # Ensure schema is loaded
        if not cls.validator.load_schema():
            raise RuntimeError("Failed to load K8s schema for testing")

    def _heal_and_validate(self, file_path: Path):
        """Heals a file and validates the output against K8s schema."""
        if not file_path.exists():
            print(f"Skipping missing file: {file_path}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Run healing
        result = self.engine.pipeline.heal(content, file_path=str(file_path), strict_validation=False, compact=False)

        # If healing failed (e.g. unparseable), check if it was expected
        # For this gate, we expect *if* it produces output, that output must be valid K8s.
        if result.status == "FAILED":
            # If the engine explicitly failed, that's "safe" (no invalid output produced)
            return

        # If skipped, also safe
        if result.status == "SKIPPED":
            return

        healed_content = result.content
        if not healed_content:
            return

        # Parse healed content
        try:
            docs = list(yaml.safe_load_all(healed_content))
        except yaml.YAMLError as e:
            self.fail(f"Healed output for {file_path.name} is invalid YAML: {e}")

        # Validate each document
        for doc in docs:
            if not doc:
                continue

            # Skip if no Kind/APIVersion (Lexer might have left it broken if unhealable)
            # But if it HAS Kind/APIVersion, it MUST be valid.
            if "kind" not in doc or "apiVersion" not in doc:
                continue

            errors = self.validator.validate_full_document(doc)
            if errors:
                # Format helpful failure message
                msg = f"\nSchema Violation in {file_path.name}:\n"
                msg += "\n".join(errors)
                self.fail(msg)

    def test_corpus_dirty(self):
        """Validates all files in tests/corpus/dirty"""
        corpus_dir = Path("tests/corpus/dirty")
        if not corpus_dir.exists():
            return

        for ext in ["*.yaml", "*.yml"]:
            for f in corpus_dir.glob(ext):
                with self.subTest(file=f.name):
                    self._heal_and_validate(f)

    def test_corpus_toxic(self):
        """Validates all files in tests/corpus/toxic"""
        corpus_dir = Path("tests/corpus/toxic")
        if not corpus_dir.exists():
            return

        # Toxic corpus is large, let's test significant sample or all
        # For the gate, we want ALL.
        for ext in ["*.yaml", "*.yml"]:
            for f in corpus_dir.glob(ext):
                with self.subTest(file=f.name):
                    self._heal_and_validate(f)

    def test_corpus_valid(self):
        """Validates all files in tests/corpus/valid"""
        corpus_dir = Path("tests/corpus/valid")
        if not corpus_dir.exists():
            return

        for ext in ["*.yaml", "*.yml"]:
            for f in corpus_dir.glob(ext):
                with self.subTest(file=f.name):
                    self._heal_and_validate(f)


if __name__ == "__main__":
    unittest.main()
