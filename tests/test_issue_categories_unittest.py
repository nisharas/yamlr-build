import unittest
import os
import shutil
import tempfile
from yamlr.core.engine import YamlrEngine
from yamlr.core.utils import resolve_bundled_asset

class TestIssueCategories(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.catalog_path = str(resolve_bundled_asset("catalog/k8s_v1_distilled.json"))
        # Initialize engine with temp workspace
        self.engine = YamlrEngine(
            workspace_path=self.test_dir, 
            catalog_path=self.catalog_path, 
            app_name="YamlrTest"
        )

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def _test_category(self, input_yaml, expected_yaml, msg=None):
        test_file = os.path.join(self.test_dir, "test.yaml")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(input_yaml)
        
        # Run audit and heal
        result = self.engine.audit_and_heal_file(
            test_file,
            dry_run=False,
            force_write=True
        )
        
        # Read back content
        with open(test_file, "r", encoding="utf-8") as f:
            healed_content = f.read()

        # Normalize line endings
        healed_content = healed_content.replace("\r\n", "\n").strip()
        expected_yaml_normalized = expected_yaml.replace("\r\n", "\n").strip()
        
        self.assertEqual(healed_content, expected_yaml_normalized, msg)

    def test_indentation_mixed(self):
        # Use labels for generic key/value
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n\t\tkey: value" 
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    key: value"
        self._test_category(input_yaml, expected_yaml, "Mixed indentation (tabs) fix failed")

    def test_colons_missing(self):
        # MagicColonHeuristic: "image nginx" -> "image: nginx"
        # Use Pod spec -> containers -> image
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n  - name: c1\n    image nginx"
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n  - name: c1\n    image: nginx"
        self._test_category(input_yaml, expected_yaml, "Missing colon fix failed")

    def test_quotes_unclosed(self):
        # QuoteBalancing. Use a value that NEEDS quotes to avoid normalization (e.g., 'true')
        # "val'ue" -> 'val''ue' ? No, "value" -> value. "val'ue" -> "val'ue".
        # Let's use 'true which means string "true".
        # Unclosed: 'true
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    unsafe: 'true"
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    unsafe: 'true'"
        self._test_category(input_yaml, expected_yaml, "Unclosed quote fix failed")

    def test_lists_flush_left(self):
        # fix_flush_left_lists: Pod containers
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n- name: c1"
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n  - name: c1"
        self._test_category(input_yaml, expected_yaml, "Flush left list fix failed")

    def test_spacing_fixes(self):
        # SpacingHeuristic: "key:value" -> "key: value"
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    key:value"
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    key: value"
        self._test_category(input_yaml, expected_yaml, "Spacing fix failed")

    def test_quote_preservation(self):
        # Use "true" string to ensure quotes are preserved (otherwise it becomes boolean true)
        input_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    force_string: \"true\""
        expected_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  labels:\n    force_string: 'true'" 
        # Note: Yamlr/Ruamel might switch " to ' or vice versa, but it MUST be quoted.
        # Let's verify it remains quoted. 
        # If expected is 'true' and actual is "true", we might have a mismatch but semantically same.
        # Let's try matching 'true' as that's often preferred.
        self._test_category(input_yaml, expected_yaml, "Quote preservation failed")


if __name__ == "__main__":
    unittest.main()
