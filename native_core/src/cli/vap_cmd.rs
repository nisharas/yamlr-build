//! In-Tree ValidatingAdmissionPolicy (VAP) and CEL Policy Exporter.
//!
//! Why: Kubernetes 1.26+ introduces native in-tree Common Expression Language (CEL) admission
//! control (`ValidatingAdmissionPolicy`), eliminating the operational latency, webhook outages,
//! and TLS certificate renewal overhead of legacy admission webhooks. This generator translates
//! Yamlr's forensic audit rules into production-ready Kubernetes VAP manifests.

use crate::cli::{EXIT_CONFIG_ERROR, EXIT_SUCCESS};
use std::fs;

/// Generates a complete Kubernetes 1.26+ `ValidatingAdmissionPolicy` manifest in YAML format.
pub fn generate_validating_admission_policy(
    policy_name: &str,
    rules_filter: Option<&[&str]>,
) -> String {
    let mut out = String::new();
    out.push_str("apiVersion: admissionregistration.k8s.io/v1\n");
    out.push_str("kind: ValidatingAdmissionPolicy\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}\n", policy_name));
    out.push_str("  labels:\n");
    out.push_str("    app.kubernetes.io/managed-by: yamlr\n");
    out.push_str("    yamlr.dev/policy-engine: cel\n");
    out.push_str("spec:\n");
    out.push_str("  failurePolicy: Fail\n");
    out.push_str("  matchConstraints:\n");
    out.push_str("    resourceRules:\n");
    out.push_str("      - apiGroups: [\"apps\"]\n");
    out.push_str("        apiVersions: [\"v1\"]\n");
    out.push_str("        operations: [\"CREATE\", \"UPDATE\"]\n");
    out.push_str("        resources: [\"deployments\", \"statefulsets\", \"daemonsets\"]\n");
    out.push_str("      - apiGroups: [\"\"]\n");
    out.push_str("        apiVersions: [\"v1\"]\n");
    out.push_str("        operations: [\"CREATE\", \"UPDATE\"]\n");
    out.push_str("        resources: [\"pods\", \"services\"]\n");
    out.push_str("  validations:\n");

    let all_rules = [
        (
            "OPS-002",
            "object.spec.template.spec.containers.all(c, !c.image.endsWith(':latest'))",
            "[OPS-002] Container images must be pinned to specific tags or digests (':latest' prohibited).",
        ),
        (
            "SEC-002",
            "object.spec.template.spec.containers.all(c, c.imagePullPolicy == 'Always')",
            "[SEC-002] Container imagePullPolicy must be set to 'Always' to guarantee authenticity.",
        ),
        (
            "SEC-004",
            "object.spec.template.spec.containers.all(c, has(c.securityContext) && c.securityContext.readOnlyRootFilesystem == true)",
            "[SEC-004] Containers must enforce readOnlyRootFilesystem to prevent tampering.",
        ),
        (
            "SEC-005",
            "object.spec.template.spec.containers.all(c, has(c.securityContext) && c.securityContext.runAsNonRoot == true)",
            "[SEC-005] Containers must run as non-root user (securityContext.runAsNonRoot must be true).",
        ),
        (
            "RES-001",
            "object.spec.template.spec.containers.all(c, has(c.resources) && has(c.resources.limits) && has(c.resources.requests))",
            "[RES-001] Containers must declare both resource limits and requests to guarantee QoS.",
        ),
        (
            "REL-001",
            "!has(object.spec.replicas) || object.spec.replicas >= 0",
            "[REL-001] Replicas must be non-negative.",
        ),
        (
            "AUT-001",
            "!has(object.spec.minReplicas) || !has(object.spec.maxReplicas) || object.spec.minReplicas <= object.spec.maxReplicas",
            "[AUT-001] spec.minReplicas must be less than or equal to spec.maxReplicas.",
        ),
    ];

    for (rule_id, expr, msg) in &all_rules {
        if let Some(filter) = rules_filter {
            if !filter.iter().any(|&f| f.eq_ignore_ascii_case(rule_id)) {
                continue;
            }
        }
        out.push_str(&format!("    # Rule {}\n", rule_id));
        out.push_str(&format!("    - expression: \"{}\"\n", expr));
        out.push_str(&format!("      message: \"{}\"\n", msg));
    }

    out
}

