"""Tests for CRDDistiller schema compilation and caching."""
import os
import tempfile

import pytest

from yamlr.core.crd_distiller import CRDDistiller

SAMPLE_CRD = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: certificates.cert-manager.io
spec:
  group: cert-manager.io
  names:
    kind: Certificate
    listKind: CertificateList
    plural: certificates
    singular: certificate
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - secretName
              properties:
                secretName:
                  type: string
                  description: Target secret name
                dnsNames:
                  type: array
                  description: Subject Alternative Names
"""


def test_distill_single_crd():
    """Verify single CRD extraction and schema JSON generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "certificate.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CRD)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "Certificate"
        assert schema["apiVersion"] == "cert-manager.io/v1"
        assert "spec" in schema["fields"]

        # Verify disk cache
        cached = distiller.list_schemas()
        assert len(cached) == 1
        assert cached[0]["kind"] == "Certificate"


def test_clean_schemas():
    """Verify schema cleaning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "certificate.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CRD)

        distiller = CRDDistiller(schema_dir)
        distiller.distill_file(crd_file)
        assert len(distiller.list_schemas()) == 1

        cleaned = distiller.clean_schemas()
        assert cleaned == 1
        assert len(distiller.list_schemas()) == 0


def test_distill_v1beta1_crd():
    """Verify v1beta1 CRD extraction with global validation schema."""
    v1beta1_crd = """apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: alerts.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: Alertmanager
    plural: alertmanagers
  scope: Namespaced
  version: v1alpha1
  validation:
    openAPIV3Schema:
      type: object
      properties:
        spec:
          type: object
          properties:
            replicas:
              type: integer
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "alertmanager.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(v1beta1_crd)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "Alertmanager"
        assert schema["apiVersion"] == "monitoring.coreos.com/v1alpha1"
        assert "spec" in schema["fields"]


def test_distill_crd_structural_fallback():
    """Verify structural fallback inference when no schema is present."""
    untyped_crd = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: legacyapps.example.com
spec:
  group: example.com
  names:
    kind: LegacyApp
    plural: legacyapps
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "legacyapp.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(untyped_crd)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "LegacyApp"
        assert "spec" in schema["fields"]
        assert "metadata" in schema["fields"]
        assert "apiVersion" in schema["fields"]

