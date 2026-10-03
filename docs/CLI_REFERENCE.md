# 📖 Yamlr CLI Reference

This is the definitive reference for all `yamlr` CLI commands, flags, and their intended usage. All commands are designed to be fast, deterministic, and safe across any Kubernetes environment (AWS EKS, Google Cloud GKE, Azure AKS, Red Hat OpenShift, Talos, KinD, and bare-metal).

---

## 🛠 Basic Commands (Core 6)

The Core 6 commands represent the primary developer lifecycle: pre-flight diagnostics, manifest scanning, diff preview, comment-preserving remediation, workspace health, and build provenance.

### 1. `scan`
**Purpose:** Audit manifests for schema compliance, relational integrity, and best practices.
- **Usage:** `yamlr scan [path] [flags]`
- **Argument Groups:**
  - **Primary Options:**
    - `path`: Path to manifest file, directory, or `-` for stdin (default: `.`).
    - `--output {text,json,sarif}`: Target report format (default: `text`).
    - `-q, --quiet`: Suppress non-essential output for quiet shell execution.
    - `-w, --watch`: Continuously poll workspace and automatically re-scan on file modifications.
  - **Targeting & Environment:**
    - `--k8s-version VERSION`: Target Kubernetes schema version (e.g., `1.30`, `1.31`). Supports v1.21-v1.37+.
    - `--crd PATH`: Ingest custom CRD definitions for dynamic schema resolution.
    - `--helm`: Audit rendered Helm chart templates in-memory.
    - `--kustomize`: Audit rendered Kustomize overlay resources in-memory.
  - **CI/CD & Pipeline Integration:**
    - `--fail-on {error,warning,note}`: Exit with code 1 if violations of specified severity or higher are found.
    - `-f, --output-file PATH`: Write report directly to file (SARIF or JSON).
    - `--exit-zero`: Always exit with code 0 for non-blocking CI warning stages.
    - `--push-telemetry`: Push anonymous ROI and health telemetry to configured gateway.

### 2. `heal`
**Purpose:** Remediate supported violations while preserving source context where the transformation permits. Review and validate proposed changes.
- **Usage:** `yamlr heal [path] [flags]`
- **Argument Groups:**
  - **Primary Remediation Options:**
    - `path`: Path to manifest file, directory, or `-` for stdin (default: `.`).
    - `--apply`: Apply fixes directly to manifests on disk (Default: Preview).
    - `--diff`: Display inline side-by-side AST diff of proposed mutations.
    - `--dry-run`: Show forensic impact and remediations without writing to disk.
  - **Targeting & Environment:**
    - `--k8s-version VERSION`: Target Kubernetes schema version (e.g., `1.30`, `1.31`).
    - `--crd PATH`: Path to custom CRD definitions for schema-aware healing.
    - `--helm`: Audit & heal Helm values in-memory.
    - `--kustomize`: Audit & heal Kustomize overlays in-memory.
  - **Policy & Tool Ingestion:**
    - `--ingest-opa PATH`: Ingest Open Policy Agent (OPA) Gatekeeper JSON violations and execute automated fixes.
    - `--ingest-kyverno PATH`: Ingest Kyverno PolicyReport JSON findings and execute automated fixes.
  - **CI/CD & Pipeline Integration:**
    - `-f, --output-file PATH`: Write remediation report to file (SARIF or JSON).
    - `--exit-zero`: Always exit with code 0.
    - `--push-telemetry`: Push anonymous ROI data to global dashboard.

### 3. `diff`
**Purpose:** Preview proposed remediations and schema alignments without modifying files on disk.
- **Usage:** `yamlr diff [path] [flags]`
- **Argument Groups:**
  - **Primary Diff Options:**
    - `path`: Path to manifests (default: `.`).
    - `-u, --unified`: Display unified diff format instead of side-by-side.
  - **Targeting & Environment:**
    - `--k8s-version VERSION`: Target Kubernetes schema version (e.g., `1.30`, `1.31`).
    - `--crd PATH`: Ingest custom CRD definitions for dynamic schema resolution.
    - `--helm`: Preview diff for rendered Helm chart templates in-memory.
    - `--kustomize`: Preview diff for rendered Kustomize overlay resources in-memory.
  - **CI/CD & Pipeline Integration:**
    - `-f, --output-file PATH`: Write forensic diff report to file (SARIF or JSON).
    - `--exit-zero`: Always exit with code 0 for non-blocking CI preview steps.

### 4. `doctor`
**Purpose:** Perform local environment diagnostics, schema cache verification, and toolchain checks.
- **Usage:** `yamlr doctor [flags]`
- **Argument Groups:**
  - **Diagnostic Options:**
    - `--fix`: Automatically download missing schemas and repair local configuration drift.
  - **Targeting & Environment:**
    - `--k8s-version VERSION`: Target Kubernetes version to diagnose (e.g., `1.30`, `1.31`).
    - `--crd PATH`: Validate specific CRD manifests against the engine parser.

### 5. `status`
**Purpose:** Display engine health, schema cache status, machine identifier, and workspace metadata.
- **Usage:** `yamlr status [flags]`
- **Argument Groups:**
  - **Primary Options:**
    - `--output {text,json}`: Output format (human-readable panel or structured JSON). Default: `text`.
  - **CI/CD & Pipeline Integration:**
    - `-f, --output-file PATH`: Path to write report (JSON).
    - `--exit-zero`: Always exit with code 0 (for non-blocking CI pipelines).

