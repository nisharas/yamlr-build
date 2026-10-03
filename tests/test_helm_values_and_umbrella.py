"""Comprehensive test suite for Helm values healing, template guardrails, and umbrella subcharts.

Why: Guarantees that values.yaml files across root umbrella charts and nested
subcharts are auto-healed safely with 100% comment and formatting preservation,
while protecting dynamic template blocks (toYaml, include) from corruption.
"""
import os
import tempfile
import yaml
import pytest
from yamlr import heal_yaml, heal_values_yaml, HealResult

# 1. OPS-002: Floating Image Tags in values.yaml
def test_heal_values_floating_tags():
    raw = """# Production Web Service Values
image:
  repository: nginx
  tag: latest # Mutable floating tag
  pullPolicy: IfNotPresent
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("OPS-002" in c for c in res.changes)
    assert any("SEC-002" in c for c in res.changes)
    assert "tag: stable-pinned" in res.healed_yaml
    assert "pullPolicy: Always" in res.healed_yaml
    assert "# Production Web Service Values" in res.healed_yaml
    assert "# Mutable floating tag" in res.healed_yaml

    # Verify idempotency
    pass2 = heal_values_yaml(res.healed_yaml)
    assert pass2.had_changes is False
    assert pass2.healed_yaml == res.healed_yaml

# 2. Combined image string pinning: repo:latest
def test_heal_values_combined_image_latest():
    raw = """service:
  image: "myregistry.io/app/frontend:latest"
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert "myregistry.io/app/frontend:stable-pinned" in res.healed_yaml

# 3. SEC-001 & SEC-004: Security Context in values.yaml
def test_heal_values_security_context():
    raw = """securityContext:
  privileged: true
  runAsUser: 0
  runAsNonRoot: false
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("SEC-001" in c for c in res.changes)
    assert any("SEC-004" in c for c in res.changes)
    assert "privileged: false" in res.healed_yaml
    assert "runAsUser: 10001" in res.healed_yaml
    assert "runAsNonRoot: true" in res.healed_yaml

# 4. HPA-001: Inverted Autoscaling Replicas
def test_heal_values_inverted_autoscaling():
    raw = """autoscaling:
  enabled: true
  minReplicas: 10
  maxReplicas: 3
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("HPA-001" in c for c in res.changes)
    assert "minReplicas: 3" in res.healed_yaml
    assert "maxReplicas: 3" in res.healed_yaml

# 5. RES-001: Inverted Resource Requests & Limits
def test_heal_values_inverted_resources():
    raw = """resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 1000m
    memory: 256Mi
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("RES-001" in c for c in res.changes)
    assert "cpu: 500m" in res.healed_yaml

# 6. REL-005: PDB Deadlock Parameters in values.yaml
def test_heal_values_pdb_deadlocks():
    raw = """pdb:
  enabled: true
  minAvailable: 100%
  maxUnavailable: 0
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("REL-005" in c for c in res.changes)
    assert "minAvailable: 50%" in res.healed_yaml
    assert "maxUnavailable: 1" in res.healed_yaml

# 7. PROBE-001: Invalid Probe Timeouts in values.yaml
def test_heal_values_probe_timeouts():
    raw = """livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  timeoutSeconds: 30
  periodSeconds: 10
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("PROBE-001" in c for c in res.changes)
    assert "timeoutSeconds: 10" in res.healed_yaml
    assert "periodSeconds: 10" in res.healed_yaml

# 8. ING-001: Deprecated Ingress Class Annotation in values.yaml
def test_heal_values_deprecated_ingress():
    raw = """ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("ING-001" in c for c in res.changes)
    assert "ingressClassName: nginx" in res.healed_yaml

# 9. SEC-003: Plaintext Secret Annotation in values.yaml
def test_heal_values_plaintext_credentials():
    raw = """database:
  user: admin
  password: "supersecretpassword123!"
"""
    res = heal_values_yaml(raw)
    assert res.had_changes is True
    assert any("SEC-003" in c for c in res.changes)
    assert "# yamlr [SEC-003]:" in res.healed_yaml
    assert "supersecretpassword123!" in res.healed_yaml

# 10. Template Guardrail: toYaml Blocks are Protected from Corruption
def test_helm_template_guardrail_toyaml():
    raw_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamic-app
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: web
          image: nginx:1.25.0
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""
    res = heal_yaml(raw_template)
    # The toYaml block must remain pristine and uncorrupted
    assert "{{- toYaml .Values.resources | nindent 12 }}" in res.healed_yaml
    # No duplicate or conflicting flat limits/requests injected under resources
    assert "limits:" not in res.healed_yaml
    assert "requests:" not in res.healed_yaml

# 11. Multi-tier Umbrella Subcharts Hierarchy Healing
def test_umbrella_subcharts_hierarchy_healing():
    with tempfile.TemporaryDirectory() as tmpdir:
        umbrella_dir = os.path.join(tmpdir, "umbrella-chart")
        charts_dir = os.path.join(umbrella_dir, "charts")
        subchart_a = os.path.join(charts_dir, "service-a")
        subchart_b = os.path.join(charts_dir, "service-b")

        os.makedirs(subchart_a)
        os.makedirs(subchart_b)

        # Root values.yaml with floating tags and PDB deadlock
        root_values = """# Root Umbrella Values
global:
  environment: prod

service-a:
  tag: latest

pdb:
  minAvailable: 100%
"""
        # Subchart values.yaml with inverted replicas and root UID
        sub_values = """# Service B Subchart Values
autoscaling:
  minReplicas: 8
  maxReplicas: 2
securityContext:
  runAsUser: 0
"""
        with open(os.path.join(umbrella_dir, "values.yaml"), "w", encoding="utf-8") as f:
            f.write(root_values)
        with open(os.path.join(subchart_b, "values.yaml"), "w", encoding="utf-8") as f:
            f.write(sub_values)

        # Heal root values
        root_res = heal_values_yaml(root_values)
        assert root_res.had_changes is True
        assert "tag: stable-pinned" in root_res.healed_yaml
        assert "minAvailable: 50%" in root_res.healed_yaml
        assert "# Root Umbrella Values" in root_res.healed_yaml

        # Heal subchart values
        sub_res = heal_values_yaml(sub_values)
        assert sub_res.had_changes is True
        assert "minReplicas: 2" in sub_res.healed_yaml
        assert "runAsUser: 10001" in sub_res.healed_yaml
        assert "# Service B Subchart Values" in sub_res.healed_yaml
