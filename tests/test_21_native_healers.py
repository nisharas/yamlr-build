"""Comprehensive integration test suite verifying all native healers via heal_yaml().

Why: Enforces that the high-level Python API (heal_yaml) actively triggers the
complete 21-healer native Rust pipeline with strict comment preservation and idempotency.
"""
import pytest
import yaml
from yamlr import heal_yaml, HealResult, generate_default_deny_network_policy, generate_stub

# 1. PDB Deadlock Preventer (Feature 16)
def test_pdb_deadlock_healer_100_percent():
    raw = """apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 100%
  selector:
    matchLabels:
      app: web
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("REL-005" in c for c in res.changes)
    assert "minAvailable: 50%" in res.healed_yaml
    
    # Verify idempotency
    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False
    assert pass2.healed_yaml == res.healed_yaml

# 2. Sidecar Modernizer (Feature 17)
def test_sidecar_modernizer_healer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: sidecar-workload
spec:
  template:
    spec:
      initContainers:
      - name: vault-agent
        image: vault:1.15
        command: ["vault", "agent"]
      containers:
      - name: app
        image: nginx:1.25.0
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("ARC-003" in c for c in res.changes)
    assert "restartPolicy: Always" in res.healed_yaml
    
    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 3. Security Context & ReadOnlyRootFS (Feature 18)
def test_security_context_tmp_mount_healer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx:1.25.0
        securityContext:
          readOnlyRootFilesystem: true
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SEC-004" in c for c in res.changes)
    assert "mountPath: /tmp" in res.healed_yaml
    assert "emptyDir:" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 4. Lifecycle PreStop & Grace Period Synchronizer (Feature 20)
def test_lifecycle_grace_period_synchronizer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: graceful-app
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: web
        image: nginx:1.25.0
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 45"]
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("OPS-004" in c for c in res.changes)
    assert "terminationGracePeriodSeconds: 60" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 5. Schema Typo Healer (Feature 1)
def test_schema_typo_healer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: typo-app
spec:
  replica: 3
  template:
    spec:
      continers:
      - name: web
        image: nginx:1.25.0
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SCHEMA-002" in c for c in res.changes)
    assert "replicas: 3" in res.healed_yaml
    assert "containers:" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 6. Enum Typo & Casing Healer (Feature 2)
def test_enum_healer_casing():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: enum-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        imagePullPolicy: alway
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SCHEMA-003" in c for c in res.changes)
    assert "imagePullPolicy: Always" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 7. Structural Healer (Feature 3)
def test_structural_healer_lift_ports():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: struct-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        envFrom:
          ports:
          - containerPort: 80
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("STRUCT-001" in c for c in res.changes)
    parsed = yaml.safe_load(res.healed_yaml)
    container = parsed["spec"]["template"]["spec"]["containers"][0]
    assert "ports" in container
    assert container["ports"][0]["containerPort"] == 80

# 8. API Infer Healer (Feature 9)
def test_api_infer_healer():
    raw = """kind: Deployment
metadata:
  name: inferred-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SCHEMA-004" in c for c in res.changes)
    assert "apiVersion: apps/v1" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 9. Resource Sanitizer (Feature 12)
def test_resource_sanitizer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: res-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        resources:
          cpu: 1000m
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("RES-001" in c for c in res.changes)
    assert "limits:" in res.healed_yaml
    assert "requests:" in res.healed_yaml

    pass2 = heal_yaml(res.healed_yaml)
    assert pass2.had_changes is False

# 10. Service Selector Alignment (Feature 4)
def test_service_selector_alignment():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  template:
    metadata:
      labels:
        app: web-service
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web-servc
  ports:
  - port: 80
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("REL-011" in c for c in res.changes)
    assert "app: web-service" in res.healed_yaml

# 11. Service Port Alignment (Feature 5)
def test_service_port_alignment():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        ports:
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  ports:
  - port: 80
    targetPort: 80
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("NET-004" in c for c in res.changes)
    assert "targetPort: 8080" in res.healed_yaml

