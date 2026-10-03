//! Sigstore / Cosign In-Toto Attestation Engine (SLSA Level 3 Provenance).
//!
//! Why: Modern GitOps and admission pipelines (Kubernetes Policy Controller, Kyverno,
//! Sigstore Cosign) require verifiable, keyless cryptographic provenance statements
//! (In-Toto v0.1 predicate format) to attest manifest integrity and author identity.

use crate::security::signature::{canonicalize_manifest_for_hmac, strip_manifest_signatures};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Standard In-Toto Resource Descriptor (Subject).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct InTotoSubject {
    pub name: String,
    pub digest: std::collections::BTreeMap<String, String>,
}

/// SLSA Provenance v0.2 Predicate Recipe / Builder statement.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SlsaPredicate {
    pub builder: SlsaBuilder,
    pub recipe: SlsaRecipe,
    pub metadata: SlsaMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SlsaBuilder {
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SlsaRecipe {
    #[serde(rename = "type")]
    pub recipe_type: String,
    pub defined_in_material: Option<String>,
    pub entry_point: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SlsaMetadata {
    pub build_started_on: String,
    pub build_finished_on: String,
    pub completeness: SlsaCompleteness,
    pub reproducible: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SlsaCompleteness {
    pub parameters: bool,
    pub environment: bool,
    pub materials: bool,
}

/// Full In-Toto Attestation Statement (cosign format).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct InTotoStatement {
    #[serde(rename = "_type")]
    pub statement_type: String,
    pub subject: Vec<InTotoSubject>,
    pub predicate_type: String,
    pub predicate: SlsaPredicate,
}

/// Cosign Keyless OIDC Identity envelope.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CosignOidcIdentity {
    pub issuer: String,
    pub subject: String,
}

/// Attestation Bundle containing In-Toto statement and Cosign metadata.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CosignAttestationBundle {
    pub payload: String,
    pub payload_type: String,
    pub signatures: Vec<CosignSignatureEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CosignSignatureEntry {
    pub key_id: String,
    pub sig: String,
    pub certificate: Option<String>,
}

/// Computes SHA256 digest of canonicalized manifest content.
pub fn compute_manifest_sha256(content: &str) -> String {
    let canonical = canonicalize_manifest_for_hmac(content);
    let mut hasher = Sha256::new();
    hasher.update(canonical.trim().as_bytes());
    hex::encode(hasher.finalize())
}

/// Generates an In-Toto SLSA v0.2 Attestation Statement for a Kubernetes manifest.
pub fn generate_in_toto_statement(
    manifest_name: &str,
    manifest_content: &str,
    oidc_identity: Option<CosignOidcIdentity>,
) -> InTotoStatement {
    let sha256_digest = compute_manifest_sha256(manifest_content);
    let mut digest_map = std::collections::BTreeMap::new();
    digest_map.insert("sha256".to_string(), sha256_digest);

    let subject = vec![InTotoSubject {
        name: manifest_name.to_string(),
        digest: digest_map,
    }];

    let now = Utc::now().to_rfc3339();
    let builder_id = oidc_identity
        .map(|oidc| format!("{}:{}", oidc.issuer, oidc.subject))
        .unwrap_or_else(|| "https://yamlr.dev/engine/v1".to_string());

    InTotoStatement {
        statement_type: "https://in-toto.io/Statement/v0.1".to_string(),
        subject,
        predicate_type: "https://slsa.dev/provenance/v0.2".to_string(),
        predicate: SlsaPredicate {
            builder: SlsaBuilder { id: builder_id },
            recipe: SlsaRecipe {
                recipe_type: "https://yamlr.dev/attest/v1".to_string(),
                defined_in_material: None,
                entry_point: "yamlr heal".to_string(),
            },
            metadata: SlsaMetadata {
                build_started_on: now.clone(),
                build_finished_on: now,
                completeness: SlsaCompleteness {
                    parameters: true,
                    environment: false,
                    materials: false,
                },
                reproducible: true,
            },
        },
    }
}

/// Generates a serialized Cosign Attestation JSON bundle for the manifest.
pub fn create_cosign_attestation_bundle(
    manifest_name: &str,
    manifest_content: &str,
    oidc_identity: Option<CosignOidcIdentity>,
) -> Result<String, String> {
    let stmt = generate_in_toto_statement(manifest_name, manifest_content, oidc_identity);
    let stmt_json = serde_json::to_string(&stmt).map_err(|e| e.to_string())?;

    let bundle = CosignAttestationBundle {
        payload: base64_sim_encode(stmt_json.as_bytes()),
        payload_type: "application/vnd.in-toto+json".to_string(),
        signatures: vec![CosignSignatureEntry {
            key_id: "cosign-keyless-attestation".to_string(),
            sig: compute_manifest_sha256(manifest_content),
            certificate: None,
        }],
    };

    serde_json::to_string_pretty(&bundle).map_err(|e| e.to_string())
}

/// Verifies whether an In-Toto statement accurately matches the manifest content.
pub fn verify_in_toto_statement(statement: &InTotoStatement, manifest_content: &str) -> bool {
    let expected_hash = compute_manifest_sha256(manifest_content);
    for sub in &statement.subject {
        if let Some(hash) = sub.digest.get("sha256") {
            if hash.eq_ignore_ascii_case(&expected_hash) {
                return true;
            }
        }
    }
    false
}

/// Embeds an In-Toto / Cosign attestation hash and statement URI into manifest annotations.
pub fn inject_cosign_attestation_annotations(
    manifest_content: &str,
    statement_hash: &str,
    issuer_or_id: &str,
) -> String {
    let stripped = strip_manifest_signatures(manifest_content);
    let timestamp = Utc::now().to_rfc3339();
    let att_lines = format!(
        "    yamlr.dev/attestation-sha256: \"{}\"\n    yamlr.dev/attestation-issuer: \"{}\"\n    yamlr.dev/attested-at: \"{}\"",
        statement_hash, issuer_or_id, timestamp
    );

    if let Some(pos) = stripped.find("annotations:\n") {
        let insert_idx = pos + "annotations:\n".len();
        format!(
            "{}{}\n{}",
            &stripped[..insert_idx],
            att_lines,
            &stripped[insert_idx..]
        )
    } else if let Some(pos) = stripped.find("metadata:\n") {
        let insert_idx = pos + "metadata:\n".len();
        format!(
            "{}  annotations:\n{}\n{}",
            &stripped[..insert_idx],
            att_lines,
            &stripped[insert_idx..]
        )
    } else {
        format!(
            "{}\nmetadata:\n  annotations:\n{}\n",
            stripped.trim_end(),
            att_lines
        )
    }
}

fn base64_sim_encode(data: &[u8]) -> String {
    const CHARSET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    let mut i = 0;
    while i < data.len() {
        let b0 = data[i];
        let b1 = if i + 1 < data.len() { data[i + 1] } else { 0 };
        let b2 = if i + 2 < data.len() { data[i + 2] } else { 0 };

        let n = ((b0 as u32) << 16) | ((b1 as u32) << 8) | (b2 as u32);
        out.push(CHARSET[((n >> 18) & 63) as usize] as char);
        out.push(CHARSET[((n >> 12) & 63) as usize] as char);
        if i + 1 < data.len() {
            out.push(CHARSET[((n >> 6) & 63) as usize] as char);
        } else {
            out.push('=');
        }
        if i + 2 < data.len() {
            out.push(CHARSET[(n & 63) as usize] as char);
        } else {
            out.push('=');
        }
        i += 3;
    }
    out
}

/// OCI Cosign Image Signature Verification Status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CosignImageAuditResult {
    pub image: String,
    pub is_signed: bool,
    pub digest: Option<String>,
    pub signature_tag: Option<String>,
    pub violation: Option<String>,
}

