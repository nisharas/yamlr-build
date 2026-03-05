import unittest
from yamlr.parsers.coercer import TypeCoercer

class TestTypeCoercer(unittest.TestCase):
    def setUp(self):
        self.coercer = TypeCoercer()

    def test_integer_coercion(self):
        schema = {"type": "integer"}
        self.assertEqual(self.coercer.coerce("3", schema), 3)
        self.assertEqual(self.coercer.coerce(" 10 ", schema), 10)
        self.assertEqual(self.coercer.coerce("\"5\"", schema), 5)
        # Should not coerce non-numeric strings
        self.assertEqual(self.coercer.coerce("abc", schema), "abc")

    def test_boolean_coercion(self):
        schema = {"type": "boolean"}
        self.assertEqual(self.coercer.coerce("true", schema), True)
        self.assertEqual(self.coercer.coerce("TRUE", schema), True)
        self.assertEqual(self.coercer.coerce("false", schema), False)
        self.assertEqual(self.coercer.coerce("\"true\"", schema), True)
        # Should not coerce non-boolean strings
        self.assertEqual(self.coercer.coerce("maybe", schema), "maybe")

    def test_number_coercion(self):
        schema = {"type": "number"}
        self.assertEqual(self.coercer.coerce("3.14", schema), 3.14)
        self.assertEqual(self.coercer.coerce("-0.5", schema), -0.5)
        self.assertEqual(self.coercer.coerce("10", schema), 10.0)

    def test_int_or_string_skip(self):
        # x-kubernetes-int-or-string should be skipped
        schema = {"x-kubernetes-int-or-string": True, "type": "string"}
        self.assertEqual(self.coercer.coerce("8080", schema), "8080")

    def test_missing_schema(self):
        self.assertEqual(self.coercer.coerce("123", None), "123")
        self.assertEqual(self.coercer.coerce("123", {}), "123")

    def test_string_coercion(self):
        schema = {"type": "string"}
        # Numbers to string
        self.assertEqual(self.coercer.coerce(123, schema), "123")
        self.assertEqual(self.coercer.coerce(1.5, schema), "1.5")
        # Booleans to string (K8s style)
        self.assertEqual(self.coercer.coerce(True, schema), "true")
        self.assertEqual(self.coercer.coerce(False, schema), "false")
        # Strings stay strings
        self.assertEqual(self.coercer.coerce("already-string", schema), "already-string")

if __name__ == "__main__":
    unittest.main()
