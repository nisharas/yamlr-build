# Yamlr Guard: Autonomous K8s Manifest Sentinel

**Yamlr Guard** (`yamlr/scan`) is an autonomous security and configuration gate for your Kubernetes manifests. Built with a **native Rust engine**, it provides high-performance auditing without exposing your environment's proprietary logic.

## Architecture

- **Native Speed**: Rust-based scanning with borrowed document-slice streaming for multi-document input; downstream parsing and AST construction allocate owned shard data.
- **Hermetic Execution**: Runs in an isolated container with zero external network calls.
- **Deep Audit**: Beyond syntax linting—Guard models Kubernetes topology and cross-resource dependencies.
- **SARIF Support**: Integrates directly with GitHub Code Scanning alerts.

## Usage

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Yamlr Guard Scan
        uses: yamlr/scan@v1
        with:
          path: './manifests'
          kube-version: '1.31'
```

## 📊 Inputs

| Input | Description | Default |
| :--- | :--- | :--- |
| `path` | Path to manifests (file or directory) | `.` |
| `fail-on-error` | Fail build if issues found | `true` |
| `kube-version` | Target K8s version | `v1.31` |

---
**Powered by Yamlr Locked-Engine Reliability.**
