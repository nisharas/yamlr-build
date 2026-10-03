//! Online renewal for portable Team entitlements.
//!
//! Team JWTs grant local access for at most 24 hours. Renewal is an explicit
//! opt-in; Enterprise offline grants remain independent of the network.

#[cfg(test)]
use std::fs;
use std::time::Duration;

use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde_json::Value;

#[cfg(test)]
use super::entitlements::activate_license_at;
use super::entitlements::{activate_license, stored_license_token};
use super::licensing::{native_license_tier, native_verify_token};

const RENEWAL_WINDOW_SECONDS: u64 = 12 * 60 * 60;
const DEFAULT_GATEWAY: &str = "https://gateway.yamlr.dev";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RenewalOutcome {
    Disabled,
    NotTeam,
    NotDue,
    Renewed,
}

fn auto_renew_enabled(value: Option<&str>) -> bool {
    value.is_some_and(|value| {
        matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        )
    })
}

pub fn should_renew_at(expiry: u64, now: u64) -> bool {
    expiry <= now.saturating_add(RENEWAL_WINDOW_SECONDS)
}

fn gateway_url(configured: Option<&str>) -> Result<String, String> {
    let base = configured
        .unwrap_or(DEFAULT_GATEWAY)
        .trim()
        .trim_end_matches('/');
    if !base.starts_with("https://")
        || base.len() <= "https://".len()
        || base.chars().any(char::is_whitespace)
    {
        return Err("The configured Yamlr licensing gateway must be an HTTPS URL.".to_string());
    }
    Ok(format!("{base}/v1/auth/renew"))
}

fn post_renewal(url: &str, token: &str) -> Result<String, String> {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(8))
        .build();
    let response = agent
        .post(url)
        .send_json(&serde_json::json!({ "token": token }))
        .map_err(|error| match error {
            ureq::Error::Status(status, _) => {
                format!("Team entitlement renewal was rejected (HTTP {status}).")
            }
            _ => "Cannot reach the Yamlr licensing service to renew the Team entitlement."
                .to_string(),
        })?;
    let body: Value = response
        .into_json()
        .map_err(|_| "The licensing service returned an invalid renewal response.".to_string())?;
    body.get("token")
        .and_then(Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| "The licensing service did not return a renewed entitlement.".to_string())
}

pub fn renew_team_access_if_due(public_key: &str) -> Result<RenewalOutcome, String> {
    if !auto_renew_enabled(std::env::var("YAMLR_LICENSE_AUTO_RENEW").ok().as_deref()) {
        return Ok(RenewalOutcome::Disabled);
    }
    let Some(token) = stored_license_token(public_key)? else {
        return Ok(RenewalOutcome::NotTeam);
    };
    let (outcome, renewed) = renew_team_token_at(
        public_key,
        &token,
        std::env::var("YAMLR_LICENSE_GATEWAY_URL").ok().as_deref(),
        chrono::Utc::now().timestamp().max(0) as u64,
        post_renewal,
    )?;
    if let Some(token) = renewed {
        activate_license(&token, public_key)?;
    }
    Ok(outcome)
}

#[cfg(test)]
pub fn renew_team_access_at(
    public_key: &str,
    token_path: &std::path::Path,
    configured_gateway: Option<&str>,
    now: u64,
    renew: impl FnOnce(&str, &str) -> Result<String, String>,
) -> Result<RenewalOutcome, String> {
    let token = fs::read_to_string(token_path)
        .map_err(|_| "No stored Team entitlement was found.".to_string())?;
    let (outcome, renewed) =
        renew_team_token_at(public_key, &token, configured_gateway, now, renew)?;
    if let Some(token) = renewed {
        activate_license_at(&token, public_key, token_path)?;
    }
    Ok(outcome)
}

