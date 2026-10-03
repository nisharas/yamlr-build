import yamlr_native
import time

# 1. Setup a Relation (Service -> Deployment)
deployment = yamlr_native.NativeIdentity(
    kind="Deployment",
    api_version="apps/v1",
    name="web",
    namespace="default",
    labels={"app": "web", "version": "v1"},
    selector={},
    config_refs=[],
    secret_refs=[],
    volume_refs=[],
    service_refs=[],
    role_refs=[],
    cluster_role_refs=[],
    service_account=None
)

service = yamlr_native.NativeIdentity(
    kind="Service",
    api_version="v1",
    name="web-svc",
    namespace="default",
    labels={},
    selector={"app": "web"}, # Points to Deployment
    config_refs=[],
    secret_refs=[],
    volume_refs=[],
    service_refs=[],
    role_refs=[],
    cluster_role_refs=[],
    service_account=None
)

# Build the graph
edges = yamlr_native.build_graph_edges([deployment, service])
print(f"Graph built with {len(edges)} edges.")
for e in edges:
    print(f" - Edge: {e.source} -> {e.target} ({e.edge_type}) Selector: {e.selector}")

# 2. PROPOSE A MUTATION: Change Deployment labels (Breaks Service link)
# Deployment is the TARGET of the Service's SelectorMatch edge
proposed_deployment = yamlr_native.NativeIdentity(
    "Deployment",
    "apps/v1",
    "web",
    "default",
    {"app": "legacy-web"}, # CHANGED
    {}, # selector
    [], [], [], [], [], [], # refs
    None # sa
)

print("\nVerifying Relational Integrity of mutation (Resource: Deployment/default/web)...")
start_time = time.time()
violations = yamlr_native.native_verify_relational_integrity(proposed_deployment, edges)
duration = time.time() - start_time

if violations:
    print(f"FAILED: INTEGRITY BREACH DETECTED ({duration:.6f}s):")
    for v in violations:
        print(f" - {v.message}")
else:
    print(f"SUCCESS: Mutation is safe ({duration:.6f}s).")

# 3. SURGICAL RECONSTRUCTION TEST
original_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web # My comment
  labels:
    app: web
spec:
  replicas: 3 # Stay at 3
"""

print("\nTesting Surgical Reconstruction...")
shards = yamlr_native.native_shard(original_yaml)
mutations = {"app": "legacy-web", "replicas": "5"}
healed_yaml = yamlr_native.native_reconstruct_manifest(shards, mutations)

print("Original:")
print(original_yaml)
print("\nHealed (Surgical):")
print(healed_yaml)
