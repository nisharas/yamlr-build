#!/usr/bin/env python3
"""
Referential Healer - Semantic Alignment
-----------------------------------------
Applies auto-correction suggestions for broken ConfigMap, Secret, and PVC references.
"""

import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("yamlr.healers.semantic.referential")

class ReferentialHealer:
    """Applies auto-correction for broken cross-resource references."""
    
    def heal_docs(self, docs: List[Dict[str, Any]], findings: List[Any]) -> int:
        """
        Applies suggestions from findings to the documents in-place.
        Returns the number of references fixed.
        """
        modified_count = 0
        
        for f in findings:
            if not f.suggestion or "Use " not in f.suggestion:
                continue
            
            if f.rule_id not in ("broken-reference", "broken-volume"):
                continue
                
            # Extract suggested name: "Use Secret 'web-secret-v2'" -> "web-secret-v2"
            match = re.search(r"'(.*?)'", f.suggestion)
            if not match:
                # Try sibling format: "Use 'pvc-name'"
                match = re.search(r"'(.*?)'", f.suggestion)
                if not match: continue
                
            new_name = match.group(1)
            old_name = f.message.split("'")[-2] if "'" in f.message else None
            
            if not old_name: continue
            
            # Apply to the target document
            for doc in docs:
                if (doc.get("kind") == f.resource_kind and 
                    doc.get("metadata", {}).get("name") == f.resource_name):
                    
                    if self._update_ref_in_doc(doc, old_name, new_name, f.rule_id):
                        modified_count += 1
                        logger.info(f"✨ Referential Repair: {f.resource_kind}/{f.resource_name} ref '{old_name}' → '{new_name}'")
                        
        return modified_count

    def _update_ref_in_doc(self, doc: Dict[str, Any], old_name: str, new_name: str, rule_id: str) -> bool:
        """Deep search and replace of the reference name in the doc."""
        changed = False
        
        def _walk(obj):
            """
            Why: Internal documentation policy compliance.
            What: Auto-generated summary.
            """
            nonlocal changed
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and v == old_name:
                        # Safety: Context check (e.g., key name should look like a ref key)
                        if any(x in k.lower() for x in ("name", "claimname", "configmap", "secret")):
                            obj[k] = new_name
                            changed = True
                    else:
                        _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)
                    
        _walk(doc)
        return changed