fn renew_team_token_at(
    public_key: &str,
    token: &str,
    configured_gateway: Option<&str>,
    now: u64,
    renew: impl FnOnce(&str, &str) -> Result<String, String>,
) -> Result<(RenewalOutcome, Option<String>), String> {
    let mut validation = Validation::new(Algorithm::RS256);
    validation.set_issuer(&["yamlr-entitlement"]);
    validation.set_audience(&["yamlr"]);
    validation.validate_exp = false;
    let decoding_key = DecodingKey::from_rsa_pem(public_key.as_bytes())
        .map_err(|_| "The configured Yamlr license public key is invalid.".to_string())?;
    let claims = decode::<Value>(&token, &decoding_key, &validation)
        .map_err(|_| "The stored entitlement signature is invalid.".to_string())?
        .claims;
    if claims.get("tier").and_then(Value::as_str) != Some("team") {
        return Ok((RenewalOutcome::NotTeam, None));
    }
    let expiry = claims
        .get("exp")
        .and_then(Value::as_u64)
        .ok_or_else(|| "The stored Team entitlement has no valid expiration.".to_string())?;
    if !should_renew_at(expiry, now) {
        return Ok((RenewalOutcome::NotDue, None));
    }

    let url = gateway_url(configured_gateway)?;
    let renewed = renew(&url, &token)?;
    if !native_verify_token(&renewed, public_key)
        || native_license_tier(&renewed, public_key).as_deref() != Some("team")
    {
        return Err("The licensing service returned an invalid Team entitlement.".to_string());
    }
    Ok((RenewalOutcome::Renewed, Some(renewed)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};
    use serde::Serialize;

    const PRIVATE_KEY: &str = include_str!("../../tests/fixtures/licensing_test_private.pem");
    const PUBLIC_KEY: &str = include_str!("../../tests/fixtures/licensing_test_public.pem");

    #[derive(Serialize)]
    struct TeamClaims<'a> {
        license_version: u32,
        sub: &'a str,
        email: &'a str,
        org_id: &'a str,
        tier: &'a str,
        seats: u32,
        org_seats: u32,
        iss: &'a str,
        aud: &'a str,
        iat: usize,
        exp: usize,
    }

    fn signed_token(tier: &str, exp: usize) -> String {
        let claims = TeamClaims {
            license_version: 1,
            sub: "developer@example.test",
            email: "developer@example.test",
            org_id: "org-1",
            tier,
            seats: 1,
            org_seats: 4,
            iss: "yamlr-entitlement",
            aud: "yamlr",
            iat: 1_700_000_000,
            exp,
        };
        encode(
            &Header::new(Algorithm::RS256),
            &claims,
            &EncodingKey::from_rsa_pem(PRIVATE_KEY.as_bytes()).unwrap(),
        )
        .unwrap()
    }

    #[test]
    fn renewal_window_starts_twelve_hours_before_expiry() {
        assert!(!should_renew_at(200_000, 150_000));
        assert!(should_renew_at(200_000, 156_800));
        assert!(should_renew_at(100, 200));
    }

    #[test]
    fn automatic_renewal_is_disabled_unless_explicitly_enabled() {
        for value in [
            None,
            Some(""),
            Some("0"),
            Some("false"),
            Some("off"),
            Some("no"),
        ] {
            assert!(
                !auto_renew_enabled(value),
                "enabled unexpectedly for {value:?}"
            );
        }
        for value in [Some("1"), Some("true"), Some("YES"), Some(" on ")] {
            assert!(auto_renew_enabled(value), "not enabled for {value:?}");
        }
    }

    #[test]
    fn gateway_url_requires_https_and_uses_configurable_origin() {
        assert_eq!(
            gateway_url(Some("https://licensing.example.test/")).unwrap(),
            "https://licensing.example.test/v1/auth/renew"
        );
        assert_eq!(
            gateway_url(None).unwrap(),
            "https://gateway.yamlr.dev/v1/auth/renew"
        );
        assert!(gateway_url(Some("http://gateway.example.test")).is_err());
    }

    #[test]
    fn non_team_tokens_are_never_sent_to_the_network() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("license.jwt");
        fs::write(&path, signed_token("enterprise", 2_000_000_000)).unwrap();
        let result = renew_team_access_at(PUBLIC_KEY, &path, None, 1_900_000_000, |_, _| {
            panic!("Enterprise grants must remain offline")
        })
        .unwrap();
        assert_eq!(result, RenewalOutcome::NotTeam);
    }

    #[test]
    fn team_tokens_are_renewed_only_when_due_and_persisted_after_verification() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("license.jwt");
        let token = signed_token("team", 1_900_000_000);
        fs::write(&path, &token).unwrap();
        let result = renew_team_access_at(
            PUBLIC_KEY,
            &path,
            Some("https://gateway.example.test"),
            1_800_000_000,
            |_, _| panic!("A current Team token must not be renewed early"),
        )
        .unwrap();
        assert_eq!(result, RenewalOutcome::NotDue);

        let new_token = signed_token("team", 2_000_000_000);
        let result = renew_team_access_at(
            PUBLIC_KEY,
            &path,
            Some("https://gateway.example.test"),
            1_900_000_000,
            |url, old| {
                assert_eq!(url, "https://gateway.example.test/v1/auth/renew");
                assert_eq!(old, token);
                Ok(new_token.clone())
            },
        )
        .unwrap();
        assert_eq!(result, RenewalOutcome::Renewed);
        assert_eq!(fs::read_to_string(path).unwrap(), new_token);
    }

    #[test]
    fn invalid_renewal_response_does_not_replace_the_existing_entitlement() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("license.jwt");
        let token = signed_token("team", 1_900_000_000);
        fs::write(&path, &token).unwrap();
        let result = renew_team_access_at(PUBLIC_KEY, &path, None, 1_900_000_000, |_, _| {
            Ok("bad-token".to_string())
        });
        assert!(result.is_err());
        assert_eq!(fs::read_to_string(path).unwrap(), token);
    }
}
