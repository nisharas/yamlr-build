# yamlr stats
[PRO] Display surgical ROI, engineering time saved, and project safety metrics.

## Usage
```bash
yamlr stats
yamlr stats --apps
```

## Flags
* `--apps`: Group safety scores and top risks by application (inferred from labels or directory structure).
* `--badge`: Generate a shareable Markdown ROI badge (Shields.io) for your repository README.
* `--org`: Show organization-wide surgical impact across all projects on this machine.
* `--output`: Output format (`text` or `json`).

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).
