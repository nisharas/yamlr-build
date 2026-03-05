#!/usr/bin/env python3
"""
Yamlr CROSS-RESOURCE ANALYZER
------------------------------
Refactored and Modularized: v1.1 Hardening Sprint.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.registry import register_analyzer
from yamlr.analyzers.rules import Rules
from yamlr.core.bridge import YamlrBridge
from yamlr.models import ManifestIdentity
from yamlr.analyzers.detectors import CrossResourceDetectors
from yamlr.analyzers.network_logic import NetworkDetectors

logger = logging.getLogger("yamlr.analyzer.cross_resource")

@register_analyzer
class CrossResourceAnalyzer(BaseAnalyzer):
    """
    Orchestrates cross-resource analysis for Kubernetes manifests.
    """

    def __init__(self, pro_mode: bool = False):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.pro_mode = pro_mode or YamlrBridge.is_pro_enabled()

    @property
    def name(self) -> str: return "cross-resource-analyzer"

    @property
    def analyzer_type(self) -> str: return "batch"

    def analyze(self, identities: List[ManifestIdentity]) -> List[AnalysisResult]:
        """Performs comprehensive cross-resource analysis."""
        results: List[AnalysisResult] = []

        # 1. Categorize Identities
        services = [i for i in identities if i.kind == "Service"]
        workloads = [i for i in identities if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod")]
        configs = [i for i in identities if i.kind in ("ConfigMap", "Secret")]
        pvcs = [i for i in identities if i.kind == "PersistentVolumeClaim"]
        ingresses = [i for i in identities if i.kind == "Ingress"]

        # 2. Execute Detection Layers
        ghosts = CrossResourceDetectors.detect_ghost_services(services, workloads, self.pro_mode)
        orphans = CrossResourceDetectors.detect_orphan_configs(configs, workloads)
        broken_refs = CrossResourceDetectors.detect_broken_refs(workloads, configs)
        broken_vols = CrossResourceDetectors.detect_broken_volumes(workloads, pvcs)
        port_mismatches = NetworkDetectors.validate_service_ports(services, workloads)
        ingress_issues = NetworkDetectors.validate_ingress_backends(ingresses, services)

        # 3. Consolidate Results
        self._map_ghosts(ghosts, results)
        self._map_ports(port_mismatches, results)
        self._map_ingress(ingress_issues, results)
        self._map_orphans(orphans, results)
        self._map_volumes(broken_vols, results)
        self._map_broken_refs(broken_refs, results)

        return results

    def _map_ghosts(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="WARNING",
                message="Ghost Service: selector matches no Pods.",
                resource_name=f["name"],
                resource_kind="Service",
                file_path=f.get("file_path", "unknown"),
                suggestion=f.get("hint"),
                rationale="Services without matching Pods are 'Ghosts' and cause traffic to blackhole.",
                rule_id=Rules.GHOST_SERVICE
            ))

    def _map_ports(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="ERROR",
                message=f["message"],
                resource_name=f["service_name"],
                resource_kind="Service",
                file_path=f.get("file_path", "unknown"),
                suggestion=f["fix"],
                rationale="Mismatched port names/numbers prevent Services from routing to container processes.",
                rule_id=Rules.PORT_MISMATCH
            ))

    def _map_ingress(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="ERROR" if "Missing" in f["message"] else "WARNING",
                message=f["message"],
                resource_name=f["ingress_name"],
                resource_kind="Ingress",
                file_path=f.get("file_path", "unknown"),
                suggestion=f["fix"],
                rationale="Ingress backends must point to valid Service names and ports for external access.",
                rule_id=Rules.INGRESS_BROKEN
            ))

    def _map_orphans(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="WARNING",
                message=f"Orphan {f['kind']} detected (unused).",
                resource_name=f["name"],
                resource_kind=f["kind"],
                file_path=f.get("file_path", "unknown"),
                suggestion="Remove if unused.",
                rationale="Unused ConfigMaps/Secrets clutter the namespace and can lead to sensitive data sprawl.",
                rule_id=Rules.ORPHAN_RESOURCE
            ))

    def _map_volumes(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="ERROR",
                message=f"Broken Volume: missing PVC '{f['missing_pvc']}'.",
                resource_name=f["workload_name"],
                resource_kind=f["workload_kind"],
                file_path=f.get("file_path", "unknown"),
                suggestion=f.get("suggestion"),
                rationale="Workloads referencing non-existent PVCs will fail to mount volumes and crash Loop.",
                rule_id=Rules.BROKEN_VOLUME
            ))

    def _map_broken_refs(self, findings, results):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        for f in findings:
            results.append(AnalysisResult(
                analyzer_name=self.name,
                severity="ERROR",
                message=f"Broken Reference: missing {f['kind']} '{f['name']}'.",
                resource_name=f["resource_name"],
                resource_kind=f["resource_kind"],
                file_path=f.get("file_path", "unknown"),
                suggestion=f.get("suggestion"),
                rationale="Broken ConfigMap/Secret references prevent Pods from obtaining required environment variables or files.",
                rule_id=Rules.BROKEN_REFERENCE
            ))

# Backward compatibility alias
KubeCrossResourceAnalyzer = CrossResourceAnalyzer
