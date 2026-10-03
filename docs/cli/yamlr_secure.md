# yamlr secure
**Analyze & suggest security hardening (Pro)**

The `yamlr secure` command is a specialized wrapper around the healing engine designed to **analyze and suggest security hardening** for your Kubernetes manifests.

It enforces a "Secure by Default" posture aligned with the Kubernetes **Pod Security Standards (Restricted)** profile.

## Usage

```bash
# Audit and propose security fixes
yamlr secure ./manifests

# Apply security fixes immediately
yamlr secure ./manifests --yes
```

## What It Enforces

When you run `yamlr secure`, the engine attempts to inject the following configurations if they are missing or insecure:

### 1. Non-Root Execution
Ensures containers do not run as root (UID 0).
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000  # Injected default if missing
```

### 2. Read-Only Root Filesystem
Prevents attackers from modifying the container's filesystem at runtime.
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

### 3. Capability Dropping
Drops all Linux capabilities by default, adding back only what is strictly necessary (NET_BIND_SERVICE, etc.).
```yaml
securityContext:
  capabilities:
    drop: ["ALL"]
```

### 4. Privilege Escalation Prevention
Prevents a process from gaining more privileges than its parent.
```yaml
securityContext:
  allowPrivilegeEscalation: false
```

## Limitations
*   `yamlr secure` is a **Best-Effort** tool. It cannot know if your specific application *requires* root access to function.
*   **Testing Required:** Always test your application in a staging environment after applying security hardening.

### Universal Expert Flags
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
*   **`--canonical`** [Pro]: Enable high-fidelity canonical export with comment grafting and schema-aware sorting.
*   **`--stream-to <FILE>`**: Batch-mode: Stream results to NDJSON (prevents RAM saturation).
*   **`--fail-on <CHOICE>`**: Exit 1 if specified severity found (error/warning/any).
*   **`--summary-only`**: Show aggregate stats only (recommended for 100+ files).
*   **`--plain`**: ASCII-only output mode (Recommended for Log redirection).
*   **`--verbose`**: Show full audit logs and engine stages.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   `-q`, `--quiet`: Minimal output mode (CI/CD optimized; errors and exit codes only).
*   **`--identity-mode {infer,strict}`**: Control how Yamlr identifies resources (Default: infer).
