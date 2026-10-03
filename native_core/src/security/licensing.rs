//! Tiered licensing and hardware fingerprinting.
//!
//! Why: Verifies portable developer licenses and organization grants. Active
//! tokens are stored in the platform credential manager, with legacy config-file
//! tokens migrated on first access.

use std::fs;
use std::process::Command;
use std::sync::OnceLock;

use hex;
#[cfg(not(target_arch = "wasm32"))]
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

static CACHED_MID: OnceLock<String> = OnceLock::new();
const LICENSE_ISSUER: &str = "yamlr-entitlement";
const LICENSE_AUDIENCE: &str = "yamlr";

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: usize,
    pub tier: String,
}

/// Claims required for a signed Yamlr paid entitlement JWT.
///
/// This remains separate from `Claims`, which is also used for legacy manifest
/// signatures and intentionally has a different payload contract.
#[derive(Debug, Serialize, Deserialize)]
struct LicenseClaims {
    pub license_version: u32,
    pub sub: String,
    pub exp: usize,
    pub iat: usize,
    pub tier: String,
    pub iss: String,
    pub aud: String,
    #[serde(default)]
    pub email: Option<String>,
    #[serde(default)]
    pub org_id: Option<String>,
    #[serde(default)]
    pub seats: Option<u32>,
    #[serde(default)]
    pub org_seats: Option<u32>,
    #[serde(default)]
    pub nodes: Option<u32>,
    #[serde(default)]
    pub machine_id: Option<String>,
}

impl LicenseClaims {
    fn is_valid_entitlement(&self) -> bool {
        if self.license_version != 1
            || self.sub.trim().is_empty()
            || self.iss != LICENSE_ISSUER
            || self.aud != LICENSE_AUDIENCE
            || self.exp <= self.iat
            || self.machine_id.is_some()
        {
            return false;
        }

        match self.tier.trim().to_ascii_lowercase().as_str() {
            "team" => {
                self.org_id
                    .as_deref()
                    .is_some_and(|id| !id.trim().is_empty())
                    && self.email.as_deref().is_some_and(|email| {
                        let email = email.trim();
                        email.split_once('@').is_some_and(|(local, domain)| {
                            !local.is_empty()
                                && domain.contains('.')
                                && !email.chars().any(char::is_whitespace)
                                && self.sub.eq_ignore_ascii_case(email)
                        })
                    })
                    && self.seats == Some(1)
                    && self.org_seats.is_some_and(|count| count > 0)
                    && self.nodes.is_none()
            }
            "enterprise" => {
                let org_id = self.org_id.as_deref().unwrap_or_default();
                !org_id.trim().is_empty()
                    && self.sub == org_id
                    && self.seats.map_or(true, |count| count > 0)
                    && self.nodes.map_or(true, |count| count > 0)
                    && (self.seats.is_some_and(|count| count > 0)
                        || self.nodes.is_some_and(|count| count > 0))
            }
            _ => false,
        }
    }
}

/// Derives a cross-platform hardware fingerprint for node-bound licensing.
#[no_mangle]
pub fn native_get_machine_id() -> String {
    CACHED_MID
        .get_or_init(|| {
            let mut signals = Vec::new();

            if cfg!(target_os = "windows") {
                if let Some(id) = get_win_hw_id("cpu", "processorid") {
                    signals.push(id);
                }
                if let Some(id) = get_win_hw_id("baseboard", "serialnumber") {
                    signals.push(id);
                }
                if let Some(id) = get_win_hw_id("diskdrive", "serialnumber") {
                    signals.push(id);
                }
            } else if cfg!(target_os = "linux") {
                if let Ok(id) = fs::read_to_string("/sys/class/dmi/id/product_uuid") {
                    signals.push(id.trim().to_string());
                }
                if let Ok(id) = fs::read_to_string("/etc/machine-id") {
                    signals.push(id.trim().to_string());
                }
            } else if cfg!(target_os = "macos") {
                if let Some(id) = get_mac_hw_id() {
                    signals.push(id);
                }
            }

            if signals.len() < 2 {
                return get_install_bound_id();
            }

            let mut hasher = Sha256::new();
            for s in signals {
                hasher.update(s.as_bytes());
            }
            hex::encode(hasher.finalize())
        })
        .clone()
}

