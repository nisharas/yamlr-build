//! SecurityContext & ReadOnlyRootFilesystem /tmp Mount Synthesizer (Feature 18).
//!
//! Why: Setting `readOnlyRootFilesystem: true` without an `emptyDir` mounted at `/tmp`
//! causes application runtimes (Node, Python, Java, Go) to immediately crash on startup.
//! Setting `runAsNonRoot: true` without `runAsUser` fails Kubernetes admission validation.
//! This healer synthesizes the required volume mounts and non-root UID.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const SEC_RULE_ID: &str = "SEC-004";

/// Evaluates whether a container running readOnlyRootFilesystem actually requires a /tmp scratch volume.
fn container_needs_tmp_scratch(container: &SemanticNode, kind: &str, explicit_opt_in: bool) -> bool {
    if explicit_opt_in {
        return true;
    }
    // Batch jobs are run-to-completion tasks; do not inject scratch volumes unless explicitly requested
    if kind == "Job" || kind == "CronJob" {
        return false;
    }
    // For long-running services, verify whether image is a known runtime/server requiring scratch write access
    if let Some(img) = container.find_value("image") {
        let img_lower = img.to_lowercase();
        let runtime_indicators = [
            "nginx", "httpd", "apache", "node", "python", "ruby", "java", "jvm",
            "tomcat", "php", "express", "flask", "django", "spring", "redis",
            "postgres", "mysql", "mariadb", "mongo", "elasticsearch", "kafka",
        ];
        for ind in runtime_indicators {
            if img_lower.contains(ind) {
                return true;
            }
        }
        // If image is a specialized/distroless/go binary, do not inject by default
        false
    } else {
        // If image is unspecified (or Helm templated), default to true for long-running workloads
        true
    }
}

