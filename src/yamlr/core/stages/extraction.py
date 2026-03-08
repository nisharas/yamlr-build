#!/usr/bin/env python3
"""
Yamlr EXTRACTION STAGES - Stages 0-3
-----------------------------------
Implements the initialization and extraction phases of the pipeline.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import List, Dict, Any, Optional

from yamlr.core.stages.base import PipelineStage
from yamlr.core.context import HealContext
from yamlr.models import ManifestIdentity, Shard

logger = logging.getLogger("yamlr.pipeline.stages.extraction")

class StageZeroReset(PipelineStage):
    """Stage 0: Internal pipeline state reset."""
    def __init__(self, shadow: Any):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 0: Reset")
        self.shadow = shadow

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.shadow.reset()
        context.audit_log.append("Stage 0: Internal pipeline state reset")
        return {"success": True}

class StageOneLexicalRepair(PipelineStage):
    """Stage 1: Lexical repair and sharding."""
    def __init__(self, lexer: Any):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 1: Lexical Repair")
        self.lexer = lexer

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        try:
            shards: List[Shard] = self.lexer.shard(context.raw_text)
            context.shards = shards
            context.audit_log.append(f"Stage 1: Lexer produced {len(shards)} shards")

            lexer_repairs = self.lexer.get_repair_audit_log()
            if lexer_repairs:
                context.audit_log.append("Stage 1: Lexer Healing Summary:")
                context.audit_log.extend([f"  → {entry}" for entry in lexer_repairs])
            else:
                context.audit_log.append("Stage 1: No lexical repairs needed (clean YAML)")

            return {
                "success": True, 
                "shards": shards,
                "stats": {
                    "lexer_repairs": sum(self.lexer.repair_stats.values())
                }
            }
        except Exception as e:
            logger.error(f"Lexer critical failure: {e}")
            return {"success": False, "error": e}

class StageTwoLayoutCapture(PipelineStage):
    """Stage 2: Layout and comment capture."""
    def __init__(self, shadow: Any):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 2: Layout Capture")
        self.shadow = shadow

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        try:
            self.shadow.capture(context.raw_text, context.shards)
            self.shadow.apply(context.shards)
            context.audit_log.append("Stage 2: Layout and comment metadata generated")
            return {"success": True}
        except Exception as e:
            context.audit_log.append(f"Stage 2: Warning - Layout preservation limited: {e}")
            return {"success": True, "warning": str(e)}

class StageThreeIdentityExtraction(PipelineStage):
    """Stage 3: Extract Kubernetes resource identities."""
    def __init__(self, lexer: Any, scanner: Any, identity_mode: str, file_path: str):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        super().__init__("Stage 3: Identity Extraction")
        self.lexer = lexer
        self.scanner = scanner
        self.identity_mode = identity_mode
        self.file_path = file_path

    def run(self, context: HealContext):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        try:
            lexer_metadata = self.lexer.prepare_for_scanner(context.shards)
            self.scanner.set_lexer_context(lexer_metadata)

            context.identities = self.scanner.scan_shards(
                context.shards, mode=self.identity_mode
            )

            for slog in self.scanner.scan_logs:
                context.audit_log.append(f"Stage 3 Audit: {slog}")

            if not context.identities:
                context.audit_log.append("Stage 3: No valid K8s identity found")
                return {"success": False, "skipped": True}

            primary = context.identities[0]
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
        except Exception as e:
            return {"success": False, "error": e}
