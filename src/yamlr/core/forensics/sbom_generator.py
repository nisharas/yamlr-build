"""
Yamlr Forensic Engine: SBOM Integrity
------------------------------------
Generates CycloneDX-compliant SBOMs from Kubernetes scan results.

Why: To meet enterprise 'Software Bill of Materials' requirements while
     bridging manifest scanning with supply-chain governance.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from yamlr.core.engine.models import AnalysisResult

__all__ = ["CycloneDXExporter"]


class CycloneDXExporter:
    """Exports AnalysisResult stream to CycloneDX v1.5 JSON."""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        self.metadata = metadata or {}
        self.spec_version = "1.5"

    def export(self, findings: List[AnalysisResult]) -> str:
        """Transforms a list of findings into an SBOM string."""
        serial_number = f"urn:uuid:{uuid.uuid4()}"
        
        bom = {
            "bomFormat": "CycloneDX",
            "specVersion": self.spec_version,
            "serialNumber": serial_number,
            "version": 1,
            "metadata": self._build_metadata(),
            "components": self._build_components(findings),
            "vulnerabilities": self._build_vulnerabilities(findings)
        }
        
        return json.dumps(bom, indent=2)

    def _build_metadata(self) -> Dict[str, Any]:
        """Builds SBOM metadata block."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {
                    "vendor": "Timonel Labs",
                    "name": "Yamlr",
                    "version": "1.9.0",
                }
            ],
            "component": {
                "type": "application",
                "name": self.metadata.get("project_name", "Kubernetes Manifests"),
                "version": "1.0.0"
            }
        }

    def _build_components(self, findings: List[AnalysisResult]) -> List[Dict[str, Any]]:
        """Extracts components (container images) from findings."""
        components = {}
        
        for f in findings:
            # Check for image-specific findings
            if f.resource_kind in ["Deployment", "Pod", "StatefulSet", "DaemonSet"]:
                # Try to extract image name from description or suggestion
                # If no image found, we treat the manifest itself as a component
                comp_key = f"{f.resource_kind}/{f.resource_name}"
                if comp_key not in components:
                    components[comp_key] = {
                        "type": "container",
                        "name": f.resource_name,
                        "version": "latest",  # Placeholder
                        "purl": f"pkg:k8s/{f.resource_kind.lower()}@{f.resource_name}",
                        "bom-ref": f"comp-{len(components)}"
                    }
        
        return list(components.values())

    def _build_vulnerabilities(self, findings: List[AnalysisResult]) -> List[Dict[str, Any]]:
        """Maps forensic findings to CycloneDX vulnerabilities."""
        vulnerabilities = []
        
        for i, f in enumerate(findings):
            if f.severity in ["ERROR", "CRITICAL"]:
                v = {
                    "id": f.rule_id,
                    "source": {"name": "Yamlr Forensic Engine"},
                    "description": f.message,
                    "detail": f.impact_description if hasattr(f, "impact_description") else f.message,
                    "ratings": [
                        {
                            "severity": self._map_severity(f.severity),
                            "method": "CVSSv31",  # Placeholder for scoring engine
                        }
                    ],
                    "recommendation": f.suggestion if hasattr(f, "suggestion") else "Review Kubernetes hardening standards.",
                    "affects": [
                        {
                            "ref": f"comp-{i}" # In a real implementation this would link back to the exact component
                        }
                    ]
                }
                vulnerabilities.append(v)
                
        return vulnerabilities

    def _map_severity(self, severity: str) -> str:
        """Maps Yamlr severity to CycloneDX levels."""
        mapping = {
            "CRITICAL": "critical",
            "ERROR": "high",
            "WARNING": "medium",
            "INFO": "low",
        }
        return mapping.get(severity.upper(), "info")
