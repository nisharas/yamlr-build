# yamlr heal
**Propose Repairs (Safe-by-default)**

The `heal` command is the core of Yamlr. It proposes repairs for syntax errors, schema violations, and logic issues in your Kubernetes manifests.

## Usage
```bash
yamlr heal [PATH]... [FLAGS]
```

## Description
Scans target files and applies fixers.
*   **Interactive Mode**: Prompts before writing unless `-y` is used.
*   **Atomic Writes**: Prevents data loss during writes.
*   **Backups**: Created in `.yamlr/backups/` automatically.
*   **Trauma Healing** [Pro]: Structural "Type Trauma" repair.
*   **Referential Alignment**: Fixes broken ConfigMap/Secret/PVC references.

> [!IMPORTANT]
> **Free Tier Healing Limits**
> Limited to **5 files per day**. `yamlr scan` remains 100% free and unlimited!

## Key Flags

### Automation
*   `-y, --yes`: Auto-approve changes for single files.
*   `--yes-all`: Auto-approve changes for batch mode.
*   `--dry-run` / `--diff`: Preview changes without writing.

### Surgical Injection
*   **`--enforce-limits`**: Inject standard CPU/RAM requests & limits.
*   **`--enforce-probes`**: Inject default Liveness/Readiness probes.
*   **`--enforce-namespace`**: Auto-inject default namespace if missing.
*   **`--fix-tags`**: Auto-remediate `:latest` or missing image tags.

### Enterprise Remediations (PRO)
*   **`--fix-refs`**: Cross-Resource Auto-Fix (Selectors, Ports, Stubs).
*   **`--complement-mode <T:P>`**: [RECON] Ingest findings from tools (checkov, kubeconform).
*   **`--receipt`**: Generate DNA-signed compliance receipts.
*   **`--evidence-dir <DIR>`**: Directory to save DNA receipts for audits.
*   **`--adapters-dir <DIR>`**: Directory for custom remediation adapters.
*   **`--rollback`**: Atomic Reversal: Undo the current session on failure.
*   **`--clinical`**: Redirect UI logs to `stderr` for clean `stdout` in GitOps.

### Advanced
*   **`--unsafe`**: Allow healing of sensitive resources like `Secret`.
*   **`--no-backup`**: Skip creation of `.yamlr/backups/` (Dangerous).
*   **`--pro-preview`**: Enterprise Demo Mode (Dry-run only).

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--kube-version <V>`**: Force specific K8s version (e.g., `1.31`).
*   **`--risk-threshold <high|medium|low>`**: Exit with code 1 if any finding meets or exceeds risk level.
*   **`--fail-on <CHOICE>`**: CI/CD Gate: Exit 1 if specified severity found (any/warning/error).
*   **`--baseline <FILE>`**: Path to violation baseline (SHA-256 fingerprints to ignore).
*   **`--fast`** [PRO]: Enable lightning-fast scanning via native Rust extension.
*   **`--max-depth <N>`**: Limit recursion depth (Default: 10).
*   **`--ext <list>`**: Extensions to scan (Default: `.yaml,.yml`).
*   **`--concurrency <N>`**: Parallel worker processes.
*   **`--strict`**: Treat warnings as hard errors.
*   **`--compact`**: Minify output (2-space indent).
*   **`--health-threshold <0-100>`**: Min score to pass (Default: 70).
*   **`--namespace <name>`**: Default namespace for generated resources.
*   **`--check-deprecations`**: Audit for and record deprecated APIs.
*   **`--cpu-limit <limit>`**: Default CPU for auto-injection.
*   **`--mem-limit <limit>`**: Default Memory for auto-injection.
*   **`--enforce-namespace`**: Auto-inject namespace.
*   **`--stream-to <FILE>`**: Stream results to NDJSON.
*   **`--summary-only`**: Aggregate stats only.
*   **`--plain`**: ASCII-only output.
*   `--verbose`: Full audit logs.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   `-q`, `--quiet`: Minimal output mode.
