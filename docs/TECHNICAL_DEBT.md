# Technical Debt Assessment

**Date:** 2026-01-31
**Status:** In Progress

This document outlines areas of the codebase that require refactoring or infrastructure improvements to ensure long-term maintainability and scalability.

## 1. Resolved Items (Completed)
*   **Build System**: `pyproject.toml` exists and is correctly configured.
*   **Deployment Script**: `hack/push_all.py` now uses `sync_config.yaml` for configuration.
*   **Hardcoded Rules**: `explain.py` now loads rules from external `src/yamlr/core/data/rules.yaml`.
*   **Error Handling**: Standardized `YamlrException` hierarchy implemented (2026-02-03).
*   **Identity Mode**: Strict filtering and smart inference integrated into Engine.
*   **Architectural Decoupling**: Phase 11 God Object refactoring completed. Extracted `YamlrManager`, modularized `HealingPipeline`, and decoupled `K8sStabilizer`.
*   **Result Standardization**: `HealFileResult` implemented as a dataclass, replacing legacy dictionaries and tuples across the engine.
*   **Pro Bridge Warning**: Resolved (2026-02-13). Suppressed for OSS-only installations by hardening `LicenseManager` detection.
*   **God-Method Decomposition**: Resolved (2026-02-13). `YamlrStructurer._build_tree` split into `IndentationPhysicist` and `SchemaHealer`.
*   **File Size Guardrail**: Resolved (2026-02-13). All files now <500 lines (e.g., `structurer.py`, `bridge.py`, `cross_resource.py`).
*   **Security Hardening**: Resolved (2026-02-13). Implemented symlink protection in `io.py` and tightened backup vault permissions to `0o700`.
*   **Entrypoint Consolidation**: Resolved (2026-02-19). Unified flag processing and Pro-gating in `base.py` using `CliOptions`. Refactored `scan.py` and `heal.py` to eliminate ~100 lines of technical debt and boilerplate.