fn get_win_hw_id(component: &str, property: &str) -> Option<String> {
    // 1. Primary: Modern PowerShell CIM query (Standard on Windows 10/11/Server)
    let ps_cmd = match component {
        "cpu" => "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty ProcessorId",
        "baseboard" => {
            "Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"
        }
        "diskdrive" => {
            "Get-CimInstance Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"
        }
        _ => "",
    };

    if !ps_cmd.is_empty() {
        if let Ok(output) = Command::new("powershell")
            .args(&["-NoProfile", "-NonInteractive", "-Command", ps_cmd])
            .output()
        {
            let val = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !val.is_empty() {
                return Some(val);
            }
        }
    }

    // 2. Legacy fallback for older Windows environments where wmic remains present
    let output = Command::new("wmic")
        .args(&[component, "get", property])
        .output();

    if let Ok(out) = output {
        let out_str = String::from_utf8_lossy(&out.stdout);
        let lines: Vec<&str> = out_str.lines().collect();
        if lines.len() >= 2 {
            let val = lines[1].trim();
            if !val.is_empty() && val != "Node" {
                return Some(val.to_string());
            }
        }
    }

    None
}

fn get_mac_hw_id() -> Option<String> {
    let output = Command::new("ioreg")
        .args(&["-rd1", "-c", "IOPlatformExpertDevice"])
        .output()
        .ok()?;

    let out_str = String::from_utf8_lossy(&output.stdout);
    for line in out_str.lines() {
        if line.contains("IOPlatformUUID") {
            if let Some(pos) = line.find(" = \"") {
                let uuid = &line[pos + 4..line.len() - 1];
                return Some(uuid.to_string());
            }
        }
    }
    None
}

