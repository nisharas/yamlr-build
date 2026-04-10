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
from typing import TYPE_CHECKING, Optional, Any, Dict, List

from yamlr.core.stages.base import PipelineStage, PipelineState, StageResult
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.pipeline.stages.identity")

class IdentityStage(PipelineStage):
    """
    Stage: Identify K8s Resources.
    
    Why: To extract the Identity DNA (Kind, APIVersion, Name) from raw shards.
    """

    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        super().__init__(name="Identity")
        self.catalog = catalog or {}

    def execute(self, state: PipelineState) -> StageResult:
        """
        Extracts resource identities from shards.
        """
        from yamlr.parsers.scanner import YamlrScanner
        scanner = YamlrScanner(catalog=self.catalog)
        
        try:
            # 1. Primary Scan
            identities = scanner.scan_shards(state.shards)
            
            # 2. Update state
            state.identities.extend(identities)
            
            # 3. Label file path on all identities
            # No relative_path on PipelineState yet?
            # I'll add it if needed, but for now we skip path labelling.
            
            return StageResult(
                success=True,
                metadata={"identity_count": len(identities)}
            )
        except Exception as e:
            logger.error(f"IdentityStage failed: {e}")
            return StageResult(success=False, errors=[str(e)])
