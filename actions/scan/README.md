# 🛡 Yamlr Guard: Autonomous K8s Manifest Sentinel

**Yamlr Guard** (`yamlr/scan`) is an autonomous security and configuration gate for your Kubernetes manifests. Built with our **natively compiled C-engine**, it provides high-performance auditing without exposing your environment's proprietary logic.

## 🚀 Why Guard?

- **Native Speed**: Compiled with Nuitka into a high-performance C binary.
- **Binary-in-a-Box**: Runs in a hermetically sealed container. No Python runtime required.
- **Deep Audit**: Beyond simple linting—Guard understands Kubernetes intent and hierarchy.
- **SARIF Support**: Seamlessly integrates with GitHub Code Scanning alerts.

## 🛠️ Usage

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