# 12. RBAC RoleRef Alignment (Feature 6)
def test_rbac_roleref_alignment():
    raw = """apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: secret-readr
subjects:
- kind: ServiceAccount
  name: default
  namespace: default
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SEC-004" in c for c in res.changes)
    assert "name: secret-reader" in res.healed_yaml

# 13. Referential ConfigMap Typo Alignment (Feature 7)
def test_referential_configmap_alignment():
    raw = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  ENV: prod
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        envFrom:
        - configMapRef:
            name: app-confg
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("REF-001" in c for c in res.changes)
    assert "name: app-config" in res.healed_yaml

# 14. Helm & Go Template Masking (Feature 13)
def test_helm_template_masking():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: "{{ .Values.appName }}"
spec:
  replica: 3
  template:
    spec:
      containers:
      - name: web
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("SCHEMA-002" in c for c in res.changes)
    assert "replicas: 3" in res.healed_yaml
    assert "{{ .Values.appName }}" in res.healed_yaml
    assert "{{ .Values.image.repository }}:{{ .Values.image.tag }}" in res.healed_yaml

# 15. CRD CertManager ClusterIssuer Healing (Feature 14)
def test_crd_cert_manager_cluster_issuer():
    raw = """apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: site-cert
spec:
  secretName: site-tls
  issuerRef:
    name: letsencrypt-prod
    kind: Issuer
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("CRD-001" in c for c in res.changes)
    assert "kind: ClusterIssuer" in res.healed_yaml

# 16. Probes Best Practice Auto-Healer (Feature 11)
def test_probes_synthesizer():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: probed-app
  annotations:
    yamlr.io/probes: "true"
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
        ports:
        - containerPort: 8080
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("REL-008" in c for c in res.changes)
    assert "livenessProbe:" in res.healed_yaml
    assert "readinessProbe:" in res.healed_yaml
    assert "port: 8080" in res.healed_yaml

# 17. Gateway API Modernizer (Feature 21)
def test_gateway_api_modernizer():
    raw = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    yamlr.io/gateway-api: "true"
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 8080
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("MIG-002" in c for c in res.changes)
    assert "kind: HTTPRoute" in res.healed_yaml
    assert "example.com" in res.healed_yaml

# 18. API Deprecation Upgrade (PRO-001)
def test_api_deprecation_upgrade():
    raw = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: legacy-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("PRO-001" in c for c in res.changes)
    assert "apiVersion: apps/v1" in res.healed_yaml

# 19. Floating Tag Pinning (OPS-002)
def test_floating_tag_pinned():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: tagged-app
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert any("OPS-002" in c for c in res.changes)
    assert "nginx:stable-pinned" in res.healed_yaml

# 20. DNA Safety Seal Injection
def test_dna_safety_seal():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: sealed-app
spec:
  replica: 2
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.25.0
"""
    res = heal_yaml(raw)
    assert res.had_changes is True
    assert "yamlr.dev/dna-seal: sha256:" in res.healed_yaml

# 21. Default Deny NetworkPolicy Generator (Feature 19)
def test_default_deny_network_policy_generation():
    netpol = generate_default_deny_network_policy("prod-cluster")
    assert "kind: NetworkPolicy" in netpol
    assert "default-deny-all" in netpol
    assert "namespace: prod-cluster" in netpol
    assert "podSelector: {}" in netpol
    assert "- Ingress" in netpol
    assert "- Egress" in netpol
    parsed = yaml.safe_load(netpol)
    assert parsed["metadata"]["namespace"] == "prod-cluster"
    assert parsed["spec"]["policyTypes"] == ["Ingress", "Egress"]

# 22. Missing Target Resource Stub Generator (Feature 8)
def test_missing_target_stub_generation():
    # Test Service stub
    svc_stub = generate_stub("Service", "payment-service", "payments")
    assert "kind: Service" in svc_stub
    assert "name: payment-service" in svc_stub
    assert "namespace: payments" in svc_stub
    parsed_svc = yaml.safe_load(svc_stub)
    assert parsed_svc["metadata"]["name"] == "payment-service"

    # Test ConfigMap stub
    cm_stub = generate_stub("ConfigMap", "app-env", "default")
    assert "kind: ConfigMap" in cm_stub
    assert "name: app-env" in cm_stub
    parsed_cm = yaml.safe_load(cm_stub)
    assert parsed_cm["metadata"]["name"] == "app-env"

    # Test Secret stub
    secret_stub = generate_stub("Secret", "db-creds", "default")
    assert "kind: Secret" in secret_stub
    assert "name: db-creds" in secret_stub
    parsed_secret = yaml.safe_load(secret_stub)
    assert parsed_secret["metadata"]["name"] == "db-creds"

