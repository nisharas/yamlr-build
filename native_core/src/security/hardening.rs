//! Enterprise Security Context & Host Isolation Hardener.
//!
//! Why: Misconfigured securityContexts and unconstrained container privileges
//! are the primary vector for container breakout, host takeover, and
//! admission rejection in restricted Kubernetes environments.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const SEC_RULE_POD: &str = "SEC-005";
pub const SEC_RULE_HOST: &str = "SEC-006";
pub const SEC_RULE_CONTAINER: &str = "SEC-007";
pub const SEC_RULE_RO_ROOT: &str = "SEC-004";

/// Injects CIS / Pod Security Standards (Restricted) security contexts and
/// auto-synthesizes emptyDir volume mounts for standard writable paths.
pub fn native_harden_security_context(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    for spec in manifest.root.find_pod_specs_mut() {
        // 1. Pod-Level Host Isolation Hardening
        harden_pod_host_isolation(spec, telemetry, &mut changes);

        // 2. Pod-Level Security Context Hardening
        harden_pod_security_context(spec, telemetry, &mut changes);

        // 3. Container-Level Hardening & Volume Mount Auto-Fix
        harden_containers_and_volumes(spec, telemetry, &mut changes);
    }

    changes
}

fn harden_pod_host_isolation(
    spec: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    for field in &["hostNetwork", "hostPID", "hostIPC"] {
        if let Some(val) = spec.find_value(field) {
            if val.trim() == "true" {
                if let Some(node) = spec.find_node_mut(field) {
                    node.value = Some("false".to_string());
                    let msg = format!(
                        "Remediation [{}]: Disabled dangerous '{}: false' on pod spec.",
                        SEC_RULE_HOST, field
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }
}

fn harden_pod_security_context(
    spec: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let pod_indent = spec.indent + 2;
    let sec_indent = pod_indent + 2;

    if spec.find_node("securityContext").is_none() {
        spec.children.push(SemanticNode {
            key: "securityContext".to_string(),
            value: None,
            indent: pod_indent,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        });
    }

    if let Some(sec) = spec.find_node_mut("securityContext") {
        if sec.find_value("runAsNonRoot").as_deref() != Some("true") {
            if let Some(node) = sec.find_node_mut("runAsNonRoot") {
                node.value = Some("true".to_string());
            } else {
                sec.children.push(SemanticNode {
                    key: "runAsNonRoot".to_string(),
                    value: Some("true".to_string()),
                    indent: sec_indent,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
            }
            let msg = format!(
                "Remediation [{}]: Enforced pod 'runAsNonRoot: true'.",
                SEC_RULE_POD
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }

        for (field, default_val) in &[
            ("runAsUser", "10001"),
            ("runAsGroup", "10001"),
            ("fsGroup", "10001"),
        ] {
            if sec.find_node(field).is_none() {
                sec.children.push(SemanticNode {
                    key: field.to_string(),
                    value: Some(default_val.to_string()),
                    indent: sec_indent,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
                let msg = format!(
                    "Remediation [{}]: Injected pod '{}: {}'.",
                    SEC_RULE_POD, field, default_val
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }

        if sec.find_node("seccompProfile").is_none() {
            let prof_indent = sec_indent + 2;
            sec.children.push(SemanticNode {
                key: "seccompProfile".to_string(),
                value: None,
                indent: sec_indent,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "type".to_string(),
                    value: Some("RuntimeDefault".to_string()),
                    indent: prof_indent,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                }],
            });
            let msg = format!(
                "Remediation [{}]: Injected pod 'seccompProfile: {{type: RuntimeDefault}}'.",
                SEC_RULE_POD
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

fn harden_containers_and_volumes(
    spec: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let mut volumes_to_inject = Vec::new();

    for container_list_key in &["containers", "initContainers"] {
        if let Some(containers) = spec.find_node_mut(container_list_key) {
            for container in &mut containers.children {
                let c_name = container
                    .find_value("name")
                    .unwrap_or_else(|| "container".to_string());
                let c_indent = container.indent + 2;
                let sc_indent = c_indent + 2;

                if container.find_node("securityContext").is_none() {
                    container.children.push(SemanticNode {
                        key: "securityContext".to_string(),
                        value: None,
                        indent: c_indent,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: Vec::new(),
                    });
                }

                if let Some(sc) = container.find_node_mut("securityContext") {
                    if sc.find_value("allowPrivilegeEscalation").as_deref() != Some("false") {
                        if let Some(node) = sc.find_node_mut("allowPrivilegeEscalation") {
                            node.value = Some("false".to_string());
                        } else {
                            sc.children.push(SemanticNode {
                                key: "allowPrivilegeEscalation".to_string(),
                                value: Some("false".to_string()),
                                indent: sc_indent,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            });
                        }
                        let msg = format!(
                            "Remediation [{}]: Set 'allowPrivilegeEscalation: false' for container '{}'.",
                            SEC_RULE_CONTAINER, c_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }

                    if sc.find_value("readOnlyRootFilesystem").as_deref() != Some("true") {
                        if let Some(node) = sc.find_node_mut("readOnlyRootFilesystem") {
                            node.value = Some("true".to_string());
                        } else {
                            sc.children.push(SemanticNode {
                                key: "readOnlyRootFilesystem".to_string(),
                                value: Some("true".to_string()),
                                indent: sc_indent,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            });
                        }
                        let msg = format!(
                            "Remediation [{}]: Set 'readOnlyRootFilesystem: true' for container '{}'.",
                            SEC_RULE_RO_ROOT, c_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }

                    if sc.find_value("privileged").as_deref() == Some("true") {
                        if let Some(node) = sc.find_node_mut("privileged") {
                            node.value = Some("false".to_string());
                            let msg = format!(
                                "Remediation [{}]: Disabled dangerous 'privileged: false' for container '{}'.",
                                SEC_RULE_CONTAINER, c_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }

                    harden_capabilities(sc, &c_name, sc_indent, telemetry, changes);
                }

                // Volume Mount Auto-Fix for ReadOnlyRootFilesystem
                check_and_inject_empty_dir_mounts(
                    container,
                    &c_name,
                    c_indent,
                    &mut volumes_to_inject,
                    telemetry,
                    changes,
                );
            }
        }
    }

    // Inject required emptyDir volumes into spec.volumes
    inject_volumes_if_missing(spec, &volumes_to_inject);
}

fn harden_capabilities(
    sc: &mut SemanticNode,
    c_name: &str,
    sc_indent: usize,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let cap_indent = sc_indent + 2;
    let list_indent = cap_indent + 2;

    if sc.find_node("capabilities").is_none() {
        sc.children.push(SemanticNode {
            key: "capabilities".to_string(),
            value: None,
            indent: sc_indent,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        });
    }

    if let Some(caps) = sc.find_node_mut("capabilities") {
        let mut has_drop_all = false;
        if let Some(drop_node) = caps.find_node("drop") {
            for child in &drop_node.children {
                if child.value.as_deref() == Some("ALL") {
                    has_drop_all = true;
                    break;
                }
            }
        }

        if !has_drop_all {
            if let Some(drop_node) = caps.find_node_mut("drop") {
                drop_node.children.push(SemanticNode {
                    key: "-".to_string(),
                    value: Some("ALL".to_string()),
                    indent: list_indent,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
            } else {
                caps.children.push(SemanticNode {
                    key: "drop".to_string(),
                    value: None,
                    indent: cap_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "-".to_string(),
                        value: Some("ALL".to_string()),
                        indent: list_indent,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    }],
                });
            }
            let msg = format!(
                "Remediation [{}]: Injected 'capabilities.drop: [ALL]' for container '{}'.",
                SEC_RULE_CONTAINER, c_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

fn check_and_inject_empty_dir_mounts(
    container: &mut SemanticNode,
    c_name: &str,
    c_indent: usize,
    volumes_to_inject: &mut Vec<(&'static str, &'static str)>,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let has_ports = container.find_node("ports").is_some();
    let env_content = container
        .find_node("env")
        .map(|e| format!("{:?}", e))
        .unwrap_or_default();

    let mut required_mounts: Vec<(&'static str, &'static str)> = vec![("/tmp", "yamlr-tmp-dir")];

    if has_ports || env_content.contains("PORT") || env_content.contains("RUN") {
        required_mounts.push(("/var/run", "yamlr-run-dir"));
    }
    if env_content.contains("LOG") {
        required_mounts.push(("/var/log", "yamlr-log-dir"));
    }

    let mut existing_mount_paths = Vec::new();
    if let Some(vm) = container.find_node("volumeMounts") {
        for mount in &vm.children {
            if let Some(p) = mount.find_value("mountPath") {
                existing_mount_paths.push(p);
            }
        }
    }

    let vm_indent = c_indent + 2;
    let item_indent = vm_indent + 2;

    for (mount_path, vol_name) in required_mounts {
        if !existing_mount_paths.iter().any(|p| p == mount_path) {
            let mount_item = SemanticNode {
                key: "-".to_string(),
                value: None,
                indent: item_indent,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "name".to_string(),
                        value: Some(vol_name.to_string()),
                        indent: item_indent + 2,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "mountPath".to_string(),
                        value: Some(mount_path.to_string()),
                        indent: item_indent + 2,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                ],
            };

            if let Some(vm) = container.find_node_mut("volumeMounts") {
                vm.children.push(mount_item);
            } else {
                container.children.push(SemanticNode {
                    key: "volumeMounts".to_string(),
                    value: None,
                    indent: vm_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![mount_item],
                });
            }

            volumes_to_inject.push((vol_name, mount_path));

            let msg = format!(
                "Remediation [{}]: Injected writable '{}' emptyDir mount for container '{}' with 'readOnlyRootFilesystem: true'.",
                SEC_RULE_RO_ROOT, mount_path, c_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

fn inject_volumes_if_missing(
    spec: &mut SemanticNode,
    volumes_to_inject: &[(&'static str, &'static str)],
) {
    let mut existing_vols = Vec::new();
    if let Some(vols) = spec.find_node("volumes") {
        for vol in &vols.children {
            if let Some(name) = vol.find_value("name") {
                existing_vols.push(name);
            }
        }
    }

    let vol_indent = spec.indent + 2;
    let item_indent = vol_indent + 2;

    for (vol_name, _) in volumes_to_inject {
        if !existing_vols.iter().any(|v| v == vol_name) {
            let empty_dir_vol = SemanticNode {
                key: "-".to_string(),
                value: None,
                indent: item_indent,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "name".to_string(),
                        value: Some(vol_name.to_string()),
                        indent: item_indent + 2,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "emptyDir".to_string(),
                        value: Some("{}".to_string()),
                        indent: item_indent + 2,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                ],
            };

            if let Some(vols) = spec.find_node_mut("volumes") {
                vols.children.push(empty_dir_vol);
            } else {
                spec.children.push(SemanticNode {
                    key: "volumes".to_string(),
                    value: None,
                    indent: vol_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![empty_dir_vol],
                });
            }
            existing_vols.push(vol_name.to_string());
        }
    }
}

/// Hardens YAML manifest content string directly, returning hardened YAML and changes.
pub fn harden_manifest_yaml(content: &str) -> (String, Vec<String>) {
    let shards = crate::sharder::native_shard(content);
    let mut manifest = crate::structurer::native_structurize(shards);
    let mut telemetry = NativeTelemetry::default();
    let changes = native_harden_security_context(&mut manifest, &mut telemetry);
    let reconstructed = crate::healing::native_reconstruct_from_semantic(&manifest);
    (reconstructed, changes)
}
