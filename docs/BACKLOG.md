# 📋 Master Engineering Backlog (Auto-Generated from Roadmap)
**Project:** Yamlr | **Status:** v1.6 ✅ 100% CERTIFIED | **Target:** $20M+ Acquisition Ready
**Source of Truth:** `PRODUCT_ROADMAP.md` (structure) + `FEATURE_SCORECARD.md` (priority tiers)

> [!IMPORTANT]
> Feature prioritization follows `FEATURE_SCORECARD.md`. Items are assigned **Tier 0** (8 weeks), **Tier 1** (weeks 9–16), **Tier 2** (rest of 2026), or **CUT** (revisit on demand). Labels below reflect the scorecard verdicts.

---

### 🔹 EPIC-40: Omega Hardening (v1.65) ✅ COMPLETED
*   [x] **[STORY-40-1]** Forensic Log Privacy & Redaction
*   [x] **[STORY-40-2]** Global Atomic Batch Transactions
*   [x] **[STORY-40-3]** Global Rollback Architecture

## 🟢 MILESTONE 1: CORE PLATFORM (✅ COMPLETED)

### 🔹 EPIC-01: Universal Ingestion
*   **Feature 1.1: Tolerant Lexing**
    *   ✅ **[STORY-01-1]** Round-Trip Parsing
        *   [x] **Task:** Implement `KubeLexer` (error-tolerant tokenization)
        *   [x] **Task:** Implement `KubeShadow` (comment/whitespace preservation)
        *   [x] **Subtask:** Handle flush-left lists
        *   [x] **Subtask:** Preserve YAML anchors & aliases

*   **Feature 1.2: Workspace Discovery**
    *   ✅ **[STORY-01-2]** Recursive Scanning
        *   [x] **Task:** `YamlrEngine.batch_heal()` with depth limits
        *   [x] **Task:** `.yamlr.yaml` config support (`config.py`)
           *   [x] **Subtask:** Create `.bak` backups before write
    *   ✅ **[STORY-01-3]** Atomic Writes
        *   [x] **Task:** `FileSystemManager.atomic_write()` (fsync + rename)

### 🔹 EPIC-16: Native Binary Distribution (✅ COMPLETED)
*   ✅ **[STORY-16-1]** Windows Native Compilation
    *   [x] **Task:** Implement Nuitka build pipeline (`scripts/build_nuitka.py`)
    *   [x] **Task:** Standardize asset anchoring (`pkgutil` for `rules.yaml`)
    *   [x] **Task:** Mitigation of Windows Defender Error 225
    *   [x] **Task:** Implement `zstandard` compression (Payload reduction to ~20MB)
    *   [x] **Task:** Post-build automated verification (`hack/verify_binary.py`)
    *   [x] **Task:** Deep Codebase Audit (Audit + Fixes for `processor`, `healer`, `structurer`)
    *   [x] **Task:** Resolve Nuitka Runtime Regressions (Union imports, license constants)

### 🔹 EPIC-02: Context-Aware Intelligence
*   **Feature 2.1: Global Graph**
    *   ✅ **[STORY-02-1]** Identity Aggregation
        *   [x] **Task:** Extract `ManifestIdentity` from each file
        *   [x] **Task:** Aggregate into project-wide graph in `engine.py`

*   **Feature 2.2: Cross-Resource Analyzers**
    *   ✅ **[STORY-02-2]** Ghost Service Detection
        *   [x] **Task:** `CrossResourceAnalyzer` - Compare `Service.selector` vs `Pod.labels`
        *   [x] **Subtask:** Fuzzy matching for suggestions
    *   ✅ **[STORY-02-3]** Orphan Resource Detection
        *   [x] **Task:** Detect unused ConfigMaps/Secrets
    *   ✅ **[STORY-02-4]** Broken Volume Detection
        *   [x] **Task:** Validate PVC references
    *   ✅ **[STORY-02-5]** Port Mismatch Validation
        *   [x] **Task:** Verify `Service.targetPort` exists in containers
    *   ✅ **[STORY-02-6]** Ingress Backend Validation
        *   [x] **Task:** Ensure Ingress rules point to valid Services

*   **Feature 3.2: Safety Integrity**
    *   ✅ **[STORY-03-3]** DNA Checksum
        *   [x] **Task:** `pipeline.py` - `_calculate_semantic_dna()` SHA-256 hash
    *   ✅ **[STORY-03-4]** IntentDNA Snapping ✅ FREE
        *   [x] **Task:** Schema-driven indentation lock for copy-paste safety

### 🔹 EPIC-03: Forensic Sovereign Hardening ✅ COMPLETED
*   **Feature 3.1: Risk Taxonomy (SHD-001 - SHD-015)**
    *   ✅ **[STORY-03-1]** Security & Privilege Audit
        *   [x] **Rule:** SHD-001 (HostPath), SHD-002 (Privileged), SHD-003 (HostNetwork), SHD-004 (RBAC Escalation)
    *   ✅ **[STORY-03-2]** Traffic & Availability Audit
        *   [x] **Rule:** SHD-005 (Ingress Hijack), SHD-006 (Traffic Misrouting), SHD-007 (Resource Starvation)
    *   ✅ **[STORY-03-3]** Data & Hygiene Audit
        *   [x] **Rule:** SHD-008 (Sensitive Volume), SHD-009 (Zombie APIs), SHD-010 (Orphan Bloat)
    *   ✅ **[STORY-03-4]** Advanced Cluster Safety
        *   [x] **Rule:** SHD-011 (Circular Deps), SHD-012 (CRD Drift), SHD-013 (HPA Conflict), SHD-014 (Disruption Blind-Spots), SHD-015 (Pod Anti-Affinity)
    *   ✅ **Verification:** `tests/verify_shield_forensics.py` (ALL 15 PASS)

### 🔹 EPIC-04: CLI Experience
*   ✅ **[STORY-04-1]** yamlr init (Scaffolding)
*   ✅ **[STORY-04-2]** yamlr explain (Documentation)
*   ✅ **[STORY-04-3]** yamlr completion (Shell autocomplete - Bash/Zsh/PowerShell)
*   ✅ **[STORY-04-4]** yamlr scan (Read-only validation)
    *   [x] **Task:** Stdin support (`cat file.yaml | yamlr scan -`)
    *   [x] **Task:**   ✅ **yamlr scan** - Read-only validation
*   ✅ **[STORY-04-5]** yamlr heal (Auto-fix mode)
    *   [x] **Task:** Interactive mode (single file diff preview)
    *   [x] **Task:** Batch mode (directory confirmation)
    *   [x] **Task:** Auto-approve flags (`-y`, `--yes-all`)
*   ✅ **[STORY-04-6]** yamlr catalog (Browse rules/analyzers)
    *   [x] **Task:** `catalog list` (Show installed versions)
    *   [x] **Task:** `catalog update` (Fetch K8s version-specific schemas)
    *   [x] **Task:** `catalog status` (Show resolved catalog path)
*   ✅ **[STORY-04-7]** yamlr check (Fast Syntax)
    *   [x] **Task:** CI/CD optimized linting (network disabled)
*   ✅ **[STORY-04-8]** yamlr diagnose (Debug Wrapper)
    *   [x] **Task:** Verbose logging wrapper
*   ✅ **[STORY-04-9]** yamlr upgrade (API Migration)
    *   [x] **Task:** Version targeting (`--to` flag)
*   ✅ **[STORY-04-10]** yamlr secure (Security Wrapper)
    *   [x] **Task:** Hardening wrapper
### 🔹 EPIC-24: Strategic Expansions (✅ COMPLETED)
*   **Feature 24.1: Performance Pillar (Yamlr-Light)**
    *   ✅ **[STORY-24-1]** Rust Integration
        *   [x] **Task:** Implement Rust-based fast crawler
        *   [x] **Task:** Python-Rust bridge in `crawler.py`
*   **Feature 24.2: Trust Pillar (DNA Receipts)**
    *   ✅ **[STORY-24-2]** Cryptographic Compliance
        *   [x] **Task:** Semantic DNA logic in core
        *   [x] **Task:** `yamlr audit --verify` implementation
*   **Feature 24.3: Breadth Pillar (Cross-Domain)**
    *   ✅ **[STORY-24-3]** HCL Expansion
        *   [x] **Task:** Regex-based HCL/Terraform parser
        *   [x] **Task:** ResourceGraph extension (19 typed edges)

### 🔹 EPIC-14: The Supplier Pivot (✅ COMPLETED) 🔴 **Tier 0**
*   **Feature 14.1: Argo CD Integration**
    *   ✅ **[STORY-14-1]** Config Management Plugin (CMP) v2
        *   [x] **Task:** Implement `plugin.yaml` with discovery/generate phases
        *   [x] **Task:** Create `sidecar-patch.yaml` for `argocd-repo-server`
        *   [x] **Task:** Implement "Clinical Output Mode" in CLI (stdout protection)
        *   [x] **Task:** Fix Windows encoding stability for GitOps streams
        *   [x] **Task:** Implement Concatenated YAML Streaming for batch mode
        *   [x] **Task:** Validate via `scripts/verify_argo.py` simulation

---

### 🔹 EPIC-25: CLI Hardening & Pruning (v1.4) ✅ COMPLETED
*   ✅ **[STORY-25-1]** The Great Pruning (Progressive Disclosure)
    *   [x] **Task:** Categorize 35+ commands into Tiers (CORE, INSIGHT, etc.)
    *   [x] **Task:** Dynamic Help Suppression logic in `parser_factory.py`
    *   [x] **Task:** Dynamic Tiered UX in `help_formatter.py`
*   ✅ **[STORY-25-2]** Diagnostic Command (`doctor`)
    *   [x] **Task:** Deterministic environment & license health check
*   ✅ **[STORY-25-3]** Capability Shielding
    *   [x] **Task:** Centralized Pro gating policy logic in `YamlrBridge`
*   ✅ **[STORY-25-4]** IDP Productization
    *   [x] **Task:** Integrated `idp-export init` template generation

---

### 🔹 EPIC-05: Enterprise Policy Shield (Pro)
*   ✅ **[STORY-05-1]** Native OPA Execution (`opa_adapter.py` subprocess)
*   ✅ **[STORY-05-2]** Remote Bundle Loading (urllib)
*   ✅ **[STORY-05-3]** Gatekeeper Extraction (ruamel.yaml)
*   ✅ **[STORY-05-4]** Enterprise Auth (`auth.py` - Device flow + JWT)

---

### 🔹 EPIC-26: Monetization Integrity (Remediation) 🟢 **Tier 0** ✅ COMPLETED
*   ✅ **[AUDIT-FIX-05]** Real-world License Validation
    *   **Task:** [x] Replace the `validate()` stub in `license.py` with cryptographic RS256 signature verification. (DONE 2026-03-25)
*   ✅ **[AUDIT-FIX-06]** Secure JWT OIDC Exchange
    *   **Task:** [x] Implement real OIDC discovery and validation in `auth.py`. (DONE 2026-03-25)
*   [x] **[AUDIT-FIX-07]** Pro Quota Hardening
    *   **Task:** [x] Prevent local bypass of the 5-file/day healing limit.
*   ✅ **[AUDIT-SEC-01]** Windows ACL Enforcement
    *   **Task:** [x] Programmatically lock down `~/.yamlr` and backups using `icacls`. (DONE 2026-03-25)
*   ✅ **[AUDIT-SEC-02]** Path Traversal Jail
    *   **Task:** [x] Implement strict Content-Aware Jail with `.resolve()` containment checks. (DONE 2026-03-25)
*   ✅ **[AUDIT-SEC-03]** Supply Chain Audit
    *   **Task:** [x] Integrate `pip-audit` into CI pipeline. (DONE 2026-03-25)

*   ✅ **[STORY-27-1]** Functional HTML Dashboards
    *   [x] **Task:** Implement Glassmorphism interactive templates for `export_html` in `exporter.py`. (DONE 2026-03-24)
*   ✅ **[STORY-27-2]** Functional PDF Evidence
    *   [x] **Task:** Implement `export_pdf` for SOC2-ready evidence reporting. (DONE 2026-03-24)

### 🔹 EPIC-28: Monetization Surface (Payments & Checkout) 🟢 **Tier 0** ✅ COMPLETED
*   [x] **[STORY-28-1]** Google-Level Upgrade Dashboard
    *   [x] **Task:** Implement high-fidelity `yamlr upgrade` view with feature comparison.
*   [x] **[STORY-28-2]** Seamless Web-to-CLI Handshake
    *   [x] **Task:** Implement `get_checkout_url` with machine-identifier tokens for frictionless attribution.
*   [x] **[STORY-28-3]** Pro-Status Refresh Callbacks
    *   **Task:** Implement proactive session refreshing upon payment confirmation.

---

