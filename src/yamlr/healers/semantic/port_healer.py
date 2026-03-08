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

import difflib
import logging
from typing import List, Dict, Any, Optional, Tuple

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.healers.semantic.port")

# Minimum similarity ratio to accept a named-port fuzzy match (0.0–1.0).
# 0.60 captures realistic K8s port-name suffix typos (e.g. 'http-svc' → 'http')
# while rejecting completely unrelated names (e.g. 'redis-port' vs 'http' ~0.25).
_NAMED_PORT_SIMILARITY_THRESHOLD = 0.60


class PortMismatchHealer:
    """Aligns Service targetPorts with workload container ports.

    Why: Kubernetes Services that reference the wrong targetPort fail
         silently — traffic is sent nowhere. This healer catches two
         categories of mismatch:
           A. Single-container-port ambiguity (original strategy).
           B. Named-port typos on multi-port workloads (new PRO-12-05 strategy).
    """

    def heal_docs(self, docs: List[Dict[str, Any]], identities: List[ManifestIdentity]) -> int:
        """Scan and align ports in-place within the documents.

        Why: Mutates docs directly (same approach as SelectorAlignment)
             to remain compatible with the pipeline's stage contract.

        Args:
            docs: List of parsed YAML documents (dicts).
            identities: Pre-built identity objects with container_ports.

        Returns:
            Number of Service documents that were modified.
        """
        modified_count = 0

        # 1. Build Workload Index
        workloads = [
            ident for ident in identities
            if ident.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod")
        ]

        # 2. Iterate through Services
        for doc in docs:
            if doc.get("kind") != "Service":
                continue

            spec = doc.get("spec")
            if not spec or not isinstance(spec, dict):
                continue

            selector = spec.get("selector")
            if not selector or not isinstance(selector, dict):
                continue

            ports = spec.get("ports")
            if not ports or not isinstance(ports, list):
                continue

            svc_name = doc.get("metadata", {}).get("name")
            svc_ns = doc.get("metadata", {}).get("namespace", "default")

            # 3. Find matching workloads
            matches = [
                w for w in workloads
                if (w.namespace or "default") == svc_ns
                and self._labels_match(selector, w.labels)
            ]

            logger.debug(f"Service {svc_name}: Found {len(matches)} matching workloads")
            if not matches:
                continue

            target_workload = matches[0]
            logger.debug(
                f"Target workload: {target_workload.kind}/{target_workload.name}, "
                f"Ports: {target_workload.container_ports}"
            )
            if not target_workload.container_ports:
                continue

            w_ports = [str(p) for p in target_workload.container_ports]
            w_port_names = self._extract_named_ports(target_workload, docs)

            doc_modified = False
            for s_port in ports:
                if not isinstance(s_port, dict):
                    continue

                target = s_port.get("targetPort", s_port.get("port"))
                if not target:
                    continue

                # Skip if the target port is already a valid numeric match.
                if str(target) in w_ports:
                    continue

                # --- STRATEGY A: Single-container-port auto-alignment ---
                # If the workload exposes exactly one port, it is unambiguous.
                if len(w_ports) == 1:
                    new_target = w_ports[0]
                    try:
                        new_target = int(new_target)
                    except ValueError:
                        pass
                    s_port["targetPort"] = new_target
                    doc_modified = True
                    logger.info(
                        f"✨ Port Surgery [A]: Service '{svc_name}' targetPort "
                        f"{target} → {new_target} (aligned with "
                        f"{target_workload.kind}/{target_workload.name})"
                    )
                    continue

                # --- STRATEGY B: Named-port fuzzy matching ---
                # If the targetPort is a string (named port reference) and the
                # workload exposes multiple named ports, fuzzy-match to find
                # the closest intended port number.
                if isinstance(target, str) and w_port_names:
                    best_port_num, best_ratio = self._fuzzy_match_named_port(
                        target, w_port_names
                    )
                    if best_port_num is not None and best_ratio >= _NAMED_PORT_SIMILARITY_THRESHOLD:
                        s_port["targetPort"] = best_port_num
                        doc_modified = True
                        logger.info(
                            f"✨ Port Surgery [B]: Service '{svc_name}' targetPort "
                            f"'{target}' → {best_port_num} (fuzzy matched named port, "
                            f"score={best_ratio:.2f})"
                        )

            if doc_modified:
                modified_count += 1

        return modified_count

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
        """Builds a {port_name: port_number} map from a workload's containers.

        Why: `ManifestIdentity.container_ports` stores only numbers. This
             method digs into the raw doc to retrieve named port entries so
             Strategy B can do name-to-number resolution.

        Args:
            workload: The matched ManifestIdentity.
            docs: Full list of documents (used to find the raw workload YAML).

        Returns:
            Dict mapping port name → container port number.
        """
        named: Dict[str, int] = {}
        for doc in docs:
            if (
                doc.get("kind") == workload.kind
                and doc.get("metadata", {}).get("name") == workload.name
            ):
                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    for port_def in container.get("ports", []):
                        if isinstance(port_def, dict):
                            port_name = port_def.get("name")
                            port_num = port_def.get("containerPort")
                            if port_name and port_num:
                                named[str(port_name)] = int(port_num)
                break
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
