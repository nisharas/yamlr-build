import os
import unittest

from yamlr.core.identity import ManifestIdentity
from yamlr.core.resource_graph import ResourceGraph


class TestNativeFidelity(unittest.TestCase):
    def setUp(self):
        self.graph = ResourceGraph()
        self.catalog = {}  # Using empty dict as mock catalog
        # Identity with a clear dependency: Deployment -> ServiceAccount
        self.identities = [
            ManifestIdentity(kind="Deployment", name="app", namespace="prod", service_account="sa-secure"),
            ManifestIdentity(kind="ServiceAccount", name="sa-secure", namespace="prod"),
            ManifestIdentity(kind="ConfigMap", name="cfg", namespace="prod"),
            ManifestIdentity(kind="Deployment", name="api", namespace="prod"),
            ManifestIdentity(kind="Service", name="api-svc", namespace="prod"),
            ManifestIdentity(kind="Ingress", name="api-ing", namespace="prod"),
        ]

    def test_fidelity_baseline(self):
        # Python-only baseline
        os.environ["YAMLR_DISABLE_NATIVE"] = "1"
        self.graph.build(self.identities)

        edges = self.graph._edges
        self.assertGreater(len(edges), 0, "Python baseline should find edges")
        self.assertTrue(
            any(e.edge_type.value == "ServiceAccount" or "sa" in e.target_key for e in edges),
            "Baseline missing SA edge",
        )

    def test_native_fidelity_fallback(self):
        # Native mode (will return 0 edges, triggering fallback)
        if "YAMLR_DISABLE_NATIVE" in os.environ:
            del os.environ["YAMLR_DISABLE_NATIVE"]

        self.graph.build(self.identities)

        print(f"DEBUG: Native/Hybrid - Nodes: {self.graph.node_count}, Edges: {self.graph.edge_count}")
        self.assertGreater(self.graph.edge_count, 0, "Fidelity Guard should ensure edges exist even in native mode")
        self.assertEqual(self.graph.node_count, 6)


if __name__ == "__main__":
    unittest.main()
