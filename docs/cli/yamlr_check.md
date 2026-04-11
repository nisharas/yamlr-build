# yamlr check
**Fast Syntax & Schema Validator**

High-speed alias for `yamlr scan` designed for CI/CD pipelines. Disables network/OPA for maximum speed. **Note: `--strict` and `--summary-only` are enabled by default.**

## Usage
```bash
yamlr check [PATH]...
```

## Description
*   **Checks**: YAML Syntax, K8s Schema (Local).
*   **Performance**: < 200ms startup.

## Examples
```bash
yamlr check .
```

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--kube-version <V>`**: Force specific K8s version.
*   **`--fast`**: Always enabled for check.
*   **`--max-depth <N>`**: Limit recursion depth.
*   **`--concurrency <N>`**: Parallel worker processes.
*   **`--strict`**: Enabled by default.
*   **`--compact`**: Minify output.
*   **`--output {text,json,sarif}`**: Output format.
*   **`--fail-on <CHOICE>`**: Exit 1 if found.
*   **`--summary-only`**: Enabled by default.
*   **`--plain`**: ASCII-only output.
*   **`--verbose`**: Full audit logs.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   `-q`, `--quiet`: Minimal output mode.
