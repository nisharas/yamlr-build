# yamlr evidence

The `yamlr evidence` command aggregates cryptographic DNA receipts (generated during a CI/CD `--evidence-dir` pipeline) into a single, auditor-ready Compliance Report.

This is an Enterprise feature designed for strict regulatory environments (SOC2, HIPAA, CIS) where infrastructure changes must be mathematically proven tamper-proof.

## Usage

```bash
yamlr evidence <dir> [options]
```

## Description

When Yamlr runs with `--evidence-dir <dir>`, it outputs JSON cryptographic receipts for every file it heals. The `evidence` command ingests this directory, verifies the `HMAC-SHA256` signatures to ensure no tampering occurred, maps the violations to their compliance framework (e.g., SOC2: CC6.1), and exports a unified PDF or HTML report.

## Options

### Core Options
*   `<dir>`: (Required) The path to the directory containing the `evidence-*.json` receipts.
*   `--format FORMAT`: The output format for the report. Options are `pdf` (default) or `html`.
*   `--output FILE`: The specific path/filename to save the generated report. If omitted, Yamlr generates a timestamped file (e.g., `yamlr-audit-report-<timestamp>.pdf`).

### Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).

## Examples

**Generate a PDF report from a CI artifacts directory:**
```bash
yamlr evidence ./audit-receipts/ --output final-compliance-report.pdf
```

**Generate a JSON dashboard report:**
```bash
yamlr evidence ./audit-receipts/ --format json --output index.json
```

## Security & Proving
If `yamlr evidence` detects that an `evidence-*.json` receipt has been tampered with (e.g., a bad HMAC signature or a mismatched `healed_content` hash), it will securely quarantine the receipt and forcefully mark the PDF report as `TAMPERED` to protect the integrity of the audit.
