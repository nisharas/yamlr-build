use super::*;

#[test]
fn test_native_strip_bom() {
    assert_eq!(native_strip_bom("\u{feff}hello"), "hello");
    assert_eq!(native_strip_bom("hello"), "hello");
}

#[test]
fn test_native_shard_basic() {
    let content = "apiVersion: v1\nkind: Pod";
    let shards = native_shard(content);
    assert_eq!(shards.len(), 2);
    assert_eq!(shards[0].key, "apiVersion");
    assert_eq!(shards[0].value, Some("v1".to_string()));
    assert_eq!(shards[1].key, "kind");
    assert_eq!(shards[1].value, Some("Pod".to_string()));
}

#[test]
fn test_native_reconstruct_yaml() {
    let content = "apiVersion: v1\nkind: Pod";
    let shards = native_shard(content);
    let reconstructed = native_reconstruct_yaml(&shards);
    assert!(reconstructed.contains("apiVersion: v1"));
    assert!(reconstructed.contains("kind: Pod"));
}

#[test]
fn test_native_find_shard_by_path() {
    let content = "spec:\n  containers:\n    - name: web";
    let shards = native_shard(content);
    let idx = native_find_shard_by_path(&shards, "spec.containers.[0].name");
    assert!(idx.is_some());
}

#[test]
fn test_shard_binary_rejection() {
    let content = "hello\0world";
    let shards = native_shard(content);
    assert!(shards.is_empty());
}

#[test]
fn test_shard_size_limit() {
    let large_content = "a".repeat(11 * 1024 * 1024);
    let shards = native_shard(&large_content);
    assert_eq!(shards.len(), 1);
    assert_eq!(shards[0].key, "Error");
}

// Non-destructive tokenizer tests

#[test]
fn test_comment_preservation() {
    let content = "apiVersion: v1 # Inline comment\n# Pure comment\nkind: Pod";
    let shards = native_shard(content);
    let reconstructed = native_reconstruct_yaml(&shards);
    assert!(reconstructed.contains("# Inline comment"));
    assert!(reconstructed.contains("# Pure comment"));
}

#[test]
fn test_multidoc_splitting() {
    let content = "apiVersion: v1\n---\nkind: Pod";
    let shards = native_shard(content);
    let docs: Vec<_> = shards.iter().filter(|s| s.is_doc_boundary).collect();
    assert_eq!(docs.len(), 1);
}

#[test]
fn test_block_scalar_parsing() {
    let content = "data:\n  config: |\n    line1\n    line2";
    let shards = native_shard(content);
    assert!(shards.iter().any(|s| s.is_block));
}

#[test]
fn test_yaml_anchors_and_aliases_survive_reconstruction() {
    let content = "defaults: &defaults\n  mode: safe\ncopy: *defaults\n";

    let shards = native_shard(content);
    let reconstructed = native_reconstruct_yaml(&shards);

    assert!(reconstructed.contains("defaults: &defaults"));
    assert!(reconstructed.contains("copy: *defaults"));
    let original_value: serde_yaml::Value = serde_yaml::from_str(content).unwrap();
    let reconstructed_value: serde_yaml::Value = serde_yaml::from_str(&reconstructed).unwrap();
    assert_eq!(reconstructed_value, original_value);
}

#[test]
fn test_flow_style_quarantine() {
    let content = "{ selector: web }";
    let shards = native_shard(content);
    assert!(shards.iter().any(|s| s.is_flow_style));
}

#[test]
fn test_crlf_handling() {
    let content = "apiVersion: v1\r\nkind: Pod\r\n";
    let shards = native_shard(content);
    let reconstructed = native_reconstruct_yaml(&shards);
    assert!(reconstructed.contains("apiVersion: v1"));
}

#[test]
fn test_quote_balancing() {
    let content = "value: \"quoted: value\"";
    let shards = native_shard(content);
    assert_eq!(shards[0].value, Some("\"quoted: value\"".to_string()));
}

#[test]
fn test_list_typo_recovery() {
    let content = "containers:\n-name: pod";
    let shards = native_shard(content);
    assert!(!shards.is_empty());
}

#[test]
fn test_odd_indent_preservation() {
    let content =
        "spec:\n   replicas: 3\n   template:\n    metadata:\n     labels:\n      app: test";
    let shards = native_shard(content);
    let reconstructed = native_reconstruct_yaml(&shards);
    assert!(reconstructed.contains("   replicas: 3"));
    assert!(reconstructed.contains("     labels:"));
}

#[test]
fn test_chomping_indicators() {
    let content = "data:\n  script: |-\n    echo hello\n  notes: |+\n    line1\n";
    let shards = native_shard(content);
    assert!(shards.iter().any(|s| s.is_block));
}

#[test]
fn test_layout_grafter_integration() {
    let content = "# Root level comment\napiVersion: v1\nkind: Pod";
    let mut shards: Vec<NativeShard> = native_shard(content)
        .into_iter()
        .filter(|s| !s.key.is_empty())
        .collect();
    native_apply_layout_grafter(content, &mut shards);
    assert!(!shards[0].layout_sequence.is_empty());
    assert!(shards[0].layout_sequence[0].contains("# Root level comment"));
}

#[test]
fn test_native_apply_heuristics_integration() {
    let content = "kindService\nenabled:yes";
    let healed = native_apply_heuristics(content);
    assert!(healed.contains("kind: Service"));
    assert!(healed.contains("enabled: \"yes\""));
}

#[test]
fn test_heuristics_wired_in_native_shard() {
    // Tests that fused keyword is recovered directly during sharding
    let content = "kindService\napiVersion: v1";
    let shards = native_shard(content);
    assert!(shards
        .iter()
        .any(|s| s.key == "kind" && s.value.as_deref() == Some("Service")));
}

#[test]
fn test_native_shard_doc_chunks() {
    let multi_doc = "apiVersion: v1\nkind: Namespace\nmetadata:\n  name: prod\n---\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n";
    let docs = native_shard_doc_chunks(multi_doc);
    assert_eq!(docs.len(), 2);
    assert!(docs[0]
        .iter()
        .any(|s| s.key == "kind" && s.value.as_deref() == Some("Namespace")));
    assert!(docs[1]
        .iter()
        .any(|s| s.key == "kind" && s.value.as_deref() == Some("Deployment")));
}