### 🔹 EPIC-14: CI/CD & Habit Integrations (Tier 0/2)
*   **Feature 14.1: GitHub Actions**
    *   ✅ **[ECO-01]** GitHub Actions Integration 🟢 **Tier 0**
        *   [x] **Task:** Create `yamlr/scan@v1` and `yamlr/heal@v1` actions
        *   [x] **Subtask:** Auto-comment diffs (🟡 Tier 1), policy gate (🟢 Tier 0)
        *   [x] **Subtask:** Surgical CI Gate logic (`--fail-on`)
        *   [x] **Subtask:** GitHub Marketplace listing
*   **Feature 14.2: IDE Integrations**
    *   ✅ **[ECO-05]** VS Code Extension (Diagnostics) 🟢 **Tier 0**
        *   [x] **Task:** LSP integration for real-time validation
        *   [x] **Subtask:** Visual Studio Marketplace listing
    *   [ ] **[ECO-06]** JetBrains IDE Plugin 🔵 **Tier 2**
*   **Feature 14.3: GitOps Integrations**
    *   ✅ **[ECO-03]** Argo CD Supplier Integration 🟢 **Tier 0/1**
        *   **Mode:** Config Management Plugin (CMP) or Pre-Sync Hook
        *   **Task:** [x] Implement native Argo CMP for manifest auto-healing.
        *   **Subtask:** [x] Block sync if healing reveals unfixable criticals.
    *   ✅ **[ECO-04]** Flux Remediation Controller 🟢 **Tier 0/1**
        *   **Mode:** Post-render webhook or specialized Kustomization controller.
        *   **Task:** [x] Pre-flight healing before Flux applies to cluster.
*   **Feature 14.4: Other CI/CD**
    *   [ ] **[ECO-02]** GitLab CI Integration 🔵 **Tier 2**
    *   [ ] **[ECO-07]** Jenkins Integration 🔵 **Tier 2**
    *   [ ] **[ECO-08]** Helm Chart Validator 🔵 **Tier 2**
*   ✅ **[STRAT-01]** Yamlr-Light (Rust Scanner Bridge) 🟢 **Tier 1**
        *   **Goal:** Scan 1M manifests in <10 seconds via Rust. (DONE 2026-03-24)
*   ✅ **[STRAT-02]** Semantic DNA Receipts 🟢 **Tier 1**
        *   **Goal:** Cryptographic proof of intent preservation. (DONE 2026-03-24)
*   ✅ **[STRAT-03]** Cross-Domain Expansion 🟢 **Tier 1**
        *   **Goal:** Multi-cloud (AWS/GCP/Azure) + Terraform/OpenTofu support. (DONE 2026-03-24)

### 🔹 EPIC-17: Legacy Parity & High-Gravity Healing (Tier 0) ✅ COMPLETED
*   ✅ **[STORY-17-1]** Multi-Doc Block Reset (COMPLETED 2026-02-21)
    *   [x] **Task:** Update `YamlrLexer.shard()` to reset `in_block` at `---`.
*   ✅ **[STORY-17-2]** Double-Dash Normalization (COMPLETED 2026-02-21)
    *   [x] **Task:** Add `- -` pattern repair to `LexicalHealer.heal_double_dash()`.
*   ✅ **[STORY-17-3]** Epistemic Reconstruction (COMPLETED 2026-02-21)
    *   [x] **Task:** Implement Map-as-List type casting in `SchemaHealer`.
    *   [x] **Task:** Add `StageSixTwoEpistemicRepair` to pipeline.
*   ✅ **[STORY-17-4] Table-Style Continuation (Legacy)**
    *   [x] **Task:** Implement `TableContinuationHeuristic` to catch bullet-less lists.
*   ✅ **[STORY-17-5] Compact-Mode Serialization (Legacy Pro)**
    *   [x] **Task:** Implement `StageTenVacuum` for blank-line removal.
*   ✅ **[STORY-17-6] Schema-Aware Sorting (Legacy)**
    *   [x] **Task:** Implement `SortingEngine` with kind-specific priorities.
*   ✅ **[STORY-17-7] Safety Threshold (Ghost Logic)**
    *   [x] **Task:** Implement Emergency Brake in `pipeline.py`.
*   ✅ **[STORY-17-8] Unique Backup Rotation (Ghost Logic)**
    *   [x] **Task:** Harden `FileSystemManager` with UUID-hashed history.

### 🔹 EPIC-15: Audit Remediation (Feb 2026 Hardening) ✅ COMPLETED
*   [x] **[AUDIT-FIX-01]** Concurrency Configuration Lockdown
    *   [x] **Task:** Fix hardcoded resource limits (`500m/512Mi`) in `processor.py` workers.
*   [x] **[AUDIT-FIX-02]** Security Whitelist Integration
    *   [x] **Task:** Wire `allowed_host_paths` config to `SecurityAnalyzer`.
*   [x] **[AUDIT-FIX-03]** Registry Enforcement Healer
    *   [x] **Task:** Implement `RegistryAnalyzer` to enforce `trusted_registries`.
*   [x] **[AUDIT-FIX-04]** Config Parity Alignment
    *   [x] **Task:** Ensure `kubernetes/version` is respected by all analyzers.

### 🔹 EPIC-18: Phase 1.5 Remediation & Alignment (P1 Debt) ✅ COMPLETED
*   [x] **[AUDIT-DEBT-01]** Global Version Propagation
    *   [x] **Task:** Audit all core analyzers to ensure they use `config.kubernetes_version` instead of hardcoded defaults.
*   [x] **[AUDIT-DEBT-02]** Result Success Bit Hardening
    *   [x] **Task:** Ensure `CrossResourceAnalyzer` errors correctly flip the `success` bit in `HealFileResult` instead of just logging a warning.
*   [x] **[AUDIT-DEBT-03]** Exception Handling Standardization
    *   [x] **Task:** Wrap analyzer execution in try/except blocks to prevent partial report generation on silent failure.

### 🔹 EPIC-29: Refined CLI Architecture (v1.3) ✅ COMPLETED
*   ✅ **[STORY-29-1] Advisory Engine Decoupling**
    *   [x] **Task:** Implement `advisory.py` for centralized UI/Advisory logic.
    *   [x] **Task:** Refactor `scan.py` and `heal.py` to use `AdvisoryRenderer`.
    *   [x] **Task:** Remove legacy `formatter` dependency from all command handlers.
    *   [x] **Task:** **Zero-Blindspot CLI Audit & Remediation**: Fixed signature mismatches in `main.py` and registered `auth` command.
*   ✅ **[STORY-29-2] Progressive Discovery Tiering**
    *   [x] **Task:** Implement tiered help categories (Core, Insight, etc.) in `help_formatter.py`.
    *   [x] **Task:** Implement `--all` flag to reveal hidden orientation/meta commands.
*   ✅ **[STORY-29-3] Dynamic Version Inference**
    *   [x] **Task:** Implement `VersionInferenceEngine` in `inference.py`.
    *   [x] **Task:** Integrate with `YamlrManager` for automated API-to-K8s version discovery.
    *   [x] **[STORY-29-4] Cluster Auto-Detection (v1.5)**
        *   [x] **Task:** Implement `ClusterDetection` for `kubectl` and in-cluster API discovery. (DONE 2026-03-25)
        *   [x] **Task:** Sync branding to "Yamlr Enterprise (Pro)" across all UI/CLI modules. (DONE 2026-03-25)
        *   [x] 13-round Zero-Blindspot forensic audit protocol. (DONE 2026-03-27)
        *   [x] Native security pre-scan for anchor/alias protection. (DONE 2026-03-27)
        *   [x] Signal-safe process pool orchestration. (DONE 2026-03-27)
    *   ✅ **[STORY-29-6] Architectural Centralization & Modularity (v1.7)**
        *   [x] **Task:** Consolidated healing surface via `HealingPipeline.process_file`.
        *   [x] **Task:** Centralized Pro gatekeeping logic in `ProGate`.
        *   [x] **Task:** Refactored `auditor.py` (Single & Stream) to use Canonical Pipeline.
        *   [x] **Task:** **Enforce < 500 line protocol** across `base.py`, `parser_factory.py`, and `processor_helpers.py`.
        *   [x] **Task:** Delegated handlers for Telemetry, Policy, and Surgery Pools.
        *   [x] **Task:** Resolved all Cognitive Complexity hotspots (Logic < 15).

---

### 🔹 EPIC-19: Remediation Adapters (The "Repair Loop") ✅ COMPLETED
> **Scorecard verdict: TIER 1.** Integrates Yamlr as the resolution engine for OPA/Kyverno. **[Valuation: $20M Milestone]**
*   [x] **[TASK-19-1]** Kyverno Report Ingester: Parse Kyverno `PolicyReport` CRDs.
*   [x] **[TASK-19-2]** OPA JSON Ingester: Map OPA violation JSON to Yamlr Rule IDs.
*   [x] **[TASK-19-3]** Auto-Patch Generator: Wire detection events to `SecurityHardener` and `ResourceLimitInjector`.
> **Scorecard verdict: TIER 0.** This is our core competitive moat—fixing the cross-resource failures others only detect.
*   **Feature 6.1: Relational Healing (Pro) 💎 PAID** ✅ ALL TASKS COMPLETE
    *   [x] **[TASK-06-1]** Implement `ReferenceResolver` stage (COMPLETED 2026-02-21)
    *   [x] **[TASK-06-2]** Service ↔ Pod Selector Surgery *(Verified 2026-02-22 — `selector_healer.py` 164L, fuzzy match + Strategy A/B)*
    *   [x] **[TASK-06-3]** Ghost Resource Generator: Create stub ConfigMaps/Secrets for missing references (COMPLETED 2026-02-21)
    *   [x] **[TASK-06-4]** Port Mismatch Healer *(Verified 2026-02-22 — `port_healer.py` 241L, Strategy A + Strategy B fuzzy match)*

### 🔹 EPIC-07: GitOps Guard ✅ COMPLETED
> **Scorecard verdict:** Policy Baseline + Security Analyzers (detection only).
    *   ✅ **[TASK-07-1]** Implement `yamlr baseline` command
        *   **Subtask:** [x] Snapshot current "accepted" issues to `.yamlr-baseline.json`
    *   ✅ **[TASK-07-2]** Regression Testing (CI fails only on NEW violations)

*   **Feature 7.2: Security Analyzers**
    *   [x] **[TASK-07-3]** RBAC Auditing (Detect wildcard `*` permissions)
    *   [x] **[TASK-07-4]** Privilege Escalation Detection (`privileged: true`)
    *   [x] **[TASK-07-5]** Ingress Security (TLS & IngressClass validation)
    *   [x] **[TASK-07-6]** Network Policy Audit (Zero Trust parity) ✅

*   **Feature 7.3: Observability**
    *   [ ] **[TASK-07-7]** Web UI (Health visualization)
    *   [ ] **[TASK-07-8]** Audit History (Who healed what)
*   ✅ **[TASK-07-9]** Pro Module: Shield Engine Implementation (`yamlr.pro.shield`) 🟢 **Tier 0**
*   ✅ **[TASK-07-10]** Pro Module: Exporter Implementation (`yamlr.pro.exporter`) 🟢 **Tier 0**

### 🔹 EPIC-19: Remediation Adapters (The "Repair Loop") ✅ COMPLETED
> **Scorecard verdict: TIER 1.** Integrates Yamlr as the resolution engine for OPA/Kyverno. **[Valuation: $20M Milestone]**
*   [x] **[TASK-19-1]** Kyverno Report Ingester: Parse Kyverno `PolicyReport` CRDs.
*   [x] **[TASK-19-2]** OPA JSON Ingester: Map OPA violation JSON to Yamlr Rule IDs.
*   [x] **[TASK-19-3]** Auto-Patch Generator: Wire detection events to `SecurityHardener` and `ResourceLimitInjector`.

### 🔹 EPIC-20: Semantic DNA API (Data Integrity Moat) ✅ COMPLETED
> **Scorecard verdict: TIER 1.** Establishes mathematical trust in automated refactors. **[Valuation: $60M Milestone]**
*   [x] **[TASK-20-1]** Implement `yamlr dna` CLI command.
*   [x] **[TASK-20-2]** DNA Verification CI Gate: Block PRs if DNA shifts without explicit approval.
*   [x] **[TASK-20-3]** DNA Audit Artifacts: Generate signed proof for SOC2 auditors (Walkthrough + Command).
*   [x] **[TASK-20-4]** `yamlr dna verify`: Command to verify if a file's DNA matches a signed manifest. 🟢 **Tier 0**

### 🔹 EPIC-21: Compliance Auto-Healing with DNA Guarantees (The Trust Anchor) ✅ COMPLETED
> **Scorecard verdict: TIER 0-1.** This is Yamlr's category-defining opportunity — the specific combination of auto-fixing K8s compliance violations with cryptographic intent guarantees at PR time does NOT exist as a product today.
>
> **The Uncontested Gap:** Existing tools either (a) detect+block (OPA, Kyverno, Checkov, Kubescape) or (b) auto-fix generic code (Dependabot, Renovate), but NO tool auto-fixes Kubernetes compliance issues with semantic integrity proofs. Yamlr fills this gap.

