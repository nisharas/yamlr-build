#!/usr/bin/env python3
"""
Port Mismatch Healer - Semantic Alignment
-------------------------------------------
Automatically aligns Service targetPorts with Container ports if they
are mismatched but clearly intended to link.

[PRO-12-05] Enhancement: Added Strategy B (named-port fuzzy matching)
to handle multi-port workloads where the Service references a port by
name (e.g. 'http-svc') and the container defines a close match (e.g. 'http').
"""

from __future__ import annotations
import difflib
import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from yamlr.models import ManifestIdentity, WORKLOAD_KINDS

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.semantic.port")

# Minimum similarity ratio to accept a named-port fuzzy match (0.0–1.0).
# 0.60 captures realistic K8s port-name suffix typos (e.g. 'http-svc' → 'http')
# while rejecting completely unrelated names (e.g. 'redis-port' vs 'http' ~0.25).
_NAMED_PORT_SIMILARITY_THRESHOLD = 0.60
__all__ = ['PortMismatchHealer']



class PortMismatchHealer:
    """Aligns Service targetPorts with workload container ports.

    Why: Kubernetes Services that reference the wrong targetPort fail
         silently — traffic is sent nowhere. This healer catches two
         categories of mismatch:
           A. Single-container-port ambiguity (original strategy).
           B. Named-port typos on multi-port workloads (new PRO-12-05 strategy).
    """
    def heal_docs(self, docs: List[Dict[str, Any]], identities: List[ManifestIdentity], context: Optional["HealContext"] = None) -> int:
        """Scan and align ports in-place within the documents.
        
        Why: Decomposed to resolve SonarQube complexity warnings per Audit Round 24.
        """
        modified_count = 0
        workloads = [ident for ident in identities if ident.kind in WORKLOAD_KINDS]

        for doc in docs:
            if doc.get("kind") != "Service":
                continue
            
            if self._heal_service_ports(doc, workloads, docs, context):
                modified_count += 1
                
        return modified_count

    def _heal_service_ports(self, doc: Dict[str, Any], workloads: List[ManifestIdentity], all_docs: List[Dict[str, Any]], context: Optional["HealContext"]) -> bool:
        """Heals ports for a single Service document."""
        spec = doc.get("spec")
        if not (isinstance(spec, dict) and spec.get("selector") and isinstance(spec.get("ports"), list)):
            return False
            
        svc_meta = doc.get("metadata", {})
        svc_name = svc_meta.get("name", "unknown")
        svc_ns = svc_meta.get("namespace", "default")
        
        target_workload = self._find_matching_workload(spec["selector"], svc_ns, workloads)
        if not (target_workload and target_workload.container_ports):
            return False
            
        w_ports = [str(p) for p in target_workload.container_ports]
        w_port_names = self._extract_named_ports(target_workload, all_docs)
        
        doc_modified = False
        for s_port in spec["ports"]:
            if not isinstance(s_port, dict):
                continue
            if self._align_port_entry(s_port, w_ports, w_port_names, svc_name, target_workload, context):
                doc_modified = True
                
        return doc_modified

    def _find_matching_workload(self, selector: Dict[str, str], namespace: str, workloads: List[ManifestIdentity]) -> Optional[ManifestIdentity]:
        """Finds the workload targeted by the Service selector."""
        for w in workloads:
            if (w.namespace or "default") == namespace and self._labels_match(selector, w.labels):
                return w
        return None

    def _align_port_entry(self, s_port: Dict[str, Any], w_ports: List[str], w_port_names: Dict[str, int], svc_name: str, target_workload: ManifestIdentity, context: Optional["HealContext"]) -> bool:
        """Aligns a single port entry using multi-strategy logic."""
        target = s_port.get("targetPort", s_port.get("port"))
        if not target or str(target) in w_ports:
            return False
            
        # Strategy A: Single-port ambiguity
        if len(w_ports) == 1:
            return self._apply_strategy_a(s_port, target, w_ports[0], svc_name, target_workload, context)
            
        # Strategy B: Named-port fuzzy matching
        if isinstance(target, str) and w_port_names:
            return self._apply_strategy_b(s_port, target, w_port_names, svc_name, context)
            
        return False

    def _apply_strategy_a(self, s_port: Dict[str, Any], old_target: Any, new_target: str, svc_name: str, target_workload: ManifestIdentity, context: Optional["HealContext"]) -> bool:
        """Strategy A: Single-container-port auto-alignment."""
        try:
            val = int(new_target)
        except ValueError:
            val = new_target
            
        s_port["targetPort"] = val
        logger.info(
            f"✨ Port Surgery [A]: Service '{svc_name}' targetPort "
            f"{old_target} → {val} (aligned with "
            f"{target_workload.kind}/{target_workload.name})"
        )
        if context:
            from yamlr.models import HealAction
            from yamlr.core.stages.boundaries import MutationScope
            context.prescribe(HealAction(
                stage="PortHealer",
                action_type="repair",
                target=f"Service/{svc_name}.spec.ports",
                description=f"Aligned Service targetPort {old_target} -> {val}",
                rationale=f"The Service targetPort was ambiguous or mismatched. Aligned with the single available container port in workload {target_workload.kind}/{target_workload.name}.",
                suggestion="Ensure targetPort matches a valid containerPort or port name in the target Pod.",
                severity="warning",
                rule_id="rule/port-mismatch",
                scope=MutationScope.SPEC_PORTS
            ))
        return True

    def _apply_strategy_b(self, s_port: Dict[str, Any], target_name: str, w_port_names: Dict[str, int], svc_name: str, context: Optional["HealContext"]) -> bool:
        """Strategy B: Named-port fuzzy matching."""
        best_num, ratio = self._fuzzy_match_named_port(target_name, w_port_names)
        if best_num is not None and ratio >= _NAMED_PORT_SIMILARITY_THRESHOLD:
            s_port["targetPort"] = best_num
            logger.info(
                f"✨ Port Surgery [B]: Service '{svc_name}' targetPort "
                f"'{target_name}' → {best_num} (fuzzy matched named port, "
                f"score={ratio:.2f})"
            )
            if context:
                from yamlr.models import HealAction
                from yamlr.core.stages.boundaries import MutationScope
                context.prescribe(HealAction(
                    stage="PortHealer",
                    action_type="repair",
                    target=f"Service/{svc_name}.spec.ports",
                    description=f"Aligned fuzzy Service targetPort '{target_name}' -> {best_num}",
                    rationale=f"The Service targetPort name '{target_name}' was a fuzzy match for container port {best_num} (score: {ratio:.2f}).",
                    suggestion="Use the exact containerPort number or name defined in the Pod spec.",
                    severity="warning",
                    rule_id="rule/fuzzy-port-match",
                    scope=MutationScope.SPEC_PORTS
                ))
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _labels_match(
        self, selector: Dict[str, str], labels: Optional[Dict[str, str]]
    ) -> bool:
        """Returns True if all selector keys/values are present in the labels.

        Why: Services select Pods by labels; we replicate that matching logic.
        """
        if not labels:
            return False
        for k, v in selector.items():
            if labels.get(k) != v:
                return False
        return True
    def _extract_named_ports(
        self,
        workload: ManifestIdentity,
        docs: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Builds a {port_name: port_number} map from a workload's containers."""
        doc = self._find_workload_doc(workload, docs)
        if not doc:
            return {}
            
        containers = (
            doc.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
        return self._collect_container_ports(containers)

    def _find_workload_doc(self, workload: ManifestIdentity, docs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Finds the raw document corresponding to a ManifestIdentity."""
        for doc in docs:
            if (
                doc.get("kind") == workload.kind
                and doc.get("metadata", {}).get("name") == workload.name
            ):
                return doc
        return None

    def _collect_container_ports(self, containers: List[Dict[str, Any]]) -> Dict[str, int]:
        """Collects all named ports from a list of containers."""
        named: Dict[str, int] = {}
        for container in containers:
            for port_def in container.get("ports", []):
                if isinstance(port_def, dict):
                    name = port_def.get("name")
                    num = port_def.get("containerPort")
                    if name and num:
                        named[str(name)] = int(num)
        return named

    def _fuzzy_match_named_port(
        self,
        target_name: str,
        named_ports: Dict[str, int],
    ) -> Tuple[Optional[int], float]:
        """Finds the best matching named port for a given target name string.

        Why: Developers often mistype port names (e.g. 'http-svc' vs 'http').
             difflib.SequenceMatcher gives a deterministic similarity score,
             satisfying the Determinism gate.

        Args:
            target_name: The (possibly incorrect) port name from the Service.
            named_ports: The {name: number} map from the workload.

        Returns:
            Tuple of (best_port_number, similarity_ratio). Returns (None, 0.0)
            if no suitable match is found.
        """
        best_number: Optional[int] = None
        best_ratio: float = 0.0

        for port_name, port_number in named_ports.items():
            ratio = difflib.SequenceMatcher(
                None, target_name.lower(), port_name.lower()
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_number = port_number

        return best_number, best_ratio
