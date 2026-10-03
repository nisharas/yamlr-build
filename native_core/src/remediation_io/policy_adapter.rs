//! Policy Ingestion Adapter for OPA Gatekeeper and Kyverno.
//!
//! Why: Ingests external admission violation reports (JSON) and executes surgical
//! auto-repair on matching Kubernetes manifests directly in native Rust.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IngestedPolicyViolation {
    pub policy: String,
    pub kind: String,
    pub name: String,
    pub message: String,
}

/// Parses an OPA Gatekeeper JSON violation report.
pub fn parse_opa_report(json_str: &str) -> Result<Vec<IngestedPolicyViolation>, String> {
    let data: Value =
        serde_json::from_str(json_str).map_err(|e| format!("Failed to parse OPA JSON: {}", e))?;

    let mut violations = Vec::new();
    let items = data
        .as_array()
        .or_else(|| data.get("violations").and_then(Value::as_array))
        .or_else(|| data.pointer("/status/violations").and_then(Value::as_array))
        .or_else(|| data.get("items").and_then(Value::as_array))
        .ok_or_else(|| {
            "OPA report must be an array or contain a violations, status.violations, or items array"
                .to_string()
        })?;

    for item in items {
        let policy = item
            .get("constraint")
            .or_else(|| item.get("rule"))
            .and_then(|v| v.as_str())
            .unwrap_or("OPA-Constraint")
            .to_string();

        let resource = item.get("resource");
        let kind = resource
            .and_then(|r| r.get("kind"))
            .or_else(|| item.get("kind"))
            .and_then(|k| k.as_str())
            .unwrap_or("")
            .to_string();

        let name = resource
            .and_then(|r| r.get("name"))
            .or_else(|| item.get("name"))
            .and_then(|n| n.as_str())
            .unwrap_or("")
            .to_string();

        let message = item
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("")
            .to_string();

        violations.push(IngestedPolicyViolation {
            policy,
            kind,
            name,
            message,
        });
    }

    Ok(violations)
}

/// Parses a Kyverno PolicyReport JSON violation report.
pub fn parse_kyverno_report(json_str: &str) -> Result<Vec<IngestedPolicyViolation>, String> {
    let data: Value = serde_json::from_str(json_str)
        .map_err(|e| format!("Failed to parse Kyverno JSON: {}", e))?;

    let mut violations = Vec::new();
    let results = data
        .as_array()
        .or_else(|| data.get("results").and_then(Value::as_array))
        .or_else(|| data.pointer("/status/results").and_then(Value::as_array))
        .ok_or_else(|| {
            "Kyverno report must be an array or contain a results or status.results array"
                .to_string()
        })?;

    for r in results {
        // Older exported reports omitted the outcome field; preserve their
        // historical interpretation as actionable while honoring standard
        // PolicyReport pass/skip results.
        match r.get("result") {
            None => {} // Legacy export without an outcome field.
            Some(Value::String(outcome)) => match outcome.to_ascii_lowercase().as_str() {
                "pass" | "skip" => continue,
                "fail" | "warn" | "error" => {}
                _ => {
                    return Err(format!(
                        "Unsupported Kyverno result '{}'; expected pass, fail, warn, error, or skip",
                        outcome
                    ));
                }
            },
            Some(_) => return Err("Kyverno result outcome must be a string".to_string()),
        }

        let policy = r
            .get("policy")
            .or_else(|| r.get("rule"))
            .and_then(|v| v.as_str())
            .unwrap_or("Kyverno-Policy")
            .to_string();

        let empty_res = vec![serde_json::json!({})];
        let resources = r
            .get("resources")
            .and_then(|res| res.as_array())
            .unwrap_or(&empty_res);

        for res in resources {
            let kind = res
                .get("kind")
                .and_then(|k| k.as_str())
                .unwrap_or("")
                .to_string();

            let name = res
                .get("name")
                .and_then(|n| n.as_str())
                .unwrap_or("")
                .to_string();

            let message = r
                .get("message")
                .and_then(|m| m.as_str())
                .unwrap_or("")
                .to_string();

            violations.push(IngestedPolicyViolation {
                policy: policy.clone(),
                kind,
                name,
                message,
            });
        }
    }

    Ok(violations)
}

