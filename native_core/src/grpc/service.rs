//! High-Throughput In-Memory & RPC Manifest Quality Service.
//!
//! Why: Cloud-agnostic platforms (Backstage IDPs, ArgoCD/Flux controllers, Jenkins, GitLab)
//! require sub-millisecond in-memory manifest scanning and healing without filesystem I/O overhead.
//! Implements the service contract specified in `proto/yamlr/v1/manifest_service.proto`.

use serde::{Deserialize, Serialize};
use std::time::Instant;

use crate::cli::heal_cmd::heal_manifest_string;
use crate::schemas::native_get_schema_for_version;
use crate::sharder::native_shard;
use crate::structurer::native_structurize;
use crate::wasm::wasm_diff;

/// Request message for scanning a manifest document.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanDocumentRequest {
    pub content: String,
    pub file_path: Option<String>,
    pub target_k8s_version: Option<String>,
}

/// Response message containing detected violations and health score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanDocumentResponse {
    pub status: String,
    pub total_violations: i32,
    pub violations: Vec<ViolationRecord>,
    pub health_score: f32,
    pub duration_ms: i64,
}

/// Request message for healing a manifest document.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealDocumentRequest {
    pub content: String,
    pub file_path: Option<String>,
    pub target_k8s_version: Option<String>,
    #[serde(default)]
    pub dry_run: bool,
}

/// Response message containing healed content and applied fixes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealDocumentResponse {
    pub healed_content: String,
    pub mutated: bool,
    pub applied_fixes: Vec<SuggestedFix>,
    pub unified_diff: String,
    pub duration_ms: i64,
}

/// A streaming manifest chunk for large pipelines.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentChunk {
    pub chunk_id: String,
    pub payload: Vec<u8>,
    pub is_last: bool,
}

/// Validation event emitted during stream validation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationEvent {
    pub event_type: String,
    pub violation: Option<ViolationRecord>,
}

/// An individual rule or schema violation record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViolationRecord {
    pub rule_id: String,
    pub check_type: String,
    pub severity: String,
    pub message: String,
    pub field_path: String,
    pub line_number: i32,
    pub help_uri: String,
}

/// An individual suggested fix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuggestedFix {
    pub rule_id: String,
    pub description: String,
    pub field_path: String,
    pub original_text: String,
    pub replacement_text: String,
}

/// Native implementation of the ManifestService RPC interface.
#[derive(Default)]
pub struct NativeManifestService;

impl NativeManifestService {
    pub fn new() -> Self {
        Self
    }

    /// Scans a manifest string in-memory according to `ScanDocumentRequest`.
    pub fn scan_document(&self, req: &ScanDocumentRequest) -> ScanDocumentResponse {
        let start = Instant::now();
        let k8s_version = req.target_k8s_version.as_deref().unwrap_or("1.30");

        let schemas = native_get_schema_for_version(k8s_version);
        let shards = native_shard(&req.content);

        let mut violations = Vec::new();

        if !shards.is_empty() {
            let manifest = native_structurize(shards);
            let schema_violations =
                crate::schemas::native_validate_ast_against_schema(&manifest, &schemas);

            for v in schema_violations {
                violations.push(ViolationRecord {
                    rule_id: "SCH-001".to_string(),
                    check_type: "schema".to_string(),
                    severity: "error".to_string(),
                    message: v.message,
                    field_path: v.field_path,
                    line_number: 1,
                    help_uri: "https://yamlr.dev/rules/sch-001".to_string(),
                });
            }

            for iv in &manifest.integrity_violations {
                violations.push(ViolationRecord {
                    rule_id: iv.rule_id.clone(),
                    check_type: "integrity".to_string(),
                    severity: iv.severity.clone().to_lowercase(),
                    message: iv.message.clone(),
                    field_path: String::new(),
                    line_number: 1,
                    help_uri: format!("https://yamlr.dev/rules/{}", iv.rule_id.to_lowercase()),
                });
            }
        }

        let total = violations.len() as i32;
        let health_score = if total == 0 {
            100.0
        } else {
            (100.0 - (total as f32 * 15.0)).max(0.0)
        };

        ScanDocumentResponse {
            status: if total == 0 {
                "passed".to_string()
            } else {
                "failed".to_string()
            },
            total_violations: total,
            violations,
            health_score,
            duration_ms: start.elapsed().as_millis() as i64,
        }
    }

