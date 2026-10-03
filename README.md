# Yamlr
**The Autonomous Resolution Plane for Kubernetes Manifests**

[![CI Matrix](https://github.com/yamlr/yamlr/actions/workflows/release-binaries.yml/badge.svg)](https://github.com/yamlr/yamlr/actions)
[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)](https://github.com/yamlr/yamlr/releases)

Yamlr is a high-performance, hermetic Kubernetes manifest healing engine built in Rust. Where standard linters only report errors, Yamlr automatically repairs schema deviations, deprecated API versions, and cross-resource misalignments while strictly preserving comments, layout formatting, and semantic intent.

---

## Key Features

- **⚡ Native Rust Execution**: Written in Rust, with borrowed document-slice streaming for multi-document input. Parsing and AST construction still allocate owned shard data. Measure representative workloads on the target platform; this project makes no fixed latency guarantee here.
- **🔒 Comment & Layout Preservation**: Layout-aware healing is covered by parser and healer tests. Preservation depends on the input and repair; review the proposed diff before applying changes.
- **🛡️ Offline Scanning**: Embeds Kubernetes schemas for supported versions (`v1.21` through `v1.37`) so core scans can run offline. Optional integrations and unsupported schema versions may require network access.
- **🔗 Cross-Resource Referential Healing**: Automatically aligns Service selectors to Deployment labels, validates ConfigMap/Secret references, and normalizes RBAC bindings.
- **🔄 Multi-Document Topological Ordering**: Emits multi-document YAML streams in deterministic dependency order (Namespaces & CRDs before workloads).
- **📊 Native SARIF & JSON Reporting**: Direct integration with GitHub Code Scanning, GitLab Security Dashboard, and CI pipelines.

---

## Installation

### Homebrew (macOS & Linux)
```bash
brew install yamlr/tap/yamlr
```

### Pre-Compiled Standalone Binaries
Download pre-built static binaries for Linux (x86_64, aarch64), macOS (Apple Silicon, Intel), and Windows (x64) from the [GitHub Releases](https://github.com/yamlr/yamlr/releases) page.

```bash
# Verify installation
yamlr version
```

### VS Code Extension
Install the official Yamlr extension directly from the VS Code Marketplace or load [`yamlr.vsix`](https://github.com/yamlr/yamlr/releases) for real-time keystroke diagnostics, schema hover tooltips, and one-click quick-fixes.

---

## Quick Start

```bash
# 1. Audit manifests for schema and integrity violations
yamlr scan ./k8s

# 2. Preview proposed auto-remediations in unified color diff
yamlr heal ./k8s --diff

# 3. Safely apply fixes in-place with comment preservation
yamlr heal ./k8s --apply

# 4. Format manifests according to official Kubernetes schema hierarchy (k8sfmt)
yamlr fmt -w ./k8s

# 5. Execute fleet batch remediation with automated branch and PR creation
yamlr fleet ./services --apply --create-pr --k8s-version 1.30

# 6. Run standalone stdio Language Server Protocol daemon
yamlr lsp

# 7. Start in-cluster mutating and validating admission webhook server
yamlr webhook --port 8443
```

---

## Pre-Commit Hook Integration

Add Yamlr to your repository's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      # Safe, comment-preserving auto-repair before commit
      - id: yamlr-heal
        args: ["--apply"]
      # Strict schema gate
      - id: yamlr-scan
        args: ["--fail-on", "error"]
```

---

## GitHub Actions CI Integration

Upload native SARIF reports directly to GitHub Code Scanning:

```yaml
name: Kubernetes Manifest Audit
on: [push, pull_request]

jobs:
  yamlr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Yamlr Scan
        uses: yamlr/yamlr/actions/scan@v1
        with:
          path: ./manifests
          output-file: results.sarif
          version: v0.1.0
      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

---

## Documentation

- [Positioning & Architecture Strategy](docs/Yamlr_Positioning_Strategy.md)
- [CLI Reference Guide](docs/CLI_REFERENCE.md)
- [Configuration Documentation](docs/CONFIGURATION.md)
- [Architecture Model](docs/ARCHITECTURE_MODEL.md)

---

## License

Yamlr is proprietary software owned by Timonel Labs. Use is governed by the [Yamlr Proprietary & Commercial Software License](LICENSE). Third-party components remain subject to their respective license terms.
