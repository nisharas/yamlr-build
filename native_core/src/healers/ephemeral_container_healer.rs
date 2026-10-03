//! Ephemeral Container Debugging & Security Auto-Healer (Rule SEC-012).
//!
//! Why: Kubernetes 1.25+ supports ephemeral containers for interactive pod troubleshooting.
//! Ephemeral containers lacking `targetContainerName`, possessing permissive security contexts,
//! or using unpinned `:latest` debug images break PodSecurity admission and production observability.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const EPHEMERAL_HEALER_RULE_ID: &str = "SEC-012";

/// Primary entrypoint: Hardens and aligns ephemeral container definitions across workloads.
pub fn heal_ephemeral_containers(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Pod" && kind != "Deployment" && kind != "StatefulSet" && kind != "DaemonSet" {
        return changes;
    }

    // Locate the pod spec (either root.spec for Pod, or root.spec.template.spec for workloads)
    let pod_spec = if kind == "Pod" {
        manifest.root.find_node_mut("spec")
    } else {
        manifest
            .root
            .find_node_mut("spec")
            .and_then(|s| s.find_node_mut("template"))
            .and_then(|t| t.find_node_mut("spec"))
    };

    let pod_spec = match pod_spec {
        Some(s) => s,
        None => return changes,
    };

    // 1. Gather all primary container names
    let mut primary_container_names: Vec<String> = Vec::new();
    if let Some(containers) = pod_spec.find_node("containers") {
        for c in &containers.children {
            if let Some(name_node) = c.find_node("name") {
                if let Some(ref val) = name_node.value {
                    primary_container_names.push(
                        val.trim()
                            .trim_matches(|c| c == '\'' || c == '"')
                            .to_string(),
                    );
                }
            }
        }
    }

    let default_target = primary_container_names
        .first()
        .cloned()
        .unwrap_or_else(|| "main".to_string());

    // 2. Validate and heal ephemeralContainers
    if let Some(ephem_node) = pod_spec.find_node_mut("ephemeralContainers") {
        for ephem_c in &mut ephem_node.children {
            // A. Validate targetContainerName
            let mut target_val = None;
            if let Some(target_node) = ephem_c.find_node("targetContainerName") {
                target_val = target_node.value.clone();
            }

            match target_val {
                None => {
                    let indent = ephem_c.indent + 2;
                    ephem_c.children.push(SemanticNode {
                        key: "targetContainerName".to_string(),
                        value: Some(default_target.clone()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Injected missing 'targetContainerName: {}' into ephemeral container.",
                        EPHEMERAL_HEALER_RULE_ID, default_target
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
                Some(ref cur) => {
                    let cur_clean = cur.trim().trim_matches(|c| c == '\'' || c == '"');
                    if !primary_container_names.is_empty()
                        && !primary_container_names.contains(&cur_clean.to_string())
                    {
                        if let Some(target_node) = ephem_c.find_node_mut("targetContainerName") {
                            target_node.value = Some(default_target.clone());
                            for s in &mut target_node.shards {
                                s.value = Some(default_target.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Realigned invalid targetContainerName '{}' -> '{}' for ephemeral container.",
                                EPHEMERAL_HEALER_RULE_ID, cur_clean, default_target
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }

            // B. Enforce securityContext (allowPrivilegeEscalation: false)
            if ephem_c.find_node("securityContext").is_none() {
                let sec_indent = ephem_c.indent + 2;
                let prop_indent = sec_indent + 2;
                let sec_node = SemanticNode {
                    key: "securityContext".to_string(),
                    value: None,
                    children: vec![
                        SemanticNode {
                            key: "allowPrivilegeEscalation".to_string(),
                            value: Some("false".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent: prop_indent,
                            is_empty_flow: false,
                        },
                        SemanticNode {
                            key: "readOnlyRootFilesystem".to_string(),
                            value: Some("false".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent: prop_indent,
                            is_empty_flow: false,
                        },
                    ],
                    shards: Vec::new(),
                    indent: sec_indent,
                    is_empty_flow: false,
                };
                ephem_c.children.push(sec_node);
                let msg = format!(
                    "Remediation [{}]: Injected baseline securityContext (allowPrivilegeEscalation: false) on ephemeral container.",
                    EPHEMERAL_HEALER_RULE_ID
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }

            // C. Validate image floating tag
            if let Some(img_node) = ephem_c.find_node_mut("image") {
                let mut needs_update = None;
                if let Some(ref img_val) = img_node.value {
                    let clean_img = img_val.trim().trim_matches(|c| c == '\'' || c == '"');
                    if clean_img.ends_with(":latest") {
                        let pinned = clean_img.replace(":latest", ":stable-debug");
                        needs_update = Some((clean_img.to_string(), pinned));
                    }
                }
                if let Some((clean_img, pinned)) = needs_update {
                    img_node.value = Some(pinned.clone());
                    for s in &mut img_node.shards {
                        s.value = Some(pinned.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Pinned ephemeral container image '{}' -> '{}'.",
                        EPHEMERAL_HEALER_RULE_ID, clean_img, pinned
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
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_ephemeral_container_target_name() {
        let yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: debug-pod
spec:
  containers:
    - name: web-app
      image: nginx:1.25
  ephemeralContainers:
    - name: debugger
      image: busybox:1.36
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ephemeral_containers(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2); // targetContainerName + securityContext
        let target_val = manifest
            .root
            .find_node("spec")
            .unwrap()
            .find_node("ephemeralContainers")
            .unwrap()
            .children[0]
            .find_value("targetContainerName");
        assert_eq!(target_val, Some("web-app".to_string()));
    }

    #[test]
    fn test_heal_ephemeral_container_image_tag() {
        let yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: debug-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
  ephemeralContainers:
    - name: debugger
      targetContainerName: app
      image: busybox:latest
      securityContext:
        allowPrivilegeEscalation: false
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ephemeral_containers(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains(
            "Pinned ephemeral container image 'busybox:latest' -> 'busybox:stable-debug'"
        ));
    }
}
