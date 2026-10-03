//! OCI Helm Chart Layer Ingestion Engine.
//!
//! Why: Modern Helm chart distribution has shifted from HTTP tarball registries to OCI
//! (Open Container Initiative) image registries (e.g. `oci://ghcr.io/org/chart:1.2.3`).
//! Yamlr must ingest and audit these charts entirely in-memory — without invoking the
//! `helm` CLI or `docker` daemon — to remain a zero-dependency, hermetic engine that
//! works in air-gapped CI environments and GitHub Actions runners.
//!
//! This module detects `oci://` URI schemes, decodes CNCF Helm chart tar+gzip layers,
//! and returns all chart template YAML content and `values.schema.json` for downstream
//! schema validation and healing.

use flate2::read::GzDecoder;
use std::io::{Cursor, Read};
use tar::Archive;

const MAX_EXPANDED_OCI_LAYER_BYTES: u64 = 100 * 1024 * 1024;
const MAX_EXTRACTED_OCI_CONTENT_BYTES: usize = 10 * 1024 * 1024;

/// Detects whether a given target string is an OCI registry URI.
///
/// Why: The entry-point `execute_scan` must distinguish filesystem paths from
/// OCI URIs before routing to the appropriate ingestion pipeline.
///
/// # Examples
/// ```no_run
/// use yamlr_native::parsers::helm::is_oci_uri;
/// assert!(is_oci_uri("oci://ghcr.io/org/chart:1.2.3"));
/// assert!(!is_oci_uri("./k8s/deploy.yaml"));
/// ```
pub fn is_oci_uri(target: &str) -> bool {
    target.starts_with("oci://")
}

/// Parsed contents extracted from a Helm OCI chart layer.
#[derive(Debug, Clone)]
pub struct OciChartContents {
    /// All `templates/*.yaml` / `templates/*.yml` content concatenated as multi-doc YAML.
    pub templates_yaml: String,
    /// Raw `values.schema.json` content if present in the chart layer.
    pub values_schema_json: Option<String>,
    /// Raw `values.yaml` content if present in the chart layer.
    pub values_yaml: Option<String>,
    /// Chart name parsed from `Chart.yaml`, if present.
    pub chart_name: Option<String>,
}

/// Unpacks a Helm chart OCI layer (tar+gzip blob) entirely in-memory and extracts
/// all auditable YAML content.
///
/// Why: OCI chart layers are stored as `application/vnd.cncf.helm.chart.content.v1.tar+gzip`
/// blobs. The tar archive contains the full chart directory tree. We extract only YAML
/// template files and schema JSON — no filesystem writes, no subprocess calls.
///
/// # Arguments
/// * `layer_bytes` — The raw tar+gzip bytes of the OCI chart content layer.
///
/// # Returns
/// `Ok(OciChartContents)` on successful extraction, or `Err(String)` describing the
/// decode or I/O failure.
pub fn unpack_oci_chart_layer(layer_bytes: &[u8]) -> Result<OciChartContents, String> {
    unpack_oci_chart_layer_with_limits(
        layer_bytes,
        MAX_EXPANDED_OCI_LAYER_BYTES,
        MAX_EXTRACTED_OCI_CONTENT_BYTES,
    )
}

