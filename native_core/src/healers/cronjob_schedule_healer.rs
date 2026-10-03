//! CronJob Schedule Format Healer (Rule OPS-003).
//!
//! Why: Kubernetes CronJobs require standard 5-field cron expressions (minute, hour, dom, month, dow).
//! Common mistakes include using Spring/Quartz 6-field cron expressions (with seconds), unsupported
//! aliases, or unquoted asterisk expressions that get corrupted by parsers.

use crate::models::{NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const CRONJOB_SCHEDULE_RULE_ID: &str = "OPS-003";

/// Normalizes and repairs cron schedule expressions.
pub fn repair_cron_schedule(raw_schedule: &str) -> Option<String> {
    let trimmed = raw_schedule
        .trim()
        .trim_matches('"')
        .trim_matches('\'')
        .trim();

    // 1. Alias replacements
    let aliased = match trimmed.to_lowercase().as_str() {
        "@yearly" | "@annually" => Some("0 0 1 1 *"),
        "@monthly" => Some("0 0 1 * *"),
        "@weekly" => Some("0 0 * * 0"),
        "@daily" | "@midnight" => Some("0 0 * * *"),
        "@hourly" => Some("0 * * * *"),
        _ => None,
    };

    if let Some(a) = aliased {
        return Some(format!("\"{}\"", a));
    }

    // 2. Multi-field check (split by whitespace)
    let parts: Vec<&str> = trimmed.split_whitespace().collect();
    if parts.len() == 6 {
        // Quartz/Spring syntax: seconds minute hour dom month dow
        // If first part is "0" or "00", strip leading seconds field
        if parts[0] == "0" || parts[0] == "00" {
            let standard_5 = parts[1..].join(" ");
            return Some(format!("\"{}\"", standard_5));
        }
    } else if parts.len() == 5 {
        // Standard 5-field cron: ensure deterministic quotes
        let normalized = parts.join(" ");
        if trimmed != normalized || !raw_schedule.starts_with('"') {
            return Some(format!("\"{}\"", normalized));
        }
    }

    None
}

/// Heals CronJob schedule syntax in a manifest.
pub fn heal_cronjob_schedules(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "CronJob" {
        return changes;
    }

    let job_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-cronjob".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(schedule_node) = spec.find_node_mut("schedule") {
            let current = schedule_node.value.clone().unwrap_or_default();
            if let Some(repaired) = repair_cron_schedule(&current) {
                if current != repaired {
                    schedule_node.value = Some(repaired.clone());
                    for s in &mut schedule_node.shards {
                        s.value = Some(repaired.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Repaired CronJob '{}' schedule '{}' -> {}.",
                        CRONJOB_SCHEDULE_RULE_ID, job_name, current, repaired
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_repair_cron_aliases() {
        assert_eq!(
            repair_cron_schedule("@daily"),
            Some("\"0 0 * * *\"".to_string())
        );
        assert_eq!(
            repair_cron_schedule("@hourly"),
            Some("\"0 * * * *\"".to_string())
        );
    }

    #[test]
    fn test_repair_6_field_cron() {
        assert_eq!(
            repair_cron_schedule("0 30 4 * * *"),
            Some("\"30 4 * * *\"".to_string())
        );
    }
}
