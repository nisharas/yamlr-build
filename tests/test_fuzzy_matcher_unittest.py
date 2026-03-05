import unittest
from yamlr.parsers.schema_manager import SchemaManager

class TestFuzzyMatcher(unittest.TestCase):
    def setUp(self):
        # Sample catalog with some common keys
        self.catalog = {
            "apiVersion": {},
            "kind": {},
            "metadata": {},
            "spec": {
                "properties": {
                    "containers": {},
                    "replicas": {}
                }
            }
        }
        self.manager = SchemaManager(catalog=self.catalog)

    def test_exact_match(self):
        self.assertEqual(self.manager.fuzzy_match("apiVersion"), "apiVersion")
        self.assertEqual(self.manager.fuzzy_match("kind"), "kind")

    def test_simple_typo(self):
        # Levenshtein distance 1
        self.assertEqual(self.manager.fuzzy_match("apiVerson"), "apiVersion")
        self.assertEqual(self.manager.fuzzy_match("metdadata"), "metadata")
        self.assertEqual(self.manager.fuzzy_match("contianers"), "containers")

    def test_no_match(self):
        # Too different
        self.assertIsNone(self.manager.fuzzy_match("completely_wrong_key"))
        # Below cutoff
        self.assertIsNone(self.manager.fuzzy_match("api", cutoff=0.9))

    def test_unambiguous_match(self):
        # "replcas" should match "replicas"
        self.assertEqual(self.manager.fuzzy_match("replcas"), "replicas")

if __name__ == "__main__":
    unittest.main()
