//! Output report renderers (text, JSON, and SARIF 2.1) for scan results.

use crate::cli::scan_cmd::ViolationRecord;

pub(crate) fn render_text(
    target: &str,
    k8s_ver: &str,
    files: usize,
    violations: usize,
    integrity: usize,
    ms: f64,
) -> String {
    let mut out = String::new();
    out.push_str(&format!("=== Yamlr Scan Report (K8s v{}) ===\n", k8s_ver));
    out.push_str(&format!("Manifests Audited: {}\n", files));
    out.push_str(&format!("Schema Violations: {}\n", violations));
    out.push_str(&format!("Integrity/Forensic Violations: {}\n", integrity));
    out.push_str(&format!("Execution Duration: {:.2}ms\n", ms));

    if violations + integrity == 0 {
        out.push_str("\n[PASS] All manifests meet Kubernetes schema and integrity standards.\n");
    } else {
        out.push_str(&format!(
            "\n[FAIL] Violations detected. Run 'yamlr heal {}' to auto-remediate.\n",
            target
        ));
    }
    out
}

pub(crate) fn render_json(
    files: usize,
    violations: usize,
    integrity: usize,
    ms: u128,
    results: &[ViolationRecord],
) -> String {
    let output = serde_json::json!({
        "status": if violations + integrity == 0 { "passed" } else { "failed" },
        "total_files": files,
        "schema_violations": violations,
        "integrity_violations": integrity,
        "duration_ms": ms,
        "results": results,
    });
    serde_json::to_string_pretty(&output).unwrap_or_default()
}

pub(crate) fn render_sarif(k8s_ver: &str, results: &[ViolationRecord]) -> String {
    let mut rules_map = std::collections::BTreeMap::new();
    rules_map.insert(
        "SCH-001".to_string(),
        serde_json::json!({
            "id": "SCH-001",
            "shortDescription": { "text": format!("Kubernetes v{} Schema Violation", k8s_ver) },
            "helpUri": "https://yamlr.dev/errors/sch-001"
        }),
    );

    // Ingest all 53 catalog detectors
    if let Ok(catalog) = serde_json::from_str::<serde_json::Value>(include_str!(
        "../../catalog/forensic_catalog.json"
    )) {
        if let Some(detectors) = catalog.get("detectors").and_then(|d| d.as_array()) {
            for d in detectors {
                if let Some(id) = d.get("id").and_then(|i| i.as_str()) {
                    let name = d.get("name").and_then(|n| n.as_str()).unwrap_or(id);
                    let rationale = d.get("rationale").and_then(|r| r.as_str()).unwrap_or("");
                    rules_map.insert(
                        id.to_string(),
                        serde_json::json!({
                            "id": id,
                            "shortDescription": { "text": name },
                            "fullDescription": { "text": rationale },
                            "helpUri": format!("https://yamlr.dev/errors/{}", id.to_lowercase())
                        }),
                    );
                }
            }
        }
    }

    let mut graph_edges = Vec::new();

    let sarif_results: Vec<serde_json::Value> = results
        .iter()
        .map(|r| {
            let level = match r.severity.as_str() {
                "error" | "critical" | "high" | "CRITICAL" | "HIGH" | "ERROR" => "error",
                "warning" | "medium" | "WARNING" | "MEDIUM" => "warning",
                _ => "note",
            };
            if !rules_map.contains_key(&r.rule_id) {
                rules_map.insert(
                    r.rule_id.clone(),
                    serde_json::json!({
                        "id": r.rule_id,
                        "shortDescription": { "text": r.message.clone() },
                        "helpUri": format!("https://yamlr.dev/errors/{}", r.rule_id.to_lowercase())
                    }),
                );
            }

            let rel_file = crate::path_utils::relativize_to_workspace(&r.file, None);

            let mut res_obj = serde_json::json!({
                "ruleId": r.rule_id,
                "level": level,
                "message": { "text": r.message },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": { "uri": rel_file },
                        "region": { "startLine": r.line, "startColumn": 1 }
                    }
                }]
            });

            // Attach SARIF 2.1 codeFlows for cross-resource correlation
            if r.rule_id.starts_with("REF-")
                || r.rule_id.starts_with("DAN-")
                || r.rule_id.starts_with("SVC-")
                || r.message.contains("selector")
            {
                let cf = crate::sarif::build_cross_resource_code_flow(
                    &rel_file,
                    r.line,
                    &r.message,
                    &rel_file,
                    r.line,
                    "Reference target unresolved in topology graph",
                );
                res_obj["codeFlows"] = serde_json::to_value(vec![cf]).unwrap_or_default();
                graph_edges.push((rel_file.clone(), r.rule_id.clone(), "violation".to_string()));
            }

            res_obj
        })
        .collect();

    let rules: Vec<serde_json::Value> = rules_map.into_values().collect();
    let sarif_graph = crate::sarif::build_sarif_graph("yamlr-scan-topology", &graph_edges);

    let output = serde_json::json!({
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "yamlr",
                    "version": "0.1.0",
                    "informationUri": "https://yamlr.dev",
                    "rules": rules
                }
            },
            "graphs": [sarif_graph],
            "results": sarif_results
        }]
    });
    serde_json::to_string_pretty(&output).unwrap_or_default()
}
