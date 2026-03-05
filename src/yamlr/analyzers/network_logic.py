#!/usr/bin/env python3
"""
Yamlr NETWORK LOGIC DETECTORS
------------------------------
Specialized logic for validating Services and Ingress relationships.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import Dict, List, Optional
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.network")

class NetworkDetectors:
    """
    Validation logic for K8s Service ports and Ingress backends.
    """

    @staticmethod
    def validate_service_ports(services: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
        """Validates that Service targetPorts actually exist in the backing Pods."""
        mismatches = []
        for service in services:
            if not service.selector or not service.service_ports: continue
            
            matches = [w for w in workloads if (service.namespace or "default") == (w.namespace or "default") 
                       and w.labels and NetworkDetectors._labels_match(service.selector, w.labels)]
            
            for workload in matches:
                if not workload.container_ports: continue
                w_ports = [str(p) for p in workload.container_ports]
                for s_port in service.service_ports:
                    target = s_port.get("targetPort", s_port.get("port"))
                    if target and str(target) not in w_ports:
                        mismatches.append({
                            "service_name": service.name,
                            "message": f"Service port targets '{target}', but workload '{workload.name}' does not expose it.",
                            "fix": f"Add containerPort: {target} to Deployment '{workload.name}'.",
                            "file_path": getattr(service, "file_path", "unknown"),
                        })
        return mismatches

    @staticmethod
    def validate_ingress_backends(ingresses: List[ManifestIdentity], services: List[ManifestIdentity]) -> List[Dict]:
        """Validates Ingress backends point to valid Services and Ports."""
        issues = []
        for ingress in ingresses:
            if not ingress.ingress_backends: continue
            for backend in ingress.ingress_backends:
                svc_name = backend.get("service")
                svc_port = backend.get("port")
                if not svc_name: continue
                
                match = next((s for s in services if s.name == svc_name and (s.namespace or "default") == (ingress.namespace or "default")), None)
                if not match:
                    issues.append({
                        "ingress_name": ingress.name,
                        "message": f"Ingress references missing Service '{svc_name}'.",
                        "fix": "Ensure Service exists in the same namespace.",
                        "file_path": getattr(ingress, "file_path", "unknown"),
                    })
                    continue
                
                if svc_port:
                    valid_ports = [str(sp.get("port")) for sp in match.service_ports if sp.get("port")]
                    valid_ports += [sp.get("name") for sp in match.service_ports if sp.get("name")]
                    if str(svc_port) not in valid_ports:
                        issues.append({
                            "ingress_name": ingress.name,
                            "message": f"Ingress references port '{svc_port}' on Service '{svc_name}', exposing: {', '.join(valid_ports)}.",
                            "fix": f"Update Ingress to use one of: {', '.join(valid_ports)}",
                            "file_path": getattr(ingress, "file_path", "unknown"),
                        })
        return issues

    @staticmethod
    def _labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
        """Checks if a selector matches a set of labels."""
        for key, value in selector.items():
            target = labels.get(key)
            if target is None or str(target).strip() != str(value).strip():
                return False
        return True
