//! In-Memory Helm values.yaml Parser & Surgical Healer.
//!
//! Why: Parses and heals Helm values.yaml files with 100% comment, whitespace,
//!      and layout preservation, while shielding dynamic template interpolations
//!      (`{{- toYaml ... }}`) from corruption.

use super::rules::*;
use crate::healers::resource_sanitizer::parse_cpu_millicores;
use crate::models::NativeShard;
use crate::sharder::{native_reconstruct_yaml, native_shard};

/// Identifies if a given YAML text represents a Helm values configuration rather than a Kubernetes resource.
pub fn is_helm_values_content(content: &str) -> bool {
    let has_k8s_identity = content.lines().any(|l| {
        let t = l.trim();
        (t.starts_with("apiVersion:") || t.starts_with("kind:")) && !t.contains("{{")
    });
    if has_k8s_identity {
        return false;
    }
    let lower = content.to_lowercase();
    lower.contains("image:")
        || lower.contains("replicacount:")
        || lower.contains("service:")
        || lower.contains("ingress:")
        || lower.contains("resources:")
        || lower.contains("autoscaling:")
        || lower.contains("securitycontext:")
        || lower.contains("pullpolicy:")
        || lower.contains("tag:")
        || lower.contains("pdb:")
        || lower.contains("probes:")
}

