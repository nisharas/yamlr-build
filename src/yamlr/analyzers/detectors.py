#!/usr/bin/env python3
"""
Yamlr CROSS-RESOURCE DETECTORS
------------------------------
Core detection algorithms for multi-resource analysis.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import difflib
import logging
from typing import Dict, List, Optional, Tuple
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.detectors")

class CrossResourceDetectors:
    """
    Collection of detection algorithms for K8s resource relationships.
    Optimized for high-volume scans using O(N) indexing.
    """

    @staticmethod
    def detect_ghost_services(services: List[ManifestIdentity], workloads: List[ManifestIdentity], pro_mode: bool = False) -> List[Dict]:
        """Detects Services with selectors that match no Pods."""
        ghost_services = []
        
        # O(N) Optimization: Index workloads by their labels
        # index[namespace][label_key][label_value] = [workload_names]
        workload_index: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        for w in workloads:
            ns = w.namespace or "default"
            if not w.labels: continue
            
            ns_idx = workload_index.setdefault(ns, {})
            for k, v in w.labels.items():
                ns_idx.setdefault(k, {}).setdefault(str(v), []).append(w.name)

        for service in services:
            if not service.selector: continue
            
            ns = service.namespace or "default"
            ns_idx = workload_index.get(ns, {})
            
            if not ns_idx:
                matches = []
            else:
                # To match a service selector, a workload must have ALL the labels in the selector
                match_sets = []
                for k, v in service.selector.items():
                    val_matches = ns_idx.get(k, {}).get(str(v), [])
                    if not val_matches:
                        match_sets = []
                        break
                    match_sets.append(set(val_matches))
                
                if not match_sets:
                    matches = []
                else:
                    matches = list(set.intersection(*match_sets))
            
            if not matches:
                hint = CrossResourceDetectors._generate_hint(service, workloads, pro_mode)
                ghost_services.append({
                    "name": service.name,
                    "namespace": ns,
                    "hint": hint,
                    "file_path": getattr(service, "file_path", "unknown"),
                })
        return ghost_services

    @staticmethod
    def detect_orphan_configs(configs: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
        """Detects ConfigMaps/Secrets that no Pod references."""
        # O(N) Optimization: Pre-calculate sets of all referenced configs and secrets
        referenced_configs = set()
        referenced_secrets = set()
        for w in workloads:
            referenced_configs.update(w.config_refs)
            referenced_secrets.update(w.secret_refs)

        orphans = []
        for config in configs:
            target_set = referenced_secrets if config.kind == "Secret" else referenced_configs
            if config.name not in target_set:
                orphans.append({
                    "kind": config.kind,
                    "name": config.name,
                    "namespace": config.namespace or "default",
                    "file_path": getattr(config, "file_path", "unknown"),
                })
        return orphans

    @staticmethod
    def detect_broken_volumes(workloads: List[ManifestIdentity], pvcs: List[ManifestIdentity]) -> List[Dict]:
        """Detects workloads referencing non-existent PVCs with fuzzy suggestion."""
        broken = []
        pvc_names = {p.name for p in pvcs}
        pvc_names_list = list(pvc_names)

        for w in workloads:
            for pvc_ref in w.volume_refs:
                if pvc_ref not in pvc_names:
                    # Fuzzy match for typo in PVC reference
                    best_match = None
                    if pvc_names_list:
                        matches = difflib.get_close_matches(pvc_ref, pvc_names_list, n=1, cutoff=0.7)
                        if matches: best_match = matches[0]

                    broken.append({
                        "workload_kind": w.kind,
                        "workload_name": w.name,
                        "missing_pvc": pvc_ref,
                        "namespace": w.namespace or "default",
                        "file_path": getattr(w, "file_path", "unknown"),
                        "suggestion": f"Use '{best_match}'" if best_match else f"Ensure PVC '{pvc_ref}' exists."
                    })
        return broken

    @staticmethod
    def detect_broken_refs(workloads: List[ManifestIdentity], configs: List[ManifestIdentity]) -> List[Dict]:
        """Detects broken ConfigMap/Secret references with fuzzy suggestions."""
        broken = []
        cm_names = {c.name for c in configs if c.kind == "ConfigMap"}
        sec_names = {c.name for c in configs if c.kind == "Secret"}
        
        cm_list = list(cm_names)
        sec_list = list(sec_names)

        for w in workloads:
            # Check ConfigMaps
            for ref in w.config_refs:
                if ref not in cm_names:
                    match = difflib.get_close_matches(ref, cm_list, n=1, cutoff=0.7)
                    broken.append({
                        "kind": "ConfigMap",
                        "name": ref,
                        "resource_name": w.name,
                        "resource_kind": w.kind,
                        "namespace": w.namespace or "default",
                        "file_path": getattr(w, "file_path", "unknown"),
                        "suggestion": f"Use ConfigMap '{match[0]}'" if match else None
                    })
            # Check Secrets
            for ref in w.secret_refs:
                if ref not in sec_names:
                    match = difflib.get_close_matches(ref, sec_list, n=1, cutoff=0.7)
                    broken.append({
                        "kind": "Secret",
                        "name": ref,
                        "resource_name": w.name,
                        "resource_kind": w.kind,
                        "namespace": w.namespace or "default",
                        "file_path": getattr(w, "file_path", "unknown"),
                        "suggestion": f"Use Secret '{match[0]}'" if match else None
                    })
        return broken

    @staticmethod
    def _labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
        """Checks if a selector matches a set of labels (Robust)."""
        for key, value in selector.items():
            target = labels.get(key)
            if target is None or str(target).strip() != str(value).strip():
                return False
        return True

    @staticmethod
    def _generate_hint(service: ManifestIdentity, workloads: List[ManifestIdentity], pro_mode: bool) -> str:
        """Generates an actionable hint for fixing a ghost service."""
        selector_yaml = "\n        ".join(f"{k}: {v}" for k, v in service.selector.items())
        hint = f"Add a Deployment with matching labels:\n    spec:\n      template:\n        metadata:\n          labels:\n            {selector_yaml}"
        
        # Optimization: Only perform fuzzy matching if workloads list is manageable 
        # or if we are in pro mode. Fuzzy matching at 20k workloads is too slow.
        if len(workloads) > 1000 and not pro_mode:
            return hint + "\n    (Fuzzy matching disabled for large datasets in OSS mode)"

        # Check for typos
        candidates = []
        for w in workloads:
            if not w.labels: continue
            # Basic key match check before expensive difflib
            if any(k in w.labels for k in service.selector):
                score = sum(difflib.SequenceMatcher(None, f"{k}={v}", f"{wk}={wv}").ratio() 
                            for k, v in service.selector.items() 
                            for wk, wv in w.labels.items() if k == wk or difflib.SequenceMatcher(None, k, wk).ratio() > 0.8)
                if score > 0.7 * len(service.selector):
                    candidates.append(f"{w.kind}/{w.name}")
        
        if candidates:
            hint += f"\n\n    💡 Potential matches found: {', '.join(candidates[:3])}"
        
        if pro_mode:
            hint += "\n    (Enterprise mode will auto-generate this in a future release)"
        return hint