fn unpack_oci_chart_layer_with_limits(
    layer_bytes: &[u8],
    max_expanded_bytes: u64,
    max_extracted_bytes: usize,
) -> Result<OciChartContents, String> {
    let gz_decoder = GzDecoder::new(Cursor::new(layer_bytes));
    let bounded_decoder = gz_decoder.take(max_expanded_bytes.saturating_add(1));
    let mut archive = Archive::new(bounded_decoder);

    let mut templates_yaml = String::new();
    let mut values_schema_json: Option<String> = None;
    let mut values_yaml: Option<String> = None;
    let mut chart_name: Option<String> = None;
    let mut extracted_bytes = 0usize;

    {
        let entries = archive
            .entries()
            .map_err(|e| format!("OCI layer tar read error: {}", e))?;

        for entry_result in entries {
            let entry = entry_result.map_err(|e| format!("OCI tar entry error: {}", e))?;
            let path = entry
                .path()
                .map_err(|e| format!("OCI tar path error: {}", e))?
                .to_string_lossy()
                .to_string();

            // Read file content lazily — skip large non-YAML blobs (images, binaries)
            let path_lower = path.to_lowercase();
            let is_template = path_lower.contains("/templates/")
                && (path_lower.ends_with(".yaml") || path_lower.ends_with(".yml"));
            let is_schema = path_lower.ends_with("values.schema.json");
            let is_values =
                path_lower.ends_with("values.yaml") && !path_lower.contains("/templates/");
            let is_chart_yaml = path_lower.ends_with("chart.yaml");

            if is_template || is_schema || is_values || is_chart_yaml {
                let remaining = max_extracted_bytes.saturating_sub(extracted_bytes);
                let mut content_bytes = Vec::new();
                entry
                    .take(remaining.saturating_add(1) as u64)
                    .read_to_end(&mut content_bytes)
                    .map_err(|e| format!("OCI tar entry read error for '{}': {}", path, e))?;
                if content_bytes.len() > remaining {
                    return Err(format!(
                        "OCI extracted chart content exceeds the {} MiB limit",
                        max_extracted_bytes / (1024 * 1024)
                    ));
                }
                add_extracted_bytes(
                    &mut extracted_bytes,
                    content_bytes.len(),
                    max_extracted_bytes,
                )?;
                let content = String::from_utf8(content_bytes).map_err(|e| {
                    format!("OCI tar entry is not valid UTF-8 for '{}': {}", path, e)
                })?;

                if is_template && !content.trim().is_empty() {
                    let separator = !templates_yaml.is_empty();
                    if separator {
                        add_extracted_bytes(&mut extracted_bytes, 5, max_extracted_bytes)?;
                    }
                    // Inject YAML document separator to form valid multi-doc stream
                    if separator {
                        templates_yaml.push_str("\n---\n");
                    }
                    templates_yaml.push_str(&content);
                } else if is_schema {
                    values_schema_json = Some(content);
                } else if is_values {
                    values_yaml = Some(content);
                } else if is_chart_yaml {
                    // Parse chart name from Chart.yaml for diagnostic messages
                    chart_name = extract_chart_name(&content);
                }
            }
        }
    }

    let mut bounded_decoder = archive.into_inner();
    std::io::copy(&mut bounded_decoder, &mut std::io::sink())
        .map_err(|e| format!("OCI layer decompression error: {}", e))?;
    if bounded_decoder.limit() == 0 {
        return Err(format!(
            "OCI expanded chart layer exceeds the {} MiB limit",
            max_expanded_bytes / (1024 * 1024)
        ));
    }

    Ok(OciChartContents {
        templates_yaml,
        values_schema_json,
        values_yaml,
        chart_name,
    })
}

fn add_extracted_bytes(
    extracted_bytes: &mut usize,
    additional_bytes: usize,
    max_extracted_bytes: usize,
) -> Result<(), String> {
    *extracted_bytes = extracted_bytes.saturating_add(additional_bytes);
    if *extracted_bytes > max_extracted_bytes {
        return Err(format!(
            "OCI extracted chart content exceeds the {} MiB limit",
            max_extracted_bytes / (1024 * 1024)
        ));
    }
    Ok(())
}

/// Extracts the `name:` field from a `Chart.yaml` string.
///
/// Why: Chart name is used in diagnostic output to identify which chart the
/// violation originated from, matching Helm CLI error messages.
fn extract_chart_name(chart_yaml: &str) -> Option<String> {
    for line in chart_yaml.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("name:") {
            return Some(
                trimmed
                    .trim_start_matches("name:")
                    .trim()
                    .trim_matches('"')
                    .trim_matches('\'')
                    .to_string(),
            );
        }
    }
    None
}