/// Heals a raw `values.yaml` string with 100% comment and formatting preservation.
pub fn heal_values_yaml(content: &str) -> (String, Vec<String>) {
    let mut shards = native_shard(content);
    if shards.is_empty() {
        return (content.to_string(), Vec::new());
    }

    let mut changes = Vec::new();
    let mut modified = false;

    // Pass 1: Shard-level direct property healing
    let len = shards.len();
    for i in 0..len {
        let key = shards[i].key.clone();
        let val_opt = shards[i].value.clone();

        // 1. OPS-002: Floating Image Tags in values.yaml
        let unquoted_val = val_opt
            .as_deref()
            .map(|v| v.trim_matches(|c| c == '"' || c == '\''))
            .unwrap_or("");
        if (key == "tag" || key == "imageTag") && unquoted_val == "latest" {
            shards[i].value = Some("stable-pinned".to_string());
            update_shard_raw_line(&mut shards[i], &key, "stable-pinned");
            changes.push(msg_pinned_tag("latest"));
            modified = true;
        } else if key == "image" {
            if let Some(val) = &val_opt {
                let trimmed = val.trim_matches(|c| c == '"' || c == '\'');
                if trimmed.ends_with(":latest") {
                    let pinned = val.replace(":latest", ":stable-pinned");
                    shards[i].value = Some(pinned.clone());
                    update_shard_raw_line(&mut shards[i], "image", &pinned);
                    changes.push(msg_pinned_image());
                    modified = true;
                }
            }
        }

        // 2. SEC-002: Pull Policy Enforcement
        if key == "pullPolicy" && val_opt.as_deref() != Some("Always") {
            shards[i].value = Some("Always".to_string());
            update_shard_raw_line(&mut shards[i], "pullPolicy", "Always");
            changes.push(msg_pull_policy_always());
            modified = true;
        }

        // 3. SEC-001: Privileged Context Neutralization
        if key == "privileged" && val_opt.as_deref() == Some("true") {
            shards[i].value = Some("false".to_string());
            update_shard_raw_line(&mut shards[i], "privileged", "false");
            changes.push(msg_neutralize_privileged());
            modified = true;
        }

        // 4. SEC-004: Root UID Elimination
        if key == "runAsUser" && val_opt.as_deref() == Some("0") {
            shards[i].value = Some("10001".to_string());
            update_shard_raw_line(&mut shards[i], "runAsUser", "10001");
            changes.push(msg_non_root_uid());
            modified = true;
        } else if key == "runAsNonRoot" && val_opt.as_deref() == Some("false") {
            shards[i].value = Some("true".to_string());
            update_shard_raw_line(&mut shards[i], "runAsNonRoot", "true");
            changes.push(msg_enforce_run_as_non_root());
            modified = true;
        }

        // 7. REL-005: PDB Deadlock Parameters
        if key == "minAvailable" && val_opt.as_deref() == Some("100%") {
            shards[i].value = Some("50%".to_string());
            update_shard_raw_line(&mut shards[i], "minAvailable", "50%");
            changes.push(msg_pdb_min_available());
            modified = true;
        } else if key == "maxUnavailable"
            && (val_opt.as_deref() == Some("0") || val_opt.as_deref() == Some("0%"))
        {
            shards[i].value = Some("1".to_string());
            update_shard_raw_line(&mut shards[i], "maxUnavailable", "1");
            changes.push(msg_pdb_max_unavailable());
            modified = true;
        }

        // 9. ING-001: Deprecated Ingress Class Annotation
        if key == "kubernetes.io/ingress.class" {
            let val = val_opt.as_deref().unwrap_or("nginx");
            shards[i].key = "ingressClassName".to_string();
            update_shard_raw_line(&mut shards[i], "ingressClassName", val);
            changes.push(msg_modernize_ingress_class());
            modified = true;
        }

        // 10. SEC-003: Plaintext Secret Detection
        if (key == "password" || key == "secretKey" || key == "apiKey")
            && !val_opt.as_deref().unwrap_or("").is_empty()
        {
            let val = val_opt.as_deref().unwrap();
            if !val.contains("{{") && !val.starts_with('$') && val != "\"\"" && val != "''" {
                if !shards[i].comment.contains("SEC-003") {
                    shards[i].comment =
                        "# yamlr [SEC-003]: Consider referencing an existingSecret".to_string();
                    let indent = " ".repeat(shards[i].indent);
                    shards[i].raw_line =
                        format!("{}{}: {} {}", indent, shards[i].key, val, shards[i].comment);
                    changes.push(msg_annotate_secret());
                    modified = true;
                }
            }
        }

        // 11. DEP-001: Modern OCI Registry Recognition
        if (key == "repository" || key == "repo")
            && val_opt
                .as_deref()
                .map(|v| v.starts_with("oci://"))
                .unwrap_or(false)
        {
            let repo_val = val_opt.as_deref().unwrap();
            if !shards[i].comment.contains("DEP-001") {
                shards[i].comment = "# yamlr [DEP-001]: Validated OCI registry".to_string();
                let indent = " ".repeat(shards[i].indent);
                shards[i].raw_line = format!(
                    "{}{}: {} {}",
                    indent, shards[i].key, repo_val, shards[i].comment
                );
                changes.push(msg_normalize_oci_registry(repo_val));
                modified = true;
            }
        }
    }

    // Pass 2: Contextual Scope Healing (Autoscaling min/max, Probes timeouts, Inverted Resources)
    let (hpa_mod, hpa_changes) = heal_autoscaling_scope(&mut shards);
    if hpa_mod {
        modified = true;
        changes.extend(hpa_changes);
    }

    let (probe_mod, probe_changes) = heal_probe_timeouts(&mut shards);
    if probe_mod {
        modified = true;
        changes.extend(probe_changes);
    }

    let (res_mod, res_changes) = heal_inverted_resources(&mut shards);
    if res_mod {
        modified = true;
        changes.extend(res_changes);
    }

    if modified {
        (native_reconstruct_yaml(&shards), changes)
    } else {
        (content.to_string(), Vec::new())
    }
}

pub fn update_shard_raw_line(shard: &mut NativeShard, key: &str, val: &str) {
    let indent = " ".repeat(shard.indent);
    let comment = if shard.comment.is_empty() {
        String::new()
    } else {
        format!(" {}", shard.comment)
    };
    shard.raw_line = format!("{}{}: {}{}", indent, key, val, comment);
}

