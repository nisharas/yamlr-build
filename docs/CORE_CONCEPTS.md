# Core Concepts

**The Engineering Architecture of Manifest Safety**

Yamlr is designed to eliminate cross-resource configuration errors and silent failures in Kubernetes deployments. While standard tools validate individual resource syntax in isolation against OpenAPI schemas, Yamlr analyzes the relational integrity of the entire manifest set as a unified topology.

---

## 1. The ResourceGraph (Dependency Topology)
Kubernetes resources depend upon one another to deliver working services. Yamlr constructs an in-memory dependency model called the **ResourceGraph**.

This graph maps key relationship types across your workspace, detecting cross-resource failures that standard linters miss:

| Relationship | Logic | Defused Failure Mode |
|:---|:---|:---|
| **Service → Pod** | Validates that service selectors match workload pod labels. | Defuses phantom services routing traffic to non-existent endpoints. |
| **Ingress → Service** | Ensures backend services exist and target ports match service definitions. | Prevents broken ingresses and 502/503 errors. |
| **ConfigMap → Pod** | Verifies that environment variable refs and volume mounts align with ConfigMap keys. | Prevents `CrashLoopBackOff` from missing keys. |
| **HPA → Deployment** | Ensures the autoscaler target reference matches a valid deployment and avoids replica fighting. | Eliminates flapping replica counts during deployments. |
| **NetworkPolicy → Pod**| Validates pod selector mapping and ingress/egress CIDR rules. | Detects accidental network isolation and exposed ports. |

---

## 2. Risk Classification
Findings are categorized by failure domain and potential blast radius:

- **Traffic Reliability**: Failures affecting ingress routing, service discovery, or port alignment.
- **Data Dependencies**: Missing or mismatched Secrets, ConfigMaps, and PersistentVolumeClaims.
- **Security Posture**: Missing `securityContext`, privilege escalation flags, and unpinned image tags.
- **API Lifecycle**: Deprecated or removed Kubernetes APIs relative to the target cluster version.

---

## 3. Semantic DNA Verification
To ensure repairs never introduce accidental regressions, every remediation is checked against **Semantic DNA**. The engine calculates a canonical hash of the manifest's structural meaning before and after remediation.

If a proposed mutation would alter intended behavior outside the targeted rule fix, the engine aborts the write automatically.

---

## 4. Comment & Format Preservation
Infrastructure engineers invest significant effort into readable, well-commented manifests. Yamlr's native Rust sharder supports source-aware repairs; review each diff to confirm the change is appropriate:

- **Indentation & Spacing**: Preserves custom spacing, 2-space or 4-space indentation, and blank line vertical rhythm.
- **Inline Comments**: Every `#` comment—inline or block—is preserved in place.
- **Quote Fidelity**: Single quotes, double quotes, and unquoted scalars are preserved verbatim.

---

## 5. Atomic Backup & Rollback
Before any file is modified during `yamlr heal --apply`, a timestamped backup snapshot is created under `.yamlr/backups/`:

- **Atomic Rollback**: `yamlr rollback` reverts the entire healing session instantly.
- **Selective Restore**: `yamlr restore <path>` restores an individual file to its pre-heal state.
- **Version Retention**: Rotates and retains up to 5 historical snapshots per file.
