"""Tests for Kubernetes Admission Webhook handler."""
import base64
import json

import pytest

from yamlr.webhook.server import AdmissionHandler

SAMPLE_ADMISSION_REVIEW = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "705ab4f5-6393-11e8-b7cc-42010a800002",
        "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
        "resource": {"group": "apps", "version": "v1", "resource": "deployments"},
        "requestKind": {"group": "apps", "version": "v1", "kind": "Deployment"},
        "object": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "clean-deployment", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{"name": "web", "image": "nginx:1.24"}]
                    }
                }
            }
        }
    }
}

DEPRECATED_ADMISSION_REVIEW = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "805ab4f5-6393-11e8-b7cc-42010a800003",
        "kind": {"group": "extensions", "version": "v1beta1", "kind": "Deployment"},
        "resource": {"group": "extensions", "version": "v1beta1", "resource": "deployments"},
        "object": {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {"name": "old-deployment", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{"name": "web", "image": "nginx:latest"}]
                    }
                }
            }
        }
    }
}


def test_validate_clean_deployment():
    """Verify validation allows clean deployments without error."""
    res = AdmissionHandler.handle_admission_review(SAMPLE_ADMISSION_REVIEW, is_mutate=False)
    assert res["apiVersion"] == "admission.k8s.io/v1"
    assert res["response"]["uid"] == "705ab4f5-6393-11e8-b7cc-42010a800002"
    assert res["response"]["allowed"] is True


def test_validate_deprecated_deployment():
    """Verify validation reports advisories on deprecated manifests."""
    res = AdmissionHandler.handle_admission_review(DEPRECATED_ADMISSION_REVIEW, is_mutate=False)
    assert res["response"]["allowed"] is True
    assert "status" in res["response"]
    assert "remediations recommended" in res["response"]["status"]["message"]


def test_mutate_deployment_jsonpatch():
    """Verify mutating webhook returns JSONPatch annotation."""
    res = AdmissionHandler.handle_admission_review(SAMPLE_ADMISSION_REVIEW, is_mutate=True)
    assert res["response"]["allowed"] is True
    assert res["response"]["patchType"] == "JSONPatch"

    patch_b64 = res["response"]["patch"]
    patch_json = json.loads(base64.b64decode(patch_b64).decode("utf-8"))
    assert len(patch_json) == 1
    assert patch_json[0]["op"] == "add"
    assert "yamlr.dev~1admitted" in patch_json[0]["path"]


def test_webhook_healthz_readyz_probes():
    """Verify cluster health and readiness probes succeed with 200 OK."""
    from unittest.mock import MagicMock
    from yamlr.webhook.server import WebhookServer

    for probe_path in ["/healthz", "/readyz", "/health"]:
        server = WebhookServer.__new__(WebhookServer)
        server.path = probe_path
        server.send_response = MagicMock()
        server.send_header = MagicMock()
        server.end_headers = MagicMock()
        server.wfile = MagicMock()

        server.do_GET()

        server.send_response.assert_called_with(200)
        server.send_header.assert_any_call("Content-Type", "application/json")
        server.wfile.write.assert_called()
        written = server.wfile.write.call_args[0][0]
        assert b"healthy" in written

