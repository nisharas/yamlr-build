# Yamlr Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **Air-Gapped Telemetry Gate**: Added `--no-telemetry` CLI flag, `YAMLR_TELEMETRY=off`, and standard `DO_NOT_TRACK` compliance enforcement via `native_core/src/telemetry_gate.rs`.
- **Pure Standalone Native Core**: Decoupled native Rust core from PyO3 runtime dependencies. Standalone binary builds pure native Rust with zero Python overhead (`default = []`), while PyO3 extension bindings are cleanly feature-gated behind `#[cfg(feature = "python")]`.
- **Release Verification & Security**: Added SHA-256 cryptographic checksum verification in `install.sh` and `install.ps1`, with automated `checksums.sha256` generation in `.github/workflows/release.yml`.
- **Continuous Integration & Security Audits**: Added unified `.github/workflows/ci.yml` matrix (Rust, Python, Golden Corpus, CLI smoke test) and scheduled vulnerability scanning in `.github/workflows/security.yml`.

### Fixed
- **Secret Leakage Detection**: Removed blanket skip for `Kind: Secret` in `audit_secret_leakage` to detect directly embedded cleartext private keys and high-entropy credentials.
- **Robust Pipeline Error Handling**: Replaced silent `unwrap_or_default()` in `native_core/src/pipeline.rs` with explicit IO error reporting and logging.
- **Safe Catalog Initialization**: Replaced `.expect()` panics in `native_core/src/audit_engine.rs` lazy statics with graceful fallback defaults.
- **RSA Signing Error Reporting**: Replaced silent `unwrap_or_default()` in `native_core/src/security/signature.rs` with formatted error message propagation.
- **Schema Serializer Reliability**: Added explicit error checking and logging in `native_core/src/cli/schema_cmd.rs`.
- **Scanner Exception Visibility**: Replaced silent exception swallowing in `src/yamlr/core/scanner.py` with structured warning logging.

## [0.1.0] - 2026-04-06
### Added
- **Core Healing Engine**:
    - `YamlrLexer` for high-fidelity manifest decomposition.
    - `YamlrStructurer` for semantic-aware reconciliation.
    - `Manifest Security Suite` (RBAC, Ingress, Pod Security).
    - `Relational Discovery` for cross-resource link validation.
- **Turbo Distribution**:
    - `yamlr_native` Rust extension and standalone native binary for manifest scanning and remediation.
    - Standalone native binary for Windows, Linux, and macOS.
- **Enterprise Features (Pro)**:
    - Unlimited batch healing.
    - Compliance DNA Integrity Proofs.
    - OPA/Kyverno remediation adapters.
