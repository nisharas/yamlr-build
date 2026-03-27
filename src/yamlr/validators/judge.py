#!/usr/bin/env python3
"""
Yamlr JUDGE - The Safety Verdict Engine
---------------------------------------
Performs pre-flight validation on reconstructed objects.
Provides the 'Safety Verdict' (Passed/Critical) and the 0-100 Trust Score.
Part of VAL-02-8 Heritage Port.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-03-10
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Tuple, List, Union, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from yamlr.core.parser.base import YamlrNode

logger = logging.getLogger("yamlr.validators.judge")
__all__ = ['KubeJudge']


class KubeJudge:
    """
    The High-Level Safety Gate.
    Issues the final verdict on the 'surgery' performed.
    """

    def __init__(self, catalog: Dict[Tuple[str, str], Any], deep_array_check: bool = False):
        """
        Why: Cross-referencing reconstructed objects against schema-level
             requirements is the only way to guarantee "Zero-Failure" trust.
        """
        self.catalog = catalog
        self.deep_array_check = deep_array_check
        self.required_fields = ["apiVersion", "kind", "metadata"]
        try:
            from yamlr.validators.schema_validator import SchemaValidator
            # [ROUND-10] Fix: Pass catalog to SchemaValidator to satisfy required argument
            self._validator = SchemaValidator(catalog)
        except ImportError:
            self._validator = None

    def judge_all(
        self, 
        docs: List[Union[dict, "YamlrNode"]], 
        strict: bool = False,
        pre_calculated: Optional[Dict[int, List[Any]]] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Validates all documents and produces an aggregate safety profile.
        """
        if not docs:
            return True, ["No documents encountered."], 100

        all_valid = True
        messages = []
        total_score = 0
        
        for i, doc in enumerate(docs):
            # Check for pre-calculated findings for this document
            doc_findings = pre_calculated.get(i) if pre_calculated else None
            
            valid, msg = self.validate_structure(doc, strict=strict, pre_calculated_findings=doc_findings)
            score = self.calculate_trust_score(valid, doc)
            total_score += score
            
            status = "PASSED" if valid else "CRITICAL"
            if not valid: all_valid = False
            messages.append(f"Document[{i}] {status}: {msg}")

        return all_valid, messages, total_score // len(docs)

    def validate_structure(
        self, 
        doc: Union[dict, "YamlrNode"], 
        strict: bool = False,
        pre_calculated_findings: Optional[List[Any]] = None
    ) -> Tuple[bool, str]:
        """Performs structural integrity check on a single resource."""
        from yamlr.core.parser.base import YamlrNode
        
        # [MODULAR-REFACTOR] Convert to dict once for validation
        if isinstance(doc, YamlrNode):
            # [ROUND-10] Defensive check: if doc is not dict-like, return failure
            if not isinstance(doc, dict) and not hasattr(doc, "to_dict") and not hasattr(doc, "keys"):
                return False, "Not a valid dictionary structure."

            doc_dict = doc.to_dict() if hasattr(doc, "to_dict") else {k: doc[k] for k in doc.keys()}
        elif isinstance(doc, dict):
            doc_dict = doc
        else:
            return False, "Not a valid dictionary structure."

        # 1. Identity Gate
        for field in self.required_fields:
            if field not in doc_dict or doc_dict[field] is None:
                return False, f"Structural Violation: Missing required field '{field}'."

        # 2. Leverage SchemaValidator results (Unified Architecture)
        findings = pre_calculated_findings
        
        if findings is None and self._validator:
             # Fallback to direct validation if no pre-calculated results
             findings = self._validator.validate_full_document(doc_dict, deep_array_check=self.deep_array_check)
        
        if findings:
             # Filter for ERROR findings only for structural verdict
             errors = [f for f in findings if f.severity == "ERROR"]
             if errors:
                 return False, f"Schema Failure: {errors[0].message}"
            
        return True, "Structural integrity verified."

    def calculate_trust_score(self, is_valid: bool, doc: Any) -> int:
        """Calculates 0-100 Confidence Metric."""
        score = 50
        if is_valid: 
            score += 30
        
        # [MODULAR-REFACTOR] Safe attribute/key access
        kind = getattr(doc, "kind", None) or (doc.get("kind") if hasattr(doc, "get") else None)
        api = getattr(doc, "apiVersion", None) or (doc.get("apiVersion") if hasattr(doc, "get") else None)
        if kind and api: 
            score += 10
        
        metadata = getattr(doc, "metadata", None) or (doc.get("metadata") if hasattr(doc, "get") else None)
        if metadata:
            name = getattr(metadata, "name", None) or (metadata.get("name") if hasattr(metadata, "get") else None)
            if name: 
                score += 10
                
        return max(0, min(100, score))
