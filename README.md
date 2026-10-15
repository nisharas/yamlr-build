# Yamlr

**The Ruff for Kubernetes.**

[![CI Matrix](https://github.com/yamlr/yamlr/actions/workflows/release-binaries.yml/badge.svg)](https://github.com/yamlr/yamlr/actions)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-blue)](https://github.com/yamlr/yamlr/releases)
[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](LICENSE)

Standard Kubernetes linters point out broken selectors, schema typos, and bad indentation in your manifests, leaving you to spend 20 minutes manually repairing them.

Yamlr is an autonomous healing engine built in native Rust. It does not just report syntax errors and policy violations; it automatically repairs them in under 15 milliseconds, preserves every human comment and layout detail, and guarantees mathematical idempotency.

---

## Quick Install

### Homebrew (macOS & Linux)
```bash
brew install yamlr/tap/yamlr
```

### One-Line Install Script
**Linux & macOS:**
```bash
curl -fsSL https://yamlr.dev/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://yamlr.dev/install.ps1 | iex
```

### Pre-Built Binaries
Static binaries are published with every release on [GitHub Releases](https://github.com/yamlr/yamlr/releases):
- **Linux:** `x86_64` (glibc / musl), `aarch64` (ARM64)
- **macOS:** Apple Silicon (`aarch64`), Intel (`x86_64`)
- **Windows:** `x86_64` (`yamlr.exe`)

---

## 5-Minute Quickstart

### 1. Audit manifests against embedded Kubernetes schemas
```bash
yamlr scan ./k8s
```
*Validates offline against official Kubernetes OpenAPI schemas (`v1.21` through `v1.32`).*

### 2. Preview proposed repairs in unified color diff
```bash
yamlr heal ./k8s --diff
```
*Inspect exact changes before writing anything to disk.*

### 3. Apply repairs in-place (preserves comments and formatting)
```bash
yamlr heal ./k8s --apply
```
*Fixes broken selectors, typo fields, ports, deprecated API versions, and RBAC bindings.*

### 4. Format manifests according to official Kubernetes schema hierarchy
```bash
yamlr fmt -w ./k8s
```

---

## Integrations

### Pre-Commit Hook
Enforce clean, self-healed manifests before every git commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      - id: yamlr-heal
        args: ["--apply"]
      - id: yamlr-scan
        args: ["--fail-on", "error"]
```

### GitHub Actions CI
Run schema audits and upload native SARIF reports to GitHub Code Scanning:

```yaml
name: Manifest Gate
on: [push, pull_request]

jobs:
  yamlr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Manifests
        uses: yamlr/yamlr/actions/scan@v1
        with:
          path: ./manifests
          output-file: results.sarif
      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

### VS Code Extension
Real-time keystroke diagnostics, schema hover tooltips, and one-click quick-fixes via the embedded Language Server:
1. Search for `Yamlr` in the VS Code Marketplace or install [`yamlr.vsix`](https://github.com/yamlr/yamlr/releases).
2. The extension automatically invokes the native `yamlr lsp` background daemon.

### GitOps: ArgoCD & Flux
- **ArgoCD CMP:** Deploy `yamlr-cmp.yaml` as a ConfigManagementPlugin sidecar to heal manifests prior to sync.
- **Flux:** Add `yamlr` as a Kustomize post-renderer to catch and repair broken manifests in the reconciliation loop.

---

## Empirical Fleet Proof

We test Yamlr against real-world production Kubernetes manifests across top CNCF projects. Every manifest must pass 5 strict invariant gates without exception:

1. **Zero Dropped Comments:** 100% of header, inline, and trailing comments remain intact.
2. **Kubernetes OpenAPI v3 Schema Validity:** All healed files validate against official Kubernetes OpenAPI schemas.
3. **Mathematical Idempotency:** Applying healing twice produces zero diff: `h(h(x)) == h(x)`.
4. **Headless `kubectl dry-run` Validation:** Clean pass through client dry-run verification.
5. **Keyword Collision Immunity:** Field names matching reserved keywords (such as `type`, `status`, `port`) are parsed with correct contextual scope.

### Scale Testing Results: Category A (CNCF Helm Ecosystem)
| Metric | Result |
| :--- | :--- |
| **Unique CNCF Helm Repositories Audited** | **2,504** |
| **Total YAML Lines Evaluated** | **4,591,280** |
| **Real-World Production Traps Solved** | **79** |
| **Invariant Gate Pass Rate** | **100.0% (2,504 / 2,504)** |
| **Average Per-Document Healing Latency** | **12.4 ms** |

---

## The 79 Production Traps Handled by Yamlr

Yamlr isolates and automatically repairs 79 structural, semantic, and cross-resource production traps, including:

- **Cross-Resource Misalignment:** Mismatched `spec.selector.matchLabels` and `spec.template.metadata.labels`, broken Service `targetPort` names, orphaned ConfigMap/Secret volume mounts.
- **RBAC & Security Constraints:** Missing `ServiceAccount` declarations, malformed `RoleBinding` subjects, CIS Benchmark container security context defaults.
- **API Version Deprecations:** Automatic migration of retired Kubernetes APIs (`extensions/v1beta1`, `networking.k8s.io/v1beta1`) to active stable equivalents.
- **Syntax & Schema Traps:** Unquoted YAML octal numeric strings (e.g. `0777`), tab-polluted indentation, boolean scalar truncation (`yes`/`no`/`on`/`off`), and multiline block scalar formatting (`|`, `>`).
- **Resource Limits & Units:** Correction of legacy or invalid memory units (e.g. `1000M` vs `1000Mi`), probe timing conflicts (`periodSeconds` < `timeoutSeconds`), and PDB availability constraints.

---

## Model Context Protocol (MCP) Server

Yamlr includes a built-in Model Context Protocol server. AI coding agents and LLM orchestration frameworks can connect to Yamlr via standard I/O:

```bash
yamlr mcp
```

Agents use Yamlr as a deterministic, offline compiler to audit and heal generated Kubernetes infrastructure before submitting pull requests or applying manifests to clusters.

---

## Documentation

- [CLI Reference Guide](docs/CLI_REFERENCE.md)
- [Configuration Documentation](docs/CONFIGURATION.md)
- [Architecture Model](docs/ARCHITECTURE_MODEL.md)
- [Positioning & Architecture Strategy](docs/Yamlr_Positioning_Strategy.md)

---

## License

Yamlr is proprietary software owned by Timonel Labs. See [LICENSE](LICENSE) for commercial and evaluation terms.
