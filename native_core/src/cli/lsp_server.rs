//! Native stdio JSON-RPC Language Server Protocol (LSP) daemon.
//!
//! Provides sub-10ms keystroke diagnostics and quick-fixes directly in Rust.

use std::collections::HashMap;
use std::io::{self, BufRead, Read, Write};

use crate::cli::EXIT_SUCCESS;
use crate::schemas::native_get_schema_for_version;
use crate::sharder::native_shard;
use crate::structurer::native_structurize;

pub fn execute_lsp() -> i32 {
    let stdin = io::stdin();
    let mut reader = io::BufReader::new(stdin.lock());
    let mut stdout = io::stdout();

    let schemas = native_get_schema_for_version("1.30");
    let mut docs: HashMap<String, String> = HashMap::new();

    loop {
        let mut line = String::new();
        let Ok(bytes_read) = reader.read_line(&mut line) else {
            break;
        };
        if bytes_read == 0 {
            break;
        }

        if line.starts_with("Content-Length:") {
            let len_str = line.trim_start_matches("Content-Length:").trim();
            let content_len: usize = len_str.parse().unwrap_or(0);

            // Read the empty separator line
            let mut empty_line = String::new();
            let _ = reader.read_line(&mut empty_line);

            // Read payload
            let mut buf = vec![0u8; content_len];
            if reader.read_exact(&mut buf).is_err() {
                break;
            }

            let Ok(msg_str) = String::from_utf8(buf) else {
                continue;
            };

            let Ok(req) = serde_json::from_str::<serde_json::Value>(&msg_str) else {
                continue;
            };

            let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
            let req_id = req.get("id").cloned();

            match method {
                "initialize" => {
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "capabilities": {
                                "textDocumentSync": 1,
                                "documentFormattingProvider": true,
                                "hoverProvider": true,
                                "codeActionProvider": {
                                    "codeActionKinds": ["quickfix", "source.fixAll.yamlr"]
                                }
                            },
                            "serverInfo": {
                                "name": "yamlr-lsp",
                                "version": env!("CARGO_PKG_VERSION")
                            }
                        }
                    });
                    send_lsp_msg(&mut stdout, &resp);
                }
                "initialized" => {
                    // Client confirmation - no response needed
                }
                "textDocument/didOpen" => {
                    if let Some(doc) = req.pointer("/params/textDocument") {
                        let uri = doc
                            .get("uri")
                            .and_then(|u| u.as_str())
                            .unwrap_or("")
                            .to_string();
                        let text = doc
                            .get("text")
                            .and_then(|t| t.as_str())
                            .unwrap_or("")
                            .to_string();
                        docs.insert(uri.clone(), text.clone());
                        publish_diagnostics(&mut stdout, &uri, &text, &schemas);
                    }
                }
                "textDocument/didChange" => {
                    if let Some(params) = req.get("params") {
                        let uri = params
                            .pointer("/textDocument/uri")
                            .and_then(|u| u.as_str())
                            .unwrap_or("")
                            .to_string();
                        if let Some(changes) =
                            params.get("contentChanges").and_then(|c| c.as_array())
                        {
                            if let Some(last_change) = changes.last() {
                                if let Some(new_text) =
                                    last_change.get("text").and_then(|t| t.as_str())
                                {
                                    docs.insert(uri.clone(), new_text.to_string());
                                    publish_diagnostics(&mut stdout, &uri, new_text, &schemas);
                                }
                            }
                        }
                    }
                }
                "textDocument/didSave" => {
                    if let Some(params) = req.get("params") {
                        let uri = params
                            .pointer("/textDocument/uri")
                            .and_then(|u| u.as_str())
                            .unwrap_or("")
                            .to_string();
                        if let Some(text) = docs.get(&uri) {
                            publish_diagnostics(&mut stdout, &uri, text, &schemas);
                        }
                    }
                }
                "textDocument/formatting" => {
                    let mut edits = Vec::new();
                    let uri = req
                        .pointer("/params/textDocument/uri")
                        .and_then(|u| u.as_str())
                        .unwrap_or("");
                    if let Some(text) = docs.get(uri) {
                        let formatted = crate::cli::fmt_cmd::format_manifest_content(text);
                        if formatted != *text {
                            edits = compute_targeted_text_edits(text, &formatted);
                        }
                    }
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": edits
                    });
                    send_lsp_msg(&mut stdout, &resp);
                }
                "textDocument/hover" => {
                    let uri = req
                        .pointer("/params/textDocument/uri")
                        .and_then(|u| u.as_str())
                        .unwrap_or("");
                    let line = req
                        .pointer("/params/position/line")
                        .and_then(|l| l.as_u64())
                        .unwrap_or(0) as usize;
                    let hover_result = handle_hover(uri, line, &docs);
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": hover_result
                    });
                    send_lsp_msg(&mut stdout, &resp);
                }
                "textDocument/codeAction" => {
                    let actions = handle_code_actions(&req, &docs);
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": actions
                    });
                    send_lsp_msg(&mut stdout, &resp);
                }
                "shutdown" => {
                    let resp = serde_json::json!({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": serde_json::Value::Null
                    });
                    send_lsp_msg(&mut stdout, &resp);
                }
                "exit" => {
                    break;
                }
                _ => {
                    if req_id.is_some() {
                        let resp = serde_json::json!({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": serde_json::Value::Null
                        });
                        send_lsp_msg(&mut stdout, &resp);
                    }
                }
            }
        }
    }

    EXIT_SUCCESS
}

