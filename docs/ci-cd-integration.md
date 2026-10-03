# CI/CD Integration Guide

Integrate **Yamlr — The Autonomous Resolution Plane for Kubernetes** into your automated pipelines.

---

## GitHub Actions Setup

### 1. Fast Composite Action (<800ms)

Add the following step to your `.github/workflows/ci.yml`:

```yaml
name: Kubernetes Manifest Quality Gate

on:
  pull_request:
    paths:
      - '**.yaml'
      - '**.yml'

jobs:
  yamlr-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Yamlr Manifest Audit
        uses: yamlr/action@v1
        with:
          path: './k8s'
          k8s-version: '1.30'
          apply: 'false'
          version: 'v1.2.3'
```

---

## GitHub Code Scanning / Security Tab Integration (SARIF 2.1.0)

Yamlr natively generates strict SARIF 2.1.0 reports. You can upload results directly to the **GitHub Security -> Code Scanning alerts** dashboard:

```yaml
name: Yamlr Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  sarif-audit:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Install Yamlr Native Binary
        env:
          YAMLR_VERSION: ${{ vars.YAMLR_VERSION }}
        run: |
          : "${YAMLR_VERSION:?Set the repository variable YAMLR_VERSION to an exact published release tag}"
          curl -fsSL "https://raw.githubusercontent.com/yamlr/yamlr/${YAMLR_VERSION}/website/public/install.sh" -o yamlr-install.sh
          gh attestation verify yamlr-install.sh --repo yamlr/yamlr --signer-workflow yamlr/yamlr/.github/workflows/release.yml --source-ref "refs/tags/${YAMLR_VERSION}"
          YAMLR_VERSION="$YAMLR_VERSION" sh yamlr-install.sh

      # The public installer requires GitHub CLI and verifies the release attestation
      # against yamlr/yamlr before it extracts or installs the binary.

      - name: Execute Forensic Scan & Export SARIF
        run: |
          if yamlr scan ./k8s --output sarif > yamlr-report.sarif; then
            scan_status=0
          else
            scan_status=$?
          fi
          if [ "$scan_status" -gt 1 ]; then
            echo "::error::Yamlr scan failed before completing (exit code ${scan_status})."
            exit "$scan_status"
          fi

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: yamlr-report.sarif
          category: yamlr-k8s-audit
```

---

## 🦊 GitLab CI/CD Pipeline

Add to `.gitlab-ci.yml`:

```yaml
yamlr_audit:
  stage: test
  image: ghcr.io/yamlr/yamlr:latest
  script:
    - yamlr scan ./manifests --fail-on error
  rules:
    - changes:
        - "**/*.yaml"
        - "**/*.yml"
```

---

## ⚓ Pre-Commit Hook Configuration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      - id: yamlr-heal
        args: ["--apply"]
```
