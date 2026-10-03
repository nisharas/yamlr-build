//! Native Rego Policy Rule Compiler & High-Speed AST Evaluator.
//!
//! Why: Enterprise platform teams define governance using Open Policy Agent (OPA)
//! Rego policies (e.g. enforcing securityContext, disallowing privileged containers,
//! forbidding :latest tags, mandating labels). Running an external OPA binary or Wasm
//! runtime adds cold-start latency and lacks Yamlr's comment-preserving auto-repair wedge.
//! This module parses declarative OPA `deny[...]` rules into compiled native AST predicates,
//! evaluating policies in microseconds and synthesizing remediation suggestions.

use crate::identity::extractors::iter_shard_paths;
use crate::models::{IntegrityViolation, NativeShard};
use serde::{Deserialize, Serialize};

/// A parsed Rego condition matching on manifest paths.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RegoCondition {
    /// Matches when the field at path equals the expected string.
    Equals { path: String, expected: String },
    /// Matches when the field at path does not equal the expected string.
    NotEquals { path: String, expected: String },
    /// Matches when the field at path is missing.
    Missing { path: String },
    /// Matches when the field at path starts with prefix.
    StartsWith { path: String, prefix: String },
    /// Matches when the field at path contains substring.
    Contains { path: String, substring: String },
}

/// A compiled Rego rule representation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompiledRegoRule {
    pub rule_id: String,
    pub name: String,
    pub message: String,
    pub severity: String,
    pub conditions: Vec<RegoCondition>,
}

/// High-speed Rego Policy Compiler & Evaluator.
pub struct RegoCompiler;

impl RegoCompiler {
    /// Compiles a simple declarative Rego deny rule string into a CompiledRegoRule.
    ///
    /// Example syntax:
    /// ```text
    /// package kubernetes.admission
    /// deny[msg] {
    ///     input.kind == "Deployment"
    ///     not input.spec.template.spec.securityContext.runAsNonRoot
    ///     msg := "Deployment must set runAsNonRoot"
    /// }
    /// ```
    pub fn compile(rule_id: &str, rego_source: &str) -> Result<CompiledRegoRule, String> {
        let mut conditions = Vec::new();
        let mut message = format!("Rego policy violation ({})", rule_id);
        let severity = "ERROR".to_string();

        for raw_line in rego_source.lines() {
            let line = raw_line.trim();
            if line.is_empty()
                || line.starts_with('#')
                || line.starts_with("package ")
                || line.starts_with("deny[")
                || line == "}"
            {
                continue;
            }

            // Parse msg := "..." or msg = "..."
            if line.starts_with("msg :=") || line.starts_with("msg =") {
                if let Some(start_q) = line.find('"') {
                    if let Some(end_q) = line.rfind('"') {
                        if end_q > start_q {
                            message = line[start_q + 1..end_q].to_string();
                        }
                    }
                }
                continue;
            }

            // Parse input.path == "value"
            if line.contains("==") {
                let parts: Vec<&str> = line.split("==").map(|s| s.trim()).collect();
                if parts.len() == 2 {
                    let path = clean_rego_path(parts[0]);
                    let expected = parts[1].trim_matches(|c| c == '"' || c == '\'');
                    conditions.push(RegoCondition::Equals {
                        path,
                        expected: expected.to_string(),
                    });
                }
            } else if line.contains("!=") {
                let parts: Vec<&str> = line.split("!=").map(|s| s.trim()).collect();
                if parts.len() == 2 {
                    let path = clean_rego_path(parts[0]);
                    let expected = parts[1].trim_matches(|c| c == '"' || c == '\'');
                    conditions.push(RegoCondition::NotEquals {
                        path,
                        expected: expected.to_string(),
                    });
                }
            } else if line.starts_with("not input.") {
                let raw_path = &line[4..]; // strip "not "
                let path = clean_rego_path(raw_path);
                conditions.push(RegoCondition::Missing { path });
            } else if line.starts_with("endswith(") || line.starts_with("contains(") {
                // Extended built-in predicates
                if let Some(args_start) = line.find('(') {
                    if let Some(args_end) = line.rfind(')') {
                        let inner = &line[args_start + 1..args_end];
                        let parts: Vec<&str> = inner.split(',').map(|s| s.trim()).collect();
                        if parts.len() == 2 {
                            let path = clean_rego_path(parts[0]);
                            let substring = parts[1].trim_matches(|c| c == '"' || c == '\'');
                            conditions.push(RegoCondition::Contains {
                                path,
                                substring: substring.to_string(),
                            });
                        }
                    }
                }
            }
        }

        Ok(CompiledRegoRule {
            rule_id: rule_id.to_string(),
            name: format!("Rego:{}", rule_id),
            message,
            severity,
            conditions,
        })
    }