fn find_field_line(field_path: &str, shards: &[crate::models::NativeShard]) -> usize {
    let target_key = field_path.rsplit('.').next().unwrap_or(field_path);
    for shard in shards {
        if shard.key.eq_ignore_ascii_case(target_key) && shard.line_no > 0 {
            return shard.line_no;
        }
    }
    1
}

fn find_violation_line(
    rule_id: &str,
    message: &str,
    shards: &[crate::models::NativeShard],
) -> usize {
    match rule_id {
        "PRO-001" => {
            for shard in shards {
                if shard.key == "apiVersion" && shard.line_no > 0 {
                    return shard.line_no;
                }
            }
        }
        "OPS-002" => {
            for shard in shards {
                if shard.key == "image" && shard.line_no > 0 {
                    if let Some(ref val) = shard.value {
                        if val.contains(":latest") || !val.contains(':') {
                            return shard.line_no;
                        }
                    }
                }
            }
        }
        "OPS-001" => {
            for shard in shards {
                if (shard.key == "spec" || shard.key == "template") && shard.line_no > 0 {
                    return shard.line_no;
                }
            }
        }
        _ => {
            // General heuristic: check if any shard key matches message keywords
            for shard in shards {
                if shard.line_no > 0 && !shard.key.is_empty() && message.contains(&shard.key) {
                    return shard.line_no;
                }
            }
        }
    }
    1
}

fn publish_diagnostics(
    stdout: &mut io::Stdout,
    uri: &str,
    text: &str,
    schemas: &[crate::models::NativeSchema],
) {
    let shards = native_shard(text);
    let mut diagnostics = Vec::new();

    if !shards.is_empty() {
        let manifest = native_structurize(shards.clone());
        let violations = crate::schemas::native_validate_ast_against_schema(&manifest, schemas);
        let lines: Vec<&str> = text.lines().collect();

        for v in violations {
            let line_no = if v.line_no > 0 {
                v.line_no
            } else {
                find_field_line(&v.field_path, &shards)
            };
            let zero_line = line_no.saturating_sub(1);
            let line_len = lines.get(zero_line).map(|l| l.len()).unwrap_or(10).max(1);
            // Why: Emit a semantic diagnostic code derived from the field path
            // (e.g. "SCH:spec.containers[].resources") so VS Code can group,
            // suppress, and hyperlink per-rule rather than a single "SCH-001" stub.
            let diag_code = if v.field_path.is_empty() {
                "SCH-001".to_string()
            } else {
                format!("SCH:{}", v.field_path)
            };

            diagnostics.push(serde_json::json!({
                "range": {
                    "start": { "line": zero_line, "character": 0 },
                    "end": { "line": zero_line, "character": line_len }
                },
                "severity": 1,
                "code": diag_code,
                "source": "yamlr",
                "message": format!("{}: {}", v.field_path, v.message)
            }));
        }

        for iv in &manifest.integrity_violations {
            let line_no = if iv.line_no > 0 {
                iv.line_no
            } else {
                find_violation_line(&iv.rule_id, &iv.message, &shards)
            };
            let zero_line = line_no.saturating_sub(1);
            let line_len = lines.get(zero_line).map(|l| l.len()).unwrap_or(10).max(1);

            diagnostics.push(serde_json::json!({
                "range": {
                    "start": { "line": zero_line, "character": 0 },
                    "end": { "line": zero_line, "character": line_len }
                },
                "severity": if iv.severity == "CRITICAL" { 1 } else { 2 },
                "code": iv.rule_id,
                "source": "yamlr",
                "message": iv.message
            }));
        }
    }

    let notif = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "textDocument/publishDiagnostics",
        "params": {
            "uri": uri,
            "diagnostics": diagnostics
        }
    });

    send_lsp_msg(stdout, &notif);
}

