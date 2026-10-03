# Yamlr Design Partner Pilot Program & Evaluation Guide

**Audience:** Platform Engineering Leads, SRE Managers, Security Architects, and DevOps Practitioners  
**Scope:** 14-Day Production Validation of the Yamlr Kubernetes Manifest Resolution Plane  
**Execution Posture:** Local manifest analysis • Reviewable repairs • Source-aware AST mutation  

---

## 1. Executive Technical Summary

Yamlr is an autonomous Kubernetes manifest resolution and validation engine. Unlike static linters that identify syntax issues without resolving them, Yamlr combines a deterministic Abstract Syntax Tree (AST) parser with an OpenAPI schema compiler to deliver safe, comment-preserving auto-remediation across complex Kubernetes manifests.

### Review and validation
Yamlr provides source-aware repairs and validates supported outputs before writing in the relevant healing flows. Preservation behavior depends on the input and transformation, and schema validation does not prove that a workload is correct for every cluster or deployment environment. During the pilot:
1. Review proposed changes with `yamlr diff` before applying them.
2. Validate repaired output against the target Kubernetes version and any cluster-specific policy.
3. Keep the repository's version-control history and normal rollback process available.

---

## 2. Security, Privacy & Network Boundary Specification

Platform and security review teams should verify network behavior before introducing tooling into developer environments and CI/CD runners. Local manifest processing is separate from optional network integrations.

### 2.1 Network Boundary & Execution Isolation
* **Local Processing:** Scan and heal process local manifests using bundled schemas; they do not upload manifest data during local analysis.
* **Optional Network Requests:** `--push-telemetry` sends an aggregate scan event when telemetry is enabled and an Enterprise entitlement is present. `YAMLR_LICENSE_AUTO_RENEW=true` enables Team entitlement renewal and sends the signed entitlement token to the configured gateway. CI workflows and other adapters may also send reports to their configured services.
* **Air-Gapped Operation:** Disable telemetry and license auto-renew, and disable CI or service integrations that require network access before using Yamlr in an isolated environment. Test the exact commands and distribution in that environment.
* **Telemetry Payload:** The scan event contains the CLI version, event type, and timestamp. It does not include manifest contents, file paths, repository URLs, or environment variables. Entitlement renewal is a separate request containing the signed token.

### 2.2 Entitlement & Licensing Architecture
* **Local Cryptographic Verification:** Enterprise entitlement tokens are validated entirely offline inside local memory.
* **Asymmetric RS256 Verification:** Token verification uses asymmetric RSA-2048 (`RS256`) public-key cryptography. The public key is embedded directly within the binary distribution. Verification requires zero network calls to licensing or authentication servers.
* **Credential Storage:** Active license tokens are stored in the operating system credential manager. Valid tokens from the legacy per-user config file migrate to the credential manager on first access and are removed from that file after successful migration.

### 2.3 Telemetry Protocol (Explicit Push)
* **No Push Without the Flag:** Scan-completion telemetry is sent only when `--push-telemetry` is supplied, telemetry is not disabled, and the stored entitlement is Enterprise.
* **Payload Transparency:** When `--push-telemetry` is enabled by an administrator, the transmitted JSON payload is restricted to operational counters:
  ```json
  {
    "cli_version": "0.1.0",
    "event_type": "scan_complete",
    "ts": 1726384800
  }
  ```
* **Payload Scope:** The scan-completion payload contains the CLI version, event type, and timestamp. It does not include file names, repository URLs, manifest contents, or environment variables. Licensing renewal is a separate opt-in request that sends the signed entitlement token.
* **Graceful Degradation:** Telemetry network requests enforce a strict 5-second timeout. Any network partition or connection drop fails silently without interrupting the exit code or execution pipeline.

---

## 3. The 14-Day Pilot Protocol

The pilot program follows a phased progression designed to establish visibility and confidence before introducing automated remediation.

```
+-----------------------------------------------------------------------------+
|                               14-DAY PILOT PROTOCOL                         |
+------------------------------------+----------------------------------------+
|   PHASE S1: Days 1 to 7            |   PHASE S2: Days 8 to 14               |
|   Zero-Risk Visibility             |   Controlled Remediation & Quality Gate|
+------------------------------------+----------------------------------------+
| - Non-blocking PR diff preview     | - Opt-in developer pre-commit hooks   |
| - Read-only SARIF audit in CI      | - Automated remediation pull requests  |
| - Zero file modifications          | - Blocking CI schema quality gates    |
| - Establish baseline error metrics | - Measure review time and zero rollbacks|
+------------------------------------+----------------------------------------+
```

### Phase S1 (Days 1–7): Zero-Risk Visibility
* **Objective:** Audit existing manifest repositories and surface proposed auto-corrections to developers without modifying files or failing builds.
* **Execution:**
  1. Add the read-only audit workflow (`yamlr diff --unified` and `yamlr scan --output sarif`) to CI pull request pipelines.
  2. Configure the action with `--exit-zero` so builds remain non-blocking.
  3. Review the proposed diffs in GitHub Step Summaries or PR comments to evaluate remediation quality and comment preservation.
* **Deliverable:** Establish baseline error metrics across target repositories.

### Phase S2 (Days 8–14): Controlled Remediation & Quality Gates
* **Objective:** Enable active auto-remediation and introduce deterministic CI quality gates.
* **Execution:**
  1. Distribute `.pre-commit-config.yaml` to development teams for pre-commit formatting and auto-healing (`yamlr-heal` with `--apply`).
  2. Configure automated remediation branches for batch manifest cleanups (`yamlr heal . --apply`).
  3. Transition CI pipelines from `--exit-zero` to `--fail-on error` to enforce schema conformance prior to merge.