*   [x] **[TASK-21-1]** SOC2/HIPAA/CIS Compliance Rule Pack 💎 PRO
    *   [x] **Subtask:** SOC2 CC6.1 — Auto-set `privileged: false` + `readOnlyRootFilesystem: true`
    *   [x] **Subtask:** SOC2 CC6.8 — Auto-inject `resources.limits` from CIS benchmark defaults
    *   [x] **Subtask:** HIPAA §164.312 — Auto-add encryption-at-rest annotations to Secrets
    *   [x] **Subtask:** CIS 5.2.2 — Auto-add `runAsNonRoot: true` + `runAsUser: 1000`
    *   [x] **Subtask:** CIS 5.1.6 — Auto-add `automountServiceAccountToken: false`
    *   [x] **Subtask:** Map each auto-fix to its control ID in rule metadata (`rules.yaml`)
    *   **Target:** 20+ auto-remediations covering SOC2/HIPAA/CIS top violations

*   [x] **[TASK-21-2]** DNA-Signed Evidence Engine 💎 PRO
    *   [x] **Subtask:** Compute SHA-256 DNA before healing begins (baseline snapshot)
    *   [x] **Subtask:** Compute SHA-256 DNA after healing completes (healed snapshot)
    *   [x] **Subtask:** Generate DNA diff log: which fields changed, which were untouched
    *   [x] **Subtask:** Sign DNA diff with GPG key (`yamlr dna sign --key <path>`)
    *   [x] **Subtask:** Machine-verifiable guarantee: DNA diff proves ONLY the compliance fix changed
    *   **Auditor value:** "Here's cryptographic proof that our automation touched ONLY these 3 fields"

*   [x] **[TASK-21-3]** SARIF Compliance Mapping
    *   [x] **Subtask:** Extend `SarifFormatter` to include `taxa` field mapping to SOC2/HIPAA/CIS control IDs
    *   [x] **Subtask:** Each SARIF result gets `relatedLocations` showing the DNA diff for that fix
    *   [x] **Subtask:** Map severity levels to compliance impact (CRITICAL = audit failure, HIGH = finding, MEDIUM = observation)

*   [x] **[TASK-21-4]** CI Evidence Pipeline
    *   [x] **Subtask:** `yamlr scan . --output sarif --harden --enforce-limits --enforce-probes --evidence-dir ./audit/`
    *   [x] **Subtask:** Generates: SARIF report + DNA diff log + signed manifest in `--evidence-dir`
    *   [x] **Subtask:** GitHub Action outputs `results-sarif` + `evidence-path` for downstream consumption
    *   [x] **Subtask:** Exit code strategy: 0 = all compliant, 1 = violations auto-fixed, 2 = unfixable violations remain

*   [x] **[TASK-21-5]** Remediation Adapter Ingest (OPA/Kyverno → Yamlr)
    *   [x] **Subtask:** `yamlr import kyverno-report.json` — parse Kyverno PolicyReport CRDs → map to Yamlr heal actions
    *   [x] **Subtask:** `yamlr import opa-results.json` — parse OPA violation JSON → map to Yamlr rules → auto-fix
    *   [x] **Subtask:** Produce DNA evidence for each imported-and-fixed violation
    *   **Positioning:** "They find it; we fix it — with proof"

*   [x] **[TASK-21-6]** Auditor-Ready Export 💎 PRO
    *   [x] **Subtask:** Generate compliance summary report (HTML/PDF) from evidence artifacts
    *   [x] **Subtask:** Include: control ID, violation description, auto-fix applied, DNA proof hash
    *   [x] **Subtask:** Wire to `yamlr scan --export compliance-report.html` with Pro gate

*   [x] **[TASK-21-7]** Compliance Benchmark Test Suite
    *   [x] **Subtask:** Create 50+ test fixtures covering SOC2/HIPAA/CIS violations
    *   [x] **Subtask:** Verify each auto-fix produces valid K8s manifests (schema validation gate)
    *   [x] **Subtask:** Verify DNA diff correctly isolates only the compliance changes

---

### 🔹 EPIC-22: Quality Hardening (B+ to A-) 🚀 🟢 **Tier 0**
> **Goal:** Reaching A- grade by addressing complexity, dead code, and documentation debt.
*   [x] **[TASK-22-1] Complexity Management (Modularity Enforcement)**
    *   [x] **Subtask:** Refactor `core/entrypoints/heal.py` to < 500 lines. (DONE 2026-03-10)
    *   [x] **Subtask:** Refactor `core/entrypoints/scan.py` to < 500 lines. (DONE 2026-03-10)
    *   [x] **Subtask:** Refactor `core/pipeline.py` to < 500 lines. (DONE 2026-03-10)
    *   [x] **Subtask:** Extract `core/deprecations.py` version maps to JSON/YAML. (DONE 2026-03-10)
    *   [x] **Subtask:** Modularize `cli/main.py` Command Registry. (DONE 2026-03-10)
*   [x] **[TASK-22-2] Dead Code Cleanup**
    *   [x] **Subtask:** Perform Vulture sweep and remove 100% of unused imports/variables. (DONE 2026-03-10)
*   [x] **[TASK-22-3] Documentation Integrity Audit**
    *   [x] **Subtask:** Verify 100% docstring coverage for public APIs with "Why" docstrings. (DONE 2026-03-10)
    *   [x] **Subtask:** Sync CLI `--help` strings with `USER_GUIDE.md`. (DONE 2026-03-10)
    *   [x] **Subtask:** Document missing `roi` command in manual and manifest. (DONE 2026-03-15)
*   [x] **[TASK-22-4] Technical Debt Sweep**
    *   [x] **Subtask:** Run Bandit/Vulture and resolve any remaining low-risk warnings. (DONE 2026-03-10)

---

### 🔹 EPIC-23: A+ Parity (Compliance & Polish) 🟢 **Tier 1** ✅ COMPLETED
> **Goal:** Reach A+ engineering grade by resolving the "last 10%" of documentation, typing, and organization debt.
*   [x] **[POLISH-23-1] Full Future Annotations Coverage (100%)**
    *   [x] **Task:** Add `from __future__ import annotations` to all remaining files.
*   [x] **[POLISH-23-2] Public API Coverage (100% `__all__`)**
    *   [x] **Task:** Add `__all__` declarations to all missing modules in `src/`.
*   [x] **[POLISH-23-3] Integration Test Expansion & Script Formalization**
    *   [x] **Task:** Move `verify_*.py` from `scripts/` and `hack/` to `tests/integration/` as formal pytest suites.
    *   [x] **Task:** Add E2E scenarios for Helm, Kustomize, and GitOps workflows.
*   [x] **[POLISH-23-4] Strict Typing (Any Type Reduction)**
    *   [x] **Task:** Reduce `Any` usage in favor of `Union` and specialized types in core models/UI.
*   [x] **[POLISH-23-5] Full Docstring Coverage (100%)**
    *   [x] **Task:** Add module-level and public API docstrings with "Why" sections to all files.

---

### 🔹 EPIC-25: Agentic Safety Engine (✅ COMPLETED) 🟢 **Tier 0**
*   **Feature 25.1: MCP Integration**
    *   ✅ **[STORY-25-1]** MCP Server Implementation
        *   [x] **Task:** Implement `mcp_server.py` with `FastMCP`
        *   [x] **Task:** Expose `scan_manifest`, `heal_manifest`, and `why` tools
        *   [x] **Task:** Register `yamlr mcp` subcommand in CLI
*   **Feature 25.2: Conversational Healing**
    *   ✅ **[STORY-25-2]** Rationale & Impact Enrichment
        *   [x] **Task:** Add `rationale`, `impact_description`, and `risk_level` to all core analyzers
        *   [x] **Task:** Verify "Safety Intelligence" output in MCP tools
*   **Feature 25.3: Strategic Documentation**
    *   ✅ **[STORY-25-3]** Roadmap & Competitive Update
        *   [x] **Task:** Add "Agentic Safety" narrative to `PRODUCT_ROADMAP.md`
        *   [x] **Task:** Update `competitive_analysis.md` with MCP differentiator

### 🔹 EPIC-30: Visual Hooks & IDP Integration (v1.3) ✅ COMPLETED 🟢 Tier 0
*   **Feature 30.1: Relational Observability**
    *   ✅ **[STORY-30-1]** yamlr graph
        *   [x] **Task:** Implement `topo`, `blast-radius`, and `export` subcommands.
        *   [x] **Task:** Support ASCII, Mermaid, and JSON formats.
*   **Feature 30.2: Application-Centric Safety**
    *   ✅ **[STORY-30-2]** yamlr stats --apps
        *   [x] **Task:** Implement `AppSafetyReport` aggregator.
        *   [x] **Task:** Surface per-app ROI and safety metrics.
*   **Feature 30.3: IDP & Distribution**
    *   ✅ **[STORY-30-3]** yamlr idp-export
        *   [x] **Task:** Implement Backstage, Prometheus, and JSON exporters.
*   **Feature 30.4: Strategic Intelligence**
    *   ✅ **[STORY-30-4]** yamlr roi & pulse
        *   [x] **Task:** Implement time-saved calculations and anonymized telemetry.

### 🔹 MILESTONE 3: ECOSYSTEM (📅 FUTURE)

### 🔹 EPIC-08: Visual Observability 🔴 CUT
> **Scorecard verdict: CUT.** No habit trigger. "Be the engine, not the dashboard."
*   [ ] **[TASK-08-1]** HTML Dashboard (Jinja2 template)
*   [ ] **[TASK-08-2]** Trend Analysis (Historical scores)
*   [ ] **[TASK-08-3]** Deprecation Reporting (Dedicated summary block)

### 🔹 EPIC-09: AI Surgeon (Enterprise) 🔴 CUT
> **Scorecard verdict: CUT.** Trust gate risky, LLM infra required. Non-LLM structural reconstruction parts (TASK-09-9 through TASK-09-11) are R&D track in Tier 2.
*   **Feature 9.1: Safety Sandwich Architecture**
    *   [ ] **[TASK-09-1]** Layer 1: Context Gathering (Graph + Secret Redaction)
    *   [ ] **[TASK-09-2]** Layer 2: AI Reasoning (LLM proposes changes)
    *   [ ] **[TASK-09-3]** Layer 3: Simulation & Policy Check (OPA + Graph validation)
*   **Feature 9.2: Intelligent Refactoring**
    *   [ ] **[TASK-09-4]** AI Explain (LLM explanations for policy failures)
    *   [ ] **[TASK-09-5]** Auto-Refactor (Split monoliths)
    *   [ ] **[TASK-09-6]** Graph Integrity Validation (Verify refs post-refactor)
    *   [ ] **[TASK-09-7]** Protected Resources (StatefulSet/PVC delete protection)
    *   [ ] **[TASK-09-8]** Human-in-the-Loop PR Generation
*   **Feature 9.3: Structural YAML Reconstruction** 🆕 (v2.0)
    *   [ ] **[TASK-09-9]** Heuristic Newline Injection
        *   **Task:** Detect `key1: value1 key2:` patterns and insert newlines
        *   **Subtask:** Build K8s keyword dictionary for boundary detection
    *   [ ] **[TASK-09-10]** Context-Aware Indentation
        *   **Task:** Infer block structure from K8s schema expectations
        *   **Subtask:** Map root-level keys (`metadata`, `spec`, `status`) to indentation rules
    *   [ ] **[TASK-09-11]** Schema-Guided Reconstruction
        *   **Task:** Use OpenAPI schema to guess correct structure
        *   **Subtask:** Build K8s resource → required fields mapping
    *   [ ] **[TASK-09-12]** LLM-Assisted Repair
        *   **Task:** For severely corrupted files, use LLM to propose valid structure
        *   **Subtask:** Integrate with AI Surgeon safety sandwich (Layer 3 validation)
---
### 🔹 EPIC-31: Mastery Pass (Hardening & Wedges) ✅ COMPLETED
*   **Feature 31.1: Forensic Ghost Logic Purge**
    *   [x] **Task:** Purge all `.git_copy` and legacy skeleton stubs. (DONE 2026-04-07)
*   **Feature 31.2: Architectural Consolidation**
    *   [x] **Task:** Merge `Shield` into `SchemaValidator` (Recursive & Heuristic). (DONE 2026-04-07)
*   **Feature 31.3: Strategic Wedge: Drift Doctor**
    *   [x] **Task:** Implement Cluster-to-Manifest Sync (Reporting-only). (DONE 2026-04-07)
*   **Feature 31.4: Compliance Wedge: SBOM Integrity**
    *   [x] **Task:** Implement CycloneDX v1.5 JSON Exporter. (DONE 2026-04-07)
*   **Feature 31.5: Cross-Platform verification**
    *   [x] **Task:** Port `audit_parity` to Python. (DONE 2026-04-07)
*   **Feature 31.6: Documentation Hardening**
    *   [x] **Task:** Update Backlog, Roadmap, and Manual. (DONE 2026-04-07)

