#!/usr/bin/env python3
"""
Yamlr NETWORK LOGIC DETECTORS
------------------------------
Specialized logic for validating Services and Ingress relationships.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import logging
from typing import Dict, List

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.network")
__all__ = ["NetworkDetectors"]


class NetworkDetectors:
    """
    Validation logic for K8s Service ports and Ingress backends.
    """

    @staticmethod
    def validate_service_ports(services: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
        """Validates that Service targetPorts actually exist in the backing Pods - Optimized O(N)."""
        mismatches = []

        # O(N) Optimization: Index workloads by their labels
        workload_index: Dict[str, Dict[str, Dict[str, List[int]]]] = {}
        id_to_workload = {id(w): w for w in workloads}

        for w in workloads:
            ns = w.namespace or "default"
            if not w.labels:
                continue

            ns_idx = workload_index.setdefault(ns, {})
            for k, v in w.labels.items():
                ns_idx.setdefault(k, {}).setdefault(str(v), []).append(id(w))

        for service in services:
            if not service.selector or not service.service_ports:
                continue

            ns = service.namespace or "default"
            ns_idx = workload_index.get(ns, {})

            if not ns_idx:
                matches = []
            else:
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
                    match_ids = set.intersection(*match_sets)
                    matches = [id_to_workload[wid] for wid in match_ids]

            for workload in matches:
                if not (workload.container_ports or []):
                    continue
                w_ports = [str(p) for p in (workload.container_ports or [])]
                for s_port in service.service_ports or []:
                    # [Zero-Blindspot] Support both dict and shorthand string ports
                    if isinstance(s_port, str):
                        target = s_port
                    elif isinstance(s_port, dict):
                        target = s_port.get("targetPort", s_port.get("port"))
                    else:
                        continue

                    if target and str(target) not in w_ports:
                        mismatches.append(
                            {
                                "service_name": service.name,
                                "message": f"Service port targets '{target}', but workload '{workload.name}' does not expose it.",
                                "fix": f"Add containerPort: {target} to Deployment '{workload.name}'.",
                                "file_path": getattr(service, "file_path", "unknown"),
                            }
                        )
        return mismatches

    @staticmethod
    def validate_ingress_backends(ingresses: List[ManifestIdentity], services: List[ManifestIdentity]) -> List[Dict]:
        """Validates Ingress backends point to valid Services and Ports - Optimized O(N)."""
        issues = []

        # O(N) Optimization: Map services by ns/name
        service_map = {}
        for s in services:
            ns = s.namespace or "default"
            service_map[(ns, s.name)] = s

            for backend in ingress.ingress_backends:
                if not isinstance(backend, dict):
                    continue
                svc_name = backend.get("service")
                svc_port = backend.get("port")
                if not svc_name:
                    continue

                # [REMOD-HARDENING] Corrected loop variable and namespace lookup
                ns = s.namespace or "default"
                match = service_map.get((ns, svc_name))
                if not match:
                    issues.append(
                        {
                            "ingress_name": "unknown", 
                            "message": f"Ingress references missing Service '{svc_name}'.",
                            "fix": "Ensure Service exists in the same namespace.",
                            "file_path": "",
                        }
                    )
                    continue

                if svc_port:
                    valid_ports = []
                    for sp in match.service_ports or []:
                        if isinstance(sp, dict):
                            if sp.get("port"):
                                valid_ports.append(str(sp.get("port")))
                            if sp.get("name"):
                                valid_ports.append(str(sp.get("name")))
                        elif isinstance(sp, (str, int)):
                            valid_ports.append(str(sp))

                    if str(svc_port) not in valid_ports:
                        port_list = list(set(valid_ports))
                        issues.append(
                            {
                                "ingress_name": "unknown",
                                "message": f"Ingress references port '{svc_port}' on Service '{svc_name}', exposing: {', '.join(port_list)}.",
                                "fix": f"Update Ingress to use one of: {', '.join(port_list)}",
                                "file_path": "",
                            }
                        )
        return issues

    @staticmethod
    def validate_network_policies(policies: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
        """
        Validates that NetworkPolicies actually match at least one workload in their namespace.

        Why: To prevent "Silent Drop" traffic rules where a policy is defined but targets zero pods.
        """
        ghosts = []

        # O(N) Optimization: Index workloads by their namespace and labels
        # workload_index[ns][label_key][label_val] = [list of workload IDs]
        workload_index: Dict[str, Dict[str, Dict[str, List[int]]]] = {}

        for w in workloads:
            ns = w.namespace or "default"
            if not w.labels:
                continue

            ns_idx = workload_index.setdefault(ns, {})
            for k, v in w.labels.items():
                ns_idx.setdefault(k, {}).setdefault(str(v), []).append(id(w))

        for policy in policies:
            # If no podSelector is defined, it matches all pods in the namespace (not a ghost)
            if not policy.network_policy_selector:
                continue

            ns = policy.namespace or "default"
            ns_idx = workload_index.get(ns, {})

            matches_exist = False
            if ns_idx:
                match_sets = []
                for k, v in policy.network_policy_selector.items():
                    val_matches = ns_idx.get(k, {}).get(str(v), [])
                    if not val_matches:
                        match_sets = []
                        break
                    match_sets.append(set(val_matches))

                if match_sets:
                    match_ids = set.intersection(*match_sets)
                    if match_ids:
                        matches_exist = True

            if not matches_exist:
                selector_str = ", ".join([f"{k}={v}" for k, v in policy.network_policy_selector.items()])
                ghosts.append(
                    {
                        "name": policy.name,
                        "selector": selector_str,
                        "message": f"Ghost NetworkPolicy: podSelector {{{selector_str}}} matches zero workloads in namespace '{ns}'.",
                        "file_path": getattr(policy, "file_path", "unknown"),
                        "hint": f"Either create workloads with labels {{{selector_str}}} or update the NetworkPolicy podSelector.",
                    }
                )

        return ghosts

    @staticmethod
    def _labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
        """Checks if a selector matches a set of labels."""
        for key, value in selector.items():
            target = labels.get(key)
            if target is None or str(target).strip() != str(value).strip():
                return False
        return True