* **Deliverable:** Measure review duration reduction and confirm zero production rollbacks on healed manifests.

---

## 4. Turnkey Integration Blueprints

### Blueprint A: GitHub Actions (PR Diff Preview & SARIF Gate)
Place this workflow at `.github/workflows/yamlr-audit.yml`:

```yaml
name: "Yamlr Manifest Quality Gate"

on:
  pull_request:
    paths:
      - "**.yaml"
      - "**.yml"

permissions:
  contents: read
  security-events: write

jobs:
  audit:
    name: "Audit & Diff Manifests"
    runs-on: ubuntu-latest
    steps:
      - name: "Checkout Repository"
        uses: actions/checkout@v4

      - name: "Set up Python"
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: "Install Yamlr"
        run: pip install yamlr

      - name: "Preview Auto-Remediation Diffs"
        run: |
          echo "### Proposed Manifest Corrections" >> $GITHUB_STEP_SUMMARY
          echo '```diff' >> $GITHUB_STEP_SUMMARY
          yamlr diff --unified . >> $GITHUB_STEP_SUMMARY 2>&1 || true
          echo '```' >> $GITHUB_STEP_SUMMARY

      - name: "Audit Manifests (SARIF Gate)"
        run: |
          yamlr scan . --output sarif --output-file results.sarif --fail-on error

      - name: "Upload SARIF to GitHub Code Scanning"
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        continue-on-error: true
        with:
          sarif_file: results.sarif
```

---

### Blueprint B: Pre-Commit Hook (.pre-commit-config.yaml)
Add to the root `.pre-commit-config.yaml` to intercept and auto-heal manifests locally before commits:

```yaml
repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      # Hook 1: Auto-heal manifests in-place with comment preservation
      - id: yamlr-heal
        args: ["--apply"]

      # Hook 2: Validate against OpenAPI schemas and block on error
      - id: yamlr-scan
        args: ["--fail-on", "error"]
```

Install hook into local git repository:
```bash
pre-commit install
```

---

### Blueprint C: GitLab CI Pipeline (.gitlab-ci.yml)
Integrate headless manifest scanning into GitLab pipelines:

```yaml
stages:
  - validate

yamlr-manifest-audit:
  stage: validate
  image: python:3.12-slim
  script:
    - pip install yamlr
    - yamlr diff --unified .
    - yamlr scan . --output text --fail-on error
  rules:
    - changes:
        - "**/*.yaml"
        - "**/*.yml"
```

---

### Blueprint D: GitOps Admission Quality Gate (ArgoCD / Flux)
Run as a pre-sync check or container hook before deploying manifests to clusters:

```bash
#!/bin/bash
set -e

echo "Validating Kubernetes manifests against target schema..."
yamlr scan ./manifests --k8s-version 1.30 --fail-on error

echo "Schema validation passed. Proceeding with deployment."
```

---

## 5. Pilot Evaluation Scorecard & Success Criteria

This blank scorecard is designed for your platform team to objectively track metrics across the 14-day evaluation window.

### 5.1 Objective Metrics Scorecard

| Metric Category | Specific Measurement | Pre-Pilot Baseline | Post-Pilot (Day 14) | Team Evaluation / Delta |
|:---|:---|:---:|:---:|:---:|
| **Reliability** | Total Schema & Semantic Violations Detected | `[   ]` | `[   ]` | `[   ]` |
| **Reliability** | Production Rollbacks Caused by Manifest Syntax Errors | `[   ]` | `[   ]` | `Target: 0.0%` |
| **Efficiency** | Average Developer PR Review Time on Manifests (Minutes) | `[   ]` | `[   ]` | `[   ]` |
| **Friction** | Disrupted Developer Commits / False Positives Reported | `[   ]` | `[   ]` | `[   ]` |
| **Performance** | CI Pipeline Execution Latency Added by Yamlr (Seconds) | `N/A` | `[   ]` | `Budget: < 5.0s` |
| **Comment Preservation** | Inline Comment Retention Rate on Auto-Healed Files | `N/A` | `[   ]` | `Target: 100.0%` |

---

### 5.2 Qualitative Assessment Checklist

| Area | Evaluation Criteria | Status (Pass / Fail / Notes) |
|:---|:---|:---:|
| **Comment Fidelity** | Developer comments, license headers, and formatting remain unchanged after `heal --apply`. | `[ Pending ]` |
| **Air-Gap Compliance** | Scans and auto-repairs execute completely offline with zero network connectivity. | `[ Pending ]` |
| **CI Gating** | Deterministic exit codes (`0` for clean, `1` for violations) reliably control PR mergeability. | `[ Pending ]` |
| **SARIF Integration** | Security findings render natively in GitHub Code Scanning / GitLab Vulnerability Reports. | `[ Pending ]` |
| **Developer Adoption** | Engineers opt into the pre-commit hook without workflow friction or configuration overhead. | `[ Pending ]` |

---

## 6. Support & Pilot Escalation Channel

During your 14-day evaluation, direct technical escalation is available for edge-case CRD schemas or custom resource transformations:
* **Technical Inquiries & Schema Support:** `support@yamlr.dev`
* **Issue Tracker & Feature Requests:** `https://github.com/yamlr/yamlr/issues`
* **Documentation & CLI Reference:** Run `yamlr help` or view `docs/cli/yamlr.md`
