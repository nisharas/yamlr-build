# Getting Started

**Quickstart Guide to Manifest Safety and Auto-Repair**

Yamlr validates and auto-repairs Kubernetes manifests before deployment. This guide covers installation and your first healing workflow in under two minutes.

---

## 1. Quick Demo Sandbox
Experience Yamlr's comment-preserving auto-repair in an isolated demo workspace:

### Step 1: Generate Demo Manifests
```bash
yamlr demo
```
This generates sample manifests with typical real-world errors (port mismatches, deprecated APIs, and missing securityContext).

### Step 2: Audit Manifests
```bash
yamlr scan yamlr-demo/
```

### Step 3: Preview and Apply Repairs
```bash
# Preview side-by-side diff
yamlr heal yamlr-demo/

# Apply repairs in-place
yamlr heal yamlr-demo/ --apply
```

**Key Behaviors to Observe**:
- **Comment Preservation**: Existing inline comments and formatting are untouched.
- **Port Alignment**: Service `targetPort` is synchronized with container ports.
- **Atomic Rollback**: Run `yamlr rollback` to immediately revert all changes.

---

## 2. Scanning Your Project

### Scan Current Directory
```bash
# Scans all YAML manifests recursively
yamlr scan .
```

### Target a Specific Kubernetes Release
```bash
yamlr scan . --k8s-version 1.30
```

### CI/CD Quality Gate
```bash
# Exits with code 1 if errors or critical violations are found
yamlr scan . --fail-on error
```

---

## 3. Execution Pipeline
On every scan, Yamlr executes a four-stage pipeline:
1. **Sharding & Syntax Ingestion**: The native Rust sharder processes YAML documents into structural shards. Streaming can borrow document slices during boundary scanning; later processing may allocate owned data.
2. **Schema Validation**: Validates fields and types against official Kubernetes OpenAPI v3 schemas.
3. **Cross-Resource Topology**: Reconciles selectors, ports, volume mounts, and RBAC bindings across manifests.
4. **Scoring & Reporting**: Calculates a 0–100 health score and outputs text, JSON, or SARIF 2.1.0 reports.

---

## Next Steps

- **[Core Concepts](/docs/core-concepts)**: ResourceGraph topology and comment-preserving parser design.
- **[Configuration Spec](/docs/configuration)**: Configuring rules in `.yamlr.yaml`.
- **[CLI Reference](/docs/cli)**: Complete guide to all commands and flags.