/// Generates a corresponding `ValidatingAdmissionPolicyBinding` manifest.
pub fn generate_policy_binding(policy_name: &str, excluded_namespaces: &[&str]) -> String {
    let mut out = String::new();
    out.push_str("apiVersion: admissionregistration.k8s.io/v1\n");
    out.push_str("kind: ValidatingAdmissionPolicyBinding\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}-binding\n", policy_name));
    out.push_str("  labels:\n");
    out.push_str("    app.kubernetes.io/managed-by: yamlr\n");
    out.push_str("spec:\n");
    out.push_str(&format!("  policyName: {}\n", policy_name));
    out.push_str("  validationActions: [Deny, Audit]\n");
    out.push_str("  matchResources:\n");
    out.push_str("    namespaceSelector:\n");
    out.push_str("      matchExpressions:\n");
    out.push_str("        - key: kubernetes.io/metadata.name\n");
    out.push_str("          operator: NotIn\n");
    out.push_str("          values:\n");
    for ns in excluded_namespaces {
        out.push_str(&format!("            - \"{}\"\n", ns));
    }
    out
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct IngestedVapRule {
    pub expression: String,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct IngestedVapPolicy {
    pub name: String,
    pub api_groups: Vec<String>,
    pub resources: Vec<String>,
    pub rules: Vec<IngestedVapRule>,
}

/// Parses a ValidatingAdmissionPolicy manifest into structured policies and CEL rules.
pub fn parse_vap_manifest(content: &str) -> Result<Vec<IngestedVapPolicy>, String> {
    let mut policies = Vec::new();
    for doc in crate::parsers::streaming::stream_document_slices(content) {
        let trimmed = doc.trim();
        if trimmed.is_empty() {
            continue;
        }
        let val: serde_yaml::Value = match serde_yaml::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => return Err(format!("Failed to parse YAML document: {}", e)),
        };

        let kind = val.get("kind").and_then(|k| k.as_str()).unwrap_or("");
        if kind != "ValidatingAdmissionPolicy" {
            continue;
        }

        let name = val
            .get("metadata")
            .and_then(|m| m.get("name"))
            .and_then(|n| n.as_str())
            .unwrap_or("unnamed-policy")
            .to_string();

        let mut api_groups = Vec::new();
        let mut resources = Vec::new();

        if let Some(spec) = val.get("spec") {
            if let Some(constraints) = spec.get("matchConstraints") {
                if let Some(rules) = constraints
                    .get("resourceRules")
                    .and_then(|r| r.as_sequence())
                {
                    for r in rules {
                        if let Some(groups) = r.get("apiGroups").and_then(|g| g.as_sequence()) {
                            for g in groups {
                                if let Some(s) = g.as_str() {
                                    api_groups.push(s.to_string());
                                }
                            }
                        }
                        if let Some(res) = r.get("resources").and_then(|res| res.as_sequence()) {
                            for res_item in res {
                                if let Some(s) = res_item.as_str() {
                                    resources.push(s.to_string());
                                }
                            }
                        }
                    }
                }
            }

            let mut vap_rules = Vec::new();
            if let Some(validations) = spec.get("validations").and_then(|v| v.as_sequence()) {
                for v in validations {
                    let expr = v
                        .get("expression")
                        .and_then(|e| e.as_str())
                        .unwrap_or("")
                        .to_string();
                    let msg = v
                        .get("message")
                        .and_then(|m| m.as_str())
                        .unwrap_or("")
                        .to_string();
                    if !expr.is_empty() {
                        vap_rules.push(IngestedVapRule {
                            expression: expr,
                            message: msg,
                        });
                    }
                }
            }

            policies.push(IngestedVapPolicy {
                name,
                api_groups,
                resources,
                rules: vap_rules,
            });
        }
    }
    Ok(policies)
}

