#!/usr/bin/env python3
import pytest

from yamlr.analyzers.rules import Rules
from yamlr.core.context import HealContext
from yamlr.healers.best_practices.ingress import IngressAuditor


@pytest.fixture
def auditor():
    return IngressAuditor()


@pytest.fixture
def context():
    return HealContext(raw_text="", docs=[], file_path="test-ingress.yaml")


def test_ingress_missing_tls(auditor):
    doc = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": "unsafe-ingress"},
        "spec": {
            "rules": [
                {
                    "host": "myapp.com",
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {"service": {"name": "svc", "port": {"number": 80}}},
                            }
                        ]
                    },
                }
            ]
        },
    }
    findings = auditor.scan_doc(doc)
    assert any(f.rule_id == Rules.INGRESS_TLS_MISSING for f in findings)


def test_ingress_missing_class(auditor):
    doc = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": "no-class-ingress"},
        "spec": {"rules": []},
    }
    findings = auditor.scan_doc(doc)
    assert any(f.rule_id == Rules.INGRESS_CLASS_MISSING for f in findings)


def test_ingress_unsafe_annotation(auditor):
    doc = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": "risky-ingress",
            "annotations": {"nginx.ingress.kubernetes.io/configuration-snippet": "more config here"},
        },
        "spec": {"rules": []},
    }
    findings = auditor.scan_doc(doc)
    assert any(f.rule_id == Rules.INGRESS_UNSAFE_ANNOTATION for f in findings)


def test_ingress_remediation(auditor, context):
    doc = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": "fix-me"},
        "spec": {"rules": [{"host": "test.local"}]},
    }
    modified = auditor.heal_doc(doc, context=context, harden=True)
    assert modified is True
    assert doc["spec"]["ingressClassName"] == "nginx"
    assert "tls" in doc["spec"]
    assert doc["spec"]["tls"][0]["hosts"] == ["test.local"]


def test_ingress_wildcard_host(auditor):
    doc = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": "wildcard-ingress"},
        "spec": {"rules": [{"http": {"paths": []}}]},
    }
    findings = auditor.scan_doc(doc)
    assert any(f.rule_id == Rules.INGRESS_WILDCARD_HOST for f in findings)
