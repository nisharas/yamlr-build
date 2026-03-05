import unittest
from yamlr.parsers.schema_manager import SchemaManager

class TestFuzzyEdgeCases(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "apiVersion": {},
            "kind": {},
            "metadata": {},
            "spec": {
                "properties": {
                    "containers": {},
                    "replicas": {},
                    "template": {}
                }
            },
            "labels": {},
            "annotations": {}
        }
        self.manager = SchemaManager(catalog=self.catalog)

    def test_case_insensitivity(self):
        # NEW: Case-insensitive match should work now
        self.assertEqual(self.manager.fuzzy_match("Kind"), "kind")
        self.assertEqual(self.manager.fuzzy_match("Apiversion"), "apiVersion")

    def test_short_keys(self):
        # 'api' should NOT match 'apiVersion' (too short/ambiguous)
        self.assertIsNone(self.manager.fuzzy_match("api"))
        # 'sp' should NOT match 'spec'
        self.assertIsNone(self.manager.fuzzy_match("sp"))

    def test_labels_collision(self):
        # A user label like 'app-version' might match 'apiVersion'?
        # ratio("app-version", "apiVersion")
        # len("app-version") = 11, len("apiVersion") = 10
        # matches: a, p, v, e, r, s, i, o, n (most of them)
        match = self.manager.fuzzy_match("app-version")
        if match:
            print(f"WARNING: 'app-version' matched '{match}' - Potential False Positive in labels!")

    def test_ambiguous_ties(self):
        # 'replica' vs 'replicas'
        self.assertEqual(self.manager.fuzzy_match("replica"), "replicas")

if __name__ == "__main__":
    unittest.main()
