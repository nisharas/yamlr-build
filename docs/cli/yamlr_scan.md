# yamlr scan
**Read-Only Manifest & Relational Integrity Audit**

The `yamlr scan` command audits Kubernetes manifests against official Kubernetes OpenAPI v3 schemas, relational topology rules, and security best practices.

It operates **100% locally and read-only**—it never modifies files on disk.

---

## Synopsis

```bash
yamlr scan [path] [flags]
```

---

## Examples

```bash
# Audit the current directory
yamlr scan .

# Audit a specific manifest file
yamlr scan deploy.yaml

# Read manifest from stdin via Unix pipeline
cat deployment.yaml | yamlr scan -
kubectl get deployment -o yaml | yamlr scan -

# Audit rendered Helm chart templates in-memory
yamlr scan ./my-chart --helm

# Audit rendered Kustomize overlays in-memory
yamlr scan ./overlays/prod --kustomize

# CI/CD Gate: Fail build if any errors are detected
yamlr scan . --fail-on error

# Generate SARIF 2.1.0 report for GitHub Security code scanning
yamlr scan . --output sarif -f results.sarif

# Emit machine-readable JSON report
yamlr scan . --output json -f scan-report.json

# Target a specific Kubernetes schema version
yamlr scan . --k8s-version 1.31

# Ingest custom CRDs for schema validation
yamlr scan . --crd ./crds/cert-manager.yaml

# Continuous live monitoring during local development
yamlr scan . --watch
```

---

## Options & Flags

### Primary Options

*   **`path`** *(positional, optional)*:
    Path to manifest file, directory, or `-` for stdin. Defaults to `.`.
*   **`--output {text,sarif,json}`**:
    Output format. Defaults to `text` (rich colorized terminal report).
    * `text`: Colorized ASCII tables, integrity scores, and actionable remediation commands.
    * `sarif`: OASIS SARIF 2.1.0 JSON format for GitHub Security Code Scanning tab.
    * `json`: Structured JSON containing file-by-file AST violations and forensic metadata.
    When writing JSON or SARIF to stdout, stdout contains only the report. Progress messages, diagnostics, and optional metrics are written to stderr. With `--output-file`, the report is written to that file and status messages go to stderr.
*   **`-q, --quiet`**:
    Quiet execution. Suppresses decorative banners and tables; emits only violations and exit codes.
*   **`-w, --watch`**:
    Continuously watch the target path for file modifications and re-execute the audit automatically.

### Targeting & Environment

*   **`--k8s-version, --kube-version <VERSION>`**:
    Target Kubernetes OpenAPI schema version (e.g. `1.28`, `1.30`, `1.31`).
    Supports Kubernetes v1.21 through v1.37+ forward compatibility.
*   **`--crd <PATH>`**:
    Path to custom CRD definitions (file or directory) to ingest into the active schema validator.
    Supported supplied schemas retain object/array structure, primitive types,
    required properties, and string property enums. Constraints that the distilled
    validator cannot enforce are rejected during ingestion, including range/length
    limits, patterns/formats, references/combinators, nullable values, restrictive
    additional properties, and Kubernetes CEL/list extensions. The diagnostic names
    the unsupported keyword and schema path; the scan is incomplete and nonzero,
    including with `--exit-zero`. This does not establish full OpenAPI validation
    for the bundled Kubernetes schemas.
*   **`--helm`**:
    Render and audit Helm chart templates in-memory without requiring a running cluster.
*   **`--kustomize`**:
    Render and audit Kustomize overlays in-memory without disk side-effects.

### Directory traversal

When `path` is a directory, scan walks its subdirectories and processes regular files whose extensions are `.yaml` or `.yml`. It does not apply implicit directory exclusions or ignore-file rules, so generated or vendored YAML beneath the target is included unless you choose a narrower target directory. Recursive traversal does not follow symbolic links; a symbolic-link entry inside the tree is skipped. Passing a file path directly scans that file.

Traversal and file-read failures are reported and make the scan return a nonzero status; they are not treated as clean results. Helm template traversal additionally accepts `.tpl` files.

When a scan cannot finish, JSON output reports `status: "error"`, `complete: false`, and an `errors` array containing the target and diagnostic (including the failed file when available). SARIF output sets `invocations[].executionSuccessful` to `false` and records an error notification. A requested output file is replaced with the failure report, so an older successful report cannot be mistaken for this run. `--exit-zero` suppresses findings-based failure only; it never suppresses traversal or read failures.

### CI/CD & Pipeline Integration

*   **`--fail-on {error,warning,note}`**:
    Exit with code `1` if violations of the specified severity or higher are found. Ideal for CI gating.
*   **`-f, --output-file <PATH>`**:
    File path to write the report output (`.sarif` or `.json`).
*   **`--exit-zero`**:
    Force exit code `0` regardless of discovered violations. Useful for non-blocking informational CI steps.
*   **`--push-telemetry`**:
    Explicitly send an Enterprise-only scan-completion event to the Yamlr gateway. The event contains only the CLI version, event type, and timestamp; scan paths, manifests, and findings are not sent. Requests time out after five seconds and never change the scan result. Set `YAMLR_TELEMETRY_GATEWAY_URL` to an HTTPS gateway base URL to override the default. `--no-telemetry`, `YAMLR_TELEMETRY=off`, and `DO_NOT_TRACK=1` suppress the request.
*   **`--otel` / `--export-metrics`**:
    Emit Prometheus/OpenMetrics scan metrics to stderr so JSON and SARIF report output remains machine-readable.

---

## Exit Codes

*   **`0`** (`EXIT_SUCCESS`): All manifests are clean and valid (or `--exit-zero` is active).
*   **`1`** (`EXIT_VIOLATIONS`): Schema or relational integrity violations found (triggered by `--fail-on`).
*   **`2`** (`EXIT_SYNTAX_ERROR`): Malformed input, including CRD/schema ingestion failure.
*   **`3`** (`EXIT_CONFIG_ERROR`): Invalid CLI arguments.
*   **`4`** (`EXIT_SYSTEM_ERROR`): File I/O failure or permission error.
