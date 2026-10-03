# Yamlr Positioning & Market Strategy: "The Ruff of Kubernetes"

## Executive Summary

Yamlr is a **manifest scanning and remediation tool** for Kubernetes. It provides a native Rust implementation for supported workflows; performance and preservation characteristics should be evaluated against representative repositories and operations.

> **"Yamlr scans Kubernetes manifests and offers reviewable repairs for supported findings."**

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE TOOLING PARADIGM SHIFT                      │
│                                                                        │
│   Python Tooling Evolution:                                            │
│   flake8 + black + isort + pyupgrade (Python runtime, >2s)             │
│      └──► Ruff (Standalone Rust binary, <20ms, automatic fixes)        │
│                                                                        │
│   Kubernetes Manifest Tooling Evolution:                               │
│   kubeval + kube-linter + conftest + custom bash scripts (Slow, noisy) │
│      └──► Yamlr (Native Rust implementation with reviewable repairs)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. The Four Non-Negotiable Trust Pillars

Enterprise platform engineering teams refuse automated remediation unless four invariant gates are satisfied:

| Pillar | Engineering Guarantee | Enforcement Mechanism |
|:---|:---|:---|
| **🔒 Comment Integrity** | Source-aware repairs aim to retain comments and layout where supported; review diffs and validate output. | Sharding and layout-aware repair paths; behavior depends on the transformation and input. |
| **🧊 Determinism** | Determinism should be verified for each supported operation and environment. | Deterministic ordering is applied in selected processing paths. |
| **🛡️ OpenAPI Conformity** | Scan validates supported resources against the selected schema set; validate healed output before deployment. | Embedded and user-provided schema paths, subject to supported versions and resource kinds. |
| **⚡ Native Processing** | No fixed latency or throughput guarantee is published. Measure representative workloads on target hardware. | Rust implementation for supported core workflows; runtime depends on input and enabled checks. |

---

## 2. Competitive Differentiation Matrix

| Capability | kubeval / kubeconform | OPA Gatekeeper / Kyverno | Datree / Bridgecrew | **Yamlr Native** |
|:---|:---:|:---:|:---:|:---:|
| **Schema Validation** | ✅ | ⚠️ (Requires Rego/CEL) | ✅ | ✅ (Embedded v1.21–v1.37) |
| **Automated Auto-Repair** | ❌ (Report only) | ❌ (Admission reject only)| ❌ (Report only) | ✅ (AST-safe healing) |
| **Comment Preservation** | Varies by tool and operation | Varies by tool and operation | Varies by tool and operation | Source-aware behavior for supported transformations; review diffs |
| **Cross-Resource Healing** | ❌ | ❌ | ❌ | ✅ (RBAC, selector, refs) |
| **Offline Air-Gapped Mode** | Depends on schema configuration | Available in selected deployments | Depends on product and configuration | Local workflows can run offline when required schemas are available locally |
| **Execution Latency** | Not compared | In-Cluster only | Not compared | Not published; benchmark equivalent workloads before comparison |
| **LSP / IDE Integration** | ❌ | ❌ | ⚠️ (Basic extension) | ✅ (LSP hover, code actions, fmt) |
| **Fleet Batch Remediation** | ❌ | ❌ | ❌ | ✅ (`yamlr fleet --create-pr`) |

---

## 3. Product Wedge & Workflow Embedding

Rather than building a heavyweight SaaS dashboard that requires organizational procurement approval, Yamlr embeds into existing developer daily habits:

```mermaid
flowchart LR
    Dev["Developer Keystroke"] --> IDE["VS Code / Cursor (Yamlr LSP)"]
    IDE --> Git["Git Commit"]
    Git --> Hook["Pre-Commit Hook"]
    Hook --> PR["GitHub / GitLab PR"]
    PR --> CI["CI Pipeline (SARIF upload)"]
    CI --> Webhook["In-Cluster Admission Webhook"]
```

1. **Local Authoring (IDE)**: Instant keystroke squigglies and hover tooltips via stdio JSON-RPC LSP daemon.
2. **Pre-Commit Gate**: Pre-commit hook runs `yamlr heal --apply` automatically before commits are registered.
3. **CI Scanning Gate**: GitHub Actions (`yamlr/yamlr-action@v1`) emits native SARIF reports directly into GitHub Code Scanning.
4. **Platform Fleet Remediation**: Platform teams execute `yamlr fleet . --apply --create-pr` to remediate hundreds of microservice repos across the company overnight.

---

## 4. The "Intel Inside" Supplier Moat

Yamlr exposes a clean, stable internal API designed for consumption as a core engine by platform tools, GitOps operators, and Backstage portals:

- **CLI Interface**: Standard POSIX exit codes (0 = Success, 1 = Violations, 2 = Syntax, 3 = Config).
- **JSON & SARIF Output**: Deterministic schema for ingestion into Datadog, Splunk, and GitHub Security tabs.
- **In-Cluster Admission Daemon**: Native Rust webhook server accepting Kubernetes `AdmissionReview` and emitting RFC 6902 JSONPatch mutations.
- **Embedded C-ABI & WASM**: Universal embedding in web browsers, IDE plugins, and foreign language runtimes.
