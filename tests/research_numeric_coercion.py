from yamlr.parsers.coercer import TypeCoercer

coercer = TypeCoercer()
integer_schema = {"type": "integer"}

# Scientific Notation Test
print(f"Coercing '1e3' to int: {coercer.coerce('1e3', integer_schema)}")
print(f"Coercing '1.0e2' to int: {coercer.coerce('1.0e2', integer_schema)}")

# Hex Test
print(f"Coercing '0x10' to int: {coercer.coerce('0x10', integer_schema)}")
