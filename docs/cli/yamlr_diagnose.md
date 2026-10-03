# yamlr diagnose

**Verbose Diagnostics & Debugging**

The `diagnose` command is a wrapper for `yamlr scan` with elevated logging levels turned on by default. Use this when `yamlr scan` fails mysteriously or when you need to understand *why* a file is being ignored or flagged.

## Usage
```bash
yamlr diagnose [PATH]...
```

## Description
Runs a standard scan but prints debug logs to stderr.
- **Enables**: `LOG_LEVEL=DEBUG`
- **Shows**: File discovery paths, Ignore pattern matching, Lexer token streams (partial), Parser decisions.

## Examples

**Debug a file being ignored:**
```bash
yamlr diagnose ignored_file.yaml
# Output will show: "DEBUG: Skipping file due to .yamlr.yaml ignore pattern..."
```

**Trace Parser Errors:**
```bash
yamlr diagnose broken.yaml
```

## Flags
*   **`--bundle`**: [PRO] Export an anonymized, founder-ready support zip containing metadata and engine states.
*   `-h, --help`: Show this help message.

### Universal Expert Flags
These flags are available across almost all primary Yamlr commands:

*   **`--output FORMAT`**: Report format (text, json).
*   **`--kube-version <V>`**: Force a specific Kubernetes version (e.g., `1.31`).
*   **`--max-depth <N>`**: Limit recursive scanning depth (Default: 10).
*   **`--ext <list>`**: Comma-separated list of file extensions (Default: `.yaml,.yml`).
*   **`--concurrency <N>`**: Number of parallel worker processes.
*   **`--strict`**: Treat all schema warnings as hard errors.
*   **`--compact`**: Use minimal whitespace (2-space indent) in output.
*   **`--health-threshold <0-100>`**: Minimum score to pass (Default: 70).
*   **`--namespace <name>`**: Default namespace for generated resources.
*   **`--check-deprecations`**: Audit for and record deprecated K8s APIs.
*   **`--cpu-limit <limit>`**: Default CPU for auto-injection (e.g., `500m`).
*   **`--mem-limit <limit>`**: Default Memory for auto-injection (e.g., `512Mi`).
*   **`--enforce-limits`**: Auto-inject missing CPU/Memory limits.
*   **`--enforce-probes`**: Auto-inject missing Liveness/Readiness probes.
*   **`--enforce-namespace`**: Auto-inject default namespace if missing.
*   **`--fix-tags`**: Auto-remediate `:latest` or missing image tags.
*   **`--harden`**: Apply security hardening (Non-root, Read-only FS).
*   **`--stream-to <FILE>`**: Batch-mode: Stream results to NDJSON (prevents RAM saturation).
*   **`--fail-on <CHOICE>`**: Exit 1 if specified severity found (error/warning/any).
*   **`--summary-only`**: Show aggregate stats only (recommended for 100+ files).
*   **`--plain`**: ASCII-only output mode (Recommended for Log redirection).
*   **`--verbose`**: Show full audit logs and engine stages.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   `-q`, `--quiet`: Minimal output mode (CI/CD optimized; errors and exit codes only).
*   **`--identity-mode {infer,strict}`**: Control how Yamlr identifies resources (Default: infer).