    /// Evaluates a compiled Rego rule against raw document shards.
    pub fn evaluate_shards(
        rule: &CompiledRegoRule,
        shards: &[NativeShard],
    ) -> Option<IntegrityViolation> {
        let paths = iter_shard_paths(shards);

        for condition in &rule.conditions {
            match condition {
                RegoCondition::Equals { path, expected } => {
                    let matched = paths.iter().any(|(p, s)| {
                        normalize_path_pattern(p, path)
                            && s.value
                                .as_deref()
                                .map(|v| v.trim_matches(|c| c == '"' || c == '\''))
                                == Some(expected.as_str())
                    });
                    if !matched {
                        return None;
                    }
                }
                RegoCondition::NotEquals { path, expected } => {
                    let matched = paths.iter().any(|(p, s)| {
                        normalize_path_pattern(p, path)
                            && s.value
                                .as_deref()
                                .map(|v| v.trim_matches(|c| c == '"' || c == '\''))
                                != Some(expected.as_str())
                    });
                    if !matched {
                        return None;
                    }
                }
                RegoCondition::Missing { path } => {
                    let exists = paths.iter().any(|(p, _)| normalize_path_pattern(p, path));
                    if exists {
                        return None; // If it exists, condition "not input..." failed
                    }
                }
                RegoCondition::StartsWith { path, prefix } => {
                    let matched = paths.iter().any(|(p, s)| {
                        normalize_path_pattern(p, path)
                            && s.value
                                .as_deref()
                                .map(|v| v.starts_with(prefix))
                                .unwrap_or(false)
                    });
                    if !matched {
                        return None;
                    }
                }
                RegoCondition::Contains { path, substring } => {
                    let matched = paths.iter().any(|(p, s)| {
                        normalize_path_pattern(p, path)
                            && s.value
                                .as_deref()
                                .map(|v| v.contains(substring))
                                .unwrap_or(false)
                    });
                    if !matched {
                        return None;
                    }
                }
            }
        }

        Some(IntegrityViolation {
            check_name: "OPA-REGO-POLICY-DENIAL".to_string(),
            severity: rule.severity.clone(),
            rule_id: rule.rule_id.clone(),
            message: rule.message.clone(),
            line_no: 0,
        })
    }
}

fn clean_rego_path(raw: &str) -> String {
    let trimmed = raw.trim();
    let stripped = trimmed.strip_prefix("input.").unwrap_or(trimmed);
    stripped.replace("[_]", ".[0]")
}

fn normalize_path_pattern(actual: &str, target: &str) -> bool {
    if actual == target {
        return true;
    }
    // Handle array wildcards e.g. spec.template.spec.containers.[0].name vs spec.containers.name
    let actual_no_idx = actual.replace(".[0]", "");
    let target_no_idx = target.replace(".[0]", "");
    actual_no_idx == target_no_idx || actual.ends_with(target)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;

    #[test]
    fn test_compile_and_eval_deny_rule() {
        let rego = r#"
            package kubernetes.admission
            deny[msg] {
                input.kind == "Deployment"
                not input.spec.template.spec.securityContext.runAsNonRoot
                msg := "Deployments must specify securityContext.runAsNonRoot: true"
            }
        "#;

        let rule = RegoCompiler::compile("OPA-001", rego).expect("Compilation must succeed");
        assert_eq!(rule.rule_id, "OPA-001");
        assert_eq!(rule.conditions.len(), 2);

        let manifest_violating =
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  replicas: 1\n";
        let shards = native_shard(manifest_violating);
        let violation = RegoCompiler::evaluate_shards(&rule, &shards);
        assert!(violation.is_some());
        let v = violation.unwrap();
        assert_eq!(v.rule_id, "OPA-001");
        assert!(v.message.contains("runAsNonRoot"));

        let manifest_compliant = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  template:\n    spec:\n      securityContext:\n        runAsNonRoot: true\n";
        let compliant_shards = native_shard(manifest_compliant);
        let compliant_violation = RegoCompiler::evaluate_shards(&rule, &compliant_shards);
        assert!(compliant_violation.is_none());
    }

    #[test]
    fn test_eval_rego_contains() {
        let rego = r#"
            deny[msg] {
                input.kind == "Pod"
                contains(input.spec.containers.image, ":latest")
                msg := "Images must not use floating :latest tag"
            }
        "#;

        let rule = RegoCompiler::compile("OPA-002", rego).expect("Compile succeed");
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n  - name: c1\n    image: redis:latest\n";
        let shards = native_shard(raw);
        let v = RegoCompiler::evaluate_shards(&rule, &shards);
        assert!(v.is_some());
        assert_eq!(v.unwrap().rule_id, "OPA-002");
    }
}
