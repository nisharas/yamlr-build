#!/usr/bin/env python3
"""
Yamlr Forensic Sovereign Verification - SHD-001 to SHD-015
---------------------------------------------------------
This script performs a 100% functional audit of the Shield Engine,
verifying that every forensic risk category is correctly detected.
"""

import logging
import sys

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger("yamlr.verify")
import os

# [HARDENING] Disable native acceleration to ensure Python edge builders are tested
os.environ["YAMLR_DISABLE_NATIVE"] = "1"

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from typing import List

import yaml

from yamlr.core.graph_models import EdgeType, GraphEdge, GraphNode
from yamlr.core.resource_graph import ResourceGraph
from yamlr.models import ManifestIdentity
from yamlr.pro.shield import ShieldEngine


def build_graph_from_yaml(yaml_blocks: List[str]) -> ResourceGraph:
    """
    Builds a real ResourceGraph from YAML strings.
    Why: Eliminates 'Mock Dependency' silent killer by using real manifest parsing.
    """
    graph = ResourceGraph()
    identities = []

    def extract_deep(obj, ident: ManifestIdentity):
        if not isinstance(obj, (dict, list)):
            return

        if isinstance(obj, list):
            for item in obj:
                extract_deep(item, ident)
            return

        # 1. Config/Secret/Volume Refs
        if "configMapRef" in obj:
            ident.config_refs.append(str(obj["configMapRef"].get("name")))
        if "configMapKeyRef" in obj:
            ident.config_refs.append(str(obj["configMapKeyRef"].get("name")))
        if "configMap" in obj and isinstance(obj["configMap"], dict):
            ident.config_refs.append(str(obj["configMap"].get("name")))

        if "secretRef" in obj:
            ident.secret_refs.append(str(obj["secretRef"].get("name")))
        if "secretKeyRef" in obj:
            ident.secret_refs.append(str(obj["secretKeyRef"].get("name")))
        if "secretName" in obj:
            ident.secret_refs.append(str(obj["secretName"]))
        if "secret" in obj and isinstance(obj["secret"], dict):
            ident.secret_refs.append(str(obj["secret"].get("secretName")))

        if "persistentVolumeClaim" in obj:
            ident.volume_refs.append(str(obj["persistentVolumeClaim"].get("claimName")))

        # 2. Ports and Backends
        if "containerPort" in obj:
            ident.container_ports.append(str(obj["containerPort"]))
        if "port" in obj and "targetPort" in obj:  # Service Port
            ident.service_ports.append({"port": str(obj["port"]), "targetPort": str(obj["targetPort"])})

        if "serviceName" in obj:  # Legacy Ingress
            ident.ingress_backends.append({"service": str(obj["serviceName"])})
        if "service" in obj and isinstance(obj["service"], dict) and "name" in obj["service"]:
            ident.ingress_backends.append({"service": str(obj["service"]["name"])})

        # 3. Controllers and RBAC
        if "scaleTargetRef" in obj:
            ident.scale_target = str(obj["scaleTargetRef"].get("name"))

        if "roleRef" in obj:
            ref = obj["roleRef"]
            if ref.get("kind") == "ClusterRole":
                ident.cluster_role_refs.append(str(ref.get("name")))
            else:
                ident.role_refs.append(str(ref.get("name")))

        for k, v in obj.items():
            extract_deep(v, ident)

    for block in yaml_blocks:
        try:
            docs = list(yaml.safe_load_all(block))
        except Exception:
            continue

        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue

            meta = doc.get("metadata", {})
            spec = doc.get("spec", {}) or {}

            ident = ManifestIdentity(
                kind=doc.get("kind"),
                api_version=doc.get("apiVersion"),
                name=meta.get("name"),
                namespace=meta.get("namespace") or "default",
                labels=meta.get("labels", {}),
                annotations=meta.get("annotations", {}),
            )

            # Index labels as strings for consistency
            ident.labels = {str(k): str(v) for k, v in ident.labels.items()}

            # Extract basic relationship markers
            # For workloads, selector is in spec; for NetPol/PDB it is also in spec
            if "selector" in spec:
                sel = spec["selector"]
                if isinstance(sel, dict) and "matchLabels" in sel:
                    ident.selector = {str(k): str(v) for k, v in sel["matchLabels"].items()}
                elif isinstance(sel, dict):
                    ident.selector = {str(k): str(v) for k, v in sel.items()}

            if doc.get("kind") == "CustomResourceDefinition":
                ident.crd_group = spec.get("group")
                if "versions" in spec:
                    ident.crd_versions = [v.get("name") for v in spec["versions"]]

            if "ownerReferences" in meta:
                for ref in meta["ownerReferences"]:
                    ident.owner_refs.append(
                        {"kind": ref.get("kind"), "name": ref.get("name"), "namespace": ident.namespace}
                    )

            extract_deep(doc, ident)
            identities.append(ident)

    graph.build(identities)
    return graph


