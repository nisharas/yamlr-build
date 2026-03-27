#!/usr/bin/env python3
"""
Yamlr STORAGE DETECTORS
-----------------------
Detection algorithms for K8s Storage resources (PVC, PV) and Cloud Volume links.
"""

from __future__ import annotations

import difflib
import logging
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.detectors.storage")

def detect_broken_volumes(workloads: List[ManifestIdentity], pvcs: List[ManifestIdentity]) -> List[Dict]:
    """Detects workloads referencing non-existent PVCs with fuzzy suggestion."""
    broken = []
    pvc_names = {p.name for p in pvcs if p.name}
    pvc_names_list = list(pvc_names)

    for w in workloads:
        for pvc_ref in (w.volume_refs or []):
            if pvc_ref not in pvc_names:
                best_match = None
                if pvc_names_list and len(workloads) < 1000:
                    matches = difflib.get_close_matches(pvc_ref, pvc_names_list, n=1, cutoff=0.7)
                    if matches: best_match = matches[0]

                broken.append({
                    "workload_kind": w.kind, "workload_name": w.name,
                    "missing_pvc": pvc_ref, "namespace": w.namespace or "default",
                    "file_path": getattr(w, "file_path", "unknown"),
                    "suggestion": f"Use '{best_match}'" if best_match else f"Ensure PVC '{pvc_ref}' exists."
                })
    return broken

class CrossDomainDetectors:
    """Detection algorithms for K8s-to-Cloud (Terraform) links."""

    @staticmethod
    def detect_broken_cloud_refs(pvs: List[ManifestIdentity], cloud_resources: List[ManifestIdentity]) -> List[Dict]:
        """Detects PersistentVolumes referencing non-existent Cloud storage."""
        broken = []
        if not pvs or not cloud_resources: return broken

        cloud_volume_ids = set()
        for i in cloud_resources:
            if not i.annotations: continue
            arn = i.annotations.get("cloud.yamlr.dev/arn", "")
            if not arn: continue
            if "/" in arn: cloud_volume_ids.add(arn.split("/")[-1])
            if ":" in arn: cloud_volume_ids.add(arn.split(":")[-1])
            cloud_volume_ids.add(arn)

        for pv in pvs:
            volume_id = (pv.annotations or {}).get("ebs.csi.aws.com/volume-id")
            if volume_id and volume_id not in cloud_volume_ids:
                 broken.append({"name": pv.name, "volume_id": volume_id, "file_path": getattr(pv, "file_path", "unknown")})
        return broken

    @staticmethod
    def detect_broken_credential_links(secrets: List[ManifestIdentity], cloud_resources: List[ManifestIdentity]) -> List[Dict]:
        """Detects Secrets referencing Cloud resources that no longer exist in TF."""
        broken = []
        if not secrets or not cloud_resources: return broken

        cloud_db_names = {i.name.lower(): i.name for i in cloud_resources if i.kind and ("db" in i.kind.lower() or "rds" in i.kind.lower())}
        if not cloud_db_names: return broken

        for secret in secrets:
            if not secret.name: continue
            name_lower = secret.name.lower()
            if "db" in name_lower or "rds" in name_lower:
                found = name_lower in cloud_db_names
                if not found:
                    for db_name_low in cloud_db_names:
                        if db_name_low in name_lower or name_lower in db_name_low:
                            found = True
                            break
                if not found:
                    broken.append({"name": secret.name, "file_path": getattr(secret, "file_path", "unknown")})
        return broken
