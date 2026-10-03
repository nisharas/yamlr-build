# Announcing Yamlr v1.7.0: Safe Auto-Repair for Kubernetes Manifests

**Announcing the General Availability of Yamlr, a high-performance manifest safety and healing engine for Kubernetes.**

---

## Why Yamlr?

In complex Kubernetes environments, configuration drift and subtle multi-resource mismatches cause silent deployment failures. Yamlr is built to catch these relational bugs before deployment:

### Key Capabilities:
- **Rust-Native Core**: Auditing and healing use a native Rust implementation. Performance depends on input, enabled checks, and hardware.
- **Embedded Schema Matrix**: Built-in support for Kubernetes OpenAPI v3 schemas (v1.21–v1.32+).
- **WebAssembly Playground**: Run the full validation and auto-repair engine client-side in your browser.
- **Comment Preservation**: Auto-repair manifests without dropping inline comments, quotes, or indentation.

---

## Getting Started

**Install on macOS / Linux:**
```bash
brew install yamlr
```

**Run an audit:**
```bash
yamlr scan ./k8s
```

**Auto-heal detected issues:**
```bash
yamlr heal ./k8s --apply
```

---

- **GitHub**: [github.com/yamlr/yamlr](https://github.com/yamlr/yamlr)
- **Documentation & Sandbox**: [yamlr.dev](https://yamlr.dev)
