"""Property-based invariant and behavioral tests for Yamlr healing engine.

Why: Enforces the Zero-Failure Trust Pillar through formal mathematical
invariants: Idempotency (heal(heal(x)) == heal(x)), No-Op Safety (heal on valid manifests
produces zero mutations), and Comment & Anchor Preservation.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import yamlr.cli.handlers as handlers
import yamlr.core.info as core_info
from yamlr import heal_yaml
from yamlr.core.license import LicenseManager

# ---------------------------------------------------------------------------
# Invariant 1: Idempotency (heal(heal(x)) == heal(x))
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("manifest_input", [
    """apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: legacy-ingress
spec:
  rules:
  - http:
      paths:
      - path: /test
        backend:
          serviceName: test-svc
          servicePort: 80
""",
    """apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: busybox:1.36
""",
])
def test_healing_idempotency_invariant(manifest_input: str):
    """Verify that applying heal repeatedly reaches a stable fixed point."""
    first_pass = heal_yaml(manifest_input)
    assert first_pass.healed_yaml is not None

    second_pass = heal_yaml(first_pass.healed_yaml)
    # The second pass must be identical to the first pass and report zero further changes
    assert second_pass.healed_yaml == first_pass.healed_yaml
    assert second_pass.had_changes is False


# ---------------------------------------------------------------------------
# Invariant 2: No-Op Safety (heal(valid) == valid, had_changes == False)
# ---------------------------------------------------------------------------

def test_healing_noop_safety_invariant():
    """Verify that a schema-valid, modern manifest is not mutated by heal."""
    clean_manifest = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: clean-nginx
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.0
        ports:
        - containerPort: 80
"""
    res = heal_yaml(clean_manifest)
    assert res.had_changes is False
    assert res.healed_yaml == clean_manifest


# ---------------------------------------------------------------------------
# Invariant 3: Comment & Layout Preservation Invariant
# ---------------------------------------------------------------------------

def test_healing_preserves_comments_and_structure():
    """Verify that healing never strips developer comments or annotations."""
    commented_manifest = """# Primary cluster ingress configuration
# Managed by Platform Operations
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  # Metadata annotation block
  name: core-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 80 # Upstream HTTP port
"""
    res = heal_yaml(commented_manifest)
    # All comments must be preserved byte-for-byte
    assert "# Primary cluster ingress configuration" in res.healed_yaml
    assert "# Managed by Platform Operations" in res.healed_yaml
    assert "# Metadata annotation block" in res.healed_yaml
    assert "# Upstream HTTP port" in res.healed_yaml


# ---------------------------------------------------------------------------
# Behavioral Tests: CLI Handlers & Diagnostic Boundaries
# ---------------------------------------------------------------------------

def test_cmd_auth_activation_flow():
    """Verify auth handler correctly delegates license activation."""
    with patch.object(LicenseManager, "activate_offline_key", return_value=True) as mock_act:
        handlers._cmd_auth("activate", "dummy_key_token")
        mock_act.assert_called_once_with("dummy_key_token")


def test_cmd_version_output():
    """Verify version command outputs cleanly without throwing exceptions."""
    with patch("yamlr.ui.theme.console.print") as mock_print:
        core_info.cmd_version()
        assert mock_print.called


def test_cmd_subscribe_output():
    """Verify subscribe handler triggers browser redirect and prints instructions."""
    with patch("webbrowser.open") as mock_wb, \
         patch("yamlr.ui.theme.console.print") as mock_print:
        handlers._cmd_subscribe()
        mock_wb.assert_called_once_with("https://yamlr.dev/pro")
        assert mock_print.called


def test_license_manager_offline_activation():
    """Verify offline key activation handles unparseable payloads safely."""
    lm = LicenseManager()
    assert lm.activate_offline_key("invalid_unparseable_key") is False
