"""Topology Analysis Stage — evaluates fleet-wide cross-resource relations."""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class TopologyAnalysisStage:
    """Stage performing graph-level analysis across discovered Kubernetes resources."""

    @staticmethod
    def analyze(results: List[Any]) -> List[Dict[str, str]]:
        """Analyzes multiple resource results for topological hazards.

        Args:
            results: List of ResourceResult items from scanner pipeline.

        Returns:
            List of structured findings dictionary objects.
        """
        try:
            import yamlr_native
        except ImportError as e:
            logger.debug("Native core not available for topology analysis: %s", e)
            return []

        try:
            identities = [res.identity for res in results if hasattr(res, 'identity') and res.identity]
            if len(identities) < 2:
                return []

            discovery = [
                yamlr_native.NativeDiscoveryResult(file_path="", identity=id, shard_count=0)
                for id in identities
            ]
            edges = yamlr_native.native_build_topology_graph(discovery)

            # Detect topological and fleet hazards
            cycles = yamlr_native.native_detect_circular_dependencies(edges)
            dangling = yamlr_native.native_detect_dangling_selectors(discovery)
            orphans = yamlr_native.native_detect_orphaned_resources(discovery)
            shadowing = yamlr_native.native_detect_service_shadowing(discovery)
            drifts = yamlr_native.native_detect_version_drift(discovery)

            findings: List[Dict[str, str]] = []
            for c in cycles:
                findings.append({"sev": "CRITICAL", "type": "Circular Dependency", "msg": str(c)})
            for d in dangling:
                findings.append({"sev": "WARNING", "type": "Dangling Selector", "msg": str(d)})
            for o in orphans:
                findings.append({"sev": "INFO", "type": "Orphaned Resource", "msg": str(o)})
            for s in shadowing:
                findings.append({"sev": "CRITICAL", "type": "Service Shadowing", "msg": str(s)})
            for v in drifts:
                findings.append({"sev": "WARNING", "type": "Version Drift", "msg": str(v)})

            # Detect cross-resource fleet audit violations via AuditRegistry
            if hasattr(yamlr_native, 'native_audit_registry'):
                registry_violations = yamlr_native.native_audit_registry(identities)
                for rv in registry_violations:
                    findings.append({
                        "sev": getattr(rv, "severity", "WARNING"),
                        "type": f"[{getattr(rv, 'rule_id', 'FLEET')}] {getattr(rv, 'check_name', 'Fleet Hazard')}",
                        "msg": getattr(rv, "message", ""),
                    })

            return findings
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.debug("Topology analysis stage encountered error: %s", e)
            return []
