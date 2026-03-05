#!/usr/bin/env python3
"""
Yamlr SARIF FORMATTER
----------------------
Generates SARIF v2.1.0 JSON reports for integration with CI/CD platforms.

Author: Yamlr Team
Date: 2026-02-19
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from yamlr.models import HealFileResult

class SarifFormatter:
    """Converts Yamlr results into the standardized SARIF format."""

    def __init__(self, app_name: str = "Yamlr", version: str = "0.1.0"):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.app_name = app_name
        self.version = version

    def format(self, results: List[HealFileResult]) -> str:
        """Generates a SARIF JSON string from processing results."""
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
                    "results": self._extract_results(results)
                }
            ]
        }
        return json.dumps(sarif_log, indent=2)

    def _extract_rules(self, results: List[HealFileResult]) -> List[Dict]:
        """Extracts unique rules from findings and maps compliance attributions."""
        rules_map = {}
        
        # [PRO-14-21-3] Attempt to load the Enterprise Compliance Registry safely
        compliance_registry = None
        try:
            from yamlr.pro.compliance.ruleset import ComplianceRegistry
            compliance_registry = ComplianceRegistry()
        except ImportError:
            pass # Graceful fallback for OSS users

        for res in results:
            for finding in res.findings:
                rule_id = finding.get("rule_id", finding.get("analyzer", "generic-rule"))
                if rule_id not in rules_map:
                    rule_def = {
                        "id": rule_id,
                        "shortDescription": {"text": finding.get("message", "Yamlr Finding")},
                        "helpUri": f"https://yamlr.dev/docs/rules/{rule_id}"
                    }
                    
                    # Inject compliance mappings into the structural payload
                    if compliance_registry:
                        attributions = compliance_registry.get_attributions(rule_id)
                        if attributions:
                            rule_def["properties"] = {
                                "tags": attributions
                            }
                            
                    rules_map[rule_id] = rule_def
                    
        return sorted(list(rules_map.values()), key=lambda r: r["id"])

    def _extract_results(self, results: List[HealFileResult]) -> List[Dict]:
        """Maps Yamlr findings to SARIF results."""
        sarif_results = []
        for res in results:
            for finding in res.findings:
                level = "error" if finding.get("severity", "").lower() == "error" else "warning"
                # Risk Intelligence Integration
                risk_l = finding.get("risk_level", "LOW").upper()
                risk_cat = finding.get("risk_category", "General")
                risk_impact = finding.get("impact_description", "")
                
                # Enhance message with risk info
                full_msg_text = finding['message']
                if risk_impact:
                    full_msg_text = f"[{risk_impact}] {full_msg_text}"
                full_msg_text += f" (Risk: {risk_l}, Suggestion: {finding.get('suggestion', 'No suggestion available')})"

                result_node = {
                    "ruleId": finding.get("rule_id", finding.get("analyzer", "generic-rule")),
                    "level": level,
                    "message": {"text": full_msg_text},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": res.file_path},
                            }
                        }
                    ],
                    "properties": {
                        "riskLevel": risk_l,
                        "riskCategory": risk_cat
                    }
                }
                sarif_results.append(result_node)
                
        # [FREE-12-08] Enforce strict determinism for CI/CD consistency
        sarif_results.sort(key=lambda x: (
            x["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            x["ruleId"],
            x["message"]["text"]
        ))
        return sarif_results