## 🧪 EPIC-12: Enterprise Stress Test Findings (NEW - 2026-02-09) 🟢 TIER 0/1
*31 items discovered during 100-cluster, 960-file stress test*
> **Scorecard verdict:** Bugs + Engine Quick Factory = **Tier 0**. FREE features scored individually (see `FEATURE_SCORECARD.md`). PRO features = **Tier 1** (preview-first). QA items = **Tier 1** (safety override).

### 🐛 Bugs (P1 - Must Fix)
*   [x] **[BUG-12-01]** Engine Constructor Default Catalog
    *   [x] [BUG-12-01] Add fallback embedded catalog path in engine.py to allow execution without a --catalog flag.
    *   [x] **Subtask:** Create minimal `catalog_minimal.json` bundled with package
    *   [x] **Subtask:** Update `__init__()` to use fallback when `catalog_path=None`

*   [x] **[BUG-12-02]** Result Dictionary Inconsistency
    *   [x] **Task:** Audit all result dicts in `engine.py` (Phase 7)
    *   [x] **Subtask:** Ensure `path` AND `full_path` always present
    *   [x] **Subtask:** Add lint check for result schema consistency

*   [x] **[BUG-12-03]** Category Extraction Fix
    *   [x] **Task:** Update stress test to use `full_path` key (Phase 7)
    *   [x] **Subtask:** Add fallback parsing for filename-based category

### ⚠️ Schema Healing Gaps (P2)
*   [x] **[GAP-12-01]** Fuzzy Typo Matcher
    *   [x] **Task:** Implement Levenshtein distance for K8s field names (Phase 5)
    *   [x] **Subtask:** Build common typo dictionary (`replicass→replicas`)
    *   [x] **Subtask:** Add "Did you mean X?" suggestions to findings

*   [x] **[GAP-12-02]** Structural Violation Fixer
    *   [x] **Task:** Detect map-vs-list violations using OpenAPI schema (Phase 7)
    *   [x] **Subtask:** Auto-wrap single-item map as list when schema expects array

*   ✅ **[GAP-12-03]** Type Coercion Engine
    *   [x] **Task:** Create `TypeCoercer` module in `yamlr.parsers` (Phase 6)
    *   [x] **Subtask:** Coerce `"3"` → `3` for integer fields
    *   [x] **Subtask:** Coerce `"true"` → `true` for boolean fields
    *   [x] **Subtask:** Schema-Aware Coercion for `None` → `{}` (`labels: null` fix)

### 🔓 FREE Tier Enhancements
*   ✅ **[FREE-12-01]** TUI Health Dashboard
    *   [x] **Task:** Implement `yamlr status` subcommand
    *   [x] **Subtask:** Show issue counts per severity
    *   [x] **Subtask:** Show health score bar
    *   [x] **Subtask:** Add PRO upsell hints
*   ✅ **[UX-12-05]** Link `welcome` to `status`
    *   [x] **Task:** Auto-trigger health score check on first run
    *   [x] **Subtask:** Display health score instead of help if initialized
    *   [x] **Subtask:** Add global configuration initialization tips (`yamlr init`) to `welcome` and `demo` outputs
*   [x] **[STORY-14-2]** TUI Health Score Dashboard 🟢 **Tier 0**
    *   [x] **Task:** Implement persistent gamified dashboard view in `welcome` / `demo`.
    *   [x] **Subtask:** Add "Dopamine Drip" animations (Rich-based) for score increases.
    *   [x] **Subtask:** Integrated cumulative "Surgical Efficiency" metric.

*   ✅ **[UX-12-06]** Context-Aware Smart Prompt (The Magic Moment)
    *   [x] **Task:** Intercept bare `yamlr` command to show interactive Doctor panel instead of default help text
    *   [x] **Subtask:** Detect K8s manifests in CWD and presence of `.yamlr.yaml`
    *   [x] **Subtask:** Offer context-aware "Next Best Action" (scan, init, demo) with single-key execution
    *   [x] **Subtask:** Graceful fallback for non-Interactive (CI/CD) and `YAMLR_CLASSIC` overrides
    *   [x] **Subtask:** Implement tree-walking config discovery (find `.yamlr.yaml` in parent directories up to git root)
    *   [x] **Subtask:** Refine prompt to prioritize `scan` over `init` for maximum DX smoothness

*   ✅ **[FREE-12-02]** Cross-Resource Suggestions
    *   [x] **Task:** Add suggestion text to `CrossResourceAnalyzer` findings
    *   [x] **Subtask:** Compute closest matching selector
    *   [x] **Subtask:** Format as "Did you mean...?" message

*   ✅ **[FREE-12-03]** Enhanced Deprecation Warnings
    *   [x] **Task:** Show side-by-side diff in deprecation warnings
    *   [x] **Subtask:** Add "Run `yamlr migrate` to fix" hint

*   [x] **[FREE-12-04]** Inline PRO Upsell Messages 🟢 **Tier 0**
    *   **Trigger:** Every issue detected but NOT auto-fixed becomes a PRO advertisement instead of silent disappointment
    *   [x] **Task:** Add upsell hint after each PRO-fixable finding: `💎 PRO: yamlr heal --harden would fix this (runAsNonRoot: true)`
    *   [x] **Task:** Show PRO-fixable count in summary: `⚠️ 12 more issues fixable with PRO`
    *   [x] **Task:** Add `--quiet` flag to suppress upsell hints in CI/CD

### 💎 PRO Tier Features
*   [x] **[PRO-12-01]** Auto-Inject Resource Limits (`--enforce-limits`)
    *   [x] **Task:** Implement `ResourceLimitInjector` healer (Phase 9)
    *   [x] **Subtask:** Detect container type (sidecar/app/pause)
    *   [x] **Subtask:** Apply smart defaults per type
    *   [x] **Subtask:** Configurable via `.yamlr.yaml` (Phase 10)

*   [x] **[PRO-12-02]** Auto-Pin Image Tags (`--fix-tags`)
    *   [x] **Task:** Implement `ImageTagPinner` healer (Phase 9)
    *   [x] **Subtask:** Replace `:latest` with configurable default
    *   [x] **Subtask:** Option for SHA256 digest pinning
    *   [x] **Subtask:** Integrate with container registries (optional)

*   [x] **[PRO-12-03]** Auto-Add Health Probes (`--enforce-probes`)
    *   [x] **Task:** Implement `ProbeInjector` healer (Phase 9)
    *   [x] **Subtask:** HTTP GET probe for web containers
    *   [x] **Subtask:** TCP Socket probe for database containers
    *   [x] **Subtask:** Configurable initial delay and periods (Phase 10)

*   [x] **[PRO-12-04]** Security Hardening (`--harden`)
    *   [x] **Task:** Implement `SecurityHardener` healer (Phase 9)
    *   [x] **Subtask:** Remove `privileged: true`
    *   [x] **Subtask:** Set `runAsNonRoot: true`
    *   [x] **Subtask:** Add `readOnlyRootFilesystem: true`
    *   [x] **Subtask:** Drop all capabilities by default

*   ✅ **[PRO-12-05]** Cross-Resource Auto-Fix (`--fix-refs`) *(Completed 2026-02-22)*
    *   [x] **Task:** Implement `ReferenceResolver` healer
    *   [x] **Subtask:** Correct selector typos via fuzzy match (`ServiceSelectorHealer`)
    *   [x] **Subtask:** Generate stub ConfigMaps/Secrets for volumes (DONE 2026-02-21)
    *   [x] **Subtask:** Fix port mismatches — Strategy A (single-port) + Strategy B (named-port fuzzy match via `difflib.SequenceMatcher`, threshold 0.60)
    *   [x] **Subtask:** Gate all 3 cross-resource stages behind `--fix-refs` Pro flag in `pipeline.py`
    *   [x] **Subtask:** Wire through parser → `CliOptions` → `extract_cli_options` Pro-gate → `heal.py` → `auditor.py` → `pipeline.heal()`
    *   [x] **Verification:** 9/9 tests pass in `tests/test_fix_refs_pro.py`

*   ✅ **[DEBT-12-08] Shield Engine Hardening** 🟢 **Tier 0**
    *   **Issue**: Current `ShieldEngine` is a stub with minimal detection logic.
    *   **Task**: [x] Implement full CIS/SOC2 shadow-risk analyzers in `pro/shield.py`.
    *   **Goal**: Detect sensitive volume mounts, privileged escalation, and container capability leaks.

### 🧪 Testing Infrastructure
*   ✅ **[QA-12-01]** CI Stress Test Integration
    *   [x] **Task:** Add `stress_test_orchestrator.py` to GitHub Actions (`stress-test.yml`).
    *   [x] **Subtask:** Integrate Schema Compliance Gate.
    *   [x] **Subtask:** Set throughput threshold (50 files/sec).
    *   [x] **Subtask:** Archive results JSON as artifact.

*   [ ] **[QA-12-02]** Category-Specific Unit Tests
    *   [ ] **Task:** Create `tests/test_issue_categories.py`
    *   [ ] **Subtask:** 1 test per 20 issue categories
    *   [ ] **Subtask:** Assert expected healing behavior

*   ✅ **[QA-12-03]** Schema Compliance Gate (COMPLETED 2026-02-15)
    *   [x] **Task:** Validate all healed files against K8s OpenAPI
    *   [x] **Subtask:** 100% compliance required
    *   [x] **Subtask:** Fail CI on any schema violation

*   ✅ **[QA-12-04]** Memory Profiling
    *   [x] **Task:** Add large file memory benchmarks via `stress_test_orchestrator.py`.
    *   [x] **Subtask:** Use `psutil` for peak RSS/VMS tracking (Target: < 1.5GB for 150k).
    *   [x] **Subtask:** Fail if memory exceeds threshold.

*   ✅ **[QA-12-05]** Crash Detection
    *   [x] **Task:** Wrap stress test in exception handler with zero-crash policy.
    *   [x] **Subtask:** Log crashes to `stress_results.json`.
    *   [x] **Subtask:** Fail CI on any unhandled exception.

### 📊 Observability
*   [ ] **[OBS-12-01]** Healing Rate Dashboard
    *   [ ] **Task:** Add category breakdown to `yamlr status`
    *   [ ] **Subtask:** Bar chart format in terminal

*   [ ] **[OBS-12-02]** Performance Benchmarks
    *   [ ] **Task:** Track files/second in CI
    *   [ ] **Subtask:** Alert if < 4 files/second (regression)

*   [ ] **[OBS-12-04]** Rollout & Deprecation Policy
    *   [ ] **Task:** Implement "Warn-Only" (S1 Preview) default for new healing rules.
    *   [ ] **Subtask:** Codify deprecation warning cycle for CLI flags.

*   [x] **[OBS-12-03]** Detection vs Fix Rate Split
    *   [x] **Task:** Separate "detected" from "auto-fixed" in reports
    *   [x] **Subtask:** Clear FREE vs PRO distinction
*   [ ] **[ENG-12-01]** Custom CRD Confidence Scoring
    *   [ ] **Task:** Improve heuristic confidence for proprietary CRDs
    *   [ ] **Subtask:** Allow teams to "bless" certain vendors in config

### 🔧 Technical Debt
*   [x] **[DEBT-12-01]** HealFileResult Dataclass (Standardized Schema)
    *   [x] **Task:** Create standardized result schema with consistent path/findings structure
    *   [x] **Subtask:** All 10 fields explicitly defined (success, max_severity, etc.)
    *   [x] **Subtask:** Type hints for all fields

*   [x] **[DEBT-12-02]** Engine Quick Factory
    *   [x] **Task:** Add `YamlrEngine.quick(path)` method (Phase 3)
    *   [x] **Subtask:** Auto-load default catalog
    *   [x] **Subtask:** Use sensible defaults

*   [ ] **[DEBT-12-03]** batch_heal Simplification
    *   [ ] **Task:** Add `recursive=True` shorthand
    *   [ ] **Subtask:** Default extensions: `.yaml`, `.yml`
    *   [ ] **Subtask:** Default max_depth: 10

*   [ ] **[DEBT-12-04]** Stress Test Improvements
    *   [ ] **Task:** Fix category extraction logic
    *   [ ] **Subtask:** Use `full_path` for category parsing
*   [x] **[DEBT-12-08]** Monolithic Pipeline Decomposition
    *   [x] **Task:** Spilt `pipeline.py` into `PipelineGate` classes
*   [x] **[DEBT-12-09]** CLI Wrapper Refactor
    *   [x] **Task:** Refactor `main.py` into a robust `ParserFactory`
*   [x] **[DEBT-12-10]** Command Dispatch Standardization
    *   [x] **Task:** Merge `core/entrypoints` and `cli/commands` logic
*   [ ] **[DEBT-12-11]** Reference Resolver Optimization
    *   [ ] **Task:** Cache identities to eliminate re-parsing overhead