def test_shield_engine_100_percent_coverage():
    print("Starting 100% Shield Engine Forensic Audit (Hardened)...")
    shield = ShieldEngine()
    results = {}
    manifest_map = {}  # key -> original doc for detect_shadow_risks

    # --- Setup Global Topology Risks ---
    yaml_topology = [
        # [SHD-006] Circular Dependency
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-a
  namespace: default
  ownerReferences:
  - kind: Deployment
    name: app-b
spec:
  template:
    spec:
      containers: [{name: c}]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-b
  namespace: default
  ownerReferences:
  - kind: Deployment
    name: app-a
spec:
  template:
    spec:
      containers: [{name: c}]
        """,
        # [SHD-009] High Impact Density (ConfigMap used by many)
        """
apiVersion: v1
kind: ConfigMap
metadata:
  name: global-config
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: isolated-app
  namespace: secure-ns
  labels: {app: isolated}
spec:
  replicas: 3
  template:
    metadata: {labels: {app: isolated}}
    spec:
      containers:
      - name: main
        image: nginx
        ports: [{containerPort: 8080}]
        """,
    ]
    # Add 15 pods using the configmap to trigger >15% density
    for i in range(15):
        yaml_topology.append(f"""
apiVersion: v1
kind: Pod
metadata:
  name: dep-{i}
spec:
  containers:
  - name: c
    image: nginx
    envFrom:
    - configMapRef:
        name: global-config
        """)

    # [SHD-007, SHD-012, SHD-014] Traffic-facing Workload with isolation gaps
    yaml_topology.append("""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-gateway
  namespace: secure-ns
  annotations:
    yamlr.io/host: "api.yamlr.pro"
spec:
  rules:
  - host: api.yamlr.pro
    http:
      paths:
      - path: /
        backend:
          service:
            name: app-svc
            port: {number: 80}
---
apiVersion: v1
kind: Service
metadata:
  name: app-svc
  namespace: secure-ns
spec:
  selector: {app: isolated}
  ports: [{port: 80, targetPort: 8080}]
---
apiVersion: v1
kind: Secret
metadata:
  name: lonely-secret
  namespace: prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: god-mode
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
subjects: [{kind: ServiceAccount, name: default}]
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: survisions.yamlr.pro
spec:
  group: yamlr.pro
  versions:
  - name: v1
    served: true
  - name: v1beta1
    served: true
    """)

    graph = build_graph_from_yaml(yaml_topology)
    # Populate manifest_map for detect_shadow_risks
    for block in yaml_topology:
        docs = list(yaml.safe_load_all(block))
        for doc in docs:
            if not doc:
                continue
            k = doc.get("kind")
            n = doc.get("metadata", {}).get("name")
            ns = doc.get("metadata", {}).get("namespace", "default")
            manifest_map[f"{k}/{ns}/{n}"] = doc

    shield.audit_global(graph)

    # Individual Scans
    print(f"Auditing {graph.node_count} nodes...")

    def check_global(key, rule_id):
        findings = shield._global_findings.get(key, [])
        return any(f.rule_id == rule_id for f in findings)

    # 1. Global Checks
    results["SHD-006"] = check_global("Deployment/default/app-a", "SHD-006")
    results["SHD-009"] = check_global("ConfigMap/default/global-config", "SHD-009")
    results["SHD-007"] = check_global("Deployment/secure-ns/isolated-app", "SHD-007")
    results["SHD-008"] = check_global("Secret/prod/lonely-secret", "SHD-008")
    results["SHD-010"] = check_global("ClusterRoleBinding/default/god-mode", "SHD-010")

    # 2. Manifest-level Checks
    # [SHD-001, 002, 004] Base Hardening
    unsafe_pod = {
        "kind": "Pod",
        "metadata": {"name": "p1", "namespace": "secure-ns"},
        "spec": {
            "hostNetwork": True,
            "containers": [{"name": "unsafe-container", "image": "nginx", "securityContext": {"privileged": True}}],
            "volumes": [{"name": "root-vol", "hostPath": {"path": "/root"}}],
        },
    }
    unsafe_f = shield.detect_shadow_risks(unsafe_pod, graph)
    results["SHD-001"] = any(f.rule_id == "SHD-001" for f in unsafe_f)
    results["SHD-002"] = any(f.rule_id == "SHD-002" for f in unsafe_f)
    results["SHD-004"] = any(f.rule_id == "SHD-004" for f in unsafe_f)

    # [SHD-003] Sensitive Volume Exposure
    leak_pod = {
        "kind": "Pod",
        "metadata": {"name": "p2"},
        "spec": {
            "volumes": [{"name": "v1", "hostPath": {"path": "/tmp"}}, {"name": "v2", "secret": {"secretName": "s1"}}]
        },
    }
    results["SHD-003"] = any(f.rule_id == "SHD-003" for f in shield.detect_shadow_risks(leak_pod, graph))

    # [SHD-005] Resource Starvation (High impact node lacks limits)
    # isolated-app has replicas=3 and is connected to Ingress.
    # Its pod spec lacks limits. This should trigger SHD-005.
    hi_pod_key = "Deployment/secure-ns/isolated-app"
    hi_doc = manifest_map[hi_pod_key]
    hi_findings = shield.detect_shadow_risks(hi_doc, graph)
    results["SHD-005"] = any(f.rule_id == "SHD-005" for f in hi_findings)

    # [SHD-011] Zombie API
    zombie_deploy = {"apiVersion": "extensions/v1beta1", "kind": "Deployment", "metadata": {"name": "z1"}}
    results["SHD-011"] = any(f.rule_id == "SHD-011" for f in shield.detect_shadow_risks(zombie_deploy, graph))

    # [SHD-012] Disruption Blind-spot (High impact node lacks PDB)
    results["SHD-012"] = any(f.rule_id == "SHD-012" for f in hi_findings)

    # [SHD-013] Route Collision Hijack
    yaml_topology.append("""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: evil-gateway
  namespace: default
  annotations:
    yamlr.io/host: "api.yamlr.pro"
    """)
    graph = build_graph_from_yaml(yaml_topology)
    shield._global_audited = False  # Re-audit
    shield.audit_global(graph)
    results["SHD-013"] = check_global("Ingress/default/evil-gateway", "SHD-013")

    # [SHD-014] HPA Conflict
    yaml_topology.append("""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-scaler
  namespace: secure-ns
spec:
  scaleTargetRef:
    kind: Deployment
    name: isolated-app
    """)
    graph = build_graph_from_yaml(yaml_topology)
    rep_deploy = {
        "kind": "Deployment",
        "metadata": {"name": "isolated-app", "namespace": "secure-ns"},
        "spec": {"replicas": 3},
    }
    results["SHD-014"] = any(f.rule_id == "SHD-014" for f in shield.detect_shadow_risks(rep_deploy, graph))

    # [SHD-015] CRD Version Drift
    cr_doc = {"apiVersion": "yamlr.pro/v2", "kind": "Survision", "metadata": {"name": "test-cr"}}
    results["SHD-015"] = any(f.rule_id == "SHD-015" for f in shield.detect_shadow_risks(cr_doc, graph))

    # [SHD-016] Template-Deep Injection
    deep_deploy = {
        "kind": "Deployment",
        "metadata": {"name": "complex-app"},
        "spec": {"template": {"spec": {"containers": [{"name": "worker", "securityContext": {"privileged": True}}]}}},
    }
    results["SHD-016"] = any(f.rule_id == "SHD-002" for f in shield.detect_shadow_risks(deep_deploy, graph))

    # --- Summary ---
    print("\nAudit Summary (16/16 Categories):")
    all_passed = True
    for cat in sorted(results.keys()):
        status = "PASS" if results[cat] else "FAIL"
        if not results[cat]:
            all_passed = False
        print(f"  [{cat}]: {status}")

    if all_passed:
        print("\nShield Engine: 100% Certified. All forensic categories functional.")
    else:
        print("\nShield Engine: Audit FAILED. Some categories not detected.")
        sys.exit(1)


if __name__ == "__main__":
    test_shield_engine_100_percent_coverage()