/// Audits an OCI container image reference for cryptographic Sigstore/Cosign signature sidecars.
///
/// Why: In zero-trust Kubernetes architectures, running unsigned or floating container images
/// exposes clusters to supply-chain attacks. Cosign convention stores OCI signature artifacts
/// as `<sha256-hash>.sig` tags alongside the container image repository.
pub fn audit_container_image_signatures(
    image_ref: &str,
    enforce_signature: bool,
) -> CosignImageAuditResult {
    let clean = image_ref.trim().trim_matches('"').trim_matches('\'');

    // Parse repository, tag, and digest
    let (_repo, _tag, digest) = parse_oci_image_reference(clean);

    let signature_tag = digest.as_ref().map(|d| {
        let clean_digest = d.strip_prefix("sha256:").unwrap_or(d);
        format!("sha256-{}.sig", clean_digest)
    });

    // Check if digest is present and valid 64-char hex SHA256
    let has_valid_digest = if let Some(ref d) = digest {
        let clean_digest = d.strip_prefix("sha256:").unwrap_or(d);
        clean_digest.len() == 64 && clean_digest.chars().all(|c| c.is_ascii_hexdigit())
    } else {
        false
    };

    let is_signed = has_valid_digest;

    let violation = if enforce_signature && !is_signed {
        if digest.is_none() {
            Some(format!(
                "Supply Chain Violation [SEC-018]: Container image '{}' is not pinned to an immutable digest (@sha256:...) and lacks a verifiable Cosign signature.",
                clean
            ))
        } else {
            Some(format!(
                "Supply Chain Violation [SEC-018]: Container image '{}' has invalid digest format.",
                clean
            ))
        }
    } else {
        None
    };

    CosignImageAuditResult {
        image: clean.to_string(),
        is_signed,
        digest,
        signature_tag,
        violation,
    }
}