### 🛡 Operational Hardening (v1.0 Reliability)
*   [x] **[DEBT-12-05]** Durability: Atomic Write `fsync` (COMPLETED 2026-02-13)
    *   [x] **Task:** Re-enable `.fsync()` in `FileSystemManager.atomic_write()`
    *   [x] **Subtask:** Benchmark performance impact on 10k file scans
*   [x] **[DEBT-12-06]** Race-Proof Backups (COMPLETED 2026-02-13)
    *   [x] **Task:** Replace `exists()` check with atomic UUID/Hashed backup naming 
    *   [x] **Subtask:** Ensure rotation logic handles hashed names correctly
*   [x] **[DEBT-12-07]** Windows `MAX_PATH` Resilience (COMPLETED 2026-02-13)
    *   [x] **Task:** Implement path-hashing for deep "external" backups
    *   [x] **Subtask:** Add Windows CI test for 260+ char paths
*   [ ] **[DEBT-12-12]** Aggressive Path Hashing
    *   [ ] **Task:** Hash paths < 200 chars if nesting depth > 10 (Windows)
*   [x] **[SEC-12-01]** Security Whitelist Externalization
    *   [x] **Task:** Move `allowed_host_paths` to `security_defaults.yaml` (Integrated into `io.py` defaults)
*   [x] **[HARDENING-11]** v1.1 Security & Debt Sprint (COMPLETED 2026-02-13)
    *   [x] **Task:** Decompose `YamlrStructurer._build_tree` (God Method)
    *   [x] **Task:** Split `structurer.py`, `bridge.py`, `cross_resource.py` (<500 lines)
    *   [x] **Task:** Implement symlink traversal protection in `io.py`
    *   [x] **Task:** Tighten backup vault permissions to `0o700`
    *   [x] **Task:** Suppress Pro bridge warnings for OSS installs

### 🎯 External Feedback (High Priority)
*   [x] **[UX-12-01]** Reframe Healing Rate Metrics 🟢 **Tier 0**
    *   **The "54.5% Trap":** Users see "Healing Rate: 54.5%" and think the tool failed. In reality, 100% of issues are detected; the remaining 45.5% require PRO flags (`--harden`, `--enforce-limits`, `--fix-refs`).
    *   **Before:** `Healing Rate: 54.5%` → User thinks: "This tool only fixes half my problems"
    *   **After:** `📊 Detection Rate: 100% | ✅ Auto-Healed (Free): 54.5% | 💎 PRO would fix: 45.5%`
    *   [ ] **Task:** Change "Healing Success Rate" → "Auto-Healing Efficiency" in CLI output
    *   [ ] **Task:** Add explicit "Issue Detection Rate: 100%" line to every scan/heal report
    *   [ ] **Task:** Update `cli/formatters.py` to split detected vs auto-fixed vs PRO-fixable

*   [x] **[UX-12-02]** Split Detection vs Fix in CLI
    *   [x] **Task:** Show detected vs auto-fixed separately
    *   [x] **Subtask:** Format: "📊 Detected: X | ✅ Fixed: Y | ⚠️ PRO: Z"
*   ✅ **[UX-12-04]** `yamlr demo` Command
    *   [x] **Task:** Create dummy broken files for instant feedback

*   [x] **[DOC-12-01]** Schema Compliance Claim Fix
    *   [x] **Task:** Change "100% K8s Compliant" → "100% compliant for issues addressed" (README)
    *   [x] **Subtask:** Update walkthrough, reports, marketing

*   ✅ **[QA-12-06]** 100x Stress Test Scale (Hyperscale)
    - [x] **Task:** Scaled to 150,000+ files across 500+ clusters using `simulate_hyperscale.py`.
    - [x] **Subtask:** Performance target: > 50 files/sec.
    - [x] **Subtask:** Memory target: < 1.5GB total peak RSS.

*   [ ] **[FREE-12-05]** Schema Typo Fixes in FREE ⚡
    *   [ ] **Task:** Implement Levenshtein ≤ 2 auto-fix for K8s fields
    *   [ ] **Subtask:** Build typo dictionary (top 1000 mistakes)
    *   [ ] **Subtask:** Boost FREE rate to 70%+
    *   [ ] **Decision:** Requires product review

*   [x] **[PRO-12-06]** `--pro-preview` Demo Mode 🟢 **Tier 0** 🚀
    *   **Command:** `yamlr heal . --pro-preview` — simulate PRO healing without writing changes
    *   **Sales funnel:** Detection (free) → Preview (free) → Fix (Pro) → Proof (Pro)
    *   [x] **Task:** Show colorized "Before → After" diff for each PRO-fixable issue
    *   [x] **Task:** Output upsell CTA at end: `🔓 Unlock these fixes: yamlr.dev/pro`
    *   [x] **Task:** Gate behind Free tier (no license needed to preview)

*   [ ] **[PRO-12-07]** Performance Target: 10+ files/sec
    *   [ ] **Task:** Cache schema lookups
    *   [ ] **Task:** Optimize parallel processing

*   [ ] **[MKT-12-01]** Norway Problem Marketing
    *   [ ] **Task:** Add to landing page, README, blog

---

## 🔧 TECHNICAL IMPROVEMENTS (From FEEDBACK_ANALYSIS.md)

### Critical Issues (Must Fix)
*   ✅ **[TECH-01]** HealResult Dataclass (COMPLETED - replaces tuple)
*   ✅ **[TECH-02]** Rule ID System (COMPLETED 2026-02-03)
    *   [x] **Task:** Update `AnalysisResult` to include `rule_id` field
    *   [x] **Task:** Switch penalty calculation from string matching to `rule_id`
*   ✅ **[TECH-03]** Identity Mode Flag (COMPLETED 2026-02-03)
    *   [x] **Task:** Add `--identity-mode=strict|infer` CLI flag
    *   [x] **Task:** Improve "Skipped" messaging (distinguish from errors)
*   ✅ **[TECH-06]** Schema Validation & CLI Stability (COMPLETED - 2026-02-01)
    *   **Issues Resolved:**
        *   ✅ **Auto-Fix**: Added fallback migration in `migrator.py` for invalid API versions (e.g., ConfigMap `v1beta1` → `v1`).
        *   ✅ **Batch Scanning**: Fixed `engine.py` to support absolute directory paths without "outside workspace" errors.
        *   ✅ **Mirror Backups**: Implemented safe backup creation for external files in `io.py` using an `external/` subdirectory.
        *   ✅ **Quote Preservation**: Implemented smart context-aware quoting in `structurer.py` for `ConfigMap.data` and `Secret.stringData`.
        *   ✅ **CLI Logic**: Fixed `heal.py` interactive `CONFIRM` prompt which was previously a hollow shell.
    *   ✅ **Task:** Implement hybrid cache schema validator
        *   ✅ **Subtask:** Create `SchemaValidator` class with GitHub fetching
        *   ✅ **Subtask:** Cache schemas in `~/.yamlr/schemas/v{version}.json`
        *   ✅ **Subtask:** Integrate into `pipeline.py` analysis phase
        *   ✅ **Subtask:** Implement **Background Downloader** for non-blocking init
    *   ✅ **Task:** Fix CLI Absolute Path & Backup Handling
    *   ✅ **Task:** Fix Interactive CONFIRM logic and Smart Quote Preservation
    *   [ ] **Task:** Add live cluster schema fetching (Paid version)
        *   **Subtask:** Query K8s API server OpenAPI endpoint when cluster connected
        *   **Subtask:** Fallback to cached schemas when offline
*   ✅ **[TECH-07]** Resources Field Corruption Fix (COMPLETED - 2026-02-02)
    *   **Issue Found:**
        *   ❌ Container `resources` fields were serialized as **arrays** instead of **maps**, breaking Kubernetes schema
        *   ❌ Root cause: `"resources"` in global `forced_arrays` set caused ALL resources fields to be treated as arrays
        *   ❌ The word "resources" has two meanings in K8s: Container resources (map) vs RBAC resources (array)
    *   **Fixes Implemented:**
        *   ✅ Removed `"resources"` from `forced_arrays` set in `structurer.py`
        *   ✅ Added `_should_be_array()` method with **context-aware detection**
            *   Walks parse stack to check parent context
            *   If parent = `containers[]` → return False (use map)
            *   If parent = `rules[]` → return True (use array)
        *   ✅ Updated 4 locations in `_build_tree()` to use `_should_be_array()` instead of direct `forced_arrays` check
    *   ✅ **Task:** Implement context-aware array detection for ambiguous fields
        *   ✅ **Subtask:** Remove "resources" from forced_arrays
        *   ✅ **Subtask:** Create _should_be_array() helper method with schema integration
        *   ✅ **Subtask:** Implement fallback heuristics for first-run stability
        *   ✅ **Subtask:** Update all structural reconstruction points
    *   ✅ **Task:** Verify both use cases work correctly
        *   ✅ **Subtask:** Test container resources (Deployment) - remains map ✓
        *   ✅ **Subtask:** Test RBAC resources (ClusterRole) - remains array ✓

### Strategic Improvements
*   [ ] **[TECH-04]** Structured Pipeline Stats
    *   **Task:** Return `PipelineStats` object with timings/counts
*   ✅ **[TECH-05]** Pro Bridge Warning Suppression *(Verified 2026-02-22)*
    *   [x] **Task:** `bridge.py` uses `logger.debug()` instead of warnings. `get_pro_module()` returns `None` silently. No user-facing warnings for OSS installs.
*   ✅ **[TECH-08]** Advanced Error Handling (PHASE 1 COMPLETED 2026-02-03)
    *   [x] **Task:** Implement `YamlrException` hierarchy in `exceptions.py`.
    *   [x] **Task:** Standardize engine error messages with remediation hints.
    *   [ ] **Task:** Integrate remediation hints into UI Formatter (Full support).
*   [ ] **[TECH-09]** Performance Scaling
    *   **Task:** Profile parser bottlenecks.
    *   **Task:** Implement multiprocessing for directory scans.
    *   **Task:** Add scan result caching.
*   [x] **[TECH-10] Master Process Bottleneck (v2.0)** 🔴 **CRITICAL**
    *   **Issue**: `processor.py` performs global reference resolution sequentially.
    *   [x] **Task:** Offload `apply_semantic_fixes` to `ProcessPoolExecutor`.
    *   **Goal**: Ensure sub-second latency for 10k+ manifests.

### v1.1 Hardening Sprint (✅ COMPLETED)
*   **[STORY-11-1] Monolithic Refactor**
*   **[STORY-11-2] Unified Scoring Engine**
*   **[STORY-11-3] DNA-SHA256 Upgrade**
*   **[STORY-11-4] Path Security Hardening**
*   **[STORY-11-7] Platform Parity**
*   **[STORY-12-01] Engine Default Catalog & Quick Factory** (COMPLETED)
    *   [x] **Task:** Implement unified catalog resolution in `YamlrManager`.
    *   [x] **Task:** Fix CLI initialization order in `main.py`.
    *   [x] **Task:** Remove redundant CLI-only resolution logic.

### v1.2 Monetization & Packaging (🚧 ACTIVE)
*   **[STORY-13-1] Binary Segregation (Free vs. Enterprise)**
    *   **Goal**: Ensure the Free binary contains ZERO enterprise code.
    *   ✅ **[TASK-13-1a]** Implement Build-Time Conditional Imports (Nuitka Segregation). (COMPLETED)
    *   ✅ **[TASK-13-1b]** Refactor `YamlrBridge` to handle "Module Not Found" gracefully in Free builds. (COMPLETED)
    *   ✅ **[TASK-13-1c]** Update `Nuitka` configs to create separate native `yamlr` and `yamlr_pro` binaries. (COMPLETED)
*   **[STORY-13-3] Nuitka "Binary-in-a-Box" Transition** 🆕 ✅ COMPLETED
    *   ✅ **[TASK-13-3a]** Replace `sys.frozen` PyInstaller logic with Nuitka-native path resolution. (COMPLETED)
    *   ✅ **[TASK-13-3b]** Implement multi-stage Docker build with Nuitka C-compilation. (COMPLETED)
    *   ✅ **[TASK-13-3c]** Verify native binary performance (150 MB/s target). (COMPLETED)
*   **[STORY-13-2] Drift Doctor (Enterprise Core)**
    *   [ ] **[TASK-13-2a]** Move Cluster Connectivity and Graph logic to `yamlr.pro`.
    *   [ ] **[TASK-13-2b]** Implement `yamlr doctor` as an enterprise-only subcommand.
*   ✅ **[STORY-12-1] Parser & CLI Decomposition**
    *   ✅ **Task:** Split `lexer.py` into `LexerPhase1`, `LexerPhase2`. (COMPLETED)
    *   ✅ **Task:** Extract heuristic rules into separate registry. (COMPLETED)
    *   ✅ **Task:** Modularize CLI Parser and Command Registry. (COMPLETED 2026-02-13)
