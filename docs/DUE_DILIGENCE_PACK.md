# Yamlr Technical Due Diligence & M&A Information Pack

**Classification:** Confidential / Proprietary  
**Target Valuation:** Not established; requires verified financials and an independent valuation  
**Target Acquirers:** Google Cloud, Palo Alto Networks, Datadog, Cisco / Splunk, Snyk  
**IP Status:** 100% Proprietary, Closed-Source Commercial Engine  
**Platform Architecture:** Cloud-Agnostic, Vendor-Neutral Native Rust Core  

---

## 1. Executive Summary & Acquisition Thesis

Yamlr is a proprietary Kubernetes manifest scanning and remediation tool. This repository review does not substantiate a market-first claim or universal lossless-healing guarantee.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE TOOLING PARADIGM SHIFT                      │
│                                                                        │
│   Legacy Kubernetes Manifest Tooling:                                  │
│   kubeval + kube-linter + conftest + custom bash scripts (Slow, noisy) │
│      └──► Yamlr (Native Rust implementation with reviewable repairs)   │
└────────────────────────────────────────────────────────────────────────┘
```

Yamlr scans Kubernetes manifests and provides reviewable repairs for supported findings. Its Rust implementation does not by itself establish fixed performance or preservation guarantees; validate changes and benchmark representative workloads before relying on those properties.

### Strategic Wedge
* **Native CLI**: Provides scanning and remediation workflows in a native binary. No fixed runtime guarantee is published.
* **The "Intel Inside" Moat**: Designed as an embeddable engine consumed via C-ABI (`libyamlr.so`), native gRPC daemon, WASM, and CLI by CI/CD providers, GitOps operators (ArgoCD, Flux), and internal developer portals (Spotify Backstage, Port).
* **Strict Cloud Neutrality**: Runs identically across AWS EKS, Google Cloud GKE, Azure AKS, Red Hat OpenShift, Rancher, Talos Linux, bare-metal on-prem clusters, and air-gapped national security enclaves.

---

## 2. Intellectual Property (IP) & License Provenance

### 2.1 Ownership & Copyright
The proprietary license states Yamlr's intended licensing terms; it does not establish chain of title. This repository review did not verify signed contributor or contractor assignments, ownership of every shipped asset, or provenance records for generated schemas and vendored material. Those records must be assembled and reviewed before making clean-title claims.

No evidence in this pack establishes that all code was developed without AI assistance or third-party contributions. Architecture and module size are not evidence of code provenance.

### 2.2 Third-Party Dependency Clearance
Automated license checks now cover Rust dependencies and locked production dependencies in the JavaScript workspaces. Python release CI also exports installed dependency license texts. Generated schemas and vendored assets still lack a complete provenance and notice review. Current evidence is:

| Area | Current evidence | Remaining review |
| :--- | :--- | :--- |
| **Rust native crates** | `cargo-deny` checks the configured allowlist in CI and the release gate. | Review every license match, source, and required notice before release. |
| **Python package and runtime dependencies** | CI builds and installs the wheel into a clean virtual environment on Linux, macOS, and Windows; it checks the `yamlr` console entrypoint, Python scan/heal APIs, and exports `PYTHON_LICENSE_TEXTS.txt`. The supported model is a Rust-backed CLI and PyO3 SDK; the archived Python CLI is source-only compatibility code, not a wheel fallback. | Review the license texts, collect any separate NOTICE files, and define a complete policy. |
| **JavaScript production dependencies** | CI installs each locked website, VS Code extension, and gateway workspace, rejects production dependency licenses outside its explicit allowlist, and uploads a JSON license inventory plus detected license texts. | Review the generated inventories and notices for each release; cover optional packages for other target platforms, schemas, vendored assets, and any separate NOTICE obligations. |

Release builds generate a CycloneDX JSON SBOM from the source workspace and include it with the platform artifacts. The Python wheel CI job exercises the installed console entrypoint and SDK APIs in a temporary virtual environment on Linux, macOS, and Windows, and emits `PYTHON_LICENSE_TEXTS.txt` from installed Python dependencies. CI also inventories locked production dependencies in the website, VS Code, and gateway JavaScript workspaces and collects detected license texts. These files support review; they do not establish license compatibility, provide every required notice, or prove that every bundled asset has been reviewed. Dependency licensing and redistribution obligations must still be reviewed for each release before making legal-clearance claims.

---

## 3. Core Architectural Differentiators & Technical Moat

### 3.1 Layout-Aware Parsing and Remediation
The Rust parser separates document-boundary streaming, lexical sharding, and semantic analysis. It creates owned shard data, and the healer applies supported changes while attempting to retain surrounding source layout. Preservation behavior depends on the input and repair; validate output and review diffs before applying changes.

### 3.2 Offline Support
* **Embedded Kubernetes Schemas**: The Rust core bundles schema data for Kubernetes versions `v1.21` through `v1.37` in compressed form.
* **Network-Optional Operation**: Core scans using an embedded schema can run without network access. Optional integrations and dynamic schema retrieval may require network access; use the documented offline configuration in restricted environments.

### 3.3 Relational & Cross-Resource Topological Intelligence
* **Referential Healing**: Automatically links Service selectors to Deployment labels, validates ConfigMap/Secret keys, and synchronizes RBAC RoleBindings to ServiceAccounts.
* **Topological Reordering**: Multi-document YAML streams are emitted in strict Kubernetes dependency priority (Namespaces & CRDs before workloads and ingress).

---

## 4. Verification & Mathematical Invariants

The repository contains Rust, Python, and integration checks. Counts and outcomes vary by revision and environment; use the CI result for the exact source revision being reviewed. Tests cover selected parser, healer, scan, and packaging behaviors, but do not prove correctness for every valid YAML input or guarantee universal idempotence or layout preservation.

---

## 5. Planetary Distribution & Developer Habit (The Wedge)

| Distribution Channel | Target Asset / Workflow | Status |
| :--- | :--- | :---: |
| **Multi-Platform Binaries** | Linux x86_64, Linux musl, Linux aarch64, macOS ARM64, macOS Intel, Windows x64 | Shipped (`.github/workflows/release-binaries.yml`) |
| **Pre-Commit Hooks** | `yamlr-fmt`, `yamlr-fix`, `yamlr-scan`, `yamlr-heal`, `yamlr-diff` | Shipped (`.pre-commit-hooks.yaml`) |
| **Homebrew Tap** | `brew install yamlr/tap/yamlr` with automated SHA-256 updater | Shipped (`Formula/yamlr.rb`) |
| **GitHub Actions** | `yamlr/yamlr-action@v1` with SARIF upload to Code Scanning | Shipped (`actions/scan/`, `actions/heal/`) |
| **VS Code & Open VSX** | Lean 2.6 MB `.vsix` extension with LSP formatting & hover docs | Shipped (`vscode/`) |
| **In-Cluster Admission** | Native TCP/HTTP admission webhook daemon; no fixed latency guarantee is published | Shipped (`native_core/src/cli/webhook_cmd.rs`) |
| **K8s 1.30+ VAP Sync** | Bi-directional `ValidatingAdmissionPolicy` CEL ingest and export | Shipped (`native_core/src/cli/vap_cmd.rs`) |
| **Helm Values Schema** | In-memory `values.schema.json` validation and type coercion | Shipped (`native_core/src/parsers/helm/schema_validator.rs`) |
| **Native RPC Service** | High-throughput `ManifestService` RPC daemon (`yamlr rpc`) | Shipped (`native_core/src/grpc/`) |
| **Embeddable C-ABI** | Shared library (`libyamlr.so`, `yamlr.dll`) and canonical C header | Shipped (`native_core/include/yamlr.h`) |

---

## 6. Commercial Model & Monetization Engine

### 6.1 Product Tiers
* **Free Developer Edition**: Single-file scanning, local formatting (`yamlr fmt`), basic schema validation.
* **Pro Individual (\$300/year)**: Cross-resource referential healing, pre-commit automation, LSP quick-fixes, air-gapped license activation.
* **Enterprise Fleet (\$15,000–\$50,000/year)**: Fleet batch remediation (`yamlr fleet --create-pr`), admission webhook daemon, Spotify Backstage IDP catalog integration, Prometheus telemetry exporter, and custom VAP/CEL ruleset sync.

### 6.2 Automated Zero-Touch Revenue Pipeline
* **Stripe Webhook Worker (`infra/stripe-webhook/worker.js`)**: Automatically ingests Stripe `checkout.session.completed` events, cryptographically signs RS256 JWT licenses, and emails customers instant air-gapped activation commands.
* **Optional Hosted Service**: The hosted licensing adapter currently runs on Cloudflare Workers with D1. This provider-specific service is separate from the local manifest engine and can be replaced behind its HTTPS and signed-token contracts.

---

## 7. M&A Due Diligence Checklist

| Diligence Area | Verification Artifact | Result |
| :--- | :--- | :---: |
| **Source Code Architecture** | Strict Modularity Protocol (`< 500 lines per module`) | **Compliant** |
| **Security & CVE Audit** | Zero high-risk CVEs; air-gapped hermetic execution | **Audited** |
| **Open Source Licensing** | Clean-bill whitelist; zero GPL/AGPL copyleft | **Cleared (`deny.toml`)** |
| **Cross-Platform Portability** | Native binaries on 5 architectures; zero external runtimes | **Verified** |
| **Enterprise Hardening** | Relativized SARIF URIs, 100k+ streaming crawler, multi-version CRD indexer | **Hardened (Phase 6A)** |
| **Unified Quality Gate** | Multi-tier automated runner (`scripts/golden_build_verify.py` -> `golden_report.json`) | **823 / 823 Tests Passing (Phase 6B)** |
| **Engineering Ingestion** | Full OpenAPI documentation; self-documenting CLI help | **48-Hour Ingestion Ready** |

---

**Corporate Development Conclusion:** Yamlr provides a native Rust codebase for Kubernetes manifest scanning and remediation. Product reliability, performance, and market fit should be assessed through reproducible benchmarks, supported-input tests, customer evidence, and a review of the shipped release artifacts.
