# Yamlr ArgoCD ConfigManagementPlugin (CMP v2)

Deploy **Yamlr — The Autonomous Resolution Plane** as an in-cluster GitOps pre-sync normalizer inside ArgoCD.

---

## 🚀 Why Use Yamlr with ArgoCD?

- **Zero-Downtime Pre-Sync Normalization**: Automatically repairs deprecated Kubernetes API versions and port mismatches inside the `repo-server` before applying resources to clusters.
- **Comment-Preserving**: Ensures GitOps repositories never drop human annotations or docstrings.
- **Fail-Safe Admission**: Blocks toxic duplicate keys and collision hazards from triggering 2 AM cluster outages.

---

## 📦 Installation

Apply the CMP sidecar overlay to your ArgoCD deployment:

```bash
kubectl apply -k integrations/argocd/
```

Or configure `plugin.yaml` inside your ArgoCD `ConfigMap/argocd-cm`.
