use super::*;
use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};

#[test]
fn test_native_sort_keys() {
    let mut node = SemanticNode {
        key: "root".into(),
        value: None,
        children: vec![
            SemanticNode {
                key: "spec".into(),
                value: None,
                children: vec![],
                shards: vec![],
                indent: 2,
                is_empty_flow: false,
            },
            SemanticNode {
                key: "apiVersion".into(),
                value: Some("v1".into()),
                children: vec![],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            SemanticNode {
                key: "kind".into(),
                value: Some("Pod".into()),
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
    native_sort_keys(&mut node, 0);
    assert_eq!(node.children[0].key, "apiVersion");
    assert_eq!(node.children[1].key, "kind");
    assert_eq!(node.children[2].key, "spec");
}

#[test]
fn test_native_apply_dna_seal() {
    let mut node = SemanticNode {
        key: "root".into(),
        value: None,
        children: vec![SemanticNode {
            key: "metadata".into(),
            value: None,
            children: vec![],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        }],
        shards: vec![],
        indent: 0,
        is_empty_flow: false,
    };
    native_apply_dna_seal(&mut node);
    let metadata = node.find_node("metadata").unwrap();
    let annotations = metadata.find_node("annotations").unwrap();
    let seal = annotations.find_node("yamlr.dev/dna-seal").unwrap();
    assert!(seal.value.as_ref().unwrap().starts_with("sha256:"));
}

// Non-destructive AST transformation tests

#[test]
fn test_replicas_removal_hpa() {
    let mut manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "metadata".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "annotations".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "yamlr.dev/hpa-scaling".into(),
                            value: Some("true".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 4,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    }],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "spec".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "replicas".into(),
                        value: Some("3".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    }],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![crate::models::IntegrityViolation {
            rule_id: "REL-003".into(),
            check_name: "HPA Conflict".into(),
            message: "Scaling War".into(),
            severity: "HIGH".into(),
            line_no: 0,
        }],
    };
    let mut telemetry = NativeTelemetry::new();
    let changes = native_heal_manifest(&mut manifest, &mut telemetry);

    let spec = manifest.root.find_node("spec").unwrap();
    assert!(spec.find_node("replicas").is_none());
    assert!(changes.iter().any(|c| c.contains("REL-003")));
}

#[test]
fn test_latest_to_pinned_conversion() {
    let mut manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "metadata".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "annotations".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "yamlr.dev/pin-tags".into(),
                            value: Some("true".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 4,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    }],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "image".into(),
                    value: Some("nginx:latest".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![crate::models::IntegrityViolation {
            rule_id: "OPS-002".into(),
            check_name: "Floating Tag".into(),
            message: "Use pinned tag".into(),
            severity: "MEDIUM".into(),
            line_no: 0,
        }],
    };
    let mut telemetry = NativeTelemetry::new();
    let changes = native_heal_manifest(&mut manifest, &mut telemetry);

    let img = manifest.root.find_node("image").unwrap();
    assert_eq!(img.value, Some("nginx:stable-pinned".to_string()));
    assert!(changes.iter().any(|c| c.contains("OPS-002")));
}

#[test]
fn test_api_deprecation_upgrade() {
    let mut manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "apiVersion".into(),
                    value: Some("extensions/v1beta1".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "kind".into(),
                    value: Some("Deployment".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![crate::models::IntegrityViolation {
            rule_id: "PRO-001".into(),
            check_name: "API Deprecated".into(),
            message: "Upgrade API".into(),
            severity: "HIGH".into(),
            line_no: 0,
        }],
    };
    let mut telemetry = NativeTelemetry::new();
    let changes = native_heal_manifest(&mut manifest, &mut telemetry);

    let api = manifest.root.find_node("apiVersion").unwrap();
    assert_eq!(api.value, Some("apps/v1".to_string()));
    assert!(changes.iter().any(|c| c.contains("PRO-001")));
}

#[test]
fn test_reconstruct_roundtrip_idempotency() {
    let manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![SemanticNode {
                key: "apiVersion".into(),
                value: Some("v1".into()),
                children: vec![],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            }],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![],
    };
    let yaml = native_reconstruct_from_semantic(&manifest);
    assert!(yaml.contains("apiVersion: v1"));
}
