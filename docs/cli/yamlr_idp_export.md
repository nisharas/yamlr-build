# yamlr idp-export
[PRO] Export safety and compliance metrics to Internal Developer Portals (IDPs).

## Usage
```bash
yamlr idp-export --format backstage
yamlr idp-export init --format backstage --output-file catalog-info.yaml
```

## Commands
* **init**: Generate opinionated integration templates for your IDP.

## Formats
* **backstage**: Emits a JSON array suitable for Backstage component annotations. Includes `yamlr.dev/safety-score` and top risks.
* **prometheus**: Emits OpenMetrics text format for ingestion into Prometheus/Grafana.
* **json**: Raw internal safety specification for custom integrations.

## Flags
* `--format`: Target platform format (`backstage`, `prometheus`, `json`).
* `--output-file`: Path to write the generated template or export data.

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).
