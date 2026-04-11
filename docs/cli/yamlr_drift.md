# yamlr drift
**Live-Manifest Reconciliation Engine (PRO)**

The `yamlr drift` command audits your live Kubernetes cluster against your local YAML manifests to detect undocumented changes and out-of-band configurations.

## Usage

```bash
# Basic Drift Detection (All Namespaces)
yamlr drift .

# Filter by Specific Namespace
yamlr drift . --namespace production

# Target a specific Kubeconfig context
yamlr drift . --context eks-cluster-1
```

## How it works

Yamlr analyzes the "Live Truth" from your cluster and compares it with the "Proposed Truth" in your local directory using its **Semantic DNA** engine. It ignores non-vital mutations (like status timestamps or system annotations) and focuses on structural drift (image tags, replicas, resource limits).

## Enterprise Features

### 1. Context Isolation (`--context`)
Explicitly target a cluster defined in your `~/.kube/config`. This is essential for preventing "Drift Leakage" when managing multiple environments.

### 2. Namespace Scoping (`--namespace`)
Limit the audit to a specific namespace to reduce noise and analysis latency in multi-tenant clusters.

### 3. Reporting Tiers
*   **Missing**: Local manifests that are not found in the cluster.
*   **Shadow**: Live resources that have no local manifest counterpart.
*   **Mutated**: Structural differences between local and live state.

---

> [!IMPORTANT]
> `yamlr drift` is a **Reporting-Only** operation in the current version. It does not automatically "heal" the cluster back to the local state. To apply fixes, use the `scan` and `heal` workflow.

> [!NOTE]
> This feature requires a [PRO] license. Run `yamlr auth login` to activate your enterprise tier.
