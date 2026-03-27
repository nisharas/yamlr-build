#!/usr/bin/env python3
"""
Yamlr SARIF FORMATTER
----------------------
Generates SARIF v2.1.0 JSON reports for integration with CI/CD platforms.

Author: Yamlr Team
Date: 2026-02-19
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from yamlr.models import HealFileResult

__all__ = ["SarifFormatter"]

class SarifFormatter:
    """Converts Yamlr results into the standardized SARIF format."""

    def __init__(self, app_name: str = "yamlr", version: str = "0.1.0"):
        """Initializes the SARIF formatter.
        
        Args:
            app_name: The name of the reporting application.
            version: The version string to include in the driver metadata.
        """
        self.app_name = app_name
        self.version = version

    def format(self, results: List[HealFileResult], timing: Optional[Dict[str, Any]] = None, extra_props: Optional[Dict[str, Any]] = None) -> str:
        """Generates a SARIF JSON string from processing results.
        
        Why: To provide a machine-readable format compatible with GitHub Code Scanning and other CI tools.
        """
        run_props = {"performanceTiming": timing}
        if extra_props:
            run_props.update(extra_props)

        sarif_log = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.app_name,
                            "semanticVersion": self.version,
                            "rules": self._extract_rules(results)
                        }
                    },
                    "taxonomies": self._get_taxonomies(),
                    "results": self._extract_results(results),
                    "properties": run_props
                }
            ]
        }
        return json.dumps(sarif_log, indent=2)

    def _get_taxonomies(self) -> List[Dict[str, Any]]:
        """Defines compliance taxonomies dynamically from the registry."""
        try:
            from yamlr.pro.compliance.ruleset import ComplianceRegistry
            taxonomies = []
            
            frameworks = {
                "SOC2": {"org": "AICPA", "desc": "Trust Services Criteria"},
                "HIPAA": {"org": "HHS", "desc": "Security Rule Controls"},
                "CIS": {"org": "CIS", "desc": "Kubernetes Benchmark"}
            }
            
            for fw, meta in frameworks.items():
                taxa = self._build_taxa_list(fw, ComplianceRegistry)
                if taxa:
                    taxonomies.append({
                        "name": fw,
                        "organization": meta["org"],
                        "shortDescription": {"text": meta["desc"]},
                        "taxa": sorted(taxa, key=lambda x: x["id"])
                    })
            if taxonomies:
                return taxonomies
        except ImportError:
            pass

        return self._get_fallback_taxonomies()

    def _build_taxa_list(self, framework: str, registry_class: Any) -> List[Dict[str, Any]]:
        """Builds a list of taxa for a specific framework."""
        taxa = []
        seen_ids = set()
        for rule_id in registry_class.MAPPING:
            ctrl = registry_class.get_controls_for_rule(rule_id)
            ids = getattr(ctrl, framework.lower(), [])
            for sub_id in ids:
                if sub_id not in seen_ids:
                    taxa.append({"id": sub_id, "shortDescription": {"text": ctrl.description}})
                    seen_ids.add(sub_id)
        return taxa

    def _get_fallback_taxonomies(self) -> List[Dict[str, Any]]:
        """Provides default taxonomies if registry is unavailable."""
        return [
            {
                "name": "SOC2",
                "organization": "AICPA",
                "shortDescription": {"text": "Trust Services Criteria"},
                "taxa": [
                    {"id": "CC6.1", "shortDescription": {"text": "Logical Access Security"}},
                    {"id": "CC6.6", "shortDescription": {"text": "Boundary Protection"}},
                ]
            }
        ]

    def _extract_rules(self, results: List[HealFileResult]) -> List[Dict[str, Any]]:
        """Extracts unique rules from findings and maps compliance attributions."""
        rules_map = {}
        compliance_registry = self._get_compliance_registry()

        for res in results:
            for finding in res.findings:
                rule_id = self._get_rule_id(finding)
                if rule_id not in rules_map:
                    rules_map[rule_id] = self._format_rule_node(rule_id, finding, compliance_registry)
                    
        return sorted(list(rules_map.values()), key=lambda r: r["id"])

    def _get_compliance_registry(self) -> Any:
        """Helper to load compliance registry safely."""
        try:
            from yamlr.pro.compliance.ruleset import ComplianceRegistry
            return ComplianceRegistry()
        except ImportError:
            return None

    def _get_rule_id(self, finding: Any) -> str:
        """Extracts rule ID from finding (dict or object)."""
        if isinstance(finding, dict):
            return finding.get("rule_id") or finding.get("analyzer", "generic-rule")
        return getattr(finding, "rule_id", None) or getattr(finding, "analyzer", "generic-rule")

    def _format_rule_node(self, rule_id: str, finding: Any, registry: Any) -> Dict[str, Any]:
        """Formats a single SARIF rule node."""
        msg = finding.get("message", "Yamlr Finding") if isinstance(finding, dict) else getattr(finding, "message", "Yamlr Finding")
        node = {
            "id": rule_id,
            "shortDescription": {"text": msg},
            "helpUri": f"https://yamlr.dev/docs/rules/{rule_id}"
        }
        if registry:
            self._apply_compliance_to_rule(node, rule_id, registry)
        return node

    def _apply_compliance_to_rule(self, node: Dict[str, Any], rule_id: str, registry: Any) -> None:
        """Injects compliance mappings into rule definition."""
        attributions = registry.get_attributions(rule_id)
        if not attributions: return
        
        node["properties"] = {"tags": attributions}
        relationships = []
        for attr in attributions:
            parts = attr.split(": ")
            if len(parts) == 2:
                fw, ctrl_id = parts
                relationships.append({
                    "target": {"id": ctrl_id, "toolComponent": {"name": fw}}
                })
        if relationships: node["relationships"] = relationships

    def _extract_results(self, results: List[HealFileResult]) -> List[Dict[str, Any]]:
        """Maps Yamlr findings to SARIF results."""
        sarif_results = []
        for res in results:
            for finding in res.findings:
                sarif_results.append(self._format_result_node(res, finding))
                
        # [DETERMINISM] Enforce strict ordering
        sarif_results.sort(key=lambda x: (
            x["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            x["ruleId"],
            x["message"]["text"]
        ))
        return sarif_results

    def _format_result_node(self, res: HealFileResult, finding: Any) -> Dict[str, Any]:
        """Formats a single SARIF result node."""
        import urllib.parse
        # RFC 3986 Compliance: Encode spaces and special chars, ensure forward slashes
        f_path_norm = str(res.file_path).replace("\\", "/")
        f_path_uri = urllib.parse.quote(f_path_norm)
        
        full_msg = self._build_result_message(finding)
        
        node = {
            "ruleId": self._get_rule_id(finding),
            "level": "error" if self._get_severity(finding) == "error" else "warning",
            "message": {"text": full_msg},
            "locations": [{"physicalLocation": self._build_physical_location(res, f_path_uri, finding)}],
            "partialFingerprints": {"primaryHash": self._compute_fingerprint(f_path_norm, full_msg, finding)},
            "properties": {
                "riskLevel": self._get_risk_prop(finding, "risk_level", "LOW"),
                "riskCategory": self._get_risk_prop(finding, "risk_category", "General"),
                "trustScore": round(getattr(res, "trust_score", 100.0), 4),
                # Normalized Integrity Score
                "integrityScore": getattr(res, "dna_integrity_score", 0)
            }
        }
        return node

    def _get_severity(self, finding: Any) -> str:
        """Extracts result severity."""
        if isinstance(finding, dict): return (finding.get("severity") or "").lower()
        return (getattr(finding, "severity", "") or "").lower()

    def _get_risk_prop(self, finding: Any, prop: str, default: str) -> str:
        """Extracts and normalizes risk properties."""
        val = finding.get(prop, default) if isinstance(finding, dict) else getattr(finding, prop, default)
        return str(val).upper() if prop == "risk_level" else str(val)

    def _build_result_message(self, finding: Any) -> str:
        """Constructs enhanced finding message with risk intelligence."""
        msg = finding.get("message", "") if isinstance(finding, dict) else getattr(finding, "message", "")
        impact = finding.get("impact_description", "") if isinstance(finding, dict) else getattr(finding, "impact_description", "")
        risk = self._get_risk_prop(finding, "risk_level", "LOW")
        sugg = finding.get("suggestion", "No suggestion") if isinstance(finding, dict) else getattr(finding, "suggestion", "No suggestion")
        
        final = f"[{impact}] {msg}" if impact else msg
        return f"{final} (Risk: {risk}, Suggestion: {sugg})"

    def _compute_fingerprint(self, path: str, msg: str, finding: Any) -> str:
        """Computes a stable fingerprint for issue tracking."""
        line = finding.get("line_number", 0) if isinstance(finding, dict) else getattr(finding, "line_number", 0)
        rule = self._get_rule_id(finding)
        raw = f"{path}:{rule}:{line}:{msg}"
        import hashlib
        return hashlib.sha256(raw.encode()).hexdigest()

    def _build_physical_location(self, res: HealFileResult, path: str, finding: Any) -> Dict[str, Any]:
        """Builds standardized physical location node."""
        phys = {"artifactLocation": {"uri": path}}
        line = finding.get("line_number", 0) if isinstance(finding, dict) else getattr(finding, "line_number", 0)
        if line > 0:
            region = {"startLine": line}
            if res.raw_content:
                lines = res.raw_content.splitlines()
                if 0 < line <= len(lines):
                    region["snippet"] = {"text": lines[line-1].strip()}
            phys["region"] = region
        return phys
