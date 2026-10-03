//! In-Cluster Admission Webhook CLI Command.
//!
//! Why: Exposes a native HTTP endpoint for Kubernetes mutating admission reviews.
//! Validation-only reviews are not supported by this command.

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR};
use crate::cluster::webhook::handle_admission_review;
use std::io::{Read, Write};
use std::net::TcpListener;

const MAX_HTTP_HEADER_BYTES: usize = 16 * 1024;
const MAX_ADMISSION_BODY_BYTES: usize = 2 * 1024 * 1024;

/// Starts or dry-runs the in-cluster admission webhook server.
pub fn execute_webhook(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("webhook", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let port = *matches.get_one::<u16>("port").unwrap();
    let dry_run = matches.get_flag("dry-run");
    let tls_cert = matches.get_one::<String>("tls-cert");
    let tls_key = matches.get_one::<String>("tls-key");

    if (tls_cert.is_some() && tls_key.is_none()) || (tls_cert.is_none() && tls_key.is_some()) {
        eprintln!("Error: Both --tls-cert and --tls-key must be provided together for TLS termination.");
        return crate::cli::EXIT_USAGE;
    }

    if let (Some(cert_path), Some(key_path)) = (tls_cert, tls_key) {
        if !std::path::Path::new(cert_path).is_file() {
            eprintln!("Error: TLS certificate file not found: {}", cert_path);
            return crate::cli::EXIT_CONFIG_ERROR;
        }
        if !std::path::Path::new(key_path).is_file() {
            eprintln!("Error: TLS key file not found: {}", key_path);
            return crate::cli::EXIT_CONFIG_ERROR;
        }
    }

    if dry_run {
        let mode = if tls_cert.is_some() { " (TLS enabled)" } else { "" };
        println!("yamlr webhook configuration valid: port={}{}", port, mode);
        return EXIT_SUCCESS;
    }

    #[cfg(not(target_arch = "wasm32"))]
    let tls_config = if let (Some(cert_path), Some(key_path)) = (tls_cert, tls_key) {
        match crate::cluster::build_tls_server_config(cert_path, key_path) {
            Ok(cfg) => Some(cfg),
            Err(e) => {
                eprintln!("Error: Failed to configure TLS: {}", e);
                return crate::cli::EXIT_CONFIG_ERROR;
            }
        }
    } else {
        None
    };

    let bind_addr = format!("0.0.0.0:{}", port);
    let listener = match TcpListener::bind(&bind_addr) {
        Ok(l) => {
            let mode = if tls_cert.is_some() {
                "HTTPS (TLS)"
            } else {
                "HTTP (plaintext)"
            };
            println!(
                "Yamlr In-Cluster Admission Webhook listening on {} [{}]",
                bind_addr, mode
            );
            l
        }
        Err(e) => {
            eprintln!(
                "Error: Failed to bind admission webhook to {}: {}",
                bind_addr, e
            );
            return EXIT_SYSTEM_ERROR;
        }
    };

    for stream in listener.incoming() {
        match stream {
            Ok(mut stream) => {
                #[cfg(not(target_arch = "wasm32"))]
                if let Some(ref config) = tls_config {
                    let mut server_conn = match rustls::ServerConnection::new(config.clone()) {
                        Ok(c) => c,
                        Err(e) => {
                            eprintln!("TLS handshake error: {}", e);
                            continue;
                        }
                    };
                    let mut tls_stream = rustls::Stream::new(&mut server_conn, &mut stream);
                    handle_client_stream(&mut tls_stream);
                    continue;
                }
                handle_client_stream(&mut stream);
            }
            Err(e) => {
                eprintln!("Connection failed: {}", e);
            }
        }
    }

    EXIT_SUCCESS
}

fn handle_client_stream<S: Read + Write>(stream: &mut S) {
    let (method, path, body) = match read_http_request(stream) {
        Ok(request) => request,
        Err(error) => {
            let _ = write_json_response(stream, "400 Bad Request", &error);
            return;
        }
    };

    if (path == "/healthz" || path == "/livez") && method == "GET" {
        let response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok";
        let _ = stream.write_all(response.as_bytes());
    } else if is_mutation_endpoint(&path) {
        if method != "POST" {
            let _ = write_json_response(
                stream,
                "405 Method Not Allowed",
                "Admission endpoints require POST",
            );
            return;
        }
        match handle_admission_review(&body) {
            Ok(response_body) => {
                let _ = write_json_response(stream, "200 OK", &response_body);
            }
            Err(error) => {
                let _ = write_json_response(stream, "400 Bad Request", &error);
            }
        }
    } else {
        let not_found = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(not_found.as_bytes());
    }
}

fn read_http_request<R: Read>(reader: &mut R) -> Result<(String, String, String), String> {
    let mut request = Vec::new();
    let mut buffer = [0u8; 4096];
    let header_end = loop {
        let count = reader
            .read(&mut buffer)
            .map_err(|error| format!("Failed to read HTTP request: {}", error))?;
        if count == 0 {
            return Err("Incomplete HTTP request headers".to_string());
        }
        request.extend_from_slice(&buffer[..count]);
        if let Some(end) = request.windows(4).position(|window| window == b"\r\n\r\n") {
            if end > MAX_HTTP_HEADER_BYTES {
                return Err("HTTP request headers exceed the size limit".to_string());
            }
            break end;
        }
        if request.len() > MAX_HTTP_HEADER_BYTES {
            return Err("HTTP request headers exceed the size limit".to_string());
        }
    };

    let header = std::str::from_utf8(&request[..header_end])
        .map_err(|_| "HTTP request headers must be UTF-8/ASCII".to_string())?;
    let mut lines = header.split("\r\n");
    let mut request_line = lines
        .next()
        .ok_or_else(|| "Missing HTTP request line".to_string())?
        .split_whitespace();
    let method = request_line
        .next()
        .ok_or_else(|| "Missing HTTP method".to_string())?;
    let path = request_line
        .next()
        .ok_or_else(|| "Missing HTTP request path".to_string())?;
    match request_line.next() {
        Some("HTTP/1.0" | "HTTP/1.1") if request_line.next().is_none() => {}
        _ => return Err("Malformed or unsupported HTTP request line".to_string()),
    }
    let method = method.to_string();
    let path = path.to_string();

    let mut content_length = None;
    for line in lines {
        let Some((name, value)) = line.split_once(':') else {
            return Err("Malformed HTTP header".to_string());
        };
        if name.eq_ignore_ascii_case("transfer-encoding") {
            return Err("Transfer-Encoding is not supported; send Content-Length".to_string());
        }
        if name.eq_ignore_ascii_case("content-length") {
            if content_length.is_some() {
                return Err("Duplicate Content-Length header".to_string());
            }
            content_length = Some(
                value
                    .trim()
                    .parse::<usize>()
                    .map_err(|_| "Invalid Content-Length header".to_string())?,
            );
        }
    }
    let content_length =
        content_length.ok_or_else(|| "Content-Length header is required".to_string())?;
    if content_length > MAX_ADMISSION_BODY_BYTES {
        return Err("AdmissionReview request body exceeds the 2 MiB limit".to_string());
    }

    let body_start = header_end + 4;
    let expected_length = body_start + content_length;
    while request.len() < expected_length {
        let remaining = expected_length - request.len();
        let read_length = remaining.min(buffer.len());
        let count = reader
            .read(&mut buffer[..read_length])
            .map_err(|error| format!("Failed to read HTTP request body: {}", error))?;
        if count == 0 {
            return Err("HTTP request body is shorter than Content-Length".to_string());
        }
        request.extend_from_slice(&buffer[..count]);
    }

    let body = std::str::from_utf8(&request[body_start..expected_length])
        .map_err(|_| "AdmissionReview body must be UTF-8 JSON".to_string())?;
    Ok((method, path, body.to_string()))
}

fn is_mutation_endpoint(path: &str) -> bool {
    path == "/mutate"
}

fn write_json_response<W: Write>(
    writer: &mut W,
    status: &str,
    message: &str,
) -> std::io::Result<()> {
    let body = if status == "200 OK" {
        message.to_string()
    } else {
        webhook_error_json(message)
    };
    let response = format!(
        "HTTP/1.1 {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        status,
        body.len(),
        body
    );
    writer.write_all(response.as_bytes())
}

fn webhook_error_json(message: &str) -> String {
    serde_json::json!({"error": message}).to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_the_mutation_route_is_enabled() {
        assert!(is_mutation_endpoint("/mutate"));
        assert!(!is_mutation_endpoint("/validate"));
        assert!(!is_mutation_endpoint("/mutate/"));
    }

    #[test]
    fn test_webhook_dry_run() {
        let args = vec![
            "yamlr".to_string(),
            "webhook".to_string(),
            "--dry-run".to_string(),
            "--port".to_string(),
            "9443".to_string(),
        ];
        assert_eq!(execute_webhook(&args), EXIT_SUCCESS);
    }

    #[test]
    fn malformed_review_error_is_valid_json_even_for_quoted_messages() {
        let message = "bad \"review\"\nbody";
        let encoded = webhook_error_json(message);
        let parsed: serde_json::Value = serde_json::from_str(&encoded).unwrap();
        assert_eq!(parsed["error"], message);
    }

    #[test]
    fn unsupported_tls_and_validation_modes_fail_visibly() {
        for option in ["--tls-cert", "--tls-key", "--validate-only", "--unknown"] {
            let args = vec![
                "yamlr".to_string(),
                "webhook".to_string(),
                option.to_string(),
            ];
            assert_eq!(execute_webhook(&args), crate::cli::EXIT_USAGE);
        }
    }

    #[test]
    fn invalid_port_fails_visibly() {
        for value in ["0", "not-a-port"] {
            let args = vec![
                "yamlr".to_string(),
                "webhook".to_string(),
                "--port".to_string(),
                value.to_string(),
            ];
            assert_eq!(execute_webhook(&args), crate::cli::EXIT_USAGE);
        }
    }

    #[test]
    fn http_request_reader_handles_split_reads_and_bodies_over_16_kib() {
        let body = "x".repeat(20 * 1024);
        let request = format!(
            "POST /mutate HTTP/1.1\r\nHost: localhost\r\nContent-Length: {}\r\n\r\n{}",
            body.len(),
            body
        );
        let mut reader = std::io::Cursor::new(request.into_bytes());

        let (method, path, parsed_body) = read_http_request(&mut reader).unwrap();

        assert_eq!(method, "POST");
        assert_eq!(path, "/mutate");
        assert_eq!(parsed_body, body);
    }

    #[test]
    fn http_request_reader_rejects_missing_length_truncation_and_chunked_bodies() {
        let missing_length = b"POST /mutate HTTP/1.1\r\nHost: localhost\r\n\r\n{}";
        assert!(read_http_request(&mut std::io::Cursor::new(missing_length)).is_err());

        let truncated = b"POST /mutate HTTP/1.1\r\nContent-Length: 5\r\n\r\n{}";
        assert!(read_http_request(&mut std::io::Cursor::new(truncated)).is_err());

        let chunked = b"POST /mutate HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n{}";
        assert!(read_http_request(&mut std::io::Cursor::new(chunked)).is_err());
    }

    #[test]
    fn webhook_tls_flags_require_both_cert_and_key() {
        let args = vec![
            "yamlr".to_string(),
            "webhook".to_string(),
            "--tls-cert".to_string(),
            "cert.pem".to_string(),
            "--dry-run".to_string(),
        ];
        assert_eq!(execute_webhook(&args), crate::cli::EXIT_USAGE);

        let args_key_only = vec![
            "yamlr".to_string(),
            "webhook".to_string(),
            "--tls-key".to_string(),
            "key.pem".to_string(),
            "--dry-run".to_string(),
        ];
        assert_eq!(execute_webhook(&args_key_only), crate::cli::EXIT_USAGE);
    }
}
