import unittest
from typing import Dict, Any
from yamlr.healers.best_practices.resources import ResourcesHealer
from yamlr.healers.best_practices.security import SecurityContextHealer
from yamlr.healers.best_practices.probes import ProbeHealer
from yamlr.healers.best_practices.image_tag import ImageTagHealer

class TestProHealers(unittest.TestCase):
    def setUp(self):
        self.resources = ResourcesHealer()
        self.security = SecurityContextHealer()
        self.probes = ProbeHealer()
        self.image_tag = ImageTagHealer()

    def test_smart_resource_limits(self):
        # Test App
        doc_app = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": "web-app", "image": "nginx"}]
                    }
                }
            }
        }
        self.resources.heal_doc(doc_app, enforce_defaults=True)
        res = doc_app["spec"]["template"]["spec"]["containers"][0]["resources"]
        self.assertEqual(res["limits"]["cpu"], "500m")
        self.assertEqual(res["requests"]["cpu"], "250m")

        # Test Sidecar
        doc_sidecar = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": "istio-proxy", "image": "envoy"}]
                    }
                }
            }
        }
        self.resources.heal_doc(doc_sidecar, enforce_defaults=True)
        res = doc_sidecar["spec"]["template"]["spec"]["containers"][0]["resources"]
        self.assertEqual(res["limits"]["cpu"], "100m")
        self.assertEqual(res["requests"]["cpu"], "50m")

        # Test Pause
        doc_pause = {
            "kind": "Pod",
            "spec": {
                "containers": [{"name": "pause", "image": "k8s.gcr.io/pause"}]
            }
        }
        self.resources.heal_doc(doc_pause, enforce_defaults=True)
        res = doc_pause["spec"]["containers"][0]["resources"]
        self.assertEqual(res["limits"]["cpu"], "10m")
        self.assertEqual(res["requests"]["cpu"], "5m")

    def test_full_security_hardening(self):
        doc = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": "web-app", "image": "nginx"}]
                    }
                }
            }
        }
        self.security.heal_doc(doc, harden=True)
        sc = doc["spec"]["template"]["spec"]["containers"][0]["securityContext"]
        self.assertTrue(sc["runAsNonRoot"])
        self.assertTrue(sc["readOnlyRootFilesystem"])
        self.assertFalse(sc["allowPrivilegeEscalation"])
        self.assertEqual(sc["capabilities"]["drop"], ["ALL"])

    def test_intelligent_probes(self):
        # Test HTTP discovery
        doc_web = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "web-app",
                            "ports": [{"containerPort": 8080}]
                        }]
                    }
                }
            }
        }
        self.probes.heal_doc(doc_web, enforce_probes=True)
        c = doc_web["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("httpGet", c["livenessProbe"])
        self.assertEqual(c["livenessProbe"]["httpGet"]["port"], 8080)

        # Test TCP discovery
        doc_db = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "db",
                            "ports": [{"containerPort": 5432}]
                        }]
                    }
                }
            }
        }
        self.probes.heal_doc(doc_db, enforce_probes=True)
        c = doc_db["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("tcpSocket", c["livenessProbe"])
        self.assertEqual(c["livenessProbe"]["tcpSocket"]["port"], 5432)

    def test_image_tag_pinning(self):
        doc = {
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": "web-app", "image": "nginx:latest"}]
                    }
                }
            }
        }
        self.image_tag.heal_doc(doc, fix_latest=True)
        c = doc["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(c["image"], "nginx:stable")

if __name__ == "__main__":
    unittest.main()
