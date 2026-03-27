#!/usr/bin/env python3
"""
Yamlr SORTER - Enterprise Aesthetic Engine (Pro)
-----------------------------------------------
Handles schema-aware field reordering and comment grafting.
Part of VAL-02-8 Heritage Port.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-03-10
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from yamlr.core.sorting import SortingEngine

class SchemaAwareSorter(SortingEngine):
    """
    Enterprise Aesthetic Engine (Pro Bridge).
    Now inherits from Core SortingEngine to ensure a single source of truth.
    """
    
    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        """
        Why: Maintains compatibility with legacy Pro-tier initializers.
        """
        self.catalog = catalog or {}

    def sort_doc(self, data: Any, kind: Optional[str] = None) -> Any:
        """
        Legacy Bridge: Reorders keys using the consolidated Core engine.
        
        Why: Ensures existing Pro-tier callers (like Exporter) remain functional
             while benefiting from the centralized logic.
        """
        if hasattr(data, "keys") and hasattr(data, "move_to_end"):
            # If it's a YamlrNode, use the recursive reorder logic
            self.reorder_node(data, kind=kind, catalog=self.catalog)
            return data
            
        # Fallback for raw primitives (rare in the main pipeline)
        return data
