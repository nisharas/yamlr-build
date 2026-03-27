#!/usr/bin/env python3
"""
Yamlr IDENTITY EXTRACTION STAGE
-----------------------------------
Stage 3: Extract Kubernetes resource identities from shards.

Why: Isolation of identity logic enables:
     1. Faster 'Light Mode' scans by running only this stage.
     2. Native acceleration specifically for identity matching.
     3. Reduced coupling between pipeline and scanner implementations.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-03-21
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from yamlr.parsers.lexer import YamlrLexer
    from yamlr.parsers.scanner import YamlrScanner
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.pipeline.stages.identity")

class IdentityStage(PipelineStage):
    """Stage 3: Extract Kubernetes resource identities."""
    def __init__(self, name: str, lexer: "YamlrLexer", scanner: "YamlrScanner", identity_mode: str, file_path: str, kind: Optional[str] = None, api_version: Optional[str] = None):
        """
        Why: To support ultra-fast 'Fast Path' where identity is already known.
        """
        super().__init__(name)
        self.lexer = lexer
        self.scanner = scanner
        self.identity_mode = identity_mode
        self.file_path = file_path
        self.kind = kind
        self.api_version = api_version

    def run(self, context: HealContext):
        """
        Why: Extracts the Identity DNA required for all subsequent analysis.
        """
        try:
            # ⚡ FAST PATH: Use pre-extracted identity from Yamlr-Light
            if self.kind and self.api_version:
                context.identities = [ManifestIdentity(
                    kind=self.kind, 
                    api_version=self.api_version,
                    name="Extracted-By-Scout"
                )]
                context.audit_log.append(
                    f"Stage 3: Using pre-extracted identity from Yamlr-Light: {self.api_version}/{self.kind}"
                )
                for ident in context.identities:
                    ident.file_path = self.file_path
                return {
                    "success": True,
                    "kind": self.kind,
                    "api_version": self.api_version,
                }

            lexer_metadata = self.lexer.prepare_for_scanner(context.shards)
            self.scanner.set_lexer_context(lexer_metadata)

            context.identities = self.scanner.scan_shards(
                context.shards, mode=self.identity_mode
            )

            for slog in self.scanner.scan_logs:
                context.audit_log.append(f"Stage 3 Audit: {slog}")

            if not context.identities:
                context.audit_log.append("Stage 3: 🛑 CRITICAL: No valid K8s identity markers found (missing apiVersion/kind)")
                return {"success": False, "error": "Identity Extraction Failed: Missing apiVersion or kind", "skipped": True}

            primary = context.identities[0]
            if not primary.kind or not primary.api_version:
                context.audit_log.append(f"Stage 3: 🛑 CRITICAL: Incomplete identity for {primary.name or 'Unnamed'} (kind={primary.kind}, apiVersion={primary.api_version})")
                return {"success": False, "error": "Identity Extraction Failed: Incomplete identity", "skipped": True}

            context.audit_log.append(
                f"Stage 3: Identified {primary.api_version}/{primary.kind}"
            )

            for ident in context.identities:
                ident.file_path = self.file_path

            return {
                "success": True,
                "kind": primary.kind,
                "api_version": primary.api_version,
            }
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.error(f"Identity Extraction failure: {e}")
            return {"success": False, "error": e}