pub fn heal_security_context_issues(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    let suppress_tmp = manifest
        .root
        .find_annotation("yamlr.dev/sec-tmp")
        .or_else(|| manifest.root.find_annotation("yamlr.io/tmp-mount"))
        .map(|v| v.trim().trim_matches('"') == "false")
        .unwrap_or(false);

    let explicit_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/sec-tmp")
        .or_else(|| manifest.root.find_annotation("yamlr.io/tmp-mount"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    for spec in manifest.root.find_pod_specs_mut() {
        let mut needs_tmp_volume = false;
        let tmp_volume_name = "yamlr-tmp-dir".to_string();

        let pod_has_run_as_user = spec
            .find_node("securityContext")
            .and_then(|sc| sc.find_node("runAsUser"))
            .is_some();

        // 1. Inspect containers
        if let Some(containers) = spec.find_node_mut("containers") {
            for container in &mut containers.children {
                let c_name = container
                    .find_value("name")
                    .unwrap_or_else(|| "container".to_string());
                let mut readonly_root = false;
                let mut run_as_non_root = false;
                let mut has_run_as_user = false;

                if let Some(sec) = container.find_node("securityContext") {
                    if let Some(v) = sec.find_value("readOnlyRootFilesystem") {
                        if v.trim() == "true" {
                            readonly_root = true;
                        }
                    }
                    if let Some(v) = sec.find_value("runAsNonRoot") {
                        if v.trim() == "true" {
                            run_as_non_root = true;
                        }
                    }
                    if sec.find_node("runAsUser").is_some() {
                        has_run_as_user = true;
                    }
                }

                // Auto-inject runAsUser: 10001 if runAsNonRoot is true but user is unspecified at container AND pod level
                if run_as_non_root && !has_run_as_user && !pod_has_run_as_user {
                    if let Some(sec) = container.find_node_mut("securityContext") {
                        let indent = sec.indent + 2;
                        sec.children.push(SemanticNode {
                            key: "runAsUser".to_string(),
                            value: Some("10001".to_string()),
                            indent,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected 'runAsUser: 10001' for container '{}' to satisfy 'runAsNonRoot: true'.",
                            SEC_RULE_ID, c_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }

                // Check for readOnlyRootFilesystem without /tmp mount
                if readonly_root && !suppress_tmp && container_needs_tmp_scratch(container, &kind, explicit_opt_in) {
                    let mut has_tmp_mount = false;
                    if let Some(vm) = container.find_node("volumeMounts") {
                        for mount in &vm.children {
                            if let Some(path) = mount.find_value("mountPath") {
                                if path.trim() == "/tmp" || path.trim() == "/tmp/" {
                                    has_tmp_mount = true;
                                    break;
                                }
                            }
                        }
                    }

                    if !has_tmp_mount {
                        needs_tmp_volume = true;
                        let mount_indent = container.indent + 2;
                        let item_indent = mount_indent + 2;

                        if let Some(vm) = container.find_node_mut("volumeMounts") {
                            vm.children.push(SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: item_indent,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "name".to_string(),
                                        value: Some(tmp_volume_name.clone()),
                                        indent: item_indent + 2,
                                        is_empty_flow: false,
                                        children: vec![],
                                        shards: vec![],
                                    },
                                    SemanticNode {
                                        key: "mountPath".to_string(),
                                        value: Some("/tmp".to_string()),
                                        indent: item_indent + 2,
                                        is_empty_flow: false,
                                        children: vec![],
                                        shards: vec![],
                                    },
                                ],
                            });
                        } else {
                            container.children.push(SemanticNode {
                                key: "volumeMounts".to_string(),
                                value: None,
                                indent: mount_indent,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "-".to_string(),
                                    value: None,
                                    indent: item_indent,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![
                                        SemanticNode {
                                            key: "name".to_string(),
                                            value: Some(tmp_volume_name.clone()),
                                            indent: item_indent + 2,
                                            is_empty_flow: false,
                                            children: vec![],
                                            shards: vec![],
                                        },
                                        SemanticNode {
                                            key: "mountPath".to_string(),
                                            value: Some("/tmp".to_string()),
                                            indent: item_indent + 2,
                                            is_empty_flow: false,
                                            children: vec![],
                                            shards: vec![],
                                        },
                                    ],
                                }],
                            });
                        }

                        let msg = format!(
                            "Remediation [{}]: Injected writable '/tmp' emptyDir mount for container '{}' with 'readOnlyRootFilesystem: true'.",
                            SEC_RULE_ID, c_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }

        // 2. If any container needs the tmp emptyDir volume, ensure it exists in spec.volumes
        if needs_tmp_volume {
            let mut volume_exists = false;
            if let Some(vols) = spec.find_node("volumes") {
                for vol in &vols.children {
                    if let Some(name) = vol.find_value("name") {
                        if name == tmp_volume_name {
                            volume_exists = true;
                            break;
                        }
                    }
                }
            }

            if !volume_exists {
                let vol_indent = spec.indent + 2;
                let item_indent = vol_indent + 2;

                let empty_dir_vol = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    indent: item_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![
                        SemanticNode {
                            key: "name".to_string(),
                            value: Some(tmp_volume_name.clone()),
                            indent: item_indent + 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        },
                        SemanticNode {
                            key: "emptyDir".to_string(),
                            value: Some("{}".to_string()),
                            indent: item_indent + 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
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
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inject_tmp_mount_for_readonly_root() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 0,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "containers".to_string(),
                        value: None,
                        indent: 2,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            indent: 4,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("web".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "securityContext".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "readOnlyRootFilesystem".to_string(),
                                        value: Some("true".to_string()),
                                        indent: 8,
                                        is_empty_flow: false,
                                        children: vec![],
                                        shards: vec![],
                                    }],
                                },
                            ],
                        }],
                    }],
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_security_context_issues(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        let containers = spec.find_node("containers").unwrap();
        let web = &containers.children[0];
        let vm = web.find_node("volumeMounts").unwrap();
        assert_eq!(vm.children.len(), 1);
        assert_eq!(
            vm.children[0].find_value("mountPath"),
            Some("/tmp".to_string())
        );

        let vols = spec.find_node("volumes").unwrap();
        assert_eq!(vols.children.len(), 1);
        assert_eq!(
            vols.children[0].find_value("name"),
            Some("yamlr-tmp-dir".to_string())
        );
    }

    #[test]
    fn test_inject_run_as_user_when_non_root() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 0,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "containers".to_string(),
                        value: None,
                        indent: 2,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            indent: 4,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("worker".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "securityContext".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "runAsNonRoot".to_string(),
                                        value: Some("true".to_string()),
                                        indent: 8,
                                        is_empty_flow: false,
                                        children: vec![],
                                        shards: vec![],
                                    }],
                                },
                            ],
                        }],
                    }],
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_security_context_issues(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        let containers = spec.find_node("containers").unwrap();
        let worker = &containers.children[0];
        let sec = worker.find_node("securityContext").unwrap();
        assert_eq!(sec.find_value("runAsUser"), Some("10001".to_string()));
    }
}
