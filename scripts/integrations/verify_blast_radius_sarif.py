#!/usr/bin/env python3
"""
Yamlr SARIF BLAST-RADIUS VERIFICATION (FIXED)
----------------------------------------------
Validates that risk metadata (blast radius, propagation depth, etc.)
is correctly exported to the SARIF output format.

Author: Yamlr Team
Date: 2026-03-31
"""

import json
import os
import sys
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from yamlr.core.io.sarif_formatter import SarifFormatter
from yamlr.core.pipeline.models import HealAction, HealFileResult


def verify_sarif_enrichment():
    print(" Starting SARIF Blast-Radius Verification...")

    # 1. Setup finding with blast radius data
    # We use a dict as findings can be serialized dicts in HealFileResult
    finding = {
        "rule_id": "k8s/wide-rbac",
        "message": "ServiceAccount has wildcard permissions",
        "severity": "ERROR",
        "line_number": 10,
        "impact_description": "High Cluster Risk",
        "risk_level": "CRITICAL",
        "risk_category": "Privilege Escalation",
        "scope_count": 5,
        "propagation_depth": 2,
        "affected_resources": ["Deployment/auth-api", "Pod/creds-harvester", "Secret/db-pass"],
    }

    # 2. Setup HealFileResult object
    res = HealFileResult(
        file_path="deployments/rbac.yaml",
        full_path="/abs/path/deployments/rbac.yaml",
        success=True,
        status="HEALED",
        kind="ServiceAccount",
        logic_logs=[],
        findings=[finding],
        dna_integrity_score=92,
        identities=[],
        timestamp=time.time(),
        raw_content="apiVersion: v1\nkind: ServiceAccount\nmetadata:\n  name: admin",
        trust_score=0.85,
    )

    # 3. Format to SARIF
    formatter = SarifFormatter()
    sarif_str = formatter.format([res])
    sarif_data = json.loads(sarif_str)

    # 4. Assertions
    result_node = sarif_data["runs"][0]["results"][0]
    props = result_node.get("properties", {})

    print("Checking SARIF Properties...")
    # Map back the property names as they are in SarifFormatter
    assert props.get("blastRadius") == 5, f"Expected blastRadius 5, got {props.get('blastRadius')}"
    assert props.get("propagationDepth") == 2, f"Expected propagationDepth 2, got {props.get('propagationDepth')}"
    assert "Deployment/auth-api" in props.get("affectedResources", []), "Missing affected resource Deployment/auth-api"
    assert props.get("riskLevel") == "CRITICAL", f"Expected riskLevel CRITICAL, got {props.get('riskLevel')}"

    print("Checking Related Locations...")
    related = result_node.get("relatedLocations", [])
    assert len(related) > 0, "Missing relatedLocations"
    assert "Affected resource: Deployment/auth-api" in related[0]["message"]["text"]

    # Check physical location URI normalized
    uri = related[0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "deployments/rbac.yaml", f"Expected normalized URI deployments/rbac.yaml, got {uri}"

    print("✅ Verification Successful: SARIF Blast-Radius Integration confirmed.")


if __name__ == "__main__":
    try:
        verify_sarif_enrichment()
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