/// Computes minimal, targeted text edits between original and healed text.
/// Why: Preserves cursor positions, active selections, and granular undo/redo history in VS Code.
pub fn compute_targeted_text_edits(orig: &str, healed: &str) -> Vec<serde_json::Value> {
    if orig == healed {
        return Vec::new();
    }

    let orig_lines: Vec<&str> = orig.lines().collect();
    let healed_lines: Vec<&str> = healed.lines().collect();

    // Find common prefix lines
    let mut prefix = 0;
    while prefix < orig_lines.len()
        && prefix < healed_lines.len()
        && orig_lines[prefix] == healed_lines[prefix]
    {
        prefix += 1;
    }

    // Find common suffix lines
    let mut suffix = 0;
    while suffix < (orig_lines.len() - prefix)
        && suffix < (healed_lines.len() - prefix)
        && orig_lines[orig_lines.len() - 1 - suffix]
            == healed_lines[healed_lines.len() - 1 - suffix]
    {
        suffix += 1;
    }

    let orig_start = prefix;
    let orig_end = orig_lines.len() - suffix;
    let healed_start = prefix;
    let healed_end = healed_lines.len() - suffix;

    let new_text_slice: Vec<&str> = healed_lines[healed_start..healed_end].to_vec();
    let mut replacement = new_text_slice.join("\n");
    if !replacement.is_empty() && (orig_end < orig_lines.len() || healed.ends_with('\n')) {
        replacement.push('\n');
    }

    let end_char = if orig_end > orig_start && orig_end <= orig_lines.len() {
        orig_lines[orig_end - 1].len()
    } else {
        0
    };

    vec![serde_json::json!({
        "range": {
            "start": { "line": orig_start, "character": 0 },
            "end": { "line": orig_end, "character": end_char }
        },
        "newText": replacement
    })]
}

fn handle_code_actions(
    req: &serde_json::Value,
    docs: &HashMap<String, String>,
) -> Vec<serde_json::Value> {
    let mut actions = Vec::new();
    let uri = req
        .pointer("/params/textDocument/uri")
        .and_then(|u| u.as_str())
        .unwrap_or("");
    let text = match docs.get(uri) {
        Some(t) => t,
        None => return actions,
    };

    // AST-Engine Safe Quick-Fix Pass (Comment-Preserving, Zero Blind-Spots)
    let (healed, changes) = crate::cli::heal_cmd::heal_manifest_string(text);
    if !changes.is_empty() && healed != *text {
        let edits = compute_targeted_text_edits(text, &healed);
        let edit = serde_json::json!({
            "changes": {
                uri: edits
            }
        });

        // Specific contextual quick-fix titles derived safely from engine changes
        for change in &changes {
            actions.push(serde_json::json!({
                "title": format!("Yamlr: {}", change),
                "kind": "quickfix",
                "edit": edit.clone()
            }));
        }

        actions.push(serde_json::json!({
            "title": format!("Yamlr: Auto-repair manifest ({} fixes)", changes.len()),
            "kind": "quickfix",
            "isPreferred": true,
            "edit": edit.clone()
        }));
        actions.push(serde_json::json!({
            "title": "Yamlr: Fix all issues in manifest",
            "kind": "source.fixAll.yamlr",
            "isPreferred": true,
            "edit": edit
        }));
    }

    actions
}

fn handle_hover(uri: &str, line_0: usize, docs: &HashMap<String, String>) -> serde_json::Value {
    let text = match docs.get(uri) {
        Some(t) => t,
        None => return serde_json::Value::Null,
    };
    let shards = native_shard(text);
    let target_shard = shards.iter().find(|s| s.line_no == line_0 + 1);

    if let Some(shard) = target_shard {
        if !shard.key.is_empty() {
            let kind = crate::identity::extract_native_identity_ref(&shards)
                .map(|id| id.kind)
                .unwrap_or_else(|| "Resource".to_string());

            let description = match shard.key.as_str() {
                "apiVersion" => "Defines the versioned schema of this representation of an object. Deprecated versions (e.g. extensions/v1beta1) are automatically healed by Yamlr.",
                "kind" => "Kind is a string value representing the REST resource this object represents.",
                "metadata" => "Standard object metadata including name, namespace, labels, and annotations.",
                "name" => "Name must be unique within a namespace. Is required when creating resources.",
                "namespace" => "Namespace defines the space within which each name must be unique. An empty namespace defaults to 'default'.",
                "labels" => "Map of string keys and values that can be used to organize and categorize objects.",
                "spec" => "Specification of the desired behavior of the resource.",
                "containers" => "List of containers belonging to the pod. Managed by the workload controller.",
                "image" => "Container image name. Floating tags (e.g. :latest) trigger security warnings and auto-pinning in Yamlr.",
                "ports" => "List of ports to expose from the container.",
                "replicas" => "Number of desired pods. Yamlr verifies minimum availability policies.",
                "selector" => "Label selector for pods. Mismatched selector keys are auto-repaired by Yamlr.",
                "template" => "Template describes the pods that will be created.",
                _ => "Kubernetes API Resource Field",
            };

            let markdown = format!(
                "**{}** (`{}`)\n\n{}\n\n*Validated by Yamlr Native Engine*",
                shard.key, kind, description
            );
            return serde_json::json!({
                "contents": {
                    "kind": "markdown",
                    "value": markdown
                }
            });
        }
    }
    serde_json::Value::Null
}

fn send_lsp_msg(stdout: &mut io::Stdout, msg: &serde_json::Value) {
    if let Ok(body) = serde_json::to_string(msg) {
        let header = format!("Content-Length: {}\r\n\r\n", body.len());
        let _ = stdout.write_all(header.as_bytes());
        let _ = stdout.write_all(body.as_bytes());
        let _ = stdout.flush();
    }
}

#[cfg(test)]
#[path = "lsp_server_tests.rs"]
mod tests;
