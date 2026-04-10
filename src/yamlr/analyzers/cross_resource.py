#!/usr/bin/env python3
"""
Yamlr CROSS-RESOURCE ANALYZER
------------------------------
Refactored and Modularized: v1.1 Hardening Sprint.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from yamlr.core.resource_graph import ResourceGraph

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.detectors.config import detect_broken_refs, detect_orphan_configs
from yamlr.analyzers.detectors.storage import CrossDomainDetectors, detect_broken_volumes
from yamlr.analyzers.detectors.traffic import detect_ghost_services
from yamlr.analyzers.network_logic import NetworkDetectors
from yamlr.analyzers.registry import register_analyzer
from yamlr.analyzers.rules import Rules
from yamlr.core.bridge import YamlrBridge
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.cross_resource")
__all__ = ["CrossResourceAnalyzer"]


@register_analyzer
class CrossResourceAnalyzer(BaseAnalyzer):
    """
    Orchestrates cross-resource analysis for Kubernetes manifests.
    """

    def __init__(self, pro_mode: bool = False):
        """Initializes the cross-resource analyzer.

        Why: Sets the licensing mode to determine which detection layers to activate.
        """
        self.pro_mode = pro_mode or YamlrBridge.is_pro_enabled()

    @property
    def name(self) -> str:
        return "cross-resource-analyzer"

    @property
    def analyzer_type(self) -> str:
        return "batch"

    def analyze(
        self, identities: List[ManifestIdentity], graph: Optional["ResourceGraph"] = None, **kwargs
    ) -> List[AnalysisResult]:
        """Performs comprehensive cross-resource analysis."""
        results: List[AnalysisResult] = []

        # 1. Categorize Identities
        services = [i for i in identities if i.kind == "Service"]
        workloads = [
            i for i in identities if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod")
        ]
        configs = [i for i in identities if i.kind in ("ConfigMap", "Secret")]
        ingresses = [i for i in identities if i.kind == "Ingress"]
        pvs = [i for i in identities if i.kind == "PersistentVolume"]
        pvcs = [i for i in identities if i.kind == "PersistentVolumeClaim"]
        netpols = [i for i in identities if i.kind == "NetworkPolicy"]
        hpas = [i for i in identities if i.kind == "HorizontalPodAutoscaler"]
        pdbs = [i for i in identities if i.kind == "PodDisruptionBudget"]
        cloud_resources = [i for i in identities if i.api_version and i.api_version.startswith("terraform")]

        # 2. Execute Detection Layers
        ghosts = detect_ghost_services(services, workloads, self.pro_mode, graph=graph)
        orphans = detect_orphan_configs(configs, workloads)
        broken_refs = detect_broken_refs(workloads + configs, graph=graph)
        broken_vols = detect_broken_volumes(workloads, pvcs)
        port_mismatches = NetworkDetectors.validate_service_ports(services, workloads)
        ingress_issues = NetworkDetectors.validate_ingress_backends(ingresses, services)
        netpol_ghosts = NetworkDetectors.validate_network_policies(netpols, workloads)
        cloud_refs = CrossDomainDetectors.detect_broken_cloud_refs(pvs, cloud_resources)
        credential_links = CrossDomainDetectors.detect_broken_credential_links(configs, cloud_resources)

        # [GOOGLE-SCALE] Cross-Resource Reliability Layers
        hpa_mismatches = self._detect_hpa_mismatches(hpas, workloads)
        missing_pdbs = self._detect_missing_pdbs(pdbs, workloads)

        # 3. Consolidate Results
        self._map_hpas(hpa_mismatches, results)
        self._map_pdbs(missing_pdbs, results)
        self._map_ghosts(ghosts, results)
        self._map_ports(port_mismatches, results)
        self._map_ingress(ingress_issues, results)
        self._map_network_policies(netpol_ghosts, results)
        self._map_orphans(orphans, results)
        self._map_volumes(broken_vols, results)
        self._map_broken_refs(broken_refs, results)
        self._map_cloud_refs(cloud_refs, results)
        self._map_credential_links(credential_links, results)

        return results

    def _map_cloud_refs(self, findings, results):
        """Maps broken cloud storage references."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR",
                    message=f"Broken Cloud Link: volume-id '{f.get('volume_id')}' not found in Terraform.",
                    resource_name=f.get("name", "unknown"),
                    resource_kind="PersistentVolume",
                    file_path=f.get("file_path", "unknown"),
                    suggestion="Update the PersistentVolume to match the current Terraform volume-id or ARN.",
                    rationale="PersistentVolumes must map to existing Cloud storage identifiers for successful mounting.",
                    rule_id=Rules.CLOUD_BROKEN,
                )
            )

    def _map_credential_links(self, findings, results):
        """Maps broken cloud credential links."""
        for f in findings:
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="WARNING",
                    message=f"Possible Orphan Secret: No matching Database resource found in Terraform for '{f['name']}'.",
                    resource_name=f["name"],
                    resource_kind="Secret",
                    file_path=f.get("file_path", "unknown"),
                    suggestion="Verify if this Secret is still required or if the referenced Database was renamed/removed.",
                    rationale="Secrets that appear to hold Cloud credentials but have no corresponding Cloud resource may be outdated.",
                    rule_id=Rules.CLOUD_BROKEN,
                )
            )

    def _map_ghosts(self, findings, results):
        """Maps Service ghosts (no matching Pods)."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="WARNING",
                    message="Ghost Service: selector matches no Pods.",
                    resource_name=f.get("name", "unknown"),
                    resource_kind="Service",
                    file_path=f.get("file_path", "unknown"),
                    suggestion=f.get("hint"),
                    rationale="Services without matching Pods are 'Ghosts'. They exist in the API but have no backend to receive traffic.",
                    external_url="https://kubernetes.io/docs/concepts/services-networking/service/",
                    impact_description="Traffic routed to this Service will have no destination, leading to 'No endpoints available' errors for clients.",
                    risk_level="MEDIUM",
                    rule_id=Rules.GHOST_SERVICE,
                )
            )

    def _map_ports(self, findings, results):
        """Maps Service/Pod port mismatches."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR",
                    message=f.get("message", "Port mismatch detected"),
                    resource_name=f.get("service_name", "unknown"),
                    resource_kind="Service",
                    file_path=f.get("file_path", "unknown"),
                    suggestion=f.get("fix"),
                    rationale="A Service targetPort must match a containerPort in the Pod. If they mismatch, the Kube-Proxy cannot route traffic to the container process.",
                    external_url="https://kubernetes.io/docs/concepts/services-networking/service/#multi-port-services",
                    impact_description="Traffic will reach the Node but fail to reach the Application. This results in 503 Service Unavailable or Connection Refused errors.",
                    risk_level="HIGH",
                    rule_id=Rules.PORT_MISMATCH,
                )
            )

    def _map_ingress(self, findings, results):
        """Maps Ingress backend violations to analysis results."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR" if "Missing" in f.get("message", "") else "WARNING",
                    message=f.get("message", "Ingress backend issue"),
                    resource_name=f.get("ingress_name", "unknown"),
                    resource_kind="Ingress",
                    file_path=f.get("file_path", ""),
                    suggestion=f.get("fix"),
                    rationale="Ingress backends must point to valid Service names and ports for external access.",
                    external_url="https://kubernetes.io/docs/concepts/services-networking/ingress/",
                    rule_id=Rules.INGRESS_BROKEN,
                )
            )

    def _map_orphans(self, findings, results):
        """Maps orphan ConfigMaps and Secrets."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="WARNING",
                    message=f"Orphan {f.get('kind', 'resource')} detected (unused).",
                    resource_name=f.get("name", "unknown"),
                    resource_kind=f.get("kind", "unknown"),
                    file_path=f.get("file_path", ""),
                    suggestion="Remove if unused.",
                    rationale="Unused ConfigMaps/Secrets clutter the namespace and can lead to sensitive data sprawl.",
                    rule_id=Rules.ORPHAN_RESOURCE,
                )
            )

    def _map_volumes(self, findings, results):
        """Maps broken Volume/PVC references."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR",
                    message=f"Broken Volume: missing PVC '{f.get('missing_pvc', 'unknown')}'.",
                    resource_name=f.get("workload_name", "unknown"),
                    resource_kind=f.get("workload_kind", "unknown"),
                    file_path=f.get("file_path", "unknown"),
                    suggestion=f.get("suggestion"),
                    rationale="Workloads referencing non-existent PVCs will fail to mount volumes and crash Loop.",
                    rule_id=Rules.BROKEN_VOLUME,
                )
            )

    def _map_broken_refs(self, findings, results):
        """Maps broken ConfigMap/Secret references."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR",
                    message=f"Broken Reference: missing {f.get('kind', 'resource')} '{f.get('name', 'unknown')}'.",
                    resource_name=f.get("resource_name", "unknown"),
                    resource_kind=f.get("resource_kind", "unknown"),
                    file_path=f.get("file_path", "unknown"),
                    suggestion=f.get("suggestion"),
                    rationale="Kubernetes requires all referenced ConfigMaps and Secrets to exist before a Pod can start. If they are missing, the Pod remains in 'CreateContainerConfigError' or 'CrashLoopBackOff'.",
                    external_url="https://kubernetes.io/docs/concepts/configuration/secret/",
                    impact_description="The dependent workload will fail to start. This blocks deployments and can cause downtime if the missing resource is critical for application bootstrap.",
                    risk_level="HIGH",
                    rule_id=Rules.BROKEN_REFERENCE,
                )
            )

    def _map_network_policies(self, findings, results):
        """Maps Ghost NetworkPolicies (matching zero workloads)."""
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="WARNING",
                    message=f.get("message", "NetworkPolicy match failure"),
                    resource_name=f.get("name", "unknown"),
                    resource_kind="NetworkPolicy",
                    file_path=f.get("file_path", "unknown"),
                    suggestion=f.get("hint"),
                    rationale="NetworkPolicies that match zero workloads are effectively dead code, but they can cause unexpected 'Silent Drop' behavior if a workload is later added without the correct labels.",
                    external_url="https://kubernetes.io/docs/concepts/services-networking/network-policies/",
                    impact_description="The policy provides no protection for any existing workloads. If the intention was to secure a specific app, that app remains unprotected.",
                    risk_level="MEDIUM",
                    rule_id=Rules.GHOST_NETWORK_POLICY,
                )
            )

    def _detect_hpa_mismatches(self, hpas: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[dict]:
        """Detects HPAs targeting non-existent or misaligned scaleTargetRefs."""
        findings = []
        for hpa in hpas:
            manifest = hpa.raw or {}
            target = manifest.get("spec", {}).get("scaleTargetRef", {})
            t_name = target.get("name")
            t_kind = target.get("kind")

            # Try to find matching workload
            match = any(w.name == t_name and w.kind == t_kind for w in workloads)
            if not match:
                findings.append({"name": hpa.name, "target": t_name, "kind": t_kind, "file_path": hpa.file_path})
        return findings

    def _detect_missing_pdbs(self, pdbs: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[dict]:
        """Detects workloads missing high-availability spread protections (PDB)."""
        findings = []
        pdb_selectors = []
        for pdb in pdbs:
            sel = (pdb.raw or {}).get("spec", {}).get("selector", {}).get("matchLabels", {})
            if sel:
                pdb_selectors.append(sel)

        for w in workloads:
            if w.kind not in ["Deployment", "StatefulSet"]:
                continue
            labels = w.labels or {}

            # Check if this workload is covered by ANY PDB selector
            covered = any(all(labels.get(k) == v for k, v in sel.items()) for sel in pdb_selectors)
            if not covered:
                findings.append({"name": w.name, "kind": w.kind, "file_path": w.file_path})
        return findings

    def _map_hpas(self, findings, results):
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="ERROR",
                    message=f"HPA target '{f.get('target', 'unknown')}' ({f.get('kind', 'workload')}) not found in current manifest set.",
                    resource_name=f.get("name", "unknown"),
                    resource_kind="HorizontalPodAutoscaler",
                    file_path=f.get("file_path") or "unknown",
                    suggestion="Update scaleTargetRef to match a valid workload.",
                    rule_id="reliability/hpa-mismatch",
                )
            )

    def _map_pdbs(self, findings, results):
        for f in findings:
            if not isinstance(f, dict):
                continue
            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    severity="WARNING",
                    message=f"Workload '{f.get('name', 'unknown')}' has no matching PodDisruptionBudget.",
                    resource_name=f.get("name", "unknown"),
                    resource_kind=f.get("kind", "Deployment"),
                    file_path=f.get("file_path") or "unknown",
                    suggestion="Create a PDB to ensure availability during cluster maintenance.",
                    rule_id="reliability/missing-pdb",
                )
            )


# Backward compatibility alias
KubeCrossResourceAnalyzer = CrossResourceAnalyzer
