//! Kubernetes In-Cluster Admission Webhook Controller.
//!
//! Why: Intercepts Kubernetes API server `AdmissionReview` requests and returns
//! RFC 6902 JSONPatch mutations to auto-heal manifests during cluster admission. Strictly < 500 lines.

use crate::cli::heal_cmd::heal_manifest_string;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Debug, Serialize, Deserialize)]
pub struct AdmissionReviewRequest {
    #[serde(rename = "apiVersion")]
    pub api_version: String,
    pub kind: String,
    pub request: Option<AdmissionRequest>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AdmissionRequest {
    pub uid: String,
    pub object: Option<Value>,
    pub operation: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AdmissionReviewResponse {
    #[serde(rename = "apiVersion")]
    pub api_version: String,
    pub kind: String,
    pub response: AdmissionResponse,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AdmissionResponse {
    pub uid: String,
    pub allowed: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub patch: Option<String>,
    #[serde(rename = "patchType", skip_serializing_if = "Option::is_none")]
    pub patch_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<Value>,
}

/// Evaluates an AdmissionReview JSON request and generates an auto-healed AdmissionReview response.
pub fn handle_admission_review(input_json: &str) -> Result<String, String> {
    let review: AdmissionReviewRequest = serde_json::from_str(input_json)
        .map_err(|e| format!("Invalid AdmissionReview payload: {}", e))?;

    if review.api_version != "admission.k8s.io/v1" || review.kind != "AdmissionReview" {
        return Err("Expected apiVersion admission.k8s.io/v1 and kind AdmissionReview".to_string());
    }

    let req = match review.request {
        Some(r) => r,
        None => return Err("Missing request payload in AdmissionReview".to_string()),
    };

    if req.uid.trim().is_empty() {
        return Err("AdmissionReview request UID must not be empty".to_string());
    }

    match req.operation.as_str() {
        "DELETE" => {
            let resp = AdmissionReviewResponse {
                api_version: review.api_version,
                kind: review.kind,
                response: AdmissionResponse {
                    uid: req.uid,
                    allowed: true,
                    patch: None,
                    patch_type: None,
                    status: None,
                },
            };
            return serde_json::to_string(&resp).map_err(|e| e.to_string());
        }
        "CREATE" | "UPDATE" => {}
        operation => {
            return Err(format!(
                "Unsupported AdmissionReview operation '{}'",
                operation
            ));
        }
    }

    let obj = req
        .object
        .ok_or_else(|| "AdmissionReview request object is required for mutation".to_string())?;

    if !obj.is_object() {
        return Err("AdmissionReview request object must be a JSON object".to_string());
    }

    // Serialize object to YAML for Yamlr healing.
    let yaml_str = serde_yaml::to_string(&obj).map_err(|e| e.to_string())?;
    let (healed_yaml, _) = heal_manifest_string(&yaml_str);
    let healed_json: Value = serde_yaml::from_str(&healed_yaml).map_err(|e| e.to_string())?;
    if !healed_json.is_object() {
        return Err("Healer returned a non-object manifest; refusing admission patch".to_string());
    }
    let patch_json = generate_json_patch(&obj, &healed_json);
    let has_patch = patch_json.is_some();

    let response = AdmissionResponse {
        uid: req.uid,
        allowed: true,
        patch: patch_json.map(|p| base64_encode(p.as_bytes())),
        patch_type: if has_patch {
            Some("JSONPatch".to_string())
        } else {
            None
        },
        status: None,
    };

    let review_resp = AdmissionReviewResponse {
        api_version: review.api_version,
        kind: review.kind,
        response,
    };

    serde_json::to_string(&review_resp).map_err(|e| e.to_string())
}

fn generate_json_patch(original: &Value, modified: &Value) -> Option<String> {
    if original == modified || !original.is_object() || !modified.is_object() {
        return None;
    }

    // Replacing the AdmissionReview object root is a single valid RFC 6902
    // operation and safely covers nested additions, removals, arrays, and keys
    // that need JSON Pointer escaping.
    serde_json::to_string(&json!([{"op": "replace", "path": "", "value": modified}])).ok()
}

fn base64_encode(bytes: &[u8]) -> String {
    const STANDARD: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    let mut i = 0;
    while i < bytes.len() {
        let b0 = bytes[i];
        let b1 = if i + 1 < bytes.len() { bytes[i + 1] } else { 0 };
        let b2 = if i + 2 < bytes.len() { bytes[i + 2] } else { 0 };

        out.push(STANDARD[(b0 >> 2) as usize] as char);
        out.push(STANDARD[(((b0 & 3) << 4) | (b1 >> 4)) as usize] as char);
        if i + 1 < bytes.len() {
            out.push(STANDARD[(((b1 & 15) << 2) | (b2 >> 6)) as usize] as char);
        } else {
            out.push('=');
        }
        if i + 2 < bytes.len() {
            out.push(STANDARD[(b2 & 63) as usize] as char);
        } else {
            out.push('=');
        }
        i += 3;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn response_preserves_review_metadata_and_emits_applicable_patch() {
        let req_json = json!({
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "request": {
                "uid": "705ab4f5-6393-11e8-b7cc-42010a800002",
                "operation": "CREATE",
                "object": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": { "name": "my-app" },
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{
                                    "name": "web",
                                    "image": "nginx"
                                }]
                            }
                        }
                    }
                }
            }
        })
        .to_string();

