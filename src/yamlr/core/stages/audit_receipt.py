#!/usr/bin/env python3
"""
Yamlr AUDIT RECEIPT STAGE
-------------------------
Stage 11: Generates a cryptographic audit receipt of the healing process.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from yamlr.core.context import HealContext
from yamlr.core.dna_utils import calculate_semantic_dna
from yamlr.core.receipts import ReceiptManager
from yamlr.core.stages.base import PipelineStage

logger = logging.getLogger("yamlr.pipeline.stages.audit")
__all__ = ['StageElevenAuditReceipt']


class StageElevenAuditReceipt(PipelineStage):
    """Stage 11: Generate Semantic DNA Receipt for compliance auditing."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.manager = ReceiptManager()

    def run(self, context: HealContext) -> Dict[str, Any]:
        """
        Why: To provide signed proof of what was changed and why.
        """
        # Generate receipt
        raw_dna = getattr(context, 'raw_dna', 'hash-pending')
        # If Stage 6 didn't run (e.g. no docs), use what we have
        healed_dna = calculate_semantic_dna(context.docs) if context.docs else raw_dna
        
        receipt = self.manager.generate_receipt(
            file_path=str(context.file_path or 'unknown'),
            original_dna=raw_dna,
            healed_dna=healed_dna,
            findings=context.findings
        )
        
        # 1. External Receipt File
        import json
        receipt_json = json.dumps(receipt, indent=2)
        receipt_name = f"{Path(context.file_path).name}.yamlr-receipt.json" if context.file_path else "audit.yamlr-receipt.json"
        receipt_path = Path.cwd() / receipt_name
        receipt_path.write_text(receipt_json, encoding="utf-8")
        
        # 2. Embedded Receipt Footer (Trust Anchor)
        compact_receipt = json.dumps({
            "dna": healed_dna[:16],
            "sig": receipt["signature"][:16],
            "ts": receipt["timestamp"]
        }, separators=(",", ":"))
        
        footer = f"\n# ---\n# [Yamlr-Receipt-of-Integrity]: {compact_receipt}\n"
        
        context.evidence_receipt = str(receipt_path)
        context.audit_log.append(f"Stage 11: Generated Audit Receipt [DNA: {healed_dna[:8]}]")
        
        return {
            "success": True, 
            "receipt": str(receipt_path),
            "receipt_footer": footer,
            "receipt_data": receipt
        }
