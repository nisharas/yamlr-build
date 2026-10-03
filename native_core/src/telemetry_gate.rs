//! Telemetry Gate and Air-Gapped Enforcement.
//!
//! Why: Many enterprise, defense, and sovereign environments mandate 100% air-gapped
//! compliance where no outbound analytics, phone-home, or telemetry beacons are permitted.
//! This module provides a deterministic gate to disable all telemetry emissions.

use std::env;

/// Checks whether telemetry collection and emission is globally permitted.
///
/// Precedence:
/// 1. CLI explicit flag (`--no-telemetry`) -> False
/// 2. Environment variable `YAMLR_TELEMETRY` (values "0", "false", "off", "no") -> False
/// 3. Environment variable `DO_NOT_TRACK` ("1", "true") -> False
/// 4. Default -> True
pub fn is_telemetry_enabled(cli_args: &[String]) -> bool {
    // 1. Check CLI arguments
    for arg in cli_args {
        if arg == "--no-telemetry" || arg == "--disable-telemetry" {
            return false;
        }
    }

    // 2. Check YAMLR_TELEMETRY environment variable
    if let Ok(val) = env::var("YAMLR_TELEMETRY") {
        let normalized = val.trim().to_lowercase();
        if normalized == "0" || normalized == "false" || normalized == "off" || normalized == "no" {
            return false;
        }
    }

    // 3. Honor standard DO_NOT_TRACK industry specification
    if let Ok(val) = env::var("DO_NOT_TRACK") {
        let normalized = val.trim().to_lowercase();
        if normalized == "1" || normalized == "true" {
            return false;
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_telemetry_flag_disables() {
        let args = vec![
            "yamlr".to_string(),
            "scan".to_string(),
            "--no-telemetry".to_string(),
        ];
        assert!(!is_telemetry_enabled(&args));

        let args_alias = vec![
            "yamlr".to_string(),
            "heal".to_string(),
            "--disable-telemetry".to_string(),
        ];
        assert!(!is_telemetry_enabled(&args_alias));
    }

    #[test]
    fn test_telemetry_enabled_with_clean_args() {
        let args = vec!["yamlr".to_string(), "scan".to_string(), ".".to_string()];
        // When neither DO_NOT_TRACK nor YAMLR_TELEMETRY is set to disable:
        if env::var("DO_NOT_TRACK").is_err() && env::var("YAMLR_TELEMETRY").is_err() {
            assert!(is_telemetry_enabled(&args));
        }
    }
}
