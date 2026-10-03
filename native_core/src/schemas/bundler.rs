//! Kubernetes Schema Bundler & Version Intelligence.
//!
//! Why: Embeds pre-compiled, distilled OpenAPI schemas for Kubernetes v1.21 through
//!      v1.37+ along with standard CNCF CRD definitions. Provides deterministic,
//!      sub-millisecond schema resolution and resilient forward-compatibility fallbacks.

use crate::models::{NativeSchema, SchemaProperty};
use serde_json::Value;
use std::collections::HashMap;

/// Decompresses embedded zstd schema bytes with zero external allocation on hit.
pub fn decompress_schema_bytes(bytes: &[u8]) -> String {
    zstd::decode_all(std::io::Cursor::new(bytes))
        .map(|v| String::from_utf8(v).unwrap_or_default())
        .unwrap_or_default()
}

/// Returns compressed embedded schema bundle mapping Kubernetes minor versions to zstd compressed bytes.
pub fn get_compressed_bundle() -> HashMap<&'static str, &'static [u8]> {
    let mut m = HashMap::new();
    m.insert(
        "1.21",
        include_bytes!("k8s_v1.21_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.22",
        include_bytes!("k8s_v1.22_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.23",
        include_bytes!("k8s_v1.23_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.24",
        include_bytes!("k8s_v1.24_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.25",
        include_bytes!("k8s_v1.25_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.26",
        include_bytes!("k8s_v1.26_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.27",
        include_bytes!("k8s_v1.27_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.28",
        include_bytes!("k8s_v1.28_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.29",
        include_bytes!("k8s_v1.29_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.30",
        include_bytes!("k8s_v1.30_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.31",
        include_bytes!("k8s_v1.31_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.32",
        include_bytes!("k8s_v1.32_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.33",
        include_bytes!("k8s_v1.33_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.34",
        include_bytes!("k8s_v1.34_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.35",
        include_bytes!("k8s_v1.35_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.36",
        include_bytes!("k8s_v1.36_distilled.json.zst").as_slice(),
    );
    m.insert(
        "1.37",
        include_bytes!("k8s_v1.37_distilled.json.zst").as_slice(),
    );
    m
}

lazy_static::lazy_static! {
    static ref DECOMPRESSED_BUNDLE: HashMap<&'static str, String> = {
        let comp = get_compressed_bundle();
        let mut m = HashMap::new();
        for (k, v) in comp {
            m.insert(k, decompress_schema_bytes(v));
        }
        m
    };
}

/// Returns pre-compiled schema bundle mapping Kubernetes minor versions to distilled JSON definitions.
pub fn get_bundle() -> HashMap<&'static str, &'static str> {
    let mut m = HashMap::new();
    for (k, v) in DECOMPRESSED_BUNDLE.iter() {
        m.insert(*k, v.as_str());
    }
    m
}

/// Returns embedded standard CNCF CRD schema definitions.
pub fn get_cncf_crd_schemas() -> Vec<NativeSchema> {
    let decompressed = decompress_schema_bytes(include_bytes!("cncf_crds_distilled.json.zst"));
    let raw: HashMap<String, Value> = serde_json::from_str(&decompressed).unwrap_or_default();
    parse_raw_schemas(raw)
}

/// Fails when a present cached or configured schema override cannot be used.
///
/// The legacy resolver keeps its Vec-returning API and skips invalid candidates;
/// scan uses this preflight so a broken override cannot silently select a baseline.
pub fn validate_schema_overrides(version: &str) -> Result<(), String> {
    let normalized = crate::schemas::normalize_k8s_version(version);
    let mut candidates = Vec::new();
    let local_cache = std::path::PathBuf::from(".yamlr").join("schemas");
    candidates.extend([
        local_cache.join(format!("k8s_v{}_distilled.json", normalized)),
        local_cache.join(format!("k8s_v{}.json", normalized)),
        local_cache.join(format!("{}.json", normalized)),
    ]);
    if let Some(home) = dirs::home_dir() {
        let user_cache = home.join(".yamlr").join("schemas");
        candidates.extend([
            user_cache.join(format!("k8s_v{}_distilled.json", normalized)),
            user_cache.join(format!("k8s_v{}.json", normalized)),
            user_cache.join(format!("{}.json", normalized)),
        ]);
    }
    if let Ok(schema_dir) = std::env::var("YAMLR_SCHEMA_DIR") {
        candidates.extend([
            std::path::PathBuf::from(&schema_dir)
                .join(format!("k8s_v{}_distilled.json", normalized)),
            std::path::PathBuf::from(&schema_dir)
                .join(format!("k8s_{}_distilled.json", normalized)),
            std::path::PathBuf::from(&schema_dir).join(format!("k8s_v{}.json", normalized)),
            std::path::PathBuf::from(schema_dir).join(format!("{}.json", normalized)),
        ]);
    }

    for candidate in candidates {
        let exists = candidate.try_exists().map_err(|error| {
            format!(
                "Failed to inspect configured Kubernetes schema '{}': {}",
                candidate.display(),
                error
            )
        })?;
        if !exists {
            continue;
        }
        if !candidate.is_file() {
            return Err(format!(
                "Configured Kubernetes schema path '{}' is not a file",
                candidate.display()
            ));
        }
        let content = std::fs::read_to_string(&candidate).map_err(|error| {
            format!(
                "Failed to read configured Kubernetes schema '{}': {}",
                candidate.display(),
                error
            )
        })?;
        crate::schemas::fetcher::validate_distilled_schema(&content).map_err(|error| {
            format!(
                "Configured Kubernetes schema '{}' is invalid: {}",
                candidate.display(),
                error
            )
        })?;
        return Ok(());
    }
    Ok(())
}

/// Resolves distilled schemas for a target Kubernetes version via the 4-Tier Resolution Hierarchy:
/// Tier 1: Local project (.yamlr/schemas/) or user global cache (~/.yamlr/schemas/)
/// Tier 2: Custom schema directory configured via `YAMLR_SCHEMA_DIR`
/// Tier 3: Pre-compiled embedded bundle for Kubernetes v1.21 through v1.37
/// Tier 4: Forward-compatible nearest-neighbor fallback (v1.38+ uses v1.37 baseline with advisory)
pub fn native_get_schema_for_version(version: &str) -> Vec<NativeSchema> {
    let clean_v = version.trim().trim_start_matches('v');
    let normalized = if let Some(dot_idx) = clean_v.find('.') {
        if let Some(second_dot) = clean_v[dot_idx + 1..].find('.') {
            &clean_v[..dot_idx + 1 + second_dot]
        } else {
            clean_v
        }
    } else {
        clean_v
    };

    // --- Tier 1: Check Local Project Cache (.yamlr/schemas/) and User Global Cache (~/.yamlr/schemas/) ---
    let mut cache_candidates = Vec::new();
    let local_cache = std::path::PathBuf::from(".yamlr").join("schemas");
    cache_candidates.push(local_cache.join(format!("k8s_v{}_distilled.json", normalized)));
    cache_candidates.push(local_cache.join(format!("k8s_v{}.json", normalized)));
    cache_candidates.push(local_cache.join(format!("{}.json", normalized)));

    if let Some(home) = dirs::home_dir() {
        let user_cache = home.join(".yamlr").join("schemas");
        cache_candidates.push(user_cache.join(format!("k8s_v{}_distilled.json", normalized)));
        cache_candidates.push(user_cache.join(format!("k8s_v{}.json", normalized)));
        cache_candidates.push(user_cache.join(format!("{}.json", normalized)));
    }

    for cached_path in &cache_candidates {
        if cached_path.is_file() {
            if let Ok(content) = std::fs::read_to_string(cached_path) {
                if let Ok(raw) = serde_json::from_str::<HashMap<String, Value>>(&content) {
                    let mut schemas = parse_raw_schemas(raw);
                    schemas.extend(get_cncf_crd_schemas());
                    return schemas;
                }
            }
        }
    }

    // --- Tier 2: Check Configured Schema Path (YAMLR_SCHEMA_DIR) ---
    if let Ok(schema_dir) = std::env::var("YAMLR_SCHEMA_DIR") {
        let dir_candidates = [
            format!("{}/k8s_v{}_distilled.json", schema_dir, normalized),
            format!("{}/k8s_{}_distilled.json", schema_dir, normalized),
            format!("{}/k8s_v{}.json", schema_dir, normalized),
            format!("{}/{}.json", schema_dir, normalized),
        ];

        for custom_file in &dir_candidates {
            if let Ok(custom_json) = std::fs::read_to_string(custom_file) {
                if let Ok(raw) = serde_json::from_str::<HashMap<String, Value>>(&custom_json) {
                    let mut schemas = parse_raw_schemas(raw);
                    schemas.extend(get_cncf_crd_schemas());
                    return schemas;
                }
            }
        }
    }

    // --- Tier 3 & Tier 4: Embedded Native Bundle & Forward-Compatible Fallback ---
    let bundle = get_bundle();

    let resolved_json = if let Some(json_str) = bundle.get(normalized) {
        *json_str
    } else {
        let parts: Vec<&str> = normalized.split('.').collect();
        let minor: u32 = parts
            .get(1)
            .and_then(|m| {
                m.chars()
                    .take_while(|c| c.is_ascii_digit())
                    .collect::<String>()
                    .parse()
                    .ok()
            })
            .unwrap_or(30);

        if minor >= 37 {
            // Tier 4: Forward-compatible fallback with advisory notice
            eprintln!(
                "[ADVISORY] Schema for Kubernetes v{} not found locally. Using v1.37 baseline with open dynamic validation. Run 'yamlr schema fetch {}' to download official OpenAPI schema.",
                normalized, normalized
            );
            bundle
                .get("1.37")
                .copied()
                .unwrap_or_else(|| bundle.get("1.36").unwrap())
        } else if minor <= 21 {
            bundle
                .get("1.21")
                .copied()
                .unwrap_or_else(|| bundle.get("1.30").unwrap())
        } else {
            let minor_str = format!("1.{}", minor);
            bundle
                .get(minor_str.as_str())
                .copied()
                .unwrap_or_else(|| bundle.get("1.30").unwrap())
        }
    };

    let raw: HashMap<String, Value> = serde_json::from_str(resolved_json).unwrap_or_default();
    let mut schemas = parse_raw_schemas(raw);
    schemas.extend(get_cncf_crd_schemas());
    schemas.sort_by(|a, b| a.kind.cmp(&b.kind).then(a.api_version.cmp(&b.api_version)));
    schemas
}

/// Parses raw JSON schema maps into strongly typed NativeSchema structures.
pub fn parse_raw_schemas(raw: HashMap<String, Value>) -> Vec<NativeSchema> {
    let mut schemas = Vec::new();
    for (kind, val) in &raw {
        let api_version = val
            .get("apiVersion")
            .and_then(|v| v.as_str())
            .unwrap_or("v1")
            .to_string();
        let mut properties = Vec::new();
        let requires_spec = matches!(
            kind.as_str(),
            "Deployment"
                | "StatefulSet"
                | "DaemonSet"
                | "Job"
                | "CronJob"
                | "ReplicaSet"
                | "Pod"
                | "Service"
                | "Ingress"
                | "PersistentVolumeClaim"
                | "HorizontalPodAutoscaler"
                | "NetworkPolicy"
                | "PodDisruptionBudget"
                | "ServiceMonitor"
                | "PrometheusRule"
                | "Certificate"
                | "Issuer"
                | "ClusterIssuer"
                | "VirtualService"
                | "DestinationRule"
                | "HTTPRoute"
                | "Gateway"
                | "Rollout"
                | "Application"
                | "ExternalSecret"
                | "SecretStore"
                | "ClusterSecretStore"
                | "CiliumNetworkPolicy"
                | "CiliumClusterwideNetworkPolicy"
                | "IngressRoute"
                | "Workflow"
                | "CronWorkflow"
                | "Provider"
                | "PodMonitor"
        );

        if let Some(fields) = val.get("fields").and_then(|f| f.as_object()) {
            for (name, f_val) in fields {
                let is_required = match name.as_str() {
                    "apiVersion" | "kind" | "metadata" => true,
                    "spec" => requires_spec,
                    _ => f_val
                        .get("required")
                        .and_then(|r| r.as_bool())
                        .unwrap_or(false),
                };

                let mut enum_values = Vec::new();
                if let Some(enums) = f_val.get("enum").and_then(|e| e.as_array()) {
                    for ev in enums {
                        if let Some(s) = ev.as_str() {
                            enum_values.push(s.to_string());
                        }
                    }
                }

                let prop_type = if let Some(t) = f_val.get("type").and_then(|t| t.as_str()) {
                    t.to_string()
                } else if f_val.get("ref").is_some()
                    || f_val.get("fields").is_some()
                    || f_val.get("properties").is_some()
                    || name == "metadata"
                    || name == "spec"
                    || name == "status"
                {
                    "object".to_string()
                } else {
                    "string".to_string()
                };

                properties.push(SchemaProperty {
                    name: name.clone(),
                    prop_type,
                    required: is_required,
                    description: f_val
                        .get("description")
                        .and_then(|d| d.as_str())
                        .unwrap_or("")
                        .to_string(),
                    enum_values,
                });
            }
        }

        super::nested::append_nested_properties(val, &raw, &mut properties);
        schemas.push(NativeSchema {
            kind: kind.clone(),
            api_version,
            properties,
        });
    }
    schemas.sort_by(|a, b| a.kind.cmp(&b.kind).then(a.api_version.cmp(&b.api_version)));
    schemas
}
