import yamlr_native
import time

# 1. Define a Mock Schema for Deployment
deployment_schema = yamlr_native.NativeSchema(
    kind="Deployment",
    api_version="apps/v1",
    properties=[
        yamlr_native.SchemaProperty(name="replicas", prop_type="integer", required=True, description="Number of replicas"),
        yamlr_native.SchemaProperty(name="template", prop_type="object", required=True, description="Pod template"),
        yamlr_native.SchemaProperty(name="name", prop_type="string", required=True, description="Resource name"),
    ]
)

# 2. Define a Malformed Resource (Missing 'replicas' and 'template')
malformed_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deploy
spec:
  selector:
    matchLabels:
      app: web
"""

print("Starting Native Schema Intelligence Test...")
start_time = time.time()

# 3. Check for Violations
violations = yamlr_native.native_check_schema_violations(malformed_yaml, [deployment_schema])

duration = time.time() - start_time
print(f"Intelligence Check Completed in {duration:.6f}s")

if violations:
    print(f"Found {len(violations)} violations:")
    for v in violations:
        print(f" - [{v.severity}] {v.field_path}: {v.message}")
else:
    print("✅ No violations found.")

# 4. Stress Test: 10,000 checks
print(f"\nRunning Stress Test: 10,000 schema checks...")
start_time = time.time()
for _ in range(10000):
    yamlr_native.native_check_schema_violations(malformed_yaml, [deployment_schema])
stress_duration = time.time() - start_time
print(f"10,000 checks completed in {stress_duration:.2f}s ({stress_duration/10000:.6f}s per check)")
