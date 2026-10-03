//! CI/CD Pipeline Auto-Healer for Argo Workflows & Tekton Pipelines (Rule ECO-003).
//!
//! Why: Argo Workflows (`argoproj.io/v1alpha1`) and Tekton Pipelines (`tekton.dev/v1`)
//! are the industry standard for cloud-native CI/CD. Broken template entrypoints,
//! untyped Tekton parameters, and missing container resource boundaries cause pipeline
//! step failures and node eviction during large CI jobs.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const PIPELINE_RULE_ID: &str = "ECO-003";

/// Primary entrypoint: Heals Argo Workflows and Tekton Pipeline manifests.
pub fn heal_pipeline_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();

    if api_version.starts_with("argoproj.io") {
        changes.extend(heal_argo_workflow(manifest, telemetry));
    } else if api_version.starts_with("tekton.dev") {
        changes.extend(heal_tekton_pipeline(manifest, telemetry));
    }

    changes
}

fn heal_argo_workflow(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Workflow" && kind != "WorkflowTemplate" && kind != "CronWorkflow" {
        return changes;
    }

    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // 1. Collect all defined template names
    let mut defined_templates: Vec<String> = Vec::new();
    if let Some(templates_node) = spec.find_node("templates") {
        for tpl in &templates_node.children {
            if let Some(name_node) = tpl.find_node("name") {
                if let Some(ref val) = name_node.value {
                    defined_templates.push(
                        val.trim()
                            .trim_matches(|c| c == '\'' || c == '"')
                            .to_string(),
                    );
                }
            }
        }
    }

    // 2. Validate spec.entrypoint against defined templates
    if let Some(entrypoint_node) = spec.find_node_mut("entrypoint") {
        let mut needs_ep_fix = None;
        if let Some(ref current_ep) = entrypoint_node.value {
            let ep_clean = current_ep.trim().trim_matches(|c| c == '\'' || c == '"');
            if !defined_templates.is_empty() && !defined_templates.contains(&ep_clean.to_string()) {
                // Find closest template name
                let mut best_match = None;
                let mut best_ratio = 0.0;
                for t in &defined_templates {
                    let ratio = crate::healers::selector_healer::similarity_ratio(ep_clean, t);
                    if ratio >= 0.60 && ratio > best_ratio {
                        best_ratio = ratio;
                        best_match = Some(t.clone());
                    }
                }

                let target = best_match.unwrap_or_else(|| defined_templates[0].clone());
                needs_ep_fix = Some((ep_clean.to_string(), target));
            }
        }

        if let Some((ep_clean, target)) = needs_ep_fix {
            entrypoint_node.value = Some(target.clone());
            for s in &mut entrypoint_node.shards {
                s.value = Some(target.clone());
            }
            let msg = format!(
                "Remediation [{}]: Aligned broken Argo entrypoint '{}' -> '{}' to match defined template.",
                PIPELINE_RULE_ID, ep_clean, target
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    // 3. Inject memory limits on template containers missing them
    if let Some(templates_node) = spec.find_node_mut("templates") {
        for tpl in &mut templates_node.children {
            if let Some(container) = tpl.find_node_mut("container") {
                if container.find_node("resources").is_none() {
                    let res_indent = container.indent + 2;
                    let lim_indent = res_indent + 2;
                    let val_indent = lim_indent + 2;

                    container.children.push(SemanticNode {
                        key: "resources".to_string(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "limits".to_string(),
                            value: None,
                            children: vec![
                                SemanticNode {
                                    key: "memory".to_string(),
                                    value: Some("512Mi".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "cpu".to_string(),
                                    value: Some("500m".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                            ],
                            shards: Vec::new(),
                            indent: lim_indent,
                            is_empty_flow: false,
                        }],
                        shards: Vec::new(),
                        indent: res_indent,
                        is_empty_flow: false,
                    });
                    let tpl_name = tpl.find_value("name").unwrap_or_else(|| "step".to_string());
                    let msg = format!(
                        "Remediation [{}]: Injected baseline container resources (cpu: 500m, memory: 512Mi) on Argo template '{}'.",
                        PIPELINE_RULE_ID, tpl_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

fn heal_tekton_pipeline(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    // 1. Upgrade deprecated tekton.dev/v1beta1 -> tekton.dev/v1
    if api_version == "tekton.dev/v1beta1" && (kind == "Pipeline" || kind == "Task") {
        if let Some(api_node) = manifest.root.find_node_mut("apiVersion") {
            api_node.value = Some("tekton.dev/v1".to_string());
            for s in &mut api_node.shards {
                s.value = Some("tekton.dev/v1".to_string());
            }
            let msg = format!(
                "Remediation [{}]: Upgraded deprecated Tekton API 'tekton.dev/v1beta1' -> 'tekton.dev/v1' on {}.",
                PIPELINE_RULE_ID, kind
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    // 2. Ensure all params have explicit type: string if untyped
    if let Some(spec) = manifest.root.find_node_mut("spec") {
        for params_node in spec.find_nodes_by_key_recursive_mut("params") {
            for param in &mut params_node.children {
                if param.find_node("type").is_none() {
                    let indent = param.indent + 2;
                    param.children.push(SemanticNode {
                        key: "type".to_string(),
                        value: Some("string".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent,
                        is_empty_flow: false,
                    });
                    let param_name = param
                        .find_value("name")
                        .unwrap_or_else(|| "param".to_string());
                    let msg = format!(
                        "Remediation [{}]: Injected explicit 'type: string' on untyped Tekton parameter '{}'.",
                        PIPELINE_RULE_ID, param_name
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
    fn test_heal_argo_entrypoint_typo_and_resources() {
        let yaml = r#"
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: build-pipeline
spec:
  entrypoint: build-and-tst
  templates:
    - name: build-and-test
      container:
        image: golang:1.22
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_pipeline_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert_eq!(
            manifest
                .root
                .find_node("spec")
                .unwrap()
                .find_value("entrypoint"),
            Some("build-and-test".to_string())
        );
        assert!(changes[1].contains("Injected baseline container resources"));
    }

    #[test]
    fn test_heal_tekton_api_and_param_type() {
        let yaml = r#"
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: git-clone
spec:
  params:
    - name: url
      description: Repository URL
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_pipeline_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert_eq!(
            manifest.root.find_value("apiVersion"),
            Some("tekton.dev/v1".to_string())
        );
        assert!(changes[1].contains("Injected explicit 'type: string'"));
    }
}
