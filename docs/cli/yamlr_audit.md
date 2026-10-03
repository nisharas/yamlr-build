# yamlr audit

Run the native compliance and forensic audit on a manifest or a directory of manifests. The audit checks the configured security and deprecation rules; it is a separate command from [`yamlr scan`](yamlr_scan.md).

## Usage

```text
yamlr audit [PATH] [--output text|json|sarif]
```

With no path, the command audits the current directory. A directory is traversed recursively and files ending in `.yaml` or `.yml` are included. A file path is audited directly. The path and output option may appear in either order. Only one target path and one output option are accepted; unsupported options and extra paths return a usage error.

## Output

`--output` and `-o` accept these formats:

- `text` (default): Human-readable summary and findings.
- `json`: Yamlr audit report with file and finding counts, elapsed time, and findings.
- `sarif`: SARIF 2.1.0 results suitable for code-scanning tools.

Examples:

```bash
yamlr audit ./manifests
yamlr audit ./manifests --output json
yamlr audit ./manifests -o sarif > audit.sarif
yamlr audit --output=json ./manifests
yamlr audit ./deployment.yaml --output json
```

## Exit status

- `0`: The audit completed with no findings.
- `1`: The audit found one or more violations, or the target path does not exist.
- `4`: The audit could not complete because a manifest could not be read or directory traversal failed.
- `2`: The requested output format is unsupported.
- `3`: An unsupported option, malformed output option, or extra target path was supplied.

Diagnostics for incomplete audits are written to stderr. A nonzero result means the report must not be treated as a clean audit.