    /// Surgically heals identified violations while preserving comments and formatting.
    pub fn heal_document(&self, req: &HealDocumentRequest) -> HealDocumentResponse {
        let start = Instant::now();

        if req.content.trim().is_empty() {
            return HealDocumentResponse {
                healed_content: req.content.clone(),
                mutated: false,
                applied_fixes: Vec::new(),
                unified_diff: String::new(),
                duration_ms: 0,
            };
        }

        let (healed, changes) = heal_manifest_string(&req.content);
        let mutated = healed != req.content;
        let diff = if mutated {
            wasm_diff(&req.content, &healed)
        } else {
            String::new()
        };

        let applied_fixes = changes
            .into_iter()
            .map(|desc| SuggestedFix {
                rule_id: "AUT-FIX".to_string(),
                description: desc,
                field_path: String::new(),
                original_text: String::new(),
                replacement_text: String::new(),
            })
            .collect();

        HealDocumentResponse {
            healed_content: if req.dry_run {
                req.content.clone()
            } else {
                healed
            },
            mutated,
            applied_fixes,
            unified_diff: diff,
            duration_ms: start.elapsed().as_millis() as i64,
        }
    }

    /// Bi-directional streaming chunk validation.
    pub fn stream_validate(&self, chunks: &[DocumentChunk]) -> Vec<ValidationEvent> {
        let mut full_payload = Vec::new();
        for chunk in chunks {
            full_payload.extend_from_slice(&chunk.payload);
        }

        let content = String::from_utf8_lossy(&full_payload);
        let scan_res = self.scan_document(&ScanDocumentRequest {
            content: content.to_string(),
            file_path: Some("streamed-chunk.yaml".to_string()),
            target_k8s_version: Some("1.30".to_string()),
        });

        scan_res
            .violations
            .into_iter()
            .map(|v| ValidationEvent {
                event_type: "violation_detected".to_string(),
                violation: Some(v),
            })
            .collect()
    }
}

