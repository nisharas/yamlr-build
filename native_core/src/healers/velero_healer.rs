//! Velero Disaster Recovery & Backup Auto-Healer (Rule ECO-004).
//!
//! Why: Velero backup manifests (`velero.io/v1` Backup, Schedule, Restore) require Go-duration
//! formatted TTLs (e.g. `720h0m0s`). YAML authors commonly write human shorthands like `ttl: 30d`
//! or omit `storageLocation`, which causes Velero controller admission rejection and silent backup gaps.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const VELERO_RULE_ID: &str = "ECO-004";

/// Primary entrypoint: Heals Velero Backup, Schedule, and Restore manifests.
pub fn heal_velero_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    if !api_version.starts_with("velero.io") {
        return changes;
    }

    match kind.as_str() {
        "Backup" | "Schedule" => changes.extend(heal_backup_or_schedule(manifest, telemetry)),
        _ => {}
    }

    changes
}

fn heal_backup_or_schedule(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // 1. Normalize TTL format: "30d" -> "720h0m0s", "7d" -> "168h0m0s"
    for ttl_node in spec.find_nodes_by_key_recursive_mut("ttl") {
        let mut needs_fix = None;
        if let Some(ref val) = ttl_node.value {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            if clean.ends_with('d') {
                if let Ok(days) = clean[..clean.len() - 1].parse::<u32>() {
                    let hours = days * 24;
                    let go_duration = format!("{}h0m0s", hours);
                    needs_fix = Some((clean.to_string(), go_duration));
                }
            } else if clean.ends_with('h') && !clean.contains('m') {
                let go_duration = format!("{}0m0s", clean);
                needs_fix = Some((clean.to_string(), go_duration));
            }
        }

        if let Some((old_val, new_val)) = needs_fix {
            ttl_node.value = Some(new_val.clone());
            for s in &mut ttl_node.shards {
                s.value = Some(new_val.clone());
            }
            let msg = format!(
                "Remediation [{}]: Converted non-standard Velero TTL duration '{}' -> Go duration '{}'.",
                VELERO_RULE_ID, old_val, new_val
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    // 2. Validate default storageLocation
    if spec.find_node("storageLocation").is_none() && spec.find_node("template").is_none() {
        let indent = spec.indent + 2;
        spec.children.push(SemanticNode {
            key: "storageLocation".to_string(),
            value: Some("default".to_string()),
            children: Vec::new(),
            shards: Vec::new(),
            indent,
            is_empty_flow: false,
        });
        let msg = format!(
            "Remediation [{}]: Injected default 'storageLocation: default' for Velero backup.",
            VELERO_RULE_ID
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    // 3. Normalize Cron schedule on Schedule resources
    if let Some(sched_node) = spec.find_node_mut("schedule") {
        let mut needs_fix = None;
        if let Some(ref val) = sched_node.value {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            match clean {
                "@daily" => needs_fix = Some(("@daily".to_string(), "0 0 * * *".to_string())),
                "@hourly" => needs_fix = Some(("@hourly".to_string(), "0 * * * *".to_string())),
                "@weekly" => needs_fix = Some(("@weekly".to_string(), "0 0 * * 0".to_string())),
                _ => {}
            }
        }

        if let Some((old_sched, new_sched)) = needs_fix {
            sched_node.value = Some(new_sched.clone());
            for s in &mut sched_node.shards {
                s.value = Some(new_sched.clone());
            }
            let msg = format!(
                "Remediation [{}]: Normalized Velero schedule macro '{}' -> standard cron '{}'.",
                VELERO_RULE_ID, old_sched, new_sched
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_velero_ttl_and_storage_location() {
        let yaml = r#"
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: nightly-backup
spec:
  ttl: 30d
  includedNamespaces:
    - default
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_velero_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert_eq!(
            manifest.root.find_node("spec").unwrap().find_value("ttl"),
            Some("720h0m0s".to_string())
        );
        assert_eq!(
            manifest
                .root
                .find_node("spec")
                .unwrap()
                .find_value("storageLocation"),
            Some("default".to_string())
        );
    }

    #[test]
    fn test_heal_velero_schedule_cron_macro() {
        let yaml = r#"
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-schedule
spec:
  schedule: "@daily"
  template:
    ttl: 7d
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_velero_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert_eq!(
            manifest
                .root
                .find_node("spec")
                .unwrap()
                .find_value("schedule"),
            Some("0 0 * * *".to_string())
        );
        let tmpl_ttl = manifest
            .root
            .find_node("spec")
            .unwrap()
            .find_node("template")
            .unwrap()
            .find_value("ttl");
        assert_eq!(tmpl_ttl, Some("168h0m0s".to_string()));
    }
}
