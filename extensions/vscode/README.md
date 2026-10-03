# Yamlr VS Code Extension

Official Visual Studio Code & Cursor extension for **Yamlr — The Autonomous Resolution Plane for Kubernetes**.

---

## ⚡ Features

- **Real-Time LSP Validation**: Instant red squiggly underlines on deprecated API versions, mismatched container ports, and missing required OpenAPI spec fields.
- **Quick Fix: Heal with Yamlr**: 1-click comment-preserving auto-remediation.
- **Native Rust Engine**: Communicates directly with the `yamlr lsp` native engine; response time depends on the workspace and enabled checks.

---

## 📦 Installation & Setup

1. Install Yamlr binary globally:
   Download an exact release from the [Yamlr releases page](https://github.com/yamlr/yamlr/releases) and verify its provenance and checksum before installing. See the [verified installer example](../../docs/ci-cd-integration.md).
2. Open any `.yaml` or `.yml` Kubernetes manifest in VS Code or Cursor.
3. Run Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) -> **`Yamlr: Heal Active Manifest`**.
