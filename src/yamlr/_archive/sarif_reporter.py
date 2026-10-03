import json
import os
from datetime import datetime
from typing import Any, List


class SarifReporter:
    """SARIF 2.1.0 report generator for CI/CD pipelines and GitHub Code Scanning."""
    
    @staticmethod
    def generate_sarif(results: List[Any], output_path: str):
        """Generates a SARIF 2.1.0 compliant JSON report."""
        rules = []
        rule_ids = set()

        # Pre-populate rule metadata
        # Load rule metadata from forensic catalog if available
        catalog_path = os.path.join(os.path.dirname(__file__), "catalog", "forensic_catalog.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    catalog = json.load(f)
                    detector_items = []
                    if isinstance(catalog, dict) and "detectors" in catalog:
                        for d in catalog["detectors"]:
                            if isinstance(d, dict) and "id" in d:
                                detector_items.append((d["id"], d))
                    elif isinstance(catalog, dict):
                        detector_items = list(catalog.items())
                    
                    for rule_id, meta in detector_items:
                        rules.append({
                            "id": rule_id,
                            "shortDescription": {"text": meta.get("name", rule_id)},
                            "fullDescription": {"text": meta.get("rationale", meta.get("description", ""))},
                            "helpUri": f"https://yamlr.dev/errors/{rule_id.lower()}",
                            "defaultConfiguration": {"level": SarifReporter._map_severity(meta.get("severity", "INFO"))}
                        })
                        rule_ids.add(rule_id)
            except Exception:
                pass


        sarif = {
            "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "yamlr",
                            "informationUri": "https://yamlr.dev",
                            "semanticVersion": "0.1.0",
                            "rules": rules
                        }
                    },
                    "results": []
                }
            ]
        }
        
        for res in results:
            # 1. Process Integrity Violations (Audit Engine)
            for v in getattr(res, "integrity_violations", []):
                rule_id = str(getattr(v, "rule_id", "UNKNOWN"))
                if rule_id not in rule_ids:
                    rules.append({
                        "id": rule_id,
                        "shortDescription": {"text": str(getattr(v, "check_name", "Integrity Check"))},
                        "fullDescription": {"text": str(getattr(v, "message", "No description provided"))},
                        "helpUri": f"https://yamlr.dev/errors/{rule_id.lower()}",
                        "defaultConfiguration": {"level": SarifReporter._map_severity(getattr(v, "severity", "INFO"))}
                    })
                    rule_ids.add(rule_id)

                fix = next((f for f in getattr(res, "suggested_fixes", []) if getattr(f, "rule_id", None) == rule_id or getattr(f, "field_path", "") in str(getattr(v, "message", ""))), None)
                sarif["runs"][0]["results"].append(SarifReporter._build_result(res, rule_id, str(getattr(v, "message", "")), getattr(v, "severity", "INFO"), getattr(v, "line_no", 1), fix))

            # 2. Process Schema Violations (OpenAPI Engine)
            for v in getattr(res, "violations", []):
                field_path = str(getattr(v, "field_path", "unknown"))
                rule_id = f"SCHEMA-{field_path}"
                if rule_id not in rule_ids:
                    rules.append({
                        "id": rule_id,
                        "shortDescription": {"text": f"Schema Violation: {field_path}"},
                        "fullDescription": {"text": str(getattr(v, "message", "Schema validation failed"))}
                    })
                    rule_ids.add(rule_id)
                
                fix = next((f for f in getattr(res, "suggested_fixes", []) if getattr(f, "field_path", "") == field_path), None)
                sarif["runs"][0]["results"].append(SarifReporter._build_result(res, rule_id, str(getattr(v, "message", "")), getattr(v, "severity", "ERROR"), 1, fix))
                
        # Sort rules and results for reproducible output
        sarif["runs"][0]["tool"]["driver"]["rules"] = sorted(rules, key=lambda x: x["id"])
        sarif["runs"][0]["results"] = sorted(
            sarif["runs"][0]["results"],
            key=lambda x: (
                x.get("locations", [{}])[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri", ""),
                x.get("locations", [{}])[0].get("physicalLocation", {}).get("region", {}).get("startLine", 1),
                x.get("ruleId", "")
            )
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2)

    @staticmethod
    def _build_result(res, rule_id, message, severity, line_no, suggested_fix=None):
        rel_path = os.path.relpath(res.file_path, os.getcwd()).replace("\\", "/")
        result = {
            "ruleId": rule_id,
            "level": SarifReporter._map_severity(severity),
            "message": {"text": message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": rel_path},
                    "region": {"startLine": line_no or 1}
                }
            }]
        }
        if suggested_fix is not None:
            field = getattr(suggested_fix, "field_path", "")
            val = getattr(suggested_fix, "suggested_value", "")
            replacement_text = f"{field}: {val}" if field and val else str(val or field)
            result["fixes"] = [{
                "description": {"text": f"Auto-heal {rule_id}: apply surgical resolution"},
                "artifactChanges": [{
                    "artifactLocation": {"uri": rel_path},
                    "replacements": [{
                        "deletedRegion": {"startLine": line_no or 1},
                        "insertedContent": {"text": replacement_text}
                    }]
                }]
            }]
        return result

    @staticmethod
    def _map_severity(severity: str) -> str:
        mapping = {
            "CRITICAL": "error",
            "HIGH": "error",
            "WARNING": "warning",
            "INFO": "note"
        }
        return mapping.get(severity, "note")