/// Ingests an OPA or Kyverno report file, searches target directory for matching manifests,
/// and applies Yamlr AST healing.
pub fn ingest_and_heal_policy_file(
    report_path: &Path,
    target_dir: &Path,
    report_type: &str,
    apply: bool,
) -> Result<Vec<String>, String> {
    let content = fs::read_to_string(report_path).map_err(|e| {
        format!(
            "Failed to read policy report '{}': {}",
            report_path.display(),
            e
        )
    })?;

    let violations = if report_type.eq_ignore_ascii_case("opa") {
        parse_opa_report(&content)?
    } else if report_type.eq_ignore_ascii_case("kyverno") {
        parse_kyverno_report(&content)?
    } else {
        return Err(format!("Unsupported policy report type: {}", report_type));
    };

    let mut applied_actions = Vec::new();

    for entry in walkdir::WalkDir::new(target_dir) {
        let entry = entry.map_err(|error| {
            format!(
                "Failed to traverse policy target '{}': {}",
                target_dir.display(),
                error
            )
        })?;
        let p = entry.path();
        if p.is_file() {
            if let Some(ext) = p.extension() {
                if ext == "yaml" || ext == "yml" {
                    let manifest_content = fs::read_to_string(p).map_err(|error| {
                        format!("Failed to read policy target '{}': {}", p.display(), error)
                    })?;
                    let shards = crate::sharder::native_shard(&manifest_content);
                    if shards.is_empty() {
                        continue;
                    }
                    let Some(id) = crate::identity::extract_native_identity(shards) else {
                        continue;
                    };

                    // Check if this manifest matches any policy violation
                    let matches: Vec<_> = violations
                        .iter()
                        .filter(|v| {
                            v.kind.eq_ignore_ascii_case(&id.kind)
                                && (v.name.is_empty() || v.name.eq_ignore_ascii_case(&id.name))
                        })
                        .collect();

                    if !matches.is_empty() {
                        let (healed, changes) =
                            crate::cli::heal_cmd::heal_manifest_string(&manifest_content);
                        if !changes.is_empty() {
                            if apply {
                                fs::write(p, &healed).map_err(|error| {
                                    format!(
                                        "Failed to write policy-healed manifest '{}': {}",
                                        p.display(),
                                        error
                                    )
                                })?;
                            }
                            let msg = format!(
                                "{}: {} (addressed {} policy violation(s))",
                                p.display(),
                                if apply { "[APPLIED]" } else { "[PREVIEW]" },
                                matches.len()
                            );
                            applied_actions.push(msg);
                        }
                    }
                }
            }
        }
    }

    Ok(applied_actions)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_opa_violations() {
        let json_str = r#"{
            "violations": [
                {
                    "constraint": "k8srequiredlabels",
                    "resource": { "kind": "Deployment", "name": "my-deploy" },
                    "message": "Missing required label: app"
                }
            ]
        }"#;

        let v = parse_opa_report(json_str).unwrap();
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].kind, "Deployment");
        assert_eq!(v[0].name, "my-deploy");
        assert_eq!(v[0].policy, "k8srequiredlabels");
    }

    #[test]
    fn test_parse_kyverno_violations() {
        let json_str = r#"{
            "results": [
                {
                    "policy": "disallow-latest-tag",
                    "resources": [
                        { "kind": "Pod", "name": "test-pod" }
                    ],
                    "message": "Using latest tag is disallowed."
                }
            ]
        }"#;

        let v = parse_kyverno_report(json_str).unwrap();
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].kind, "Pod");
        assert_eq!(v[0].name, "test-pod");
        assert_eq!(v[0].policy, "disallow-latest-tag");
    }
}
