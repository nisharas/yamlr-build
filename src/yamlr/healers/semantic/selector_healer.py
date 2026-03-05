#!/usr/bin/env python3
"""
Service Selector Healer - Semantic Alignment
---------------------------------------------
Automatically aligns Service selectors with Workload labels if they
are clearly intended to match but have typos or mismatches.
"""

import logging
import difflib
from typing import List, Dict, Any, Optional
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.healers.semantic.selector")

class ServiceSelectorHealer:
    """Aligns Service selectors with workload labels."""
    
    def heal_docs(self, docs: List[Dict[str, Any]], identities: List[ManifestIdentity]) -> int:
        """
        Scan and align selectors in-place within the documents.
        Returns the number of services fixed.
        """
        modified_count = 0
        
        # 1. Build Workload Index
        workloads = [ident for ident in identities if ident.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod")]
        
        # 2. Extract Services from docs to modify them in-place
        for doc in docs:
            if doc.get("kind") != "Service":
                continue
                
            spec = doc.get("spec")
            if not spec or not isinstance(spec, dict):
                continue
                
            selector = spec.get("selector")
            if not selector or not isinstance(selector, dict):
                continue
                
            svc_name = doc.get("metadata", {}).get("name")
            svc_ns = doc.get("metadata", {}).get("namespace", "default")
            
            # 3. Check if current selector matches anything
            if self._matches_existing(selector, svc_ns, workloads):
                continue # Already working
                
            # 4. Attempt to find the "Intended" workload
            # Strategy A: Find workload with same name in same namespace
            target_workload = self._find_target_by_name(svc_name, svc_ns, workloads)
            
            # Strategy B: If no name match, find best fuzzy match for selector
            if not target_workload:
                target_workload = self._find_best_fuzzy_match(selector, svc_ns, workloads)
            
            if target_workload and target_workload.labels:
                # 5. Align Selector
                # We only want to align if the workload has a subset of labels that look like the selector
                # OR if the name match is strong enough.
                
                logger.info(f"Aligning Service '{svc_name}' selector with {target_workload.kind}/{target_workload.name}")
                
                # We update the selector to match the target workload's labels
                # (Ideally we only take the relevant labels, but taking all is safer than having a broken service)
                # Actually, many workloads have extra labels (heritage, chart, etc.).
                # A better approach: fix the typos in specific keys if they are close.
                
                # For now, let's take the labels from the workload that were ALMOST matched, 
                # or just use the common standard labels.
                
                new_selector = self._suggest_fixed_selector(selector, target_workload.labels)
                if new_selector != selector:
                    spec["selector"] = new_selector
                    modified_count += 1
                    logger.info(f"  → Fixed selector: {selector} -> {new_selector}")
                    
        return modified_count

    def _matches_existing(self, selector: Dict[str, str], namespace: str, workloads: List[ManifestIdentity]) -> bool:
        """Checks if selector already matches any workload."""
        for w in workloads:
            if (w.namespace or "default") == namespace:
                if w.labels and all(w.labels.get(k) == v for k, v in selector.items()):
                    return True
        return False

    def _find_target_by_name(self, name: str, namespace: str, workloads: List[ManifestIdentity]) -> Optional[ManifestIdentity]:
        """Finds workload with the same name (often intended target)."""
        for w in workloads:
            if w.name == name and (w.namespace or "default") == namespace:
                return w
        return None

    def _find_best_fuzzy_match(self, selector: Dict[str, str], namespace: str, workloads: List[ManifestIdentity]) -> Optional[ManifestIdentity]:
        """Finds workload with most similar label set."""
        best_w = None
        best_score = 0.5 # Minimum 50% similarity
        
        for w in workloads:
            if (w.namespace or "default") != namespace or not w.labels:
                continue
                
            score = self._calculate_label_similarity(selector, w.labels)
            if score > best_score:
                best_score = score
                best_w = w
                
        return best_w

    def _calculate_label_similarity(self, selector: Dict[str, str], labels: Dict[str, str]) -> float:
        """Calculates similarity score (0.0 to 1.0)."""
        matches = 0
        total = len(selector)
        
        for k, v in selector.items():
            # Exact match
            if labels.get(k) == v:
                matches += 1
            # Key exists but value mismatch (fuzzy check)
            elif k in labels:
                sim = difflib.SequenceMatcher(None, str(v), str(labels[k])).ratio()
                matches += sim * 0.8 # Value typos are very likely
            # Key typo?
            else:
                for wk in labels:
                    sim = difflib.SequenceMatcher(None, k, wk).ratio()
                    # Lower threshold if values match exactly
                    threshold = 0.5 if labels[wk] == v else 0.8
                    if sim > threshold:
                        # Value match on the fuzzy key
                        if labels[wk] == v:
                            matches += max(sim, 0.8) * 0.9 # High confidence if value matches
                        else:
                            val_sim = difflib.SequenceMatcher(None, str(v), str(labels[wk])).ratio()
                            matches += sim * val_sim * 0.7
                        break
        
        return matches / total

    def _suggest_fixed_selector(self, selector: Dict[str, str], labels: Dict[str, str]) -> Dict[str, str]:
        """Generates a fixed selector based on actual workload labels."""
        fixed = {}
        for k, v in selector.items():
            if labels.get(k) == v:
                fixed[k] = v
            elif k in labels:
                # Use actual value if key is correct
                fixed[k] = labels[k]
            else:
                # Look for the fuzzy key we matched earlier
                found = False
                for wk in labels:
                    sim = difflib.SequenceMatcher(None, k, wk).ratio()
                    threshold = 0.5 if labels[wk] == v else 0.8
                    if sim > threshold:
                        fixed[wk] = labels[wk]
                        found = True
                        break
                if not found:
                    # Keep if we can't find anything better (fallback)
                    fixed[k] = v
        return fixed
