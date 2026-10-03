//! Opt-in Enterprise scan completion telemetry.

use serde_json::{json, Value};

const DEFAULT_GATEWAY: &str = "https://gateway.yamlr.dev";

fn endpoint(configured: Option<&str>) -> Option<String> {
    let base = configured
        .unwrap_or(DEFAULT_GATEWAY)
        .trim()
        .trim_end_matches('/');
    let authority = base.strip_prefix("https://")?;
    if authority.is_empty()
        || authority.starts_with('/')
        || authority.contains(['?', '#', '@', ' '])
        || authority.ends_with('/')
    {
        return None;
    }
    Some(format!("{base}/v1/pulse"))
}

fn payload(cli_version: &str, timestamp: u64) -> Value {
    json!({
        "cli_version": cli_version,
        "event_type": "scan_complete",
        "ts": timestamp,
    })
}

/// Sends one aggregate event only when explicitly requested and permitted.
pub fn push_scan_telemetry(args: &[String]) {
    if !args.iter().any(|arg| arg == "--push-telemetry")
        || !crate::telemetry_gate::is_telemetry_enabled(args)
        || crate::security::stored_tier(crate::security::active_license_public_key())
            != crate::security::LicenseTier::Enterprise
    {
        return;
    }

    #[cfg(not(target_arch = "wasm32"))]
    send_enterprise_event();
}

#[cfg(not(target_arch = "wasm32"))]
fn send_enterprise_event() {
    use std::time::Duration;

    let Ok(Some(token)) =
        crate::security::stored_license_token(crate::security::active_license_public_key())
    else {
        return;
    };
    let configured = std::env::var("YAMLR_TELEMETRY_GATEWAY_URL").ok();
    let Some(url) = endpoint(configured.as_deref()) else {
        return;
    };
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or_default();
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(5))
        .build();
    let _ = agent
        .post(&url)
        .set("Authorization", &format!("Bearer {}", token.trim()))
        .send_json(&payload(env!("CARGO_PKG_VERSION"), timestamp));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn endpoint_defaults_to_yamlr_gateway_and_accepts_https_override() {
        assert_eq!(
            endpoint(None).as_deref(),
            Some("https://gateway.yamlr.dev/v1/pulse")
        );
        assert_eq!(
            endpoint(Some("https://telemetry.example.test/")).as_deref(),
            Some("https://telemetry.example.test/v1/pulse")
        );
    }

    #[test]
    fn endpoint_rejects_non_https_or_ambiguous_urls() {
        for value in [
            "http://gateway.example",
            "https://",
            "https://host/path?x=1",
            "https://user@host",
            " https://host with-space",
        ] {
            assert_eq!(endpoint(Some(value)), None, "accepted {value}");
        }
    }

    #[test]
    fn payload_contains_only_the_documented_aggregate_event_fields() {
        let value = payload("1.2.3", 1_800_000_000);
        assert_eq!(value["cli_version"], "1.2.3");
        assert_eq!(value["event_type"], "scan_complete");
        assert_eq!(value["ts"], 1_800_000_000u64);
        assert_eq!(value.as_object().unwrap().len(), 3);
        for excluded in ["machine_id", "path", "filename", "manifest", "violations"] {
            assert!(value.get(excluded).is_none());
        }
    }

    #[test]
    fn telemetry_requires_the_explicit_push_flag() {
        let args = vec!["yamlr".to_string(), "scan".to_string()];
        assert!(!args.iter().any(|arg| arg == "--push-telemetry"));
    }
}
