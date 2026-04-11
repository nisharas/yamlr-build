# yamlr upgrade
**✅ FREE / OSS**

The `yamlr upgrade` command is a specialized wrapper around the healing engine designed for **Kubernetes API Version Migrations**.

It helps you move from deprecated APIs (e.g., `extensions/v1beta1`) to modern stable APIs (e.g., `apps/v1`) while preserving your application's logic.

## Usage

```bash
# Upgrade to match the version of your currently connected cluster
yamlr upgrade ./manifests

# Upgrade to a specific target version
yamlr upgrade ./manifests --to 1.30
```

## How It Works

### 1. Forward-Only Guarantee
`yamlr upgrade` is strictly **Forward-Only**.
*   **If your manifest is older than the target:** It upgrades it.
*   **If your manifest is equal to or newer:** It does nothing (Green/Pass).
*   **It NEVER downgrades.** You cannot use this tool to revert to an older API version.

### 2. Structural Reconstruction
Unlike `sed` or `grep` replacements, Yamlr parses the object into a semantic model and reconstructs it.
*   **Fixes Structure:** It adds standard fields that are required in newer versions (e.g., `spec.selector` for Deployments).
*   **Preserves Comments:** It strives to keep your YAML comments intact.

### 3. Safety First
By default, `yamlr upgrade` runs in **Preview Mode** (dry-run).
*   It shows a diff of what *would* change.
*   To apply changes, you must pass `--yes` or answer "y" in the prompt.

## Examples

### Upgrading a Deployment
**Input (Old):**
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: my-app
```

**Output (New - Target v1.30):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:             # <--- Injected automatically
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
```

### 🛡 Universal Expert Flags
These flags are available across almost all primary Yamlr commands:

*   **`--output FORMAT`**: Report format (text, json).
*   **`--dry-run`**: Show proposed changes without writing (Preview mode).
*   **`--diff`**: Show visual diff of changes (Preview mode).
*   **`--fast`**: Skip heavy semantic analysis for maximum speed.
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
*   **`--sovereign`** [Pro]: Enable high-fidelity sovereign export with comment grafting and schema-aware sorting.
*   **`--stream-to <FILE>`**: Batch-mode: Stream results to NDJSON (prevents RAM saturation).
*   **`--fail-on <CHOICE>`**: Exit 1 if specified severity found (error/warning/any).
*   **`--summary-only`**: Show aggregate stats only (recommended for 100+ files).
*   **`--plain`**: ASCII-only output mode (Recommended for Log redirection).
*   **`--verbose`**: Show full audit logs and engine stages.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   `-q`, `--quiet`: Minimal output mode (CI/CD optimized; errors and exit codes only).
*   **`--identity-mode {infer,strict}`**: Control how Yamlr identifies resources (Default: infer).
