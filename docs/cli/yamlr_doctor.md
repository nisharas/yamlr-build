# yamlr doctor

**Brutally fast health check: Runtime, Catalog, Cluster & Pro status**

The `doctor` command runs a suite of diagnostic tests to ensure your Yamlr Healing Engine and its environment are healthy and functioning correctly.

## Usage
```bash
yamlr doctor [FLAGS]
```

## Description
Verifies:
*   Python Runtime Version Checks
*   Pro Engine Entitlements
*   K8s Catalog Matrices and Integrity

## Key Flags
*   **`--k8s-matrix`**, **`--k8s`**: Validate K8s matrix support externally and deterministically against the bundled catalog. Prints timestamps and SHA-256 integrity hashes for the default bundle.
*   **`--k8s-matrix-strict`**: Validates the K8s matrix and exits non-zero (`exit 1`) if any claimed catalog bundle is missing or stale. Ideal for CI/CD gating.
*   **`--output FORMAT`**: Report format (text, json).

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   **`--kube-version <V>`**: Target specific K8s version environment payload.
*   `-q`, `--quiet`: Minimal output mode.