*   **[STORY-12-2] OPA Adapter Refinement**
    *   [ ] **[TASK-12-2a]** Refactor `opa_adapter.py` to remove duplicate class fallbacks (use centralized models).
    *   [ ] **[TASK-12-2b]** **OPA Mutation Support (v1.2)**
        *   **Goal**: Move hardcoded Python fixes to Rego patches.
        *   **Value**: Allows SREs to define custom auto-healing logic in policy code.
    *   [ ] **[TASK-12-2c]** **Partial Evaluation (Milestone 3)**
        *   **Goal**: Pre-compute static rule components to optimize large-scale CI runs.
*   **[STORY-12-3] Test Suite Stabilization**
    *   ✅ **[TASK-12-3a]** Fix case-sensitivity in `end_user_simulation.py` (backups dir naming). (COMPLETED)
    *   ✅ **[TASK-12-3b]** Fix binary file decoding tracebacks in `engine.py`. (COMPLETED)
    *   ✅ **[TASK-12-3c]** Verify SRE backup rotation (Found 5/5 backups). (COMPLETED)
*   **[STORY-12-4] Config & Model Architecture**
    *   [ ] **[TASK-12-4a]** Implement recursive merge logic in `ConfigManager` for nested enterprise/analyzer configs.
    *   [ ] **[TASK-12-4b]** Centralize OPA-specific fallback models into `yamlr.models` to eliminate redundancy in `opa_adapter.py`.

### Documentation (Pre-Launch v1.0)
*   ✅ **[DOC-01]** Document yamlr catalog command (COMPLETED)
    *   [x] **Task:** Add to README.md (30 min)
        *   [x] **Subtask:** `catalog list` usage example
        *   [x] **Subtask:** `catalog update` usage example
        *   [x] **Subtask:** `catalog status` usage example
    *   [x] **Task:** Add to USER_GUIDE.md
        *   [x] **Subtask:** Full command reference section
*   ✅ **[DOC-02] Expand yamlr auth Documentation** (COMPLETED)
    *   [x] **Task:** Add Enterprise section to USER_GUIDE.md
        *   [x] **Subtask:** Device flow login walkthrough
        *   [x] **Subtask:** JWT token storage explanation
        *   [x] **Subtask:** License tier verification details
*   ✅ **[DOC-03] Rule ID & Market Readiness (Audit Improvements)**
    *   ✅ **Task:** Sync Rule IDs between Analyzers and `rules.yaml` (COMPLETED)
    *   ✅ **Task:** Hydrate `rules.yaml` with all 14 implemented rule descriptions (COMPLETED)
    *   ✅ **Task:** Standardize CLI help help-strings for discoverability (COMPLETED)
    *   ✅ **Task:** Fix discrepancy in `USER_GUIDE.md` command syntax (COMPLETED)
    *   ✅ **Task:** Implement `yamlr welcome` guided tour (COMPLETED)
    *   ✅ **Task:** Document "Ghost Features" (DNA, Backups, Quotes) in Guide (COMPLETED)
    *   ✅ **Task:** Interactive Rule Explain Tips (COMPLETED)
    *   ✅ **Task:** `yamlr rules` Dashboard (COMPLETED)
    *   ✅ **Task:** `yamlr dna verify` command (COMPLETED)
    *   [x] **[TASK-DOC-03j]** Add batch-healing discovery tip to root help output.
    *   [x] **[TASK-DOC-03k]** Add "Quick Start" section to root help.
    *   [x] **[TASK-DOC-03l]** **Explainable Rationale**: Add `rationale` field to all analyzer findings explaining WHY a fix is being proposed. 🟢 **Tier 0**

---

## 🛡 QUALITY ASSURANCE (100% Reliability Initiative)

### Phase 1: Foundation (2 weeks) - ✅ COMPLETED
*   ✅ **[QA-001]** Comprehensive Exception Handling Audit (Completed 2026-02-01)
*   ✅ **[QA-002]** Input Validation Layer (Stage 1 validation implemented)
*   ✅ **[QA-003]** Timeout Protection (OPA 30s timeout verified)
*   ✅ **[QA-004]** Unit Test Suite Creation (Target coverage achieved)

### Phase 2: Hardening (1 month) - 🚧 ACTIVE
*   ✅ **[QA-005]** Expanded Fuzz Testing (Lexer torture tests completed)
*   ✅ **[QA-008]** Integration Testing Expansion (UAT simulation completed)
*   ✅ **[QA-006]** Property-Based Testing (Hypothesis-driven Lexer/Structurer stress tests). (DONE 2026-03-25)
*   ✅ **[QA-007]** Mutation Testing (Native auditor with 100% scoring logic sensitivity). (DONE 2026-03-25)

### Phase 3: Certification (2 months)
*   [ ] **[QA-009]** Third-Party Security Audit
    *   **Task:** Hire external penetration testers
    *   **Task:** OWASP Top 10 compliance check
    *   **Task:** CVE database vulnerability scan
    *   **Task:** Remediate all critical findings

*   ✅ **[QA-010]** Chaos Engineering Tests (Disk Full, Network Down, Process Interruption). (DONE 2026-03-25)
    *   [x] **Task:** Randomly kill processes mid-operation
    *   [x] **Task:** Corrupt files mid-write
    *   [x] **Task:** Fill disk to 100% during operation
    *   [x] **Task:** Verify: No data loss, clean error messages

*   [ ] **[QA-011]** Compliance Certification Prep 🧊 **Tier 3 (Post-Launch)**
    *   **Task:** SOC 2 Type II documentation
    *   **Task:** ISO 27001 information security prep
    *   **Task:** GDPR compliance review

*   [ ] **[QA-012]** Reliability SLA Definition
    *   **Task:** Publish uptime guarantee (99.9%)
    *   **Task:** Define bug severity levels (P0-P4)
    *   **Task:** Commit to patch timelines

### Continuous Monitoring
*   [ ] **[QA-013]** Pre-Commit Quality Gates
    *   **Task:** All tests must pass
    *   **Task:** No new lint errors
    *   **Task:** Code coverage must not decrease

*   [ ] **[QA-014]** Pre-Release Quality Gates
    *   **Task:** Full test suite (all 6+ suites)
    *   **Task:** Fuzz testing (1000+ cases)
    *   **Task:** Manual QA walkthrough
    *   **Task:** Change log review

---

## 💰 EPIC-13: Valuation-Critical Features ($20M Strategy)
*Strategic features required for acquisition/investment talks*

### 🎯 VAL-01: Telemetry & Valuation Proof Layer
*   [ ] **[VAL-01-1]** Anonymized Telemetry System
    *   [ ] **Task:** Implement opt-in telemetry module
    *   [ ] **Subtask:** Track files healed, issue types, time saved
    *   [ ] **Subtask:** Ensure no PII collection
    > [!WARNING]
    > **Status: DEFERRED (Tier 2+ per Feature Scorecard).** Milestone 2 epics are not in v1.x scope. No timeline assigned. Existing code and stubs like `bridge.get_validator()` and `bridge.get_shield()` are preserved for future activation.
*   [x] **[VAL-01-2]** ROI Calculator (`yamlr stats`)
    *   [x] **Task:** Implement `yamlr stats` command
    *   [x] **Subtask:** Show cumulative time saved, failures prevented
    *   [ ] **[VAL-01-3]** Enterprise Telemetry Dashboard (PRO)
        *   [ ] **Task:** Org-wide healing stats web UI
        *   [ ] **Subtask:** CSV/JSON export for executives
    *   [ ] **[VAL-01-4]** Distribution & Tracking** 🟢 **Tier 0**
        *   **Task**: Implement GitHub Release download tracking.
        *   **Task**: Setup `yamlr.dev/download/latest` redirector.

### ⚡ VAL-02: Extreme Performance Constraints
*   [x] **[VAL-02-1]** 200ms CLI Response Target
    *   [x] **Task:** Add `--timing` flag
    *   [x] **Subtask:** CI gate for performance budget
*   [x] **[VAL-02-2]** Latency Justification Policy
    *   [x] **Task:** Add "Performance Impact" to PR template
*   [x] **[VAL-02-3]** Performance Benchmarking Suite
    - [x] **Task:** Automated benchmarks in CI (p50, p95, p99) against fixed 1k fixture.
    - [x] **Subtask:** CI failure gate if regression > 10% on stable core.
*   [x] **[VAL-02-4]** Lazy Loading & Caching
    *   [x] **Task:** Schema lazy load, OPA cache, incremental graph
*   [x] **[VAL-02-5]** joblib.Parallel with Memmapping ⚡
    *   [x] **Task:** Replace multiprocessing.Pool with joblib
    *   [x] **Subtask:** Reduce pickle overhead 10-30x
*   [x] **[VAL-02-6]** Unified Rust/Python Acceleration 🚀
    *   [x] **Task:** Implement Rust-based YAML parser bindings (via `serde_yaml` or specialized crate)
    *   [x] **Subtask:** Reach 150 MB/s target for core healing engine processing
*   [x] **[VAL-02-8]** Restore Enterprise Aesthetics (Heritage Port) 💎
    *   [x] **Task:** Port "Field Priority Ordering" and "Comment Grafting" from `old_codebase`
    *   [x] **Subtask:** Implement `SchemaAwareSorter` and `AttributeGrafter` in `pro/exporter.py`
*   [x] **[VAL-02-7]** Throughput vs File Count Graph
    *   [x] **Task:** Generate marketing-grade dashboard (`reports/performance_report.html`) from `stress_history.json`.

*   [ ] **[VAL-03-2]** Plugin Registry System
    *   [ ] **Task:** Create `plugins/` directory and base classes
*   [ ] **[VAL-03-3]** Core Freeze Enforcement
    *   [ ] **Task:** CI gate blocking locked file modifications
*   [ ] **[VAL-03-4]** Extension API Documentation
    *   [ ] **Task:** "How to Write a Custom Analyzer/Healer" guide

### 🎓 VAL-04: Zero-Knowledge Onboarding
*   [x] **[VAL-04-1]** Error → Fix Command Mapping 🔵 **Tier 2 (Internal Expert)**
    *   [x] **Task:** Add `remediation_command` to AnalysisResult
*   [ ] **[VAL-04-2]** Typo → Suggestion System
    *   [ ] **Task:** Levenshtein ≤ 2 for K8s field suggestions
*   [ ] **[VAL-04-3]** Progressive Disclosure CLI
    *   [ ] **Task:** Implement `--expert` mode levels
*   [ ] **[VAL-04-4]** Interactive Tutorial Mode (`yamlr learn`)
    *   [ ] **Task:** Step-by-step walkthrough command
*   [ ] **[VAL-04-5]** Structured Error Classification
    *   [ ] **Task:** Implement unique error codes (e.g., IO_001, SCHEMA_402).
    *   [ ] **Subtask:** Update `exceptions.py` and UI formatters to display codes.

---

## EPIC-12: Go-to-Market & Distribution (Audit v3 — 2026-02-15)

*Items identified during corrected audit. Moves scorecard from 17→22.*

### 🏪 GTM-01: Marketplace & Discovery

*   [ ] **[GTM-01-1]** GitHub Marketplace Listing — `yamlr/scan-action`
    *   [ ] **Task:** Publish scan action to GitHub Marketplace
    *   [ ] **Subtask:** Add marketplace metadata (icon, categories, verified badge)
    *   [ ] **Subtask:** Write marketplace-optimized README
*   [ ] **[GTM-01-2]** GitHub Marketplace Listing — `yamlr/heal-action`
    *   [ ] **Task:** Publish heal action to GitHub Marketplace
    *   [ ] **Subtask:** Add marketplace metadata + "Surgeon" branding
*   [ ] **[GTM-01-3]** VS Code Marketplace Listing
    *   [ ] **Task:** Package `yamlr-vscode` v1.1.0 as `.vsix` and publish
    *   [ ] **Subtask:** Create marketplace screenshots, icon, and description
    *   [ ] **Subtask:** Configure auto-publish CI workflow
*   [ ] **[GTM-01-4]** Samples/Playground Repo
    *   [ ] **Task:** Create `yamlr/yamlr-playground` with broken K8s manifests
    *   [ ] **Subtask:** Add GH Action that runs yamlr on the repo
    *   [ ] **Subtask:** Write "Try It" section in main README

### 🎬 GTM-02: Activation & Conversion

*   [ ] **[GTM-02-1]** Demo Video (5 min)
    *   [ ] **Task:** Record `yamlr heal .` on real-ish repo with diff + stats
    *   [ ] **Subtask:** Embed in README.md and USER_GUIDE.md
*   [x] **[GTM-02-2]** `--pro-preview` Mode
    *   [x] **Task:** Implement preview of PRO-only fixes without license
    *   [x] **Subtask:** Output diff + upsell CTA: "💎 PRO would fix N more issues"
*   [x] **[GTM-02-3]** PR Comment Summaries
    *   [x] **Task:** Add bot auto-comment to `actions/scan/` with scan summary
    *   [x] **Subtask:** Include health score, issue count, top 3 findings
    *   [ ] **Subtask:** Link to SARIF report if uploaded

### 💳 GTM-03: Revenue Infrastructure

