"""Phase 13: Enterprise Policy, Admission & Attestation Verification Suite.

Why: Verifies that Kubernetes 1.26+ ValidatingAdmissionPolicy manifests,
     OCI Cosign container image signature audits, and ArgoCD CMP plugin specifications
     operate deterministically across all environments.
"""

from pathlib import Path
import yaml
import yamlr_native


def test_native_export_vap_generates_valid_k8s_manifests():
    """Verify that export-vap produces valid ValidatingAdmissionPolicy and binding manifests."""
    bundle_str = yamlr_native.native_export_vap("corp-security-policy")
    docs = list(yaml.safe_load_all(bundle_str))

    assert len(docs) == 2, "Expected 2 manifests in VAP export (Policy and Binding)"

    vap, binding = docs[0], docs[1]

    # Check ValidatingAdmissionPolicy
    assert vap["apiVersion"] == "admissionregistration.k8s.io/v1"
    assert vap["kind"] == "ValidatingAdmissionPolicy"
    assert vap["metadata"]["name"] == "corp-security-policy"
    assert vap["spec"]["failurePolicy"] == "Fail"

    # Verify CEL validation expressions
    validations = vap["spec"]["validations"]
    expressions = [v["expression"] for v in validations]
    messages = [v["message"] for v in validations]

    assert any("!c.image.endsWith(':latest')" in expr for expr in expressions)
    assert any("c.imagePullPolicy == 'Always'" in expr for expr in expressions)
    assert any("c.securityContext.runAsNonRoot == true" in expr for expr in expressions)
    assert any("c.securityContext.readOnlyRootFilesystem == true" in expr for expr in expressions)
    assert any("has(c.resources.limits)" in expr for expr in expressions)
    assert any("[OPS-002]" in msg for msg in messages)

    # Check ValidatingAdmissionPolicyBinding
    assert binding["apiVersion"] == "admissionregistration.k8s.io/v1"
    assert binding["kind"] == "ValidatingAdmissionPolicyBinding"
    assert binding["metadata"]["name"] == "corp-security-policy-binding"
    assert binding["spec"]["policyName"] == "corp-security-policy"
    assert "Deny" in binding["spec"]["validationActions"]


def test_native_audit_image_signature_verification():
    """Verify OCI Cosign image signature verification and digest parsing."""
    # 1. Signed image with valid sha256 digest
    signed_ref = "registry.k8s.io/kube-apiserver@sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    is_signed, digest, sig_tag, violation = yamlr_native.native_audit_image_signature(signed_ref, True)

    assert is_signed is True
    assert digest == "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    assert sig_tag == "sha256-1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.sig"
    assert violation is None

    # 2. Unsigned floating image with signature enforcement
    unsigned_ref = "my-registry.io/app/backend:latest"
    is_signed, digest, sig_tag, violation = yamlr_native.native_audit_image_signature(unsigned_ref, True)

    assert is_signed is False
    assert digest is None
    assert sig_tag is None
    assert violation is not None
    assert "SEC-018" in violation

    # 3. Unsigned image without enforcement
    is_signed, digest, sig_tag, violation = yamlr_native.native_audit_image_signature(unsigned_ref, False)
    assert is_signed is False
    assert violation is None


def test_argocd_cmp_plugin_v2_spec():
    """Verify that integrations/argocd/plugin.yaml conforms to CMP v2 specification."""
    plugin_path = Path("integrations/argocd/plugin.yaml")
    assert plugin_path.exists(), "plugin.yaml must exist"

    content = yaml.safe_load(plugin_path.read_text(encoding="utf-8"))
    assert content["apiVersion"] == "argoproj.io/v1alpha1"
    assert content["kind"] == "ConfigManagementPlugin"
    assert content["metadata"]["name"] == "yamlr-healer"
    assert content["spec"]["version"] == "v2.0"
    assert "yamlr heal -" in content["spec"]["generate"]["args"][0]
    assert content["spec"]["discover"]["find"]["glob"] == "**/*.{yaml,yml}"
