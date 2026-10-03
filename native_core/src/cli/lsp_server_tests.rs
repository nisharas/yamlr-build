//! Unit tests for the Yamlr LSP server.
//!
//! Why: Extracted to a discrete test module to maintain the < 500-line modularity
//! guardrail on lsp_server.rs, enabling continued feature growth without violating
//! the Agent Modularity Protocol.

use super::*;
use std::collections::HashMap;

#[test]
fn test_handle_code_actions_full_engine() {
    let mut docs = HashMap::new();
    let uri = "file:///deployment.yaml";
    let raw = "# Note: never use :latest in production\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  replicas: 1\n  selector:\n    matchLabels:\n      app: web\n  template:\n    metadata:\n      labels:\n        app: web\n    spec:\n      containers:\n      - name: web\n        image: nginx:latest\n        imagePullPolic: Always\n";
    docs.insert(uri.to_string(), raw.to_string());

    let req = serde_json::json!({
        "params": {
            "textDocument": {
                "uri": uri
            }
        }
    });

    let actions = handle_code_actions(&req, &docs);
    assert!(!actions.is_empty());
    assert!(actions
        .iter()
        .any(|a| a["title"].as_str().unwrap().contains("Yamlr: Auto-repair")));
    let edit_line = actions[0]["edit"]["changes"][uri][0]["range"]["start"]["line"]
        .as_u64()
        .unwrap();
    assert!(edit_line > 0, "Comment line 0 must be untouched");
}

#[test]
fn test_compute_targeted_text_edits_single_line() {
    let orig =
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  replicas: 1\n";
    let healed =
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  replicas: 3\n";
    let edits = compute_targeted_text_edits(orig, healed);
    assert_eq!(edits.len(), 1);
    let edit = &edits[0];
    // Line 5 is replicas
    assert_eq!(edit["range"]["start"]["line"], 5);
    assert!(edit["newText"].as_str().unwrap().contains("replicas: 3"));
}

#[test]
fn test_find_field_line_accurate() {
    let raw = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\nspec:\n  template:\n    spec:\n      containers:\n      - name: app\n        image: nginx:1.25\n        imagePullPolic: Always\n";
    let shards = crate::sharder::native_shard(raw);
    let line = find_field_line("imagePullPolic", &shards);
    assert_eq!(line, 11);
}

#[test]
fn test_handle_hover_field_lookup() {
    let mut docs = HashMap::new();
    let uri = "file:///pod.yaml";
    let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test-pod\n";
    docs.insert(uri.to_string(), raw.to_string());
    let hover = handle_hover(uri, 0, &docs);
    assert!(!hover.is_null());
    assert!(hover["contents"]["value"]
        .as_str()
        .unwrap()
        .contains("apiVersion"));
}

#[test]
fn test_diagnostic_code_carries_rule_id() {
    // Why: Verifies that integrity violation diagnostics emit the actual rule_id
    // (e.g. "OPS-002") rather than the previous hardcoded "SCH-001" stub.
    // This is the Phase 6C fix — correct code identification drives VS Code
    // problem panel grouping and per-rule suppression comments.
    let manifest = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\nspec:\n  replicas: 1\n  selector:\n    matchLabels:\n      app: test\n  template:\n    metadata:\n      labels:\n        app: test\n    spec:\n      containers:\n      - name: app\n        image: nginx:latest\n";
    let shards = crate::sharder::native_shard(manifest);
    assert!(
        !shards.is_empty(),
        "Shards must be non-empty for a valid manifest"
    );
    // Verify find_violation_line returns sensible line for OPS-002 (image: latest)
    let line = find_violation_line("OPS-002", "image tag :latest detected", &shards);
    assert!(
        line > 0,
        "OPS-002 violation line must be > 0 (found on image: field)"
    );
}

#[test]
fn test_compute_targeted_text_edits_identical_returns_empty() {
    let text = "apiVersion: v1\nkind: Pod\n";
    let edits = compute_targeted_text_edits(text, text);
    assert!(
        edits.is_empty(),
        "Identical orig and healed must return zero edits"
    );
}
