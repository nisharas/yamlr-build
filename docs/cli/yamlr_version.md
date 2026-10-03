# yamlr version

Display version and build information for the Yamlr CLI, native PyO3 core, and Python runtime.

## Usage
```bash
yamlr version [OPTIONS]
# OR
yamlr -v
yamlr --version
```

## Argument Groups

### Primary Options
*   `--output {text,json}`: Output format (human-readable text or structured JSON). Default: `text`.

### CI/CD & Pipeline Integration
*   `-f, --output-file <FILE>`: Path to write structured report (JSON).
*   `--exit-zero`: Always exit with code 0.

## Description
The `version` command provides detailed release and engine metadata:
- **CLI Version**: Release version of the CLI toolchain.
- **Native Core**: Build identifier, PyO3 standard linkage, and engine status.
- **Python**: Python runtime version.

## Examples
```bash
# Standard version display
yamlr version

# Machine-readable JSON output for CI pipelines
yamlr version --output json
```
