import unittest
from yamlr.parsers.coercer import TypeCoercer

class TestTypeCoercerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.coercer = TypeCoercer()

    def test_boolean_variations(self):
        schema = {"type": "boolean"}
        self.assertTrue(self.coercer.coerce("yes", schema))
        self.assertTrue(self.coercer.coerce("on", schema))
        self.assertFalse(self.coercer.coerce("no", schema))
        self.assertFalse(self.coercer.coerce("off", schema))
        self.assertIsNone(self.coercer.coerce("", schema))

    def test_integer_robustness(self):
        schema = {"type": "integer"}
        # Scientific Notation
        self.assertEqual(self.coercer.coerce("1e3", schema), 1000)
        self.assertEqual(self.coercer.coerce("1.0e2", schema), 100)
        # Hex/Octal
        self.assertEqual(self.coercer.coerce("0x10", schema), 16)
        self.assertEqual(self.coercer.coerce("0o10", schema), 8)
        # Decimal strings
        self.assertEqual(self.coercer.coerce("1.0", schema), 1)
        self.assertIsNone(self.coercer.coerce("", schema))
        
    def test_number_robustness(self):
        schema = {"type": "number"}
        self.assertEqual(self.coercer.coerce("1.23", schema), 1.23)
        self.assertIsNone(self.coercer.coerce("", schema))

if __name__ == "__main__":
    unittest.main()
