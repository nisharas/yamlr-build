#!/usr/bin/env python3
"""
Scanner FORENSICS Mixin
-----------------------
Logging, audit trails, deprecation checks, and Pro mode detection.

Why: Extracted from scanner.py to enforce the <500 line modularity rule.
This mixin provides all forensic/audit methods that YamlrScanner inherits.

Architecture: Mixin pattern — shares state via `self` with the main class.
All methods are private (_prefixed) and called only by YamlrScanner internals.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
"""

from __future__ import annotations

import logging
import os
from typing import List

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.scanner")
__all__ = ["ForensicsMixin"]


class ForensicsMixin:
    """
    Forensic audit methods for YamlrScanner.

    Responsibilities:
    - Schema initialization logging
    - Pro/Enterprise mode detection
    - Post-scan summary logging
    - API deprecation auditing
    """

    def _log_schema_initialization_verbose(self) -> None:
        """
        Logs a detailed summary of the registered archeology toolkit.

        Rationale:
        Provides a breakdown of how many schemas were loaded from each source.
        Crucial for diagnosing missing CRDs or plugin failures in CI/CD.
        Higher verbosity helps developers verify that their custom schemas
        were correctly ingested before Stage 3 starts.
        """
        catalog_count = len(self.catalog)
        openapi_count = len(self.openapi_catalog)
        crd_count = len(self.crd_catalog)
        plugin_count = len(self.plugin_catalogs)

        logger.debug(
            f"Scanner initialized with schema_type='{self.schema_type}': "
            f"{catalog_count} K8s schemas, {openapi_count} OpenAPI schemas, "
            f"{crd_count} CRD schemas, {plugin_count} plugin catalogs registered. "
            f"Ready for high-fidelity manifest archeology."
        )

    def _detect_pro_mode(self) -> bool:
        """
        Detects if Yamlr is running in Pro/Enterprise mode via the Bridge.

        Why: Centralizes capability discovery to ensure consistency across
             different internal modules (Parser vs Engine vs CLI).
        """
        from yamlr.core.bridge import YamlrBridge

        return YamlrBridge.is_pro_enabled()

    def _log_scan_summary_verbose(self, valid_ids: List[ManifestIdentity]) -> None:
        """
        Summarizes scan results for forensic audit logs.

        Integrates Lexer telemetry to show a complete picture of the Stage 1-3
        pipeline health for each file processed.
        """
        count = len(valid_ids)
        summary = f"Stage 3 (Scanner): Archeology complete. {count} identities mined."
        if self._lexer_context:
            fixes = sum(self._lexer_context.get("repair_stats", {}).values())
            if fixes > 0:
                summary += f" (Lexer performed {fixes} structural heals)"
        logger.debug(summary)
        for idnt in valid_ids:
            logger.debug(f"  → DNA MATCH: {idnt.api_version}/{idnt.kind} (name={idnt.name or 'N/A'})")

    def _audit_deprecations(self, valid_ids: List[ManifestIdentity]) -> None:
        """
        Checks for API deprecations early in the pipeline cycle.

        This prevents the Structurer from processing APIs that are
        guaranteed to fail in the target cluster version.
        """
        for idnt in valid_ids:
            if idnt.api_version and idnt.kind:
                dep_info = self.deprecation_checker.check(idnt.api_version, idnt.kind)
                if dep_info:
                    logger.debug(
                        f"DEPRECATION DETECTED: {idnt.api_version} {idnt.kind} removed in K8s {dep_info.removed_in_version}."
                    )
                    idnt.deprecation_info = dep_info