/// Resolves an `oci://` URI into its constituent registry, repository, and tag/digest parts.
///
/// Why: Provides clean structured access to OCI reference components for logging,
/// diagnostic source attribution, and future registry authentication integration.
///
/// # Examples
/// `oci://ghcr.io/my-org/my-chart:1.2.3` → `OciReference { registry: "ghcr.io", repository: "my-org/my-chart", tag: Some("1.2.3") }`
#[derive(Debug, Clone, PartialEq)]
pub struct OciReference {
    pub registry: String,
    pub repository: String,
    pub tag: Option<String>,
    pub digest: Option<String>,
}

/// Parses an `oci://` URI string into its structured components.
pub fn parse_oci_uri(uri: &str) -> Result<OciReference, String> {
    let without_scheme = uri
        .strip_prefix("oci://")
        .ok_or_else(|| format!("Not an OCI URI: '{}'", uri))?;

    // Split on '@' for digest references first
    let (ref_part, digest) = if let Some(idx) = without_scheme.find('@') {
        let (r, d) = without_scheme.split_at(idx);
        (r, Some(d.trim_start_matches('@').to_string()))
    } else {
        (without_scheme, None)
    };

    // Split on first '/' to separate registry from repository
    let (registry, rest) = if let Some(idx) = ref_part.find('/') {
        (&ref_part[..idx], &ref_part[idx + 1..])
    } else {
        return Err(format!("OCI URI missing repository: '{}'", uri));
    };

    // Split repository and tag on ':'
    let (repository, tag) = if let Some(idx) = rest.rfind(':') {
        let (repo, t) = rest.split_at(idx);
        (repo, Some(t.trim_start_matches(':').to_string()))
    } else {
        (rest, None)
    };

    Ok(OciReference {
        registry: registry.to_string(),
        repository: repository.to_string(),
        tag,
        digest,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use flate2::write::GzEncoder;
    use flate2::Compression;

    fn make_mock_oci_layer(files: &[(&str, &str)]) -> Vec<u8> {
        // Build an in-memory tar+gz with the given (path, content) pairs
        let compressed_buf = Vec::new();
        let gz = GzEncoder::new(compressed_buf, Compression::fast());
        let mut tar_builder = tar::Builder::new(gz);

        for (path, content) in files {
            let content_bytes = content.as_bytes();
            let mut header = tar::Header::new_gnu();
            header.set_path(path).unwrap();
            header.set_size(content_bytes.len() as u64);
            header.set_mode(0o644);
            header.set_cksum();
            tar_builder
                .append(&header, Cursor::new(content_bytes))
                .unwrap();
        }
        let gz_encoder = tar_builder.into_inner().unwrap();
        gz_encoder.finish().unwrap()
    }

    #[test]
    fn test_is_oci_uri_detection() {
        assert!(is_oci_uri("oci://ghcr.io/org/chart:1.2.3"));
        assert!(is_oci_uri(
            "oci://registry.k8s.io/charts/ingress-nginx:4.11.0"
        ));
        assert!(!is_oci_uri("./k8s/deploy.yaml"));
        assert!(!is_oci_uri("https://helm.example.com/chart.tgz"));
        assert!(!is_oci_uri("/absolute/path.yaml"));
    }

    #[test]
    fn test_parse_oci_uri_full_reference() {
        let r = parse_oci_uri("oci://ghcr.io/my-org/my-chart:1.2.3").unwrap();
        assert_eq!(r.registry, "ghcr.io");
        assert_eq!(r.repository, "my-org/my-chart");
        assert_eq!(r.tag, Some("1.2.3".to_string()));
        assert_eq!(r.digest, None);
    }

    #[test]
    fn test_parse_oci_uri_digest_reference() {
        let r = parse_oci_uri("oci://ghcr.io/org/chart@sha256:abc123def456").unwrap();
        assert_eq!(r.registry, "ghcr.io");
        assert_eq!(r.digest, Some("sha256:abc123def456".to_string()));
        assert_eq!(r.tag, None);
    }

    #[test]
    fn test_parse_oci_uri_missing_repository_errors() {
        assert!(parse_oci_uri("oci://ghcr.io").is_err());
    }

    #[test]
    fn test_unpack_oci_chart_layer_mock_tarball() {
        // Why: Verifies end-to-end extraction pipeline without a live OCI registry.
        // Uses an in-memory tar+gzip stream mimicking a real Helm OCI layer.
        let deployment_yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ .Values.name }}\nspec:\n  replicas: {{ .Values.replicas }}\n";
        let service_yaml =
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: {{ .Values.name }}-svc\n";
        let schema_json = r#"{"type":"object","properties":{"replicas":{"type":"integer"}}}"#;
        let chart_yaml = "apiVersion: v2\nname: my-test-chart\nversion: 1.0.0\n";

        let layer = make_mock_oci_layer(&[
            ("my-test-chart/templates/deployment.yaml", deployment_yaml),
            ("my-test-chart/templates/service.yaml", service_yaml),
            ("my-test-chart/values.schema.json", schema_json),
            ("my-test-chart/Chart.yaml", chart_yaml),
        ]);

        let contents = unpack_oci_chart_layer(&layer).unwrap();

        // Verify templates were extracted and concatenated
        assert!(
            contents.templates_yaml.contains("kind: Deployment"),
            "Deployment template must be extracted"
        );
        assert!(
            contents.templates_yaml.contains("kind: Service"),
            "Service template must be extracted"
        );

        // Verify schema was captured
        assert!(
            contents.values_schema_json.is_some(),
            "values.schema.json must be present"
        );
        assert!(contents.values_schema_json.unwrap().contains("replicas"));

        // Verify chart name parsing
        assert_eq!(contents.chart_name, Some("my-test-chart".to_string()));
    }

    #[test]
    fn extracted_templates_preserve_the_multi_document_separator_layout() {
        let layer = make_mock_oci_layer(&[
            ("chart/templates/first.yaml", "kind: First\n"),
            ("chart/templates/second.yaml", "kind: Second\n"),
        ]);

        let contents = unpack_oci_chart_layer(&layer).unwrap();

        assert_eq!(
            contents.templates_yaml,
            "kind: First\n\n---\nkind: Second\n"
        );
    }

    #[test]
    fn extracted_chart_content_limit_is_enforced() {
        let layer = make_mock_oci_layer(&[("chart/templates/workload.yaml", "kind: Workload")]);

        let error = unpack_oci_chart_layer_with_limits(&layer, 1024 * 1024, 8).unwrap_err();

        assert!(error.contains("extracted chart content exceeds"));
    }

    #[test]
    fn expanded_archive_limit_includes_unselected_entries() {
        let ignored_content = "x".repeat(4096);
        let layer = make_mock_oci_layer(&[("chart/images/ignored.bin", &ignored_content)]);

        let error = unpack_oci_chart_layer_with_limits(&layer, 1024, 1024).unwrap_err();

        assert!(
            error.contains("OCI tar entry error") || error.contains("expanded chart layer exceeds")
        );
    }

    #[test]
    fn test_extract_chart_name_quoted_and_unquoted() {
        assert_eq!(
            extract_chart_name("apiVersion: v2\nname: my-chart\nversion: 1.0.0\n"),
            Some("my-chart".to_string())
        );
        assert_eq!(
            extract_chart_name("name: \"quoted-chart\"\nversion: 2.0.0\n"),
            Some("quoted-chart".to_string())
        );
        assert_eq!(
            extract_chart_name("# no name field\nversion: 1.0.0\n"),
            None
        );
    }
}
