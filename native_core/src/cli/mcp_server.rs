//! Native stdio JSON-RPC Model Context Protocol (MCP) Server Daemon.
//!
//! Why: Provides native sub-5ms AI tool integration for Claude Desktop, Cursor,
//! and AGY without requiring Python runtimes. Strictly < 500 lines.

use crate::cli::heal_cmd::heal_manifest_string;
use crate::cli::EXIT_SUCCESS;
use crate::schemas::native_get_schema_for_version;
use crate::sharder::native_shard;
use crate::structurer::native_structurize;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

/// Runs the standalone Yamlr MCP server over stdio or outputs client config.
pub fn execute_mcp(args: &[String]) -> i32 {
    if args.iter().any(|a| a == "-h" || a == "--help") {
        println!("Yamlr MCP Server — Native Model Context Protocol Daemon for AI Agents");
        println!("\nUSAGE:");
        println!("    yamlr mcp [OPTIONS]");
        println!("\nOPTIONS:");
        println!("    --install-config    Print JSON configuration for Claude Desktop and Cursor");
        println!("    -h, --help          Print help information");
        return EXIT_SUCCESS;
    }

    if args
        .iter()
        .any(|a| a == "--install-config" || a == "--config")
    {
        let exe_path = std::env::current_exe()
            .ok()
            .and_then(|p| p.to_str().map(String::from))
            .unwrap_or_else(|| "yamlr".to_string());
        let config = json!({
            "mcpServers": {
                "yamlr": {
                    "command": exe_path,
                    "args": ["mcp"]
                }
            }
        });
        println!("Add the following to your Claude Desktop or Cursor configuration:\n");
        println!(
            "{}",
            serde_json::to_string_pretty(&config).unwrap_or_default()
        );
        return EXIT_SUCCESS;
    }

    let stdin = io::stdin();
    let mut reader = io::BufReader::new(stdin.lock());
    let mut stdout = io::stdout();

    let schemas = native_get_schema_for_version("1.30");

    let mut line = String::new();
    while let Ok(bytes) = reader.read_line(&mut line) {
        if bytes == 0 {
            break;
        }

        let trimmed = line.trim();
        if trimmed.is_empty() {
            line.clear();
            continue;
        }

        if let Ok(req) = serde_json::from_str::<Value>(trimmed) {
            let id = req.get("id").cloned();
            let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");

            match method {
                "initialize" => {
                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "yamlr-native-mcp",
                                "version": "0.1.0"
                            }
                        }
                    });
                    send_mcp_response(&mut stdout, &resp);
                }
                "notifications/initialized" => {
                    // Client acknowledgment, no response needed
                }
                "tools/list" => {
                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "tools": [
                                {
                                    "name": "yamlr_scan",
                                    "description": "High-performance Kubernetes manifest scanner with schema validation and forensic integrity checks.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "manifest": { "type": "string", "description": "Raw YAML manifest content" },
                                            "k8s_version": { "type": "string", "description": "Target Kubernetes version (default 1.30)" }
                                        },
                                        "required": ["manifest"]
                                    }
                                },
                                {
                                    "name": "yamlr_heal",
                                    "description": "Autonomous AST resolution engine that repairs Kubernetes manifests with comment preservation.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "manifest": { "type": "string", "description": "Raw YAML manifest content" }
                                        },
                                        "required": ["manifest"]
                                    }
                                }
                            ]
                        }
                    });
                    send_mcp_response(&mut stdout, &resp);
                }
                "tools/call" => {
                    let tool_name = req
                        .get("params")
                        .and_then(|p| p.get("name"))
                        .and_then(|n| n.as_str())
                        .unwrap_or("");
                    let args = req.get("params").and_then(|p| p.get("arguments"));
                    let manifest_content = args
                        .and_then(|a| a.get("manifest"))
                        .and_then(|m| m.as_str())
                        .unwrap_or("");

                    let result_text = match tool_name {
                        "yamlr_scan" => {
                            let shards = native_shard(manifest_content);
                            let manifest = native_structurize(shards);
                            let violations = crate::schemas::native_validate_ast_against_schema(
                                &manifest, &schemas,
                            );
                            let integrity = &manifest.integrity_violations;

                            json!({
                                "status": if violations.is_empty() && integrity.is_empty() { "valid" } else { "violations_found" },
                                "schema_violations_count": violations.len(),
                                "integrity_violations_count": integrity.len(),
                                "schema_violations": violations,
                                "integrity_violations": integrity
                            }).to_string()
                        }
                        "yamlr_heal" => {
                            let (healed, _) = heal_manifest_string(manifest_content);
                            json!({
                                "healed_manifest": healed,
                                "changed": healed != manifest_content
                            })
                            .to_string()
                        }
                        _ => format!("Unknown tool: {}", tool_name),
                    };

                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ]
                        }
                    });
                    send_mcp_response(&mut stdout, &resp);
                }
                _ => {
                    let err_resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "error": {
                            "code": -32601,
                            "message": format!("Method not found: {}", method)
                        }
                    });
                    send_mcp_response(&mut stdout, &err_resp);
                }
            }
        }
        line.clear();
    }

    EXIT_SUCCESS
}

fn send_mcp_response(stdout: &mut io::Stdout, val: &Value) {
    if let Ok(serialized) = serde_json::to_string(val) {
        let _ = writeln!(stdout, "{}", serialized);
        let _ = stdout.flush();
    }
}
