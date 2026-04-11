# yamlr features
**Capability Discovery & Roadmap Matrix**

The `yamlr features` command provides a comprehensive inventory of all engine capabilities, their tiers (Free vs. Pro), and their current activation status.

## Usage

```bash
# Display the full capability matrix
yamlr features
```

## The Tiered Engine

Yamlr classifies features into four strategic categories:

### 1. Core (FREE)
Fundamental safety operations available to the community.
*   **Schema Validation**: OpenAPI-driven audit.
*   **Visual Healing**: Interactive, comment-preserving repair.
*   **API Deprecation**: Detecting legacy K8s versions.
*   **Forensic Journal**: Atomic WAL journaling of all mutation attempts.

### 2. Observability (FREE)
Visual context and relational awareness.
*   **Relational Topology**: `graph topo` - ASCII resource trees.
*   **Blast Radius**: `graph blast-radius` - Impact analysis.

### 3. Surgical (FREE/PRO)
High-precision remediations and GitOps protections.
*   **Auto-Injection**: Injecting limits, probes, and namespaces (Free).
*   **Tag Sanitization**: Remediating `:latest` image tags (Free).
*   **Clinical Mode**: `--clinical` - Protecting GitOps pipes by redirecting UI to stderr (Free).
*   **Rust Acceleration**: `--fast` - Native engine for hyperscale (Pro).

### 4. Enterprise (PRO)
Advanced security, compliance, and strategic integrations.
*   **Drift Remediation**: Reconciling live cluster state with local manifests.
*   **Auto-Hardening**: Autonomous PSS-style policy injection.
*   **Semantic DNA**: SHA-256 identity for manifest integrity.
*   **Evidence Receipts**: DNA-signed PDF receipts for auditors.
*   **AI Agent Bridge (MCP)**: High-fidelity healing server for LLMs.
*   **Sovereign IDE (LSP)**: Real-time safety guard in VS Code.

---

> [!TIP]
> Use `yamlr features` to quickly check if your enterprise license is active and which "Surgical" capabilities are available in your current environment.