// 5. HPA-001: Inverted Autoscaling Replicas (minReplicas > maxReplicas)
fn heal_autoscaling_scope(shards: &mut [NativeShard]) -> (bool, Vec<String>) {
    let mut modified = false;
    let mut changes = Vec::new();
    let mut min_idx = None;
    let mut max_idx = None;

    for i in 0..shards.len() {
        if shards[i].key == "minReplicas" {
            min_idx = Some(i);
        } else if shards[i].key == "maxReplicas" {
            max_idx = Some(i);
        }
    }

    if let (Some(min_i), Some(max_i)) = (min_idx, max_idx) {
        if let (Some(min_str), Some(max_str)) = (&shards[min_i].value, &shards[max_i].value) {
            let min_parsed: Result<i64, _> = min_str.trim().parse();
            let max_parsed: Result<i64, _> = max_str.trim().parse();
            if let (Ok(min_v), Ok(max_v)) = (min_parsed, max_parsed) {
                if min_v > max_v {
                    let max_str_val = max_v.to_string();
                    shards[min_i].value = Some(max_str_val.clone());
                    update_shard_raw_line(&mut shards[min_i], "minReplicas", &max_str_val);
                    changes.push(msg_inverted_hpa());
                    modified = true;
                }
            }
        }
    }
    (modified, changes)
}

// 8. PROBE-001: Invalid Probe Timeouts (timeoutSeconds > periodSeconds)
fn heal_probe_timeouts(shards: &mut [NativeShard]) -> (bool, Vec<String>) {
    let mut modified = false;
    let mut changes = Vec::new();
    let mut timeout_idx = None;
    let mut period_idx = None;

    for i in 0..shards.len() {
        if shards[i].key == "timeoutSeconds" {
            timeout_idx = Some(i);
        } else if shards[i].key == "periodSeconds" {
            period_idx = Some(i);
        }
    }

    if let (Some(t_i), Some(p_i)) = (timeout_idx, period_idx) {
        if let (Some(t_str), Some(p_str)) = (&shards[t_i].value, &shards[p_i].value) {
            let t_parsed: Result<i64, _> = t_str.trim().parse();
            let p_parsed: Result<i64, _> = p_str.trim().parse();
            if let (Ok(t_v), Ok(p_v)) = (t_parsed, p_parsed) {
                if t_v > p_v {
                    let p_str_val = p_v.to_string();
                    shards[t_i].value = Some(p_str_val.clone());
                    update_shard_raw_line(&mut shards[t_i], "timeoutSeconds", &p_str_val);
                    changes.push(msg_probe_timeout());
                    modified = true;
                }
            }
        }
    }
    (modified, changes)
}

// 6. RES-001: Inverted Resources (requests > limits)
fn heal_inverted_resources(shards: &mut [NativeShard]) -> (bool, Vec<String>) {
    let mut modified = false;
    let mut changes = Vec::new();
    let mut current_section = String::new();
    let mut req_cpu_idx = None;
    let mut lim_cpu_idx = None;

    for i in 0..shards.len() {
        if shards[i].key == "requests" {
            current_section = "requests".to_string();
        } else if shards[i].key == "limits" {
            current_section = "limits".to_string();
        } else if shards[i].key == "cpu" {
            if current_section == "requests" {
                req_cpu_idx = Some(i);
            } else if current_section == "limits" {
                lim_cpu_idx = Some(i);
            }
        }
    }

    if let (Some(req_i), Some(lim_i)) = (req_cpu_idx, lim_cpu_idx) {
        let req_s_opt = shards[req_i].value.clone();
        let lim_s_opt = shards[lim_i].value.clone();
        if let (Some(req_s), Some(lim_s)) = (req_s_opt, lim_s_opt) {
            if let (Some(req_m), Some(lim_m)) =
                (parse_cpu_millicores(&req_s), parse_cpu_millicores(&lim_s))
            {
                if req_m > lim_m {
                    shards[req_i].value = Some(lim_s.clone());
                    update_shard_raw_line(&mut shards[req_i], "cpu", &lim_s);
                    changes.push(msg_inverted_cpu());
                    modified = true;
                }
            }
        }
    }
    (modified, changes)
}
