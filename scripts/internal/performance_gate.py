import os
import subprocess
import sys
import time
from pathlib import Path


def measure_command(cmd_list):
    start = time.perf_counter()
    result = subprocess.run(
        cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "PYTHONPATH": "src"}
    )
    end = time.perf_counter()
    return (end - start) * 1000, result.returncode


def check_fidelity():
    """Verifies that the graph engine is actually building relationships."""
    print("[INFO] Starting Fidelity Checks (Edge Density Gate)")
    try:
        from yamlr.core.catalog import ManifestCatalog
        from yamlr.core.identities import ManifestIdentity

        from yamlr.core.resource_graph import ResourceGraph

        # Create a tiny test corpus with a known dependency (Deployment -> ServiceAccount)
        graph = ResourceGraph()
        catalog = ManifestCatalog()

        # Mock nodes
        identities = [
            ManifestIdentity(kind="Deployment", name="app", namespace="default", service_account="sa-1"),
            ManifestIdentity(kind="ServiceAccount", name="sa-1", namespace="default"),
        ]

        # Build graph
        graph.build(identities, catalog)

        # Verify
        if graph.node_count < 2:
            print(f"[FAIL] Fidelity: Not enough nodes ({graph.node_count})")
            return False

        # We expect at least 1 edge (Deployment -> ServiceAccount)
        if graph.edge_count < 1:
            print(f"[FAIL] Fidelity: 0 edges found for {graph.node_count} nodes (Native Edge Vacuum!)")
            return False

        density = graph.edge_count / graph.node_count
        print(f"[PASS] Fidelity: {graph.edge_count} edges, {graph.node_count} nodes (Density: {density:.2f})")
        return True
    except Exception as e:
        print(f"[ERROR] Fidelity check crashed: {e}")
        return False


def main():
    print("[INFO] Starting CI Performance & Fidelity Gate")

    # Check 1: Latency
    commands = [["python", "-m", "yamlr.cli.main", "-h"], ["python", "-m", "yamlr.cli.main", "status"]]

    latency_passed = True
    for cmd in commands:
        latency_ms, code = measure_command(cmd)
        cmd_str = " ".join(cmd[1:])
        if latency_ms > 1500:  # Realistic threshold for cold-start Python on Windows
            print(f"[FAIL] Latency {cmd_str}: {latency_ms:.1f}ms")
            latency_passed = False
        else:
            print(f"[PASS] Latency {cmd_str}: {latency_ms:.1f}ms")

    # Check 2: Fidelity
    fidelity_passed = check_fidelity()

    if not (latency_passed and fidelity_passed):
        print("\n[RED] CI GATE FAILED: Performance or Fidelity regression detected.")
        sys.exit(1)

    print("\n[GREEN] CI GATE PASSED: All metrics within performance thresholds.")


if __name__ == "__main__":
    main()
