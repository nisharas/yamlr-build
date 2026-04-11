# yamlr migrate
**✅ FREE / OSS**

**Kubernetes API Migration (Alias for [upgrade](yamlr_upgrade.md))**

The `migrate` command is an alias for `yamlr upgrade`. It is used to transform manifests from deprecated or stale API versions to modern, stable ones.

## Usage
```bash
yamlr migrate --to [VERSION] [PATH]...
```

## Description
Performs the same structural reconstruction and API versioning upgrades as `yamlr upgrade`.

For a full list of features, flags, and examples, please refer to the [yamlr upgrade](yamlr_upgrade.md) manual.

### Options
*   **`--dry-run`**: Show proposed changes without writing.
*   **`--diff`**: Show visual diff.
*   **`-y`, `--yes`**: Auto-confirm changes.
*   **`--output FORMAT`**: Report format.
*   **`--kube-version <V>`**: Force a specific Kubernetes version (alias: **`--k8s-version <V>`**).
*   **`--max-depth <N>`**: Limit recursion depth.
*   **`--ext <list>`**: Extensions to scan (default: `.yaml,.yml`).
*   **`--concurrency <N>`**: Number of parallel worker processes.
*   **`--verbose`**: Detailed execution logs.
*   **`-s`, `--summary-only`**: Show aggregate stats.
*   **`-p`, `--plain`**: ASCII-only output mode.
*   **`--identity-mode {infer,strict}`**: Identity detection style.
*   **`-q`, `--quiet`**: Minimal output.
*   **`--strict`**: Enable strict schema validation.
*   **`--compact`**: Output with minimal whitespace.
*   **`--cpu-limit L`**: Override default CPU limit.
*   **`--mem-limit L`**: Override default Memory limit.
*   **`--namespace NS`**: Default namespace.
*   **`--health-threshold N`**: Min score to consider Healthy.
*   **`--enforce-limits`**: Auto-inject limits.
*   **`--enforce-probes`**: Auto-inject probes.
*   **`--enforce-namespace`**: Auto-inject namespace.
*   **`--fix-tags`**: Auto-remediate tags.
*   **`--harden`**: Apply hardening.
*   **`--stream-to FILE`**: Stream results.
*   **`--fail-on CHOICE`**: CI/CD Gate.
*   **`--check-deprecations`**: Check for deprecated APIs.