*   [ ] **[GTM-03-1]** Stripe Payment Integration
    *   [ ] **Task:** Integrate Stripe Checkout for Pro license ($15-30/seat/month)
    *   [ ] **Subtask:** `yamlr auth --purchase` opens checkout flow
    *   [ ] **Subtask:** License key delivery via email + local storage
    *   [ ] **Subtask:** License validation in `pro/license.py`
*   [x] **[GTM-03-2]** Time-Saved Estimation in `yamlr status`
    *   [x] **Status:** COMPLETED
    *   [x] **Task:** Add "estimated time saved" metric based on issue complexity
    *   [x] **Subtask:** Display in `yamlr status` output: "⏱️ Est. 4.2 hours saved"
    *   [x] **Subtask:** Optimized performance metrics for Peak Throughput logic.

### 🔬 GTM-04: VS Code Extension Enhancement

*   [ ] **[GTM-04-1]** VS Code Quick-Fix Actions
    *   [ ] **Task:** Add LSP Code Actions to `lsp/server.py`
    *   [ ] **Subtask:** Map healing-eligible diagnostics to quick-fix actions
    *   [ ] **Subtask:** Apply healed content in-editor on click

### 📊 GTM-05: Telemetry & Data Moat

*   [ ] **[GTM-05-1]** Error Corpus Telemetry (Opt-in) 🧊 **Tier 3 (Strategic)**
    *   [ ] **Task:** Implement anonymous telemetry: error types, fix patterns, K8s versions
    *   [ ] **Subtask:** `yamlr init` prompts for opt-in consent
    *   [ ] **Subtask:** No PII collection, compliant with GDPR
*   [ ] **[GTM-05-2]** Team Config Sharing
    *   [ ] **Task:** Support `.yamlr.yaml` inheritance via `extends:` directive
    *   [ ] **Subtask:** Resolve remote configs from git URLs
    *   [ ] **Subtask:** Merge strategy: remote base + local overrides
*   [ ] **[GTM-05-3]** Real-World Adoption Metrics
    *   [ ] **Task:** Track install counts, active users, CI runs
    *   [ ] **Subtask:** GitHub API integration for download/usage stats
    *   [ ] **Subtask:** Simple dashboard or CLI report

---

## ✅ EPIC-13: Codebase Cleanup *(Completed 2026-02-22 — Forensic Verification)*

*   ✅ **[CLEAN-01]** Delete `.bak` Phantom Files *(Verified 2026-02-22)*
    *   [x] **Task:** Confirmed `core/bridge.py.bak` and `analyzers/cross_resource.py.bak` no longer exist anywhere in the repo. `find *.bak` → 0 results.
*   ✅ **[CLEAN-02]** `scanner.py` Decomposition *(Completed 2026-02-17 — see Engineering Quality section below)*
    *   [x] **Task:** `scanner.py` 380-line coordinator + `scanner_identity.py` (193L) + `scanner_heuristics.py` (168L) + `scanner_forensics.py` (104L)
*   ✅ **[CLEAN-03]** `ui/formatter.py` Decomposition *(Completed 2026-02-17 — see Engineering Quality section below)*
    *   [x] **Task:** `formatter.py` 122-line coordinator + `formatter_report.py` (312L) + `formatter_batch.py` (335L)

---

## EPIC-14: Pro Tier Hardening — Critical Bugs (2026-02-15)

*Audit discovered Pro features run without license checks. Revenue-blocking.*

### 🚨 PRO-BUG: License Gating & Phantom Modules

*   ✅ **[PRO-BUG-01]** Pro Flag Gating *(Resolved 2026-02-17 via PRO-NEW-01)*
    *   [x] **Task:** `extract_cli_options()` in `base.py` (L285-312) gates ALL 7 Pro flags
    *   [x] **Subtask:** Gates: `harden`, `enforce_limits`, `enforce_probes`, `fix_tags`, `enforce_namespace`, `check_deprecations`, `fix_refs`
    *   [x] **Subtask:** Calls `YamlrBridge.notify_pro_required()` for polite refusal
    *   [x] **Subtask:** Zeros out all Pro flags for non-Pro users
    *   [x] **Verification:** 9/9 tests pass in `test_fix_refs_pro.py`

*   ✅ **[PRO-BUG-02]** OPA Integration — Demo Mode Fallback (P1)
    *   [x] **Task:** Replace demo-mode fallback with proper "OPA not installed" guidance. (DONE 2026-03-25)
    *   [x] **Subtask:** Remove hardcoded "cost-center" policy from `opa_adapter.py`.
    *   [x] **Subtask:** Add clear error: "Install OPA binary or provide --opa-bundle URL"
    *   [x] **Subtask:** Add built-in enterprise Rego policies in `policies/` directory

*   [/] **[PRO-BUG-03]** Shield Engine — STUB MODULE *(Partially resolved 2026-02-22)*
    *   [x] **Task:** `pro/shield.py` EXISTS (56 lines) — `ShieldEngine` class created
    *   [x] **Subtask:** `calculate_trust_score()` implemented (weighted PHY/KBS/SEM aggregate)
    *   [ ] **Subtask:** `detect_shadow_risks()` is placeholder — returns empty list
    *   [ ] **Subtask:** `verify_integrity()` is placeholder — always returns True
    *   **Note:** `bridge.get_shield()` is NOT dead code — it correctly imports and instantiates `ShieldEngine`

*   ✅ **[PRO-BUG-04]** Exporter — STUB MODULE *(Resolved 2026-03-25)*
    *   [x] **Task:** `pro/exporter.py` EXISTS — `Exporter` class implemented.
    *   [x] **Subtask:** `export_html()` implemented with Glassmorphism templates.
    *   [x] **Subtask:** `export_sarif()` implemented for CI/CD.
    *   **Note:** `bridge.get_exporter()` is NOT dead code — it correctly imports and instantiates `Exporter`

*   ✅ **[PRO-BUG-05]** Auth System — Mock JWT Only (P2) *(Resolved 2026-03-25)*
    *   [x] **Task:** Replace mock JWT generation with real license key validation (RS256).
    *   [x] **Subtask:** Option B: Clerk/Auth0 integration for device flow.
    *   [x] **Subtask:** Implemented `ClerkIdentityService` with secure OIDC polling.

---

## EPIC-15: Pro Feature Expansion — New Revenue Features (2026-02-15)

*Priority order: Wire gates → Build value → Justify enterprise purchase.*

### 💎 PRO-P0: Foundation (Must ship before any Pro revenue)

*   ✅ **[PRO-NEW-01]** Wire the License Gates (P0) *(Completed 2026-02-17)*
    *   [x] **Task:** Add license check to Pro flag paths in `heal.py` and `scan.py`
    *   [x] **Subtask:** Import `YamlrBridge` in both entrypoints
    *   [x] **Subtask:** Check `bridge.is_pro_enabled()` before setting `harden`/`enforce_limits`/`enforce_probes`
    *   [x] **Subtask:** Free users see: "✨ Upgrade to Pro" panel with graceful degradation
    *   [x] **Subtask:** Ensure free `yamlr heal .` (without Pro flags) still works unchanged
    *   [x] **Subtask:** Fixed duplicate `display_report()` bug in `heal.py`
    *   [x] **Verification:** 9/9 tests pass (5 new gating + 4 existing healer)

### 💎 PRO-P1: Core Pro Value (Ship within 2 weeks)

*   ✅ **[PRO-NEW-02]** Cross-Resource AUTO-FIX (P1) *(Completed 2026-02-22 as PRO-12-05)*
    *   [x] **Task:** Pro auto-generates missing stub files for ghost services/orphan refs
    *   [x] **Subtask:** Generate Deployment stub from Service selector (`ServiceSelectorHealer`)
    *   [x] **Subtask:** Generate Service stub from Deployment labels
    *   [x] **Subtask:** Generate ConfigMap/Secret stubs from volume refs (DONE 2026-02-21)
    *   [x] **Subtask:** Wire to `--fix-refs` flag with Pro gate (parser → `CliOptions` → `pipeline.py`)
    *   [x] **Subtask:** PortMismatchHealer Strategy B: named-port fuzzy match (threshold 0.60)
    *   [x] **Verification:** 9/9 tests pass (pro gating + strategy A + strategy B)

*   ✅ **[PRO-NEW-03]** Compliance Report Export (P1) *(Completed 2026-03-25)*
    *   [x] **Task:** Implement `pro/exporter.py` with PDF/HTML report generation.
    *   [x] **Subtask:** SOC2 control mapping (findings → SOC2 criteria).
    *   [x] **Subtask:** CIS Kubernetes Benchmark mapping.
    *   [x] **Subtask:** NSA-CISA hardening guide mapping.
    *   [x] **Subtask:** Severity breakdown chart + remediation timeline.
    *   [x] **Subtask:** Wire to `yamlr scan --export <path>` with Pro gate.

*   ✅ **[PRO-NEW-04]** OPA Production Mode — Policy-as-Code (P1) *(Completed 2026-03-25)*
    *   [x] **Task:** Full OPA integration with remote bundle support.
    *   [x] **Subtask:** Implement `--opa-bundle <url>` flag for remote policy download.
    *   [x] **Subtask:** Add built-in enterprise Rego policies (PCI-DSS, HIPAA, CIS K8s).
    *   [x] **Subtask:** Policy caching (download once, validate offline).
    *   [x] **Subtask:** Custom policy directory support (`--policy-dir ./policies/`).

### 💎 PRO-P2: Category-Defining (Ship within 4 weeks)

*   [ ] **[PRO-NEW-05]** Drift Detection (P2)
    *   [ ] **Task:** Compare live cluster state vs. Git manifests
    *   [ ] **Subtask:** Implement `kubectl get` integration via kubeconfig
    *   [ ] **Subtask:** Diff engine: live state vs. declared state
    *   [ ] **Subtask:** Detect: missing resources, changed fields, orphaned objects
    *   [ ] **Subtask:** Optional auto-heal: `yamlr drift --heal`
    *   [ ] **Subtask:** Wire to `yamlr drift` command with Pro gate

*   [ ] **[PRO-NEW-06]** AI-Assisted Healing Suggestions (P2)
    *   [ ] **Task:** LLM-powered fix suggestions for complex edge cases
    *   [ ] **Subtask:** Local model integration (Ollama/llama.cpp) for offline use
    *   [ ] **Subtask:** Optional API mode for cloud LLM
    *   [ ] **Subtask:** Wire to `--ai-suggest` flag on heal command

*   [ ] **[PRO-NEW-07]** Team Usage Dashboard (P2)
    *   [ ] **Task:** Org-level healing stats and ROI proof
    *   [ ] **Subtask:** Cumulative issues fixed, time saved, trend charts
    *   [ ] **Subtask:** Per-repo health scores
    *   [ ] **Subtask:** HTML/JSON export for executives
    *   [ ] **Subtask:** Wire to `yamlr stats --org` with Pro gate

---

## 🧹 ENGINEERING QUALITY (Completed 2026-02-17)

*   ✅ **[CLEAN-02]** Decompose `scanner.py` (907 → 312 lines + 3 mixins)
    *   [x] **Task:** Extract `IdentityMixin` (`scanner_identity.py`, 193 lines)
    *   [x] **Task:** Extract `HeuristicsMixin` (`scanner_heuristics.py`, 168 lines)
    *   [x] **Task:** Extract `ForensicsMixin` (`scanner_forensics.py`, 104 lines)
    *   [x] **Task:** Rewrite `scanner.py` as slim coordinator (312 lines)
    *   [x] **Verification:** 5/5 gates pass — 38/38 tests, import parity, behavioral hash identical

*   ✅ **[CLEAN-03]** Decompose `formatter.py` (795 → 100 lines + 2 mixins)
    *   [x] **Task:** Extract `ReportMixin` (`formatter_report.py`, 312 lines)
    *   [x] **Task:** Extract `BatchMixin` (`formatter_batch.py`, 335 lines)
    *   [x] **Task:** Rewrite `formatter.py` as slim coordinator (100 lines)
    *   [x] **Verification:** 5/5 gates pass — 38/38 tests, import parity, behavioral hash identical

*   ✅ **[CLEAN-04]** Decompose `base.py` and `formatter_batch.py` (< 500 lines) *(Completed 2026-02-23)*
    *   [x] **Task:** Extract `display.py` from `core/entrypoints/base.py`
    *   [x] **Task:** Extract `formatter_summary.py` from `ui/formatter_batch.py`
    *   [x] **Verification:** Pytest suite passes fully, downstream imports intact

*   ✅ **[CLEAN-05]** Institutional Knowledge Transfer *(Completed 2026-02-23)*
    *   [x] **Task:** Execute AST-based docstring generation for 52 undocumented components
    *   [x] **Subtask:** Ensure 100% Google-style docstring coverage across `core/`, `analyzers/`, `parsers/`, `pro/`
    *   [x] **Verification:** Zero syntax errors injected, M&A due diligence constraint met

---

