//! Sovereign Semantic DNA Fingerprinting Engine (Feature 15 of 15).
//!
//! Why: In GitOps and regulated CI/CD pipelines, compliance auditors require mathematical
//! proof that manifest auto-healing has not altered operational intent or injected rogue
//! changes (Semantic Invariance Guarantee).
//!
//! This module computes an order-invariant, comment-invariant SHA-256 canonical hash
//! of the AST ("Semantic DNA") and stamps it into `metadata.annotations["yamlr.dev/dna-seal"]`.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;
use sha2::{Digest, Sha256};

/// Serializes a node into a deterministic canonical string for hashing.
/// Ignores the `yamlr.dev/dna-seal` annotation itself to prevent self-referential hash loops.
fn canonical_serialize_node(node: &SemanticNode, buf: &mut String) {
    if node.key == "yamlr.dev/dna-seal" {
        return;
    }

    buf.push_str(&node.key);
    buf.push(':');
    if let Some(ref val) = node.value {
        buf.push_str(val.trim());
    }
    buf.push('\n');

    // Clone and sort children deterministically by key
    let mut sorted_children = node.children.clone();
    sorted_children.sort_by(|a, b| a.key.cmp(&b.key));

    for child in &sorted_children {
        canonical_serialize_node(child, buf);
    }
}

/// Computes the 64-character lowercase SHA-256 Semantic DNA hash of an AST node tree.
pub fn compute_semantic_dna(root: &SemanticNode) -> String {
    let mut canonical_buf = String::new();
    canonical_serialize_node(root, &mut canonical_buf);

    let mut hasher = Sha256::new();
    hasher.update(canonical_buf.as_bytes());
    hex::encode(hasher.finalize())
}

/// Applies the cryptographic Semantic DNA hash seal to `metadata.annotations["yamlr.dev/dna-seal"]`.
pub fn apply_sovereign_dna_seal(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> String {
    let dna_hash = compute_semantic_dna(&manifest.root);
    let seal_value = format!("sha256:{}", dna_hash);

    if let Some(metadata) = manifest.root.find_node_mut("metadata") {
        let ann_indent = metadata.indent + 2;
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            let seal_indent = annotations.indent + 2;
            if let Some(seal_node) = annotations.find_node_mut("yamlr.dev/dna-seal") {
                seal_node.value = Some(seal_value.clone());
                for s in &mut seal_node.shards {
                    s.value = Some(seal_value.clone());
                }
            } else {
                annotations.children.push(SemanticNode {
                    key: "yamlr.dev/dna-seal".to_string(),
                    value: Some(seal_value.clone()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: seal_indent,
                    is_empty_flow: false,
                });
            }
        } else {
            metadata.children.push(SemanticNode {
                key: "annotations".to_string(),
                value: None,
                children: vec![SemanticNode {
                    key: "yamlr.dev/dna-seal".to_string(),
                    value: Some(seal_value.clone()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: ann_indent + 2,
                    is_empty_flow: false,
                }],
                shards: Vec::new(),
                indent: ann_indent,
                is_empty_flow: false,
            });
        }
    }

    let msg = format!(
        "Remediation [DNA-001]: Sealed manifest with cryptographic Semantic DNA '{}'.",
        seal_value
    );
    native_record_healing_impact(telemetry, &msg);

    seal_value
}

/// Verifies whether a manifest matches an expected Semantic DNA hash.
pub fn verify_semantic_dna(manifest: &SemanticManifest, expected_hash: &str) -> bool {
    let current_dna = compute_semantic_dna(&manifest.root);
    let target = expected_hash
        .strip_prefix("sha256:")
        .unwrap_or(expected_hash)
        .trim();
    current_dna.eq_ignore_ascii_case(target)
}

/// Applies the DNA Safety Seal directly onto a semantic AST node.
pub fn native_apply_dna_seal(node: &mut SemanticNode) -> Option<String> {
    let dna_hash = compute_semantic_dna(node);
    let seal_value = format!("sha256:{}", dna_hash);

    if let Some(metadata) = node.find_node_mut("metadata") {
        let indent = metadata.indent + 2;
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            let ann_indent = annotations.indent + 2;
            if let Some(seal) = annotations.find_node_mut("yamlr.dev/dna-seal") {
                if seal.value.as_deref() == Some(&seal_value) {
                    return None;
                }
                seal.value = Some(seal_value);
            } else {
                annotations.children.push(SemanticNode {
                    key: "yamlr.dev/dna-seal".into(),
                    value: Some(seal_value),
                    children: vec![],
                    shards: vec![],
                    indent: ann_indent,
                    is_empty_flow: false,
                });
            }
        } else {
            metadata.children.push(SemanticNode {
                key: "annotations".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "yamlr.dev/dna-seal".into(),
                    value: Some(seal_value),
                    children: vec![],
                    shards: vec![],
                    indent: indent + 2,
                    is_empty_flow: false,
                }],
                shards: vec![],
                indent,
                is_empty_flow: false,
            });
        }
        Some("Injected 'DNA Safety Seal' into manifest.".to_string())
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_semantic_dna_order_invariance() {
        // Node 1: key A then key B
        let node1 = SemanticNode {
            key: "root".to_string(),
            value: None,
            indent: 0,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "replicas".to_string(),
                    value: Some("3".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "app".to_string(),
                    value: Some("web".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };

        // Node 2: key B then key A (order inverted)
        let node2 = SemanticNode {
            key: "root".to_string(),
            value: None,
            indent: 0,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "app".to_string(),
                    value: Some("web".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "replicas".to_string(),
                    value: Some("3".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };

        let hash1 = compute_semantic_dna(&node1);
        let hash2 = compute_semantic_dna(&node2);
        assert_eq!(hash1, hash2, "Semantic DNA must be invariant to key order");
        assert_eq!(hash1.len(), 64);
    }
}
