//! Golden Standard Kubernetes Key Sorter.
//!
//! Why: Enforces the industry standard canonical ordering of Kubernetes top-level
//! and nested manifest keys: apiVersion, kind, metadata, spec, data, status.

use crate::models::SemanticNode;

pub fn native_sort_keys(node: &mut SemanticNode, depth: usize) -> bool {
    if depth > 255 {
        return false;
    } // SAFETY: Stack Overflow Protection
    let golden_order = ["apiVersion", "kind", "metadata", "spec", "data", "status"];
    let mut changed = false;
    let orig: Vec<String> = node.children.iter().map(|c| c.key.clone()).collect();

    node.children.sort_by(|a, b| {
        let pos_a = golden_order.iter().position(|&x| x == a.key).unwrap_or(999);
        let pos_b = golden_order.iter().position(|&x| x == b.key).unwrap_or(999);
        if pos_a != pos_b {
            pos_a.cmp(&pos_b)
        } else {
            a.key.cmp(&b.key)
        }
    });

    if node.children.iter().map(|c| &c.key).ne(orig.iter()) {
        changed = true;
    }

    for child in &mut node.children {
        if native_sort_keys(child, depth + 1) {
            changed = true;
        }
    }
    changed
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_golden_key_sorting() {
        let mut node = SemanticNode {
            key: "root".to_string(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "apiVersion".to_string(),
                    value: Some("v1".to_string()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "kind".to_string(),
                    value: Some("Pod".to_string()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        };

        assert!(native_sort_keys(&mut node, 0));
        assert_eq!(node.children[0].key, "apiVersion");
        assert_eq!(node.children[1].key, "kind");
        assert_eq!(node.children[2].key, "spec");
    }
}