        let resp_json = handle_admission_review(&req_json).unwrap();
        let response: Value = serde_json::from_str(&resp_json).unwrap();
        assert_eq!(response["apiVersion"], "admission.k8s.io/v1");
        assert_eq!(response["kind"], "AdmissionReview");
        assert_eq!(
            response["response"]["uid"],
            "705ab4f5-6393-11e8-b7cc-42010a800002"
        );
        assert_eq!(response["response"]["allowed"], true);
        assert!(response["response"]["patch"].is_string());

        if let Some(encoded_patch) = response["response"]["patch"].as_str() {
            assert_eq!(response["response"]["patchType"], "JSONPatch");
            let request: Value = serde_json::from_str(&req_json).unwrap();
            let original = request["request"]["object"].clone();
            let yaml = serde_yaml::to_string(&original).unwrap();
            let (healed, _) = heal_manifest_string(&yaml);
            let modified: Value = serde_yaml::from_str(&healed).unwrap();
            let expected_patch = generate_json_patch(&original, &modified).unwrap();
            assert_eq!(encoded_patch, base64_encode(expected_patch.as_bytes()));
            let patch: Value = serde_json::from_str(&expected_patch).unwrap();
            assert_eq!(patch[0]["op"], "replace");
            assert_eq!(patch[0]["path"], "");
            assert_eq!(patch[0]["value"], modified);
        } else {
            assert!(response["response"].get("patchType").is_none());
        }
    }

    #[test]
    fn invalid_review_envelopes_and_missing_uid_are_rejected() {
        let cases = [
            json!({"apiVersion":"v1","kind":"AdmissionReview","request":{"uid":"u","object":{}}}),
            json!({"apiVersion":"admission.k8s.io/v1","kind":"Other","request":{"uid":"u","object":{}}}),
            json!({"apiVersion":"admission.k8s.io/v1","kind":"AdmissionReview","request":{"uid":"","object":{}}}),
            json!({"apiVersion":"admission.k8s.io/v1","kind":"AdmissionReview"}),
            json!({"apiVersion":"admission.k8s.io/v1","kind":"AdmissionReview","request":{"uid":"u","object":[]} }),
        ];
        for request in cases {
            assert!(handle_admission_review(&request.to_string()).is_err());
        }
        assert!(handle_admission_review("not json").is_err());
    }

    #[test]
    fn json_patch_handles_deletions_and_nested_changes_by_replacing_the_root() {
        let original = json!({"metadata":{"labels":{"old":"value"}},"spec":{"items":[1]}});
        let modified = json!({"metadata":{"labels":{"new":"value"}},"spec":{"items":[1,2]}});
        let patch = generate_json_patch(&original, &modified).unwrap();
        let patch: Value = serde_json::from_str(&patch).unwrap();
        assert_eq!(patch.as_array().unwrap().len(), 1);
        assert_eq!(patch[0]["op"], "replace");
        assert_eq!(patch[0]["path"], "");
        assert_eq!(patch[0]["value"], modified);
        assert!(generate_json_patch(&original, &original).is_none());
    }

    #[test]
    fn base64_encoder_matches_standard_vectors() {
        assert_eq!(base64_encode(b"Man"), "TWFu");
        assert_eq!(base64_encode(b"Ma"), "TWE=");
        assert_eq!(base64_encode(b"M"), "TQ==");
    }
}
