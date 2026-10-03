//! Dynamic Resource Allocation (DRA) Healer (K8s 1.30+ / Rule DRA-001).
//!
//! Why: Kubernetes 1.30+ Dynamic Resource Allocation introduces `spec.resourceClaims`
//!      and container `resources.claims` for GPU/AI accelerators. Mismatches between
//!      container claim requests and pod claim declarations cause immediate admission rejections.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const DRA_RULE_ID: &str = "DRA-001";
pub const DRA_SIMILARITY_THRESHOLD: f64 = 0.65;

/// Heals and aligns Dynamic Resource Allocation (DRA) claim references in workload specs.
pub fn heal_dynamic_resource_allocation(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    // 1. Collect all declared pod-level resourceClaim names in this manifest
    let mut declared_claims = Vec::new();
    collect_declared_claims(&manifest.root, &mut declared_claims);

    if declared_claims.is_empty() {
        return changes;
    }

    // 2. Validate and align container resources.claims[].name against declared claims
    align_container_claims(
        &mut manifest.root,
        &declared_claims,
        telemetry,
        &mut changes,
    );

    changes
}

fn collect_declared_claims(node: &SemanticNode, claims: &mut Vec<String>) {
    if node.key == "resourceClaims" {
        for child in &node.children {
            if let Some(name_val) = child.find_value("name") {
                let clean = name_val
                    .trim()
                    .trim_matches('"')
                    .trim_matches('\'')
                    .to_string();
                if !clean.is_empty() && !claims.contains(&clean) {
                    claims.push(clean);
                }
            }
        }
    }

    for child in &node.children {
        collect_declared_claims(child, claims);
    }
}

fn align_container_claims(
    node: &mut SemanticNode,
    declared_claims: &[String],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "claims" {
        // Container claims array element
        for claim_node in &mut node.children {
            if let Some(name_node) = claim_node.find_node_mut("name") {
                let current_name = name_node.value.clone().unwrap_or_default();
                let clean = current_name.trim().trim_matches('"').trim_matches('\'');

                if !clean.is_empty() && !declared_claims.contains(&clean.to_string()) {
                    let mut best_match = None;
                    let mut best_ratio = 0.0;

                    for decl in declared_claims {
                        let ratio = crate::healers::selector_healer::similarity_ratio(clean, decl);
                        if ratio >= DRA_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_match = Some(decl.clone());
                        }
                    }

                    if let Some(target) = best_match {
                        name_node.value = Some(target.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Aligned container resource claim '{}' -> '{}' to match pod resourceClaims (similarity: {:.2}).",
                            DRA_RULE_ID, clean, target, best_ratio
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    for child in &mut node.children {
        align_container_claims(child, declared_claims, telemetry, changes);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_dra_claim_alignment() {
        let yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  resourceClaims:
  - name: shared-gpu-pool
    resourceClaimTemplateName: gpu-claim-template
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0
    resources:
      claims:
      - name: shared-gpu-pool-typo
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dynamic_resource_allocation(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("shared-gpu-pool"));

        // Verify aligned AST value
        let spec = manifest.root.find_node("spec").unwrap();
        let containers = spec.find_node("containers").unwrap();
        let container = &containers.children[0];
        let resources = container.find_node("resources").unwrap();
        let claims = resources.find_node("claims").unwrap();
        let claim_item = &claims.children[0];
        assert_eq!(claim_item.find_value("name").unwrap(), "shared-gpu-pool");
    }

    #[test]
    fn test_dra_no_declared_claims_noop() {
        let yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: standard-app
spec:
  containers:
  - name: web
    image: nginx:latest
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dynamic_resource_allocation(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }
}
