# yamlr scan
**Local Analysis & Read-Only Audit**

The `yamlr scan` command is the core auditing engine. It performs deep analysis **100% locally**:
1.  **Syntax & Structure**: Checks for valid YAML and basic Kubernetes fields.
2.  **Schema Validation**: Validates against K8s API schemas (strict typing).
3.  **Policy Enforcement (OPA)**: Runs custom Rego policies.
4.  **Scientific Benchmarking**: Measures healing accuracy (HAS).

## Usage

```bash
# Basic Audit (1,000+ files/sec)
yamlr scan .

# Audit a specific target K8s version
yamlr scan . --kube-version 1.31

# CI/CD Gate: Fail if any errors found
yamlr scan . --fail-on error

# GitOps Guard: Ignore existing violations from baseline
yamlr scan . --baseline .yamlr-baseline.json
```

## Advanced Features

### 1. Identity Mode (`--identity-mode`)
Yamlr uses AI-like heuristics ("Brain") to identify resources even if `apiVersion` or `kind` is missing.
*   `--identity-mode=infer` (Default): Attempts to identify broken resources.
*   `--identity-mode=strict`: Skips any file that doesn't strictly declare `apiVersion` and `kind`.

### 2. OPA Policy Engine (`--opa-bundle`)
Yamlr embeds a full Open Policy Agent engine.
```bash
# Use local Gatekeeper ConstraintTemplates
yamlr scan . --opa-bundle ./gatekeeper/templates/
```

### 3. Output Formats (`--output`)
*   `--output=text` (Default): Human-readable table.
*   `--output=json`: Full structured report.
*   `--output=sarif`: GitHub Security format.

### 4. Enterprise Compliance & Integrity
*   **`--receipt`**: Generate a cryptographic DNA receipt for this scan.
*   **`--baseline <FILE>`**: Path to violation baseline (SHA-256 fingerprints to ignore).
*   **`--kyverno-report <PATH>`**: [PRO] Ingest Kyverno reports for investigation.
*   **`--from-report <PATH>`**: [PRO] Unified Ingest: OPA or Kyverno JSON remediation.
*   **`--complement-mode <T:P>`**: [PRO] Reconciliation Mode: Ingest findings from tools (checkov, kubeconform).
*   **`--opa-bundle <PATH|URL>`**: [PRO] Path to OPA bundle or Gatekeeper templates.

### 5. Performance & Scaling
*   **`--fast`** [PRO]: Enable lightning-fast scanning via native Rust extension (10x faster).
*   **`--concurrency <N>`**: Force parallel worker count (Defaults to CPU count).
*   **`--stream-to <FILE>`**: Batch-mode: Stream results to NDJSON (prevents RAM saturation).

### 6. Advanced Observability & Simulation
*   **`--emulate <TOOL>`**: Simulate sidecar containers (e.g., `istiod`, `linkerd`) during local analysis to reduce false negatives.
*   **`--shadow`**: [EXPERIMENTAL] Capture dynamic server-side mutations using a Kubernetes dry-run shadowing technique.
*   **`--patch`**: Instead of full output, generate a `yamlr-patches.yaml` containing just the remediation fragments.
*   **`--clinical`**: [SURGICAL] Redirect all visual/UI terminal logs to `stderr` while keeping `stdout` reserved for pure YAML. Ideal for ArgoCD/GitOps pipelines.

### 🛡 Universal Expert Flags
These flags are available across almost all primary commands:

*   **`--kube-version <V>`**: Force a specific Kubernetes version (e.g., `1.31`).
*   **`--risk-threshold <high|medium|low>`**: Exit with code 1 if any finding meets or exceeds this risk level.
*   **`--fail-on <CHOICE>`**: CI/CD Gate: Exit 1 if specified severity found (any/warning/error).
*   **`--max-depth <N>`**: Limit recursive scanning depth (Default: 10).
*   **`--ext <list>`**: Comma-separated list of file extensions (Default: `.yaml,.yml`).
*   **`--strict`**: Treat all schema warnings as hard errors.
*   **`--compact`**: Use minimal whitespace (2-space indent) in output.
*   **`--health-threshold <0-100>`**: Minimum score to pass (Default: 70).
*   **`--namespace <name>`**: Default namespace for generated resources.
*   **`--check-deprecations`**: Audit for and record deprecated K8s APIs.
*   **`--summary-only`**: Show aggregate stats only (recommended for 100+ files).
*   **`--plain`**: ASCII-only output mode (Recommended for Log redirection).
*   **`--verbose`**: Show full audit logs and engine stages.
*   **`-q`, `--quiet`**: Minimal output mode (exit codes only).
*   **`--diff` / `--dry-run`**: Show proposed fixes as a preview.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
