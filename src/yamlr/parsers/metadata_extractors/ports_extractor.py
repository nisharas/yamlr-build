#!/usr/bin/env python3
"""
Extractor for Port definitions (Service & Workload).

Extracts:
- Service: spec.ports[] (port, targetPort, name)
- Workload: spec.containers[].ports[] (containerPort, name)
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["PortsExtractor"]


from .base_extractor import BaseMetadataExtractor


class PortsExtractor(BaseMetadataExtractor):
    """Extracts Port information from Services and Workloads."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract Port information if in Service or Workload context.
        """
        # 1. SERVICE PORTS
        if identity.kind == "Service":
            if "ports" in path_keys:
                # [Hardening] Capture port details regardless of shard order
                if shard.is_list_item:
                    if identity.service_ports is None:
                        identity.service_ports = []
                    identity.service_ports.append({})

                if not identity.service_ports:
                    identity.service_ports = [{}]

                if key in ("port", "targetPort", "name", "nodePort", "protocol"):
                    # [Forensic Sync] Ensure value is stored as a string for metadata consistency
                    identity.service_ports[-1][key] = str(val) if val is not None else None
                    return True

        # 2. WORKLOAD PORTS
        elif identity.kind in (
            "Deployment",
            "StatefulSet",
            "DaemonSet",
            "Pod",
            "Job",
            "CronJob",
            "ReplicaSet",
        ):
            if "containers" in path_keys and "ports" in path_keys:
                if key in ("containerPort", "name"):
                    return PortsExtractor._apply_list_extraction(shard, key, val, identity, "container_ports")

        return False