/// Ingests a ValidatingAdmissionPolicy manifest and displays compiled CEL rules.
pub fn execute_vap_ingest(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("vap", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let path = match matches
        .get_one::<String>("file-target")
        .or_else(|| matches.get_one::<String>("file"))
    {
        Some(path) => path,
        None => return EXIT_CONFIG_ERROR,
    };

    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[ERROR] Failed to read VAP manifest '{}': {}", path, e);
            return EXIT_CONFIG_ERROR;
        }
    };

    let policies = match parse_vap_manifest(&content) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("[ERROR] Failed to parse VAP manifest: {}", e);
            return EXIT_CONFIG_ERROR;
        }
    };

    if policies.is_empty() {
        eprintln!(
            "[WARN] No ValidatingAdmissionPolicy resources found in '{}'",
            path
        );
        return EXIT_SUCCESS;
    }

    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("  Yamlr VAP Ingestion Engine (Kubernetes 1.30+ CEL)");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    let mut total_rules = 0;
    for pol in &policies {
        println!("[*] Ingested Policy: '{}'", pol.name);
        println!("    ├─ Scoped Groups   : {:?}", pol.api_groups);
        println!("    ├─ Scoped Resources: {:?}", pol.resources);
        println!("    └─ Active CEL Rules: {} rule(s)", pol.rules.len());
        for (idx, r) in pol.rules.iter().enumerate() {
            println!("       {}. Expression: {}", idx + 1, r.expression);
            if !r.message.is_empty() {
                println!("          Message   : {}", r.message);
            }
        }
        total_rules += pol.rules.len();
    }

    println!(
        "\n[+] Successfully ingested {} policy(ies) with {} active CEL validation rule(s).",
        policies.len(),
        total_rules
    );
    EXIT_SUCCESS
}

/// Exports ValidatingAdmissionPolicy manifests to stdout or output file.
pub fn execute_vap_export(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("vap", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let policy_name = matches.get_one::<String>("name").unwrap();
    let output_path = matches.get_one::<String>("output");

    let excluded_ns = ["kube-system", "kube-public", "kube-node-lease"];
    let vap_yaml = generate_validating_admission_policy(&policy_name, None);
    let binding_yaml = generate_policy_binding(&policy_name, &excluded_ns);

    let bundle = format!("{}\n---\n{}", vap_yaml.trim(), binding_yaml.trim());

    if let Some(path) = output_path {
        if let Err(e) = fs::write(&path, &bundle) {
            eprintln!("Error writing VAP bundle to '{}': {}", path, e);
            return EXIT_CONFIG_ERROR;
        }
        println!("[*] Exported ValidatingAdmissionPolicy bundle to: {}", path);
    } else {
        println!("{}", bundle);
    }

    EXIT_SUCCESS
}

/// Dispatches VAP operations (export or ingest).
pub fn execute_vap(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("vap", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let is_ingest = matches.get_flag("ingest")
        || matches
            .get_one::<String>("mode")
            .is_some_and(|mode| mode == "ingest");
    if is_ingest {
        return execute_vap_ingest(args);
    }
    execute_vap_export(args)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_export_vap_produces_valid_crd() {
        let vap = generate_validating_admission_policy("test-policy", None);
        assert!(vap.contains("kind: ValidatingAdmissionPolicy"));
        assert!(vap.contains("test-policy"));
        assert!(vap.contains("matchConstraints:"));
        assert!(vap.contains("failurePolicy: Fail"));

        let binding = generate_policy_binding("test-policy", &["kube-system"]);
        assert!(binding.contains("kind: ValidatingAdmissionPolicyBinding"));
        assert!(binding.contains("policyName: test-policy"));
        assert!(binding.contains("kube-system"));
    }

    #[test]
    fn test_vap_cel_rules_compiled() {
        let vap = generate_validating_admission_policy("test-policy", None);
        assert!(vap.contains("[OPS-002]"));
        assert!(vap.contains("[SEC-002]"));
        assert!(vap.contains("[SEC-004]"));
        assert!(vap.contains("[SEC-005]"));
        assert!(vap.contains("[RES-001]"));
        assert!(vap.contains("[AUT-001]"));

        // Verify filter
        let filtered =
            generate_validating_admission_policy("filtered-policy", Some(&["OPS-002", "SEC-002"]));
        assert!(filtered.contains("[OPS-002]"));
        assert!(filtered.contains("[SEC-002]"));
        assert!(!filtered.contains("[SEC-004]"));
    }

    #[test]
    fn test_parse_and_ingest_vap_manifest() {
        let sample_vap = r#"
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: test-replica-limit
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: "object.spec.replicas <= 10"
      message: "Replicas cannot exceed 10"
"#;
        let policies = parse_vap_manifest(sample_vap).expect("Failed to parse VAP manifest");
        assert_eq!(policies.len(), 1);
        let pol = &policies[0];
        assert_eq!(pol.name, "test-replica-limit");
        assert_eq!(pol.api_groups, vec!["apps"]);
        assert_eq!(pol.resources, vec!["deployments"]);
        assert_eq!(pol.rules.len(), 1);
        assert_eq!(pol.rules[0].expression, "object.spec.replicas <= 10");
        assert_eq!(pol.rules[0].message, "Replicas cannot exceed 10");
    }
}
