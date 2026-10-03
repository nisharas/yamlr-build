# The Healing Engine

**Yamlr Auto-Repair & Mutation Internals**

Yamlr couples static manifest analysis with an automated remediation engine. The Healing Engine is designed to apply multi-file fixes while strictly preserving formatting, comments, and semantic correctness.

---

## 1. Interactive & Preview Flow
By default, `yamlr heal` operates in preview mode to prevent unintended modifications:

1. **Side-by-Side Diffing**: Renders a color-coded terminal diff showing exact lines to be modified.
2. **Interactive Gating**: Prompts for confirmation before writing changes to disk:
   ```bash
   yamlr heal ./k8s/
   ```
3. **Atomic Commit**: When invoked with `--apply`, writes changes using an atomic write-and-rename pattern to prevent partially written files.

```bash
# Run in non-interactive CI mode
yamlr heal ./k8s --apply
```

---

## 2. Multi-Stage Safety Verification
Every mutation passes through three verification filters before being written to disk:

| Filter | Identifier | Scope |
|:---|:---|:---|
| **Structural Syntax** | `[SYN]` | Validates YAML syntax, indentation boundaries, and comment preservation. |
| **Schema Compliance** | `[SCH]` | Validates the mutated node against official Kubernetes OpenAPI v3 schemas. |
| **Relational Integrity**| `[REL]` | Re-evaluates the ResourceGraph to verify that selectors, ports, and refs remain aligned. |

**If an automated repair violates any safety filter, the mutation is aborted and the file is left unchanged.**

---

## 3. Structural Type Remediation
A frequent source of Kubernetes admission errors is YAML type mismatch (e.g. declaring a map where Kubernetes expects an array of maps). Yamlr includes transformation logic for:

- **Type Alignment**: Converts malformed maps to valid arrays of maps without dropping nested child keys.
- **Port Alignment**: Harmonizes Service `targetPort` definitions with container `containerPort` values.
- **HPA / Replica De-confliction**: Removes hardcoded `replicas` from Deployments when a HorizontalPodAutoscaler is actively managing the workload.

---

## 4. Multi-Layered Recovery (The Vault)
Remediation is always non-destructive and fully reversible:

- **Session Rollback**: `yamlr rollback` reverts the most recent healing session across all affected files.
- **Single-File Restore**: `yamlr restore <path>` restores an individual manifest from the backup vault.
- **Audit Journal**: Every mutation writes a timestamped record to `.yamlr/backups/`, enabling full audit traceability.

---

> [!NOTE]
> **Deterministic Remediation**
> The Healing Engine is strictly deterministic. Identical input files with identical configuration will produce byte-for-byte identical output on every run.