fn get_install_bound_id() -> String {
    let Some(mut path) = dirs::home_dir() else {
        let id = new_install_bound_id();
        eprintln!(
            "[WARN] Could not resolve a home directory; using a temporary machine ID that will not persist between runs."
        );
        return id;
    };
    path.push(".yamlr");
    path.push("machine.id");

    if let Ok(id) = fs::read_to_string(&path) {
        let trimmed = id.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    let new_id = new_install_bound_id();
    if let Some(parent) = path.parent() {
        if let Err(error) = fs::create_dir_all(parent) {
            eprintln!(
                "[WARN] Could not create machine ID directory '{}': {}. The machine ID will not persist between runs.",
                parent.display(),
                error
            );
            return new_id;
        }
    }
    if let Err(error) = fs::write(&path, &new_id) {
        eprintln!(
            "[WARN] Could not persist machine ID at '{}': {}. The machine ID will not persist between runs.",
            path.display(),
            error
        );
    }
    new_id
}

fn new_install_bound_id() -> String {
    format!("inst-{}", uuid::Uuid::new_v4())
}

/// Verifies the signature and required claims of a portable paid entitlement JWT.
#[cfg(not(target_arch = "wasm32"))]
pub fn native_verify_token(token: &str, pubkey: &str) -> bool {
    native_license_tier(token, pubkey).is_some()
}

#[cfg(not(target_arch = "wasm32"))]
pub fn native_license_tier(token: &str, pubkey: &str) -> Option<String> {
    let key = DecodingKey::from_rsa_pem(pubkey.as_bytes()).ok()?;
    let claims = decode::<LicenseClaims>(token, &key, &license_validation())
        .ok()?
        .claims;
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .ok()?
        .as_secs() as usize;
    if !claims.is_valid_entitlement() || claims.iat > now.saturating_add(60) {
        return None;
    }
    Some(claims.tier.to_ascii_lowercase())
}

#[cfg(not(target_arch = "wasm32"))]
fn license_validation() -> Validation {
    let mut validation = Validation::new(Algorithm::RS256);
    validation.validate_exp = true;
    validation.set_issuer(&[LICENSE_ISSUER]);
    validation.set_audience(&[LICENSE_AUDIENCE]);
    validation.required_spec_claims = ["exp", "iat", "iss", "aud", "sub", "tier"]
        .iter()
        .map(|claim| (*claim).to_string())
        .collect();
    validation
}

#[cfg(target_arch = "wasm32")]
pub fn native_verify_token(_token: &str, _pubkey: &str) -> bool {
    false
}

#[cfg(target_arch = "wasm32")]
pub fn native_license_tier(_token: &str, _pubkey: &str) -> Option<String> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};

    const TEST_PRIVATE_KEY: &str = include_str!("../../tests/fixtures/licensing_test_private.pem");
    const TEST_PUBLIC_KEY: &str = include_str!("../../tests/fixtures/licensing_test_public.pem");

    fn valid_license_claims() -> LicenseClaims {
        LicenseClaims {
            license_version: 1,
            sub: "developer@example.test".to_string(),
            exp: (chrono::Utc::now().timestamp() + 3600) as usize,
            iat: chrono::Utc::now().timestamp() as usize,
            tier: "TEAM".to_string(),
            iss: LICENSE_ISSUER.to_string(),
            aud: LICENSE_AUDIENCE.to_string(),
            email: Some("developer@example.test".to_string()),
            org_id: Some("org-123".to_string()),
            seats: Some(1),
            org_seats: Some(5),
            nodes: None,
            machine_id: None,
        }
    }

    #[test]
    fn accepts_named_team_seat_across_machine_changes() {
        let mut claims = valid_license_claims();
        assert!(claims.is_valid_entitlement());
        claims.machine_id = None;
        assert!(claims.is_valid_entitlement());
    }

    #[test]
    fn accepts_enterprise_organization_grants_with_contracted_limits() {
        let mut claims = valid_license_claims();
        claims.tier = "enterprise".to_string();
        claims.sub = "org-123".to_string();
        claims.seats = Some(25);
        claims.org_seats = None;
        claims.nodes = Some(10);
        assert!(claims.is_valid_entitlement());

        claims.seats = None;
        claims.org_seats = None;
        assert!(claims.is_valid_entitlement());
    }

    #[test]
    fn rejects_invalid_subject_issuer_audience_and_hardware_binding() {
        let mut claims = valid_license_claims();
        claims.machine_id = Some("machine-123".to_string());
        assert!(!claims.is_valid_entitlement());

        claims = valid_license_claims();
        claims.sub.clear();
        assert!(!claims.is_valid_entitlement());

        claims = valid_license_claims();
        claims.email = Some("another@example.test".to_string());
        assert!(!claims.is_valid_entitlement());

        claims = valid_license_claims();
        claims.iss = "untrusted-issuer".to_string();
        assert!(!claims.is_valid_entitlement());

        claims = valid_license_claims();
        claims.aud = "another-product".to_string();
        assert!(!claims.is_valid_entitlement());
    }

    #[test]
    fn rejects_free_and_unknown_tiers() {
        let mut claims = valid_license_claims();
        claims.tier = "free".to_string();
        assert!(!claims.is_valid_entitlement());

        claims.tier = "unrecognized".to_string();
        assert!(!claims.is_valid_entitlement());

        claims.tier = "pro".to_string();
        assert!(!claims.is_valid_entitlement());
    }

    #[test]
    fn team_requires_named_developer_and_exactly_one_seat() {
        let mut claims = valid_license_claims();
        claims.seats = None;
        assert!(!claims.is_valid_entitlement());
        claims.seats = Some(2);
        assert!(!claims.is_valid_entitlement());
        claims.seats = Some(1);
        claims.org_seats = Some(5);
        claims.org_id = None;
        assert!(!claims.is_valid_entitlement());
        claims.org_id = Some("org-123".to_string());
        claims.org_seats = Some(0);
        assert!(!claims.is_valid_entitlement());
    }

    #[test]
    fn enterprise_requires_organization_subject_and_positive_contract_limit() {
        let mut claims = valid_license_claims();
        claims.tier = "enterprise".to_string();
        claims.sub = "org-123".to_string();
        claims.seats = None;
        claims.nodes = None;
        assert!(!claims.is_valid_entitlement());
        claims.nodes = Some(0);
        assert!(!claims.is_valid_entitlement());
        claims.nodes = Some(3);
        claims.seats = Some(0);
        assert!(!claims.is_valid_entitlement());
        claims.seats = None;
        claims.sub = "other-org".to_string();
        assert!(!claims.is_valid_entitlement());
    }

    #[test]
    fn required_common_claims_cannot_be_omitted() {
        let token_payload = serde_json::json!({
            "sub": "developer@example.test",
            "exp": usize::MAX,
            "iss": LICENSE_ISSUER,
            "aud": LICENSE_AUDIENCE
        });

        assert!(serde_json::from_value::<LicenseClaims>(token_payload).is_err());
    }

    #[test]
    fn validation_requires_canonical_issuer_audience_and_expiry() {
        let validation = license_validation();

        assert_eq!(validation.algorithms, vec![Algorithm::RS256]);
        assert!(validation.validate_exp);
        assert!(validation.iss.as_ref().unwrap().contains(LICENSE_ISSUER));
        assert!(validation.aud.as_ref().unwrap().contains(LICENSE_AUDIENCE));
        for required in ["exp", "iat", "iss", "aud", "sub", "tier"] {
            assert!(validation.required_spec_claims.contains(required));
        }
    }

    #[test]
    fn rejects_missing_or_future_issued_at_claims() {
        let key = EncodingKey::from_rsa_pem(TEST_PRIVATE_KEY.as_bytes()).unwrap();

        let mut missing_iat = serde_json::to_value(valid_license_claims()).unwrap();
        missing_iat.as_object_mut().unwrap().remove("iat");
        let token_without_iat = encode(&Header::new(Algorithm::RS256), &missing_iat, &key).unwrap();
        assert!(!native_verify_token(&token_without_iat, TEST_PUBLIC_KEY));

        let future_claims = LicenseClaims {
            iat: chrono::Utc::now().timestamp() as usize + 120,
            ..valid_license_claims()
        };
        let token_with_future_iat =
            encode(&Header::new(Algorithm::RS256), &future_claims, &key).unwrap();
        assert!(!native_verify_token(
            &token_with_future_iat,
            TEST_PUBLIC_KEY
        ));

        let claims_with_exp_before_iat = LicenseClaims {
            exp: 1,
            iat: 2,
            ..valid_license_claims()
        };
        assert!(!claims_with_exp_before_iat.is_valid_entitlement());
    }

    #[test]
    fn verifies_signed_portable_team_license() {
        let token = encode(
            &Header::new(Algorithm::RS256),
            &valid_license_claims(),
            &EncodingKey::from_rsa_pem(TEST_PRIVATE_KEY.as_bytes()).unwrap(),
        )
        .unwrap();

        assert_eq!(
            native_license_tier(&token, TEST_PUBLIC_KEY).as_deref(),
            Some("team")
        );
    }

    #[test]
    fn rejects_expired_or_noncanonical_signed_licenses() {
        let key = EncodingKey::from_rsa_pem(TEST_PRIVATE_KEY.as_bytes()).unwrap();
        let expired_claims = LicenseClaims {
            exp: 1,
            ..valid_license_claims()
        };
        let expired_token = encode(&Header::new(Algorithm::RS256), &expired_claims, &key).unwrap();
        assert!(!native_verify_token(&expired_token, TEST_PUBLIC_KEY));

        let mut free_claims = valid_license_claims();
        free_claims.tier = "free".to_string();
        let free_token = encode(&Header::new(Algorithm::RS256), &free_claims, &key).unwrap();
        assert!(!native_verify_token(&free_token, TEST_PUBLIC_KEY));

        let mut wrong_issuer_claims = valid_license_claims();
        wrong_issuer_claims.iss = "another-issuer".to_string();
        let wrong_issuer_token =
            encode(&Header::new(Algorithm::RS256), &wrong_issuer_claims, &key).unwrap();
        assert!(!native_verify_token(&wrong_issuer_token, TEST_PUBLIC_KEY));

        let mut wrong_audience_claims = valid_license_claims();
        wrong_audience_claims.aud = "another-product".to_string();
        let wrong_audience_token =
            encode(&Header::new(Algorithm::RS256), &wrong_audience_claims, &key).unwrap();
        assert!(!native_verify_token(&wrong_audience_token, TEST_PUBLIC_KEY));

        let hmac_token = encode(
            &Header::new(Algorithm::HS256),
            &valid_license_claims(),
            &EncodingKey::from_secret(b"test-only-hmac-key"),
        )
        .unwrap();
        assert!(!native_verify_token(&hmac_token, TEST_PUBLIC_KEY));
    }
}
