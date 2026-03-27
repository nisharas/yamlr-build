#!/usr/bin/env python3
"""
Yamlr CROSS-DOMAIN EDGES
------------------------
Bridges Kubernetes with Cloud Infrastructure (HCL/Terraform).
"""

from __future__ import annotations
from typing import List
from yamlr.models import ManifestIdentity
from yamlr.core.graph_models import EdgeType, GraphEdge
from yamlr.core.edges.base import AddEdgeFn, MakeKeyFn
__all__ = ['build_cross_domain_edges']


def build_cross_domain_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """K8s.resource → Cloud.resource (CLOUD_REF / CREDENTIAL_LINK)."""
    # 1. PV → Cloud Storage (EBS, GCP-PD, etc.)
    pvs = [i for i in identities if i.kind == "PersistentVolume" and i.annotations]
    cloud_resources = {
        i.name: i for i in identities 
        if i.api_version and i.api_version.startswith("terraform") and i.name
    }

    for pv in pvs:
        volume_id = pv.annotations.get("ebs.csi.aws.com/volume-id")
        if volume_id:
            for name, cloud_res in cloud_resources.items():
                if volume_id in cloud_res.annotations.get("cloud.yamlr.dev/arn", ""):
                    add_edge(GraphEdge(
                        source_key=make_key("PersistentVolume", pv),
                        target_key=make_key(cloud_res.kind, cloud_res),
                        edge_type=EdgeType.CLOUD_REF,
                        metadata={"volume_id": volume_id}
                    ))

    # 2. Secret → Cloud Database (Credential Link)
    secrets = [i for i in identities if i.kind == "Secret"]
    for secret in secrets:
        for name, cloud_res in cloud_resources.items():
            if "db" in cloud_res.kind and (name in secret.name or secret.name in name):
                add_edge(GraphEdge(
                    source_key=make_key("Secret", secret),
                    target_key=make_key(cloud_res.kind, cloud_res),
                    edge_type=EdgeType.CREDENTIAL_LINK
                ))
