# CI/CD Integration
**Automated Manifest Quality Gate**

Yamlr is architected to act as the ultimate deterministic gatekeeper for infrastructure-as-code. Designed with a **Local-First** execution model, it returns standard Unix exit codes and generates industrial-grade reporting (SARIF/JSON) natively, making it a drop-in integration for GitHub Actions, GitLab CI, and pre-commit hooks.

---

## 🧬 1. The Safety Gate (Exit Logic)
While Yamlr prefers guidance during local development, it acts as a ruthless validator in CI/CD pipelines. You control the workflow blocking logic via the following clinical flags:

| Flag | Logic | Impact |
|:---|:---|:---|
| `--fail-on` | Severity-based gating: `error`, `warning`, `any`. | Instructs the engine to return **Exit Code 1** if a finding matches or exceeds the severity. |
| `--risk-threshold`| Impact-based gating: `high`, `medium`, `low`. | Forces a failure only if the architectural "Blast Radius" identified by the engine exceeds the threshold. |
| `--quiet` | Minimal signal mode. | Suppresses all UI elements except for critical blockers and binary pass/fail signals. |

---

## GitHub Actions Integration
Yamlr is fully compatible with GitHub Actions and supports **GitHub Code Scanning** via the SARIF format.

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Manifest Security Audit
        run: |
          yamlr scan . \
            --fail-on error \
            --output sarif > yamlr-results.sarif
      - name: Upload Audit Results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: yamlr-results.sarif
```

---

## 🧬 2. Standard Workspace configuration
For consistent CI/CD behavior, use a repository-level **Workspace Configuration** (`.yamlr.yaml`). This ensures that the same rules and thresholds are applied across every runner in your fleet.

```yaml
# .yamlr.yaml
rules:
  threshold: 85
  ignore:
    - "rules/no-latest-tag"

healing:
  risk_threshold: high
```

---

## 🛠 Advanced Pipeline Patterns

### GitLab CI/CD
```yaml
yamlr-audit:
  image: yamlr/engine:v0.1.0
  script:
    - yamlr scan . --fail-on warning --output json > report.json
  artifacts:
    paths: [report.json]
```

### Pre-Commit Hooks
Include Yamlr in your `pre-commit-config.yaml` to catch violations before they are even committed to the local ledger.

```yaml
- repo: local
  hooks:
    - id: yamlr-scan
      name: Yamlr Scan
      entry: yamlr scan . --fail-on error --quiet
      language: system
      files: \.(yaml|yml)$
```

---

> [!IMPORTANT]
> **Zero-Exfiltration Pipelines**
> Because Yamlr never uploads manifests to an external server, your secrets and manifest structures remain securely within your CI/CD runner's memory. This makes Yamlr suitable for air-gapped environments, PCI-DSS boundaries, and strict data governance policies.
