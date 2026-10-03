//! NetworkPolicy Baseline Generator (Feature 13 of 15).
//!
//! Why: By default, Kubernetes pods have unrestricted flat network communication.
//! Unprotected namespaces allow lateral movement in the event of a container compromise.
//! Zero-trust security frameworks (CIS Kubernetes Benchmark, PCI-DSS, SOC 2) require a
//! default-deny isolation policy as the foundation of cluster networking.

use crate::models::{NativeIdentity, NativeTelemetry};
use crate::telemetry::native_record_healing_impact;
use std::collections::HashSet;

/// Generates a default-deny NetworkPolicy YAML string for a given namespace.
pub fn generate_default_deny_network_policy(namespace: &str) -> String {
    format!(
        "apiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: default-deny-all\n  namespace: {}\n  annotations:\n    yamlr.io/baseline-shield: \"true\"\nspec:\n  podSelector: {{}}\n  policyTypes:\n    - Ingress\n    - Egress\n",
        namespace
    )
}

/// Primary Entrypoint: Detects namespaces without NetworkPolicy and generates zero-trust baseline policies.
pub fn heal_missing_network_policies(
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> (Vec<String>, Vec<String>) {
    let mut generated_policies = Vec::new();
    let mut changes = Vec::new();

    let mut active_namespaces = HashSet::new();
    let mut protected_namespaces = HashSet::new();

    for id in identities {
        if id.kind == "NetworkPolicy" {
            let ns = if id.namespace.is_empty() {
                "default"
            } else {
                &id.namespace
            };
            protected_namespaces.insert(ns.to_string());
        } else if id.kind == "Namespace" {
            active_namespaces.insert(id.name.clone());
        } else if !id.namespace.is_empty() && id.namespace != "__cluster_scoped__" {
            active_namespaces.insert(id.namespace.clone());
        }
    }

    if active_namespaces.is_empty() {
        active_namespaces.insert("default".to_string());
    }

    let mut sorted_ns: Vec<String> = active_namespaces.into_iter().collect();
    sorted_ns.sort();

    for ns in sorted_ns {
        if !protected_namespaces.contains(&ns) {
            let policy_yaml = generate_default_deny_network_policy(&ns);
            generated_policies.push(policy_yaml);

            let msg = format!(
                "Remediation [SEC-005]: Generated default-deny zero-trust NetworkPolicy baseline for namespace '{}'.",
                ns
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    (generated_policies, changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_default_deny_policy() {
        let policy = generate_default_deny_network_policy("production");
        assert!(policy.contains("kind: NetworkPolicy"));
        assert!(policy.contains("name: default-deny-all"));
        assert!(policy.contains("namespace: production"));
        assert!(policy.contains("podSelector: {}"));
        assert!(policy.contains("- Ingress"));
        assert!(policy.contains("- Egress"));
    }
}