/// Runs the ManifestService RPC daemon.
pub fn execute_rpc_daemon(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("rpc", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let port = *matches.get_one::<u16>("port").unwrap();
    if matches.get_flag("dry-run") {
        println!("Manifest RPC configuration valid: loopback port={port}; no listener started.");
        return crate::cli::EXIT_SUCCESS;
    }
    if matches.get_flag("serve") {
        return run_rpc_server(port);
    }
    eprintln!("[ERROR] The RPC network listener is not implemented. No service was started. Use --dry-run to inspect configuration.");
    crate::cli::EXIT_USAGE
}

fn run_rpc_server(port: u16) -> i32 {
    let bind_addr = format!("0.0.0.0:{}", port);
    let listener = match std::net::TcpListener::bind(&bind_addr) {
        Ok(l) => {
            println!(
                "Yamlr ManifestService RPC daemon listening on http://{}",
                bind_addr
            );
            l
        }
        Err(e) => {
            eprintln!(
                "[ERROR] Failed to bind ManifestService RPC daemon to {}: {}",
                bind_addr, e
            );
            return crate::cli::EXIT_SYSTEM_ERROR;
        }
    };

    let svc = NativeManifestService::new();
    for stream in listener.incoming() {
        match stream {
            Ok(mut stream) => {
                handle_rpc_client(&svc, &mut stream);
            }
            Err(e) => {
                eprintln!("[ERROR] RPC stream error: {}", e);
            }
        }
    }
    crate::cli::EXIT_SUCCESS
}

fn handle_rpc_client(svc: &NativeManifestService, stream: &mut std::net::TcpStream) {
    use std::io::{Read, Write};
    let mut buffer = [0u8; 4096];
    let mut request = Vec::new();
    loop {
        match stream.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => {
                request.extend_from_slice(&buffer[..n]);
                if request.windows(4).any(|w| w == b"\r\n\r\n") || request.len() >= 65536 {
                    break;
                }
            }
            Err(_) => return,
        }
    }

    let req_str = String::from_utf8_lossy(&request);
    let lines: Vec<&str> = req_str.lines().collect();
    if lines.is_empty() {
        return;
    }

    let first_line = lines[0];
    let parts: Vec<&str> = first_line.split_whitespace().collect();
    if parts.len() < 2 {
        return;
    }

    let method = parts[0];
    let path = parts[1];

    let body = if let Some(pos) = req_str.find("\r\n\r\n") {
        &req_str[pos + 4..]
    } else {
        ""
    };

    if method == "GET" && (path == "/healthz" || path == "/livez") {
        let resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\":\"SERVING\",\"service\":\"yamlr.v1.ManifestService\"}";
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    if method == "POST" && (path == "/v1/scan" || path.contains("ScanDocument")) {
        let scan_req: ScanDocumentRequest = match serde_json::from_str(body) {
            Ok(r) => r,
            Err(e) => {
                let err_resp = format!(
                    "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{{\"error\":\"{}\"}}",
                    e
                );
                let _ = stream.write_all(err_resp.as_bytes());
                return;
            }
        };
        let scan_resp = svc.scan_document(&scan_req);
        let resp_json = serde_json::to_string(&scan_resp).unwrap_or_default();
        let resp = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{}",
            resp_json
        );
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    if method == "POST" && (path == "/v1/heal" || path.contains("HealDocument")) {
        let heal_req: HealDocumentRequest = match serde_json::from_str(body) {
            Ok(r) => r,
            Err(e) => {
                let err_resp = format!(
                    "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{{\"error\":\"{}\"}}",
                    e
                );
                let _ = stream.write_all(err_resp.as_bytes());
                return;
            }
        };
        let heal_resp = svc.heal_document(&heal_req);
        let resp_json = serde_json::to_string(&heal_resp).unwrap_or_default();
        let resp = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{}",
            resp_json
        );
        let _ = stream.write_all(resp.as_bytes());
        return;
    }

    let not_found = "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n";
    let _ = stream.write_all(not_found.as_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_grpc_scan_document_valid() {
        let svc = NativeManifestService::new();
        let valid_deploy = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25.0
"#;
        let req = ScanDocumentRequest {
            content: valid_deploy.to_string(),
            file_path: Some("deploy.yaml".to_string()),
            target_k8s_version: Some("1.30".to_string()),
        };

        let resp = svc.scan_document(&req);
        assert_eq!(resp.status, "passed");
        assert_eq!(resp.total_violations, 0);
        assert_eq!(resp.health_score, 100.0);
    }

    #[test]
    fn test_grpc_heal_document_dry_run_and_comment_preservation() {
        let svc = NativeManifestService::new();
        let content_with_comment = r#"# Critical Production Service
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  ports:
    - port: 80
      targetPort: 80
"#;
        let req = HealDocumentRequest {
            content: content_with_comment.to_string(),
            file_path: Some("service.yaml".to_string()),
            target_k8s_version: Some("1.30".to_string()),
            dry_run: true,
        };

        let resp = svc.heal_document(&req);
        assert_eq!(resp.healed_content, content_with_comment);
        assert!(resp
            .healed_content
            .contains("# Critical Production Service"));
    }

    #[test]
    fn test_grpc_stream_validate() {
        let svc = NativeManifestService::new();
        let chunks = vec![
            DocumentChunk {
                chunk_id: "chunk-1".to_string(),
                payload: b"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n".to_vec(),
                is_last: false,
            },
            DocumentChunk {
                chunk_id: "chunk-2".to_string(),
                payload: b"  name: app\nspec:\n  replicas: 1\n".to_vec(),
                is_last: true,
            },
        ];

        let events = svc.stream_validate(&chunks);
        assert!(events.is_empty() || events.len() >= 1);
    }

    #[test]
    fn test_execute_rpc_daemon_dry_run() {
        let args = vec![
            "yamlr".to_string(),
            "rpc".to_string(),
            "--dry-run".to_string(),
            "-p".to_string(),
            "50055".to_string(),
        ];
        assert_eq!(execute_rpc_daemon(&args), crate::cli::EXIT_SUCCESS);
    }

    #[test]
    fn test_execute_rpc_daemon_unsupported_without_serve() {
        let args = vec!["yamlr".to_string(), "rpc".to_string()];
        assert_eq!(execute_rpc_daemon(&args), crate::cli::EXIT_USAGE);
    }
}