## 🛡️ EPIC-22: THE STRATEGIC SHIELD (🚧 ACTIVE)
> **Scorecard verdict: TIER 0.** Defensive architecture to protect IP, scale, and valuation.

### 🔹 Feature 22.1: Truth-in-Healing (Phase 1)
*   ✅ **[STORY-22-1]** Sub-System Status Reporting
    *   [x] **Task:** Implement PHY/KBS/SEM status flags in `HealFileResult`.
    *   [x] **Task:** Update UI formatters to show "Structure Repaired (Logic Pending)".
*   ✅ **[STORY-22-2]** HAS Dashboard Integration
    *   [x] **Task:** Surface Scientific HAS scores in `yamlr status`.

### 🔹 Feature 22.3: Robustness & Specs (Phase 2)
*   [ ] **[STORY-22-5]** The Physicist Manifesto
    *   [ ] **Task:** Codify the 14 Physics Rules in `docs/SPECS_PHYSICS.md`.
*   [ ] **[STORY-22-6]** Physics Regression Suite
    *   [ ] **Task:** Create 100+ minimal "Physics Fixtures" for `physicist.py`.

### 🔹 Feature 22.2: Monetization Rebalancing (Phase 3)
*   [x] **[STORY-22-3]** Surgery Migration 💎 PRO
    *   [x] **Task:** Move Map-as-List healing and DNA Reconstruction to `yamlr.pro`.
*   [x] **[STORY-22-4]** Habit Gate Implementation
    *   [x] **Task:** Implement 5-file/day limit for free batch healing.
    *   [x] **Task:** Add "Enterprise Guardrail" for >10 file batch requests.
*   [x] **[PRO-12-06]** `--pro-preview` Demo Mode
    *   [x] **Task:** Implement `yamlr heal . --pro-preview` to simulate PRO healing without writing.
    *   [x] **Task:** Show "Before → After" diff for each PRO-fixable issue.
    *   [x] **Task:** Output upsell CTA at the end of the run.

### 🔹 Feature 22.4: Scaling & Performance (Phase 4)
*   [ ] **[STORY-22-7]** Dual-Core Engine (Yamlr-Light) ⚡ TIER 2
    *   [ ] **Task:** Research/Implement high-speed C-based validator.

---

## 🛡️ EPIC-23: SAFETY ENGINE ARCHITECTURE (✅ COMPLETED 2026-02-28)
> **Scorecard verdict: TIER 0.** Transforms Yamlr from file-level healing to system-level safety intelligence. This is the category-defining architectural shift.

### 🔹 Feature 23.1: ResourceGraph (Foundation Layer)

*   [x] **[TASK-23-1]** ResourceGraph Data Structure *(Completed 2026-02-28)*
    *   [x] **Task:** Created `core/resource_graph.py` (~380L) and modularized edge collectors into `yamlr.core.edges` package.
    *   [x] **Subtask:** Implemented 17 typed edge builders across specialized collectors (`K8sStandardCollector`, `NetworkLogicCollector`, `SecurityPolicyCollector`).
    *   [x] **Subtask:** Added `resource_graph` field to `HealContext` + 4 new `ManifestIdentity` fields
    *   [x] **Gate:** Trust ✅ | Determinism ✅ | Speed ✅ (0.15s for 114 tests)
*   [x] **[TASK-23-2]** Graph Traversal API *(Completed 2026-02-28)*
    *   [x] **Task:** Implemented `dependents()`, `dependencies()`, `blast_radius()`, `critical_path()`
    *   [x] **Subtask:** `BlastRadius` dataclass with affected nodes, depth, risk level
    *   [x] **Tests:** 43 tests in `tests/test_resource_graph.py` — all 17 edge types ✅

### 🔹 Feature 23.2: Impact Propagation Engine

*   [x] **[TASK-23-3]** Risk Classification Model *(Completed 2026-02-28)*
    *   [x] **Task:** Created `analyzers/risk_classifier.py` (~460L) with 15 risk categories, 14 heuristic rules
    *   [x] **Subtask:** Extended `AnalysisResult` with `impact_description`, `scope_count`, `risk_level`, `risk_category`, `affected_resources`, `blast_radius`
    *   [x] **Heuristics:** NetworkPolicy/Image=HIGH, Traffic/Deprecation/Security=HIGH, Orphan=LOW, rest=MEDIUM
    *   [x] **Tests:** 46 tests in `tests/test_risk_classifier.py` ✅

### 🔹 Feature 23.3: Output Reframing

*   ✅ **[TASK-23-4]** Safety-Audit CLI Output *(Completed 2026-02-28)*
    *   [x] **Task:** Update `ui/formatter_report.py` for safety-audit tone (Integrated via `render_upgrade_advisory`)
    *   [x] **Task:** Update `ui/formatter_batch.py` with safety summary section (Integrated via `render_upgrade_advisory`)
    *   [x] **Task:** Decompose `cli/help_formatter.py` (392→165L + 4 modules) *(Completed 2026-02-28)*

### 🔹 Feature 23.4: Version Intelligence Extension

*   [x] **[TASK-23-5]** Full K8s Version Coverage (1.9→1.35 + 1.36 forward-looking) *(Completed 2026-02-28)*
    *   [x] **Task:** Extended `core/deprecations.py` with K8s 1.30–1.35 deprecations
    *   [x] **Subtask:** Added `upgrade_risk_score(from_version, to_version)` method
    *   [x] **Tests:** 26 tests in `tests/test_version_intelligence.py` ✅
*   [x] **[TASK-23-6]** Field-Level Deprecation Tracking *(Completed 2026-02-28)*
    *   [x] **Task:** Added `DEPRECATED_FIELDS` database in `core/deprecations.py`
    *   [x] **Subtask:** `check_field()` method for field-level migration guidance

### 🔹 Feature 23.5: Safety Gate

*   [x] **[TASK-23-7]** Safety Gate Documentation *(Completed 2026-02-28)*
    *   [x] **Task:** Created `docs/SAFETY_GATE.md` — Feature acceptance criteria

---

## 🤝 EPIC-24: COMPLEMENT STRATEGY (✅ COMPLETED)
> **Scorecard verdict: TIER 0.** Position Yamlr as the "Remediation Adapter" for existing policy engines. "They detect; we fix; we prove."

*   [x] **[TASK-24-1]** Kyverno/OPA Report Ingest
    *   [x] **Task:** Implement Kyverno/OPA Report ingestion via `batch_heal`
    *   [x] **Subtask:** Parse Kyverno PolicyReport and OPA ResultSet formats
    *   [x] **Subtask:** Map violations to Yamlr healing actions
    *   [x] **Subtask:** Auto-remediate with DNA proof
*   [ ] **[TASK-24-2]** SARIF Output with Graph Context
    *   [ ] **Task:** Extend SARIF output with `blast_radius` in `relatedLocations`
    *   [ ] **Subtask:** Add dependency chain to each finding's SARIF result
    *   [ ] **Subtask:** GitHub Advanced Security compatibility verification
*   [x] **[TASK-24-3]** Complement Mode
    *   [x] **Task:** Implement `--complement-mode` flag
    *   [x] **Subtask:** Post-process Kubeconform/Checkov JSON output
    *   [x] **Subtask:** Map external findings to Yamlr auto-fix actions
    *   [x] **Subtask:** Output reconciliation report

---

## 🛡️ EPIC-25: STRUCTURAL HARDENING (✅ COMPLETED 2026-02-28)
> **Scorecard verdict: TIER 0.** Internal resilience and configuration hygiene.

### 🔹 Feature 25.1: HealConfig & Pydantic
*   [x] **[TASK-25-1]** Refactor `YamlrEngine` to use `HealConfig` Pydantic model.
*   [x] **[TASK-25-2]** Centralize all analysis/healing flags in `core/context.py`.

### 🔹 Feature 25.2: Telemetry & Performance
*   [x] **[TASK-25-3]** Implement stage-level timing metrics in `PipelineStats`.
*   [x] **[TASK-25-4]** Add `stage_timings` dictionary to UI formatters.

### 🔹 Feature 25.3: Error Resilience
*   [x] **[TASK-25-5]** Eliminate silent failures (except: pass) in `structurer.py`.
*   [x] **[TASK-25-6]** Add explicit logging for schema mismatches in `schema_store.py`.
*   [ ] **[TASK-25-7]** Centralized Logging Configuration 🟢 **Tier 1**
    *   [ ] **Task:** Create `core/logging_config.py` for structured logging.
*   [ ] **[TASK-25-8]** Platform Compatibility Isolation 🟢 **Tier 1**
    *   [ ] **Task:** Move platform-specific logic from `cli/main.py` to `core/platform_compat.py`.
*   [ ] **[TASK-25-9]** Type Precision Hardening 🔵 **Tier 2**
    *   [ ] **Task:** Replace `Any` with `TypedDict` or `Protocol` for catalog/graph structures.
*   [ ] **[TASK-25-10]** Public API Clarity 🟢 **Tier 1**
    *   [ ] **Task:** Enforce `__all__` declarations globally; automate with CI gate.

### 🔹 Feature 25.4: CI/CD & Testing Infrastructure 🟢 **Tier 1** (✅ COMPLETED 2026-03-11)
*   [x] **[TASK-25-11]** Windows CI Pipeline
    *   [x] **Task:** Add Windows testing job to GitHub Actions.
*   [x] **[TASK-25-12]** Test Coverage Enforcement
    *   [x] **Task:** Integrate `pytest-cov` and enforce 75% coverage gate.
*   ✅ **[TASK-25-13]** Performance Regression Gate *(Completed 2026-03-27)*
    *   [x] **Task:** CI failure if `performance_gate.py` (latency) or `benchmark.py` (throughput) regresses.
    *   [x] **Subtask:** Achieved sub-150ms CLI response target (**[VAL-02-1]**).
    *   [x] **Subtask:** Implemented Lazy Loading & Caching (**[VAL-02-4]**).
    *   [x] **Subtask:** Verified `joblib.Parallel` efficiency (**[VAL-02-5]**).
    *   [x] **Subtask:** Benchmark Rust bindings at 150 MB/s (**[VAL-02-6]**).
*   [x] **[TASK-25-14]** Auto-generated API Documentation
    *   [x] **Task:** Implement Sphinx/autodoc for automatic API reference generation.

---

### 🔹 EPIC-24: Complement Strategy (Ecosystem Integration) ✅ COMPLETED
*   ✅ **[TASK-24-1]** Unified Remediation Ingest (`--from-report`)
    *   [x] **Task:** Implement generic report ingestion adapter for OPA/Kyverno.
    *   [x] **Subtask:** Map JSON violation paths to Yamlr SHIELD selectors.
*   ✅ **[TASK-24-2]** SARIF Output with Graph Context
    *   [x] **Task:** Extend SARIF generator to include relational data (`relatedLocations`).
*   ✅ **[TASK-24-3]** Complement Mode (`--complement-mode`)
    *   [x] **Task:** Implement post-processing logic for Checkov/Kubeconform JSON results.
    *   [x] **Subtask:** High-fidelity reconciliation summary panel in CLI.

---

## 🛡️ EPIC-26: A+ SECURITY HARDENING (🚧 ACTIVE)
> **Scorecard verdict: TIER 0.** Resolving "Silent Killers" in authentication, licensing, and I/O. Essential for M&A readiness and enterprise trust.

### 🔹 Feature 26.1: Cryptographic Authentication
*   ✅ **[SEC-26-1]** Asymmetric JWT Signature Verification *(Completed 2026-03-25)*
    *   [x] **Task:** Replace mock `iss` check with RS256 signature validation in `pro/auth.py`.
    *   [x] **Subtask:** Implement public key load from local trust store or `Yamlr_AUTH_PUBLIC_KEY`.
    *   [x] **Subtask:** Update `pro/license.py` to only decode after successful signature verification.

### 🔹 Feature 26.2: Platform-Native Permissions
*   ✅ **[SEC-26-2]** Windows ACL Enforcement (Hardening) *(Completed 2026-03-25)*
    *   [x] **Task:** Use `icacls` to restrict `~/.yamlr` and backups to current user only.
    *   [x] **Subtask:** Implement Windows-native permission enforcement in `core/io/__init__.py`.

### 🔹 Feature 26.3: Advanced Path Traversal Protection
*   ✅ **[SEC-26-3]** Content-Aware "Jail" Enforcement *(Completed 2026-03-25)*
    *   [x] **Task:** Implement `.resolve()` containment checks in `FileSystemManager` and `HardeningEngine`.
    *   [x] **Subtask:** Audit all path access calls for potential bypasses with `..` segments or symlinks.

### 🔹 Feature 26.4: Supply Chain Integrity
*   ✅ **[SEC-26-4]** Automated Dependency Security Audit *(Completed 2026-03-25)*
    *   [x] **Task:** Integrate `pip-audit` into CI pipeline (`.github/workflows/security_audit.yml`).
    *   [x] **Subtask:** Ensure zero high-risk CVEs found in dependencies.



