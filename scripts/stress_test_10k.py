#!/usr/bin/env python3
"""
Yamlr Google-Scale Stress Test (Sprint 3) - Optimized
----------------------------------------------------
Uses native batch processing to verify the Core Engine.
"""

import os
import time
import shutil
import random
from pathlib import Path

# Configuration
MANIFEST_COUNT = 10000
WORKSPACE_DIR = Path("d:/yamlr/scratch/stress_test_manifests")

def generate_manifests(count: int):
    """Generates 10k unique K8s manifests."""
    if WORKSPACE_DIR.exists():
        shutil.rmtree(WORKSPACE_DIR, ignore_errors=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    
    kinds = ["Deployment", "Service", "ConfigMap", "Secret", "Ingress"]
    
    print(f"Generating {count} manifests...")
    for i in range(count):
        kind = random.choice(kinds)
        name = f"resource-{i}"
        namespace = f"ns-{i // 100}"
        
        # Create a relationship: Every 10th resource is a Service pointing to the 9th resource (Deployment)
        target_name = f"resource-{i-1}" if i % 10 == 0 and i > 0 else name
        
        content = f"""apiVersion: v1
kind: {kind}
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: {name}
    env: production
spec:
  selector:
    matchLabels:
      app: {target_name}
  serviceAccountName: sa-global
"""
        with open(WORKSPACE_DIR / f"{name}.yaml", "w") as f:
            f.write(content)
    
    # Add the global ServiceAccount to make edges work
    with open(WORKSPACE_DIR / "sa-global.yaml", "w") as f:
        f.write("""apiVersion: v1
kind: ServiceAccount
metadata:
  name: sa-global
  namespace: ns-0
""")

def run_stress_test():
    import yamlr_native
    print(f"Using yamlr_native from: {yamlr_native.__file__}")

    all_identities = []
    
    print("\nStarting Discovery (10k files)...")
    start_time = time.time()
    
    # [ACCELERATION] Single native call for the entire directory
    native_results = yamlr_native.native_discover_resources(str(WORKSPACE_DIR))
    
    all_identities = [r.identity for r in native_results if r.identity]
    discovery_time = time.time() - start_time
    print(f"Discovery Completed in {discovery_time:.2f}s (Target: <10s)")
    print(f"Total Files Found: {len(native_results)}")
    print(f"Identities Discovered: {len(all_identities)}")
    
    if not all_identities:
        print("❌ FAILED: No identities discovered.")
        return

    print(f"\nStarting Native Graph Building ({len(all_identities)} nodes)...")
    start_time = time.time()
    
    # [HARDENING] Use the correct class for graph building
    edges = yamlr_native.build_graph_edges(all_identities)
    
    graph_time = time.time() - start_time
    print(f"Graph Building Completed in {graph_time:.2f}s")
    print(f"Nodes: {len(all_identities)}, Edges: {len(edges)}")

    if edges:
        print("\nStarting Native Blast Radius Calculation...")
        start_time = time.time()
        # Calculate for a random node
        sample_node = edges[0].source
        radius = yamlr_native.native_calculate_blast_radius(sample_node, edges)
        radius_time = time.time() - start_time
        print(f"Blast Radius Calculation Completed in {radius_time:.4f}s")
        print(f"Source: {radius.source}, Affected Nodes: {radius.affected_count}, Depth: {radius.depth}, Risk: {radius.risk_level}")

    # 2. Native Journaling Stress (1k entries)
    print("\nStarting Journaling Stress Test (1k entries)...")
    journal_path = WORKSPACE_DIR / "stress.jsonl"
    start_time = time.time()
    for i in range(1000):
        yamlr_native.native_log_remediation(
            journal_path=str(journal_path),
            file_path=f"file-{i}.yaml",
            pre_dna="hash1",
            post_dna="hash2",
            rules=["RULE-001"],
            status="HEALED"
        )
    journal_time = time.time() - start_time
    print(f"Journaling Completed in {journal_time:.2f}s (Target: <0.5s)")

if __name__ == "__main__":
    generate_manifests(MANIFEST_COUNT)
    run_stress_test()
