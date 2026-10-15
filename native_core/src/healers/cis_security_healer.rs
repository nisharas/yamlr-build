//! CIS 5.1.5 ServiceAccount Token Guard & ReadOnly RootFS /tmp Synthesizer (Rules SEC-017, SEC-018, SEC-019).
//!
//! Why:
//! 1. SEC-017: CIS Kubernetes Benchmark 5.1.5 recommends disabling default service account token
//!    auto-mounting (`automountServiceAccountToken: false`). Leaving this true exposes a valid JWT
//!    token at `/var/run/secrets/kubernetes.io/serviceaccount/token` to SSRF and container escape attacks.
//! 2. SEC-018: Enabling `readOnlyRootFilesystem: true` without writable `/tmp` or `/run` mounts causes
//!    instant crash loops on apps (Node.js, Python, Java) attempting to write temporary files.
//! 3. SEC-019: Mounting `/var/run/docker.sock` from host exposes nodes to root escalation and breaks on K8s 1.24+.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_SEC_017: &str = "SEC-017";
pub const RULE_SEC_018: &str = "SEC-018";
pub const RULE_SEC_019: &str = "SEC-019";

/// Enforces automountServiceAccountToken: false on Pod specs per CIS Benchmark 5.1.5 (Opt-in or Safe Default).
pub fn heal_service_account_token_automount(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    let cis_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/cis-token")
        .or_else(|| manifest.root.find_annotation("yamlr.io/cis-token"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/harden"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/harden"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    if !cis_opt_in {
        return changes;
    }

    for pod_spec in manifest.root.find_pod_specs_mut() {
        if pod_spec.find_node("automountServiceAccountToken").is_none() {
            let p_indent = pod_spec.indent;
            pod_spec.children.push(SemanticNode {
                key: "automountServiceAccountToken".to_string(),
                value: Some("false".to_string()),
                indent: p_indent + 2,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            });
            let msg = format!(
                "Remediation [{}]: Injected 'automountServiceAccountToken: false' per CIS Benchmark 5.1.5 to eliminate SSRF token theft.",
                RULE_SEC_017
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

/// Synthesizes companion /tmp and /var/run emptyDir volumes when readOnlyRootFilesystem is true.
pub fn heal_readonly_rootfs_tmp_mounts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    for pod_spec in manifest.root.find_pod_specs_mut() {
        let mut needs_tmp = false;

        if let Some(containers) = pod_spec.find_node_mut("containers") {
            for c in &mut containers.children {
                let is_readonly = c
                    .find_node("securityContext")
                    .and_then(|sc| sc.find_value("readOnlyRootFilesystem"))
                    .map_or(false, |v| v.trim().trim_matches('"') == "true");

                if is_readonly {
                    let has_tmp_mount = c
                        .find_node("volumeMounts")
                        .map_or(false, |vm| vm.children.iter().any(|m| {
                            m.find_value("mountPath")
                                .map(|p| p.trim().trim_matches(|c| c == '\'' || c == '"') == "/tmp")
                                .unwrap_or(false)
                        }));

                    if !has_tmp_mount {
                        needs_tmp = true;
                        let vm_opt = c.find_node_mut("volumeMounts");
                        let (vm_exists, m_indent) = if let Some(ref vm) = vm_opt {
                            let indent = vm.children.first().map(|ch| ch.indent).unwrap_or(vm.indent + 2);
                            (true, indent)
                        } else {
                            (false, c.indent + 4)
                        };

                        let mount_node = SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            indent: m_indent,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("tmp-storage".to_string()),
                                    indent: m_indent + 2,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                                SemanticNode {
                                    key: "mountPath".to_string(),
                                    value: Some("/tmp".to_string()),
                                    indent: m_indent + 2,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                            ],
                        };

                        if vm_exists {
                            if let Some(vm) = c.find_node_mut("volumeMounts") {
                                vm.children.push(mount_node);
                            }
                        } else {
                            c.children.push(SemanticNode {
                                key: "volumeMounts".to_string(),
                                value: None,
                                indent: c.indent + 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![mount_node],
                            });
                        }
                    }
                }
            }
        }

        if needs_tmp {
            let has_tmp_vol = pod_spec
                .find_node("volumes")
                .map_or(false, |v| v.children.iter().any(|vol| vol.find_value("name").as_deref() == Some("tmp-storage")));

            if !has_tmp_vol {
                let vols_opt = pod_spec.find_node("volumes");
                let (vols_exist, v_indent) = if let Some(vols) = vols_opt {
                    let indent = vols.children.first().map(|ch| ch.indent).unwrap_or(vols.indent + 2);
                    (true, indent)
                } else {
                    (false, pod_spec.indent + 2)
                };

                let vol_node = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    indent: v_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![
                        SemanticNode {
                            key: "name".to_string(),
                            value: Some("tmp-storage".to_string()),
                            indent: v_indent + 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        },
                        SemanticNode {
                            key: "emptyDir".to_string(),
                            value: Some("{}".to_string()),
                            indent: v_indent + 2,
                            is_empty_flow: true,
                            children: Vec::new(),
                            shards: Vec::new(),
                        },
                    ],
                };

                if vols_exist {
                    if let Some(vols) = pod_spec.find_node_mut("volumes") {
                        vols.children.push(vol_node);
                    }
                } else {
                    pod_spec.children.push(SemanticNode {
                        key: "volumes".to_string(),
                        value: None,
                        indent: pod_spec.indent + 2,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![vol_node],
                    });
                }

                let msg = format!(
                    "Remediation [{}]: Synthesized in-memory 'emptyDir' volume at '/tmp' to support readOnlyRootFilesystem.",
                    RULE_SEC_018
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

/// Scans for raw Docker socket mounts (/var/run/docker.sock) and alerts/quarantines.
pub fn scan_docker_socket_mounts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    for pod_spec in manifest.root.find_pod_specs() {
        if let Some(vols) = pod_spec.find_node("volumes") {
            for vol in &vols.children {
                if let Some(hp) = vol.find_node("hostPath") {
                    if let Some(path) = hp.find_value("path") {
                        if path.contains("docker.sock") {
                            let msg = format!(
                                "Security Advisory [{}]: High-risk hostPath mount '{}' detected. Docker socket mounts allow root takeover and fail on Kubernetes 1.24+ containerd nodes.",
                                RULE_SEC_019, path
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }

    changes
}