### 6. `version`
**Purpose:** Display CLI release version, native PyO3 engine build, Rust toolchain metadata, and active schema catalogue.
- **Usage:** `yamlr version [flags]`
- **Argument Groups:**
  - **Primary Options:**
    - `--output {text,json}`: Output format (human-readable or structured JSON). Default: `text`.
  - **CI/CD & Pipeline Integration:**
    - `-f, --output-file PATH`: Path to write report (JSON).
    - `--exit-zero`: Always exit with code 0 (for non-blocking CI pipelines).

---

## 📦 Ecosystem & Integration Commands

### `fmt`
**Purpose:** Canonical Kubernetes manifest formatter (k8sfmt / yamlfix).
- **Usage:** `yamlr fmt [path...] [-w]`
- **Flags:**
  - `-w, --write`: Write formatted output back to source file in-place (default prints to stdout).
- **Pipe Mode:** Supports streaming stdin/stdout: `helm template my-chart | yamlr fmt -`
- **Canonical Ordering:** Enforces authoritative Kubernetes field hierarchy:
  `apiVersion` -> `kind` -> `metadata` -> `spec` -> `data` -> `status`.

### `fix`
**Purpose:** Canonical zero-configuration auto-repair (alias to `yamlr heal --apply`).
- **Usage:** `yamlr fix [path...]`
- **Description:** Automatically remediates deprecated API versions, missing labels, and schema issues with zero configuration flags required.

### `help`
**Purpose:** Display precision help and command registry.
- **Usage:** `yamlr help [topic] [--all]`

### `install`
**Purpose:** Install Git hooks or continuous integration workflow templates.
- **Usage:** `yamlr install {hook,action}`

### `completion`
**Purpose:** Generate shell autocompletion scripts.
- **Usage:** `yamlr completion {bash,zsh}`

### `mcp`
**Purpose:** Start the Model Context Protocol (MCP) server for IDE and editor integrations.
- **Usage:** `yamlr mcp`
- **Description:** Exposes a standardized Model Context Protocol (MCP) server over stdio for editor extensions and development tooling to execute manifest validation and remediation.

### `lsp`
**Purpose:** Start the Language Server Protocol (LSP) server for real-time editor diagnostics.
- **Usage:** `yamlr lsp`

### `init`
**Purpose:** Initialize a new Yamlr workspace configuration file (`.yamlr.yaml`).
- **Usage:** `yamlr init [path]`

---

## 🌐 Intelligence & Enterprise Commands

### `graph`
**Purpose:** Visualize and query resource relationships, dependencies, and blast radius.
- **Usage:** `yamlr graph [path] [--focus RESOURCE]`

### `pulse`
**Purpose:** Real-time manifest integrity monitoring and health trends.
- **Usage:** `yamlr pulse [path]`

### `drift`
**Purpose:** Reconcile live cluster state against source of truth.
- **Usage:** `yamlr drift [path]`

### `audit`
**Purpose:** Fleet-wide cross-resource analysis and topological scoring.
- **Usage:** `yamlr audit [path]`

### `dna`
**Purpose:** Generate immutable semantic integrity signatures for manifests.
- **Usage:** `yamlr dna [path]`

### `roi` | `impact`
**Purpose:** Calculate manifest engineering quality and reliability impact metrics.
- **Usage:** `yamlr roi [path] [--output {text,json}]`

### `secure`
**Purpose:** Apply autonomous security hardening policies (PSS, SecurityContext).
- **Usage:** `yamlr secure [path]`

### `rollback` | `restore`
**Purpose:** Atomic reversal of the last remediation session.
- **Usage:** `yamlr rollback [path]`

### `evidence`
**Purpose:** Collect and package cryptographic audit evidence bundles.
- **Usage:** `yamlr evidence [path]`

### `sign` & `verify`
**Purpose:** Cryptographically sign manifests and verify against DNA baseline receipts.
- **Usage:** `yamlr sign [path]` / `yamlr verify [path]`

### `fleet`
**Purpose:** Multi-repository GitOps Pull Request batching and fleet upgrade automation.
- **Usage:** `yamlr fleet [status|pr-batch] [flags]`

### `migrate` | `upgrade`
**Purpose:** Automated API version migration across Kubernetes releases.
- **Usage:** `yamlr migrate [path] [--to-k8s VERSION] [--apply]`

---

## 🔄 GitOps & CI/CD Integrations

### Pre-Commit Hooks (`.pre-commit-hooks.yaml`)
Integrates Yamlr into local Git workflows to prevent unformatted or invalid manifests from being committed:
- `yamlr-fmt`: Automatically canonicalizes manifest keys and 2-space indentation on staged files before commit (`yamlr fmt -w`).
- `yamlr-fix`: Automatically resolves deprecated APIs, floating tags, and schema issues before commit (`yamlr fix`).
- `yamlr-scan`: Read-only gatekeeper audit exiting with code 1 on errors (`yamlr scan --fail-on error`).
- `yamlr-heal`: Multi-resource in-place remediation (`yamlr heal --apply`).

### GitHub Action (`action.yml`)
Run Yamlr natively in GitHub Actions with optional automated commits:
```yaml
- uses: yamlr-dev/yamlr@v0.1.0
  with:
    command: fix        # Options: scan, fmt, fix, heal
    autocommit: true    # Automatically push repairs back to the branch
```