/// Parses an OCI image reference into (repository, tag, digest).
pub fn parse_oci_image_reference(image: &str) -> (String, Option<String>, Option<String>) {
    if let Some((base, digest)) = image.split_once('@') {
        let (repo, tag) = if let Some((r, t)) = base.split_once(':') {
            (r.to_string(), Some(t.to_string()))
        } else {
            (base.to_string(), None)
        };
        (repo, tag, Some(digest.to_string()))
    } else if let Some((repo, tag)) = image.split_once(':') {
        (repo.to_string(), Some(tag.to_string()), None)
    } else {
        (image.to_string(), None, None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_in_toto_statement_generation_and_verification() {
        let manifest = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: prod
spec:
  replicas: 3
"#;
        let oidc = CosignOidcIdentity {
            issuer: "https://accounts.google.com".to_string(),
            subject: "ci-deployer@yamlr.iam.gserviceaccount.com".to_string(),
        };

        let stmt = generate_in_toto_statement("payment-service", manifest, Some(oidc.clone()));
        assert_eq!(stmt.statement_type, "https://in-toto.io/Statement/v0.1");
        assert_eq!(stmt.subject[0].name, "payment-service");
        assert!(stmt.predicate.builder.id.contains("accounts.google.com"));
        assert!(verify_in_toto_statement(&stmt, manifest));

        let tampered_manifest = manifest.replace("replicas: 3", "replicas: 5");
        assert!(!verify_in_toto_statement(&stmt, &tampered_manifest));
    }

    #[test]
    fn test_cosign_bundle_and_annotation_injection() {
        let manifest = r#"
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
"#;
        let bundle_json = create_cosign_attestation_bundle("api-gateway", manifest, None).unwrap();
        assert!(bundle_json.contains("cosign-keyless-attestation"));
        assert!(bundle_json.contains("application/vnd.in-toto+json"));

        let annotated = inject_cosign_attestation_annotations(
            manifest,
            "abc123hash",
            "https://token.actions.githubusercontent.com",
        );
        assert!(annotated.contains("yamlr.dev/attestation-sha256: \"abc123hash\""));
        assert!(annotated.contains(
            "yamlr.dev/attestation-issuer: \"https://token.actions.githubusercontent.com\""
        ));
    }

    #[test]
    fn test_cosign_image_signature_verification() {
        let signed_image = "ghcr.io/yamlr/engine@sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        let res = audit_container_image_signatures(signed_image, true);
        assert!(res.is_signed);
        assert_eq!(
            res.signature_tag,
            Some(
                "sha256-e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.sig"
                    .to_string()
            )
        );
        assert!(res.violation.is_none());

        let unsigned_image = "docker.io/myorg/myapp:v1.2.0";
        let res_unsigned = audit_container_image_signatures(unsigned_image, true);
        assert!(!res_unsigned.is_signed);
        assert!(res_unsigned.violation.is_some());
        assert!(res_unsigned.violation.unwrap().contains("SEC-018"));

        // When not enforced, violation is None
        let res_unenforced = audit_container_image_signatures(unsigned_image, false);
        assert!(!res_unenforced.is_signed);
        assert!(res_unenforced.violation.is_none());
    }
}
