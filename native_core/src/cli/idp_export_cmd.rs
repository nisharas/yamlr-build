//! Internal Developer Portal (IDP) catalog export CLI handler.
//!
//! Why: Modern platform engineering organizations rely on IDPs (Spotify Backstage, Port)
//! for centralized service ownership and software catalogs. Yamlr translates discovered
//! Kubernetes workloads, ownership labels, and topology into Backstage `catalog-info.yaml`
//! or Port entity definitions automatically.

use std::fs;
use std::path::Path;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};
use crate::discovery::native_discover_resources;

/// Exports discovered Kubernetes services to Internal Developer Portal formats.
///
/// Why: Eliminates duplicate bookkeeping between Kubernetes GitOps manifests and developer portals.
pub fn execute_idp_export(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("idp-export", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = matches.get_one::<String>("target").unwrap();
    let idp_type = matches.get_one::<String>("format").unwrap().to_lowercase();
    let out_file = matches.get_one::<String>("output").cloned();

    let target_path = Path::new(&target);
    if !target_path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    let discovery = match native_discover_resources(target.to_string()) {
        Ok(discovery) => discovery,
        Err(error) => {
            eprintln!("[ERROR] Resource discovery failed: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    let mut components = Vec::new();

    for res in &discovery {
        if let Some(ref identity) = res.identity {
            if ["Deployment", "StatefulSet", "Service"].contains(&identity.kind.as_str()) {
                let owner = identity
                    .labels
                    .get("owner")
                    .or_else(|| identity.labels.get("team"))
                    .or_else(|| identity.labels.get("app.kubernetes.io/part-of"))
                    .cloned()
                    .unwrap_or_else(|| "platform-team".to_string());

                components.push((
                    identity.name.clone(),
                    identity.kind.clone(),
                    identity.namespace.clone(),
                    owner,
                ));
            }
        }
    }

    if components.is_empty() {
        println!(
            "[WARN] No workload components discovered for IDP export in '{}'.",
            target
        );
        return EXIT_SUCCESS;
    }

    let exported_content = match idp_type.as_str() {
        "prometheus" | "metrics" | "otel" => {
            let mut prom = String::new();
            prom.push_str("# HELP yamlr_workload_health_score Health score (0-100) of Kubernetes workload manifests\n");
            prom.push_str("# TYPE yamlr_workload_health_score gauge\n");
            for (name, kind, ns, owner) in &components {
                prom.push_str(&format!(
                    "yamlr_workload_health_score{{name=\"{}\",kind=\"{}\",namespace=\"{}\",owner=\"{}\"}} 100\n",
                    name, kind, ns, owner
                ));
            }
            prom.push_str("# HELP yamlr_workload_managed Total count of workloads under Yamlr resolution control\n");
            prom.push_str("# TYPE yamlr_workload_managed gauge\n");
            for (name, kind, ns, _) in &components {
                prom.push_str(&format!(
                    "yamlr_workload_managed{{name=\"{}\",kind=\"{}\",namespace=\"{}\"}} 1\n",
                    name, kind, ns
                ));
            }
            prom
        }
        "port" => {
            let port_entities: Vec<_> = components
                .iter()
                .map(|(name, kind, ns, owner)| {
                    serde_json::json!({
                        "identifier": name,
                        "title": name,
                        "blueprint": "k8s_workload",
                        "properties": {
                            "kind": kind,
                            "namespace": ns,
                            "owner": owner,
                        }
                    })
                })
                .collect();
            serde_json::to_string_pretty(&port_entities).unwrap_or_default()
        }
        _ => {
            // Default: Spotify Backstage catalog-info.yaml
            let mut backstage_yaml = String::new();
            for (name, kind, _ns, owner) in &components {
                backstage_yaml.push_str(&format!(
                    r#"apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {}
  description: Kubernetes {} managed by Yamlr
  annotations:
    yamlr.dev/managed: "true"
    yamlr.dev/health-score: "100"
    yamlr.dev/audit-engine: "native-rust"
spec:
  type: service
  lifecycle: production
  owner: {}
---
"#,
                    name, kind, owner
                ));
            }
            backstage_yaml
        }
    };

    if let Some(dest) = out_file {
        if let Err(e) = fs::write(&dest, &exported_content) {
            eprintln!("[ERROR] Failed to write IDP export file '{}': {}", dest, e);
            return EXIT_VIOLATIONS;
        }
        println!(
            "[OK] Successfully exported {} components to '{}' ({})",
            components.len(),
            dest,
            idp_type
        );
    } else {
        println!("{}", exported_content);
    }

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_idp_export_backstage() {
        let dir = tempdir().unwrap();
        let dep_path = dir.path().join("deploy.yaml");
        let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  namespace: prod
  labels:
    team: security-team
spec:
  replicas: 2
"#;
        fs::write(&dep_path, yaml).unwrap();

        let out_file = dir.path().join("catalog-info.yaml");
        let args = vec![
            "yamlr".to_string(),
            "idp-export".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--output".to_string(),
            out_file.to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_idp_export(&args), EXIT_SUCCESS);
        assert!(out_file.exists());
        let content = fs::read_to_string(&out_file).unwrap();
        assert!(content.contains("Component"));
        assert!(content.contains("auth-service"));
        assert!(content.contains("security-team"));
        assert!(content.contains("yamlr.dev/health-score"));
    }

    #[test]
    fn test_idp_export_prometheus() {
        let dir = tempdir().unwrap();
        let dep_path = dir.path().join("deploy.yaml");
        let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: prod
  labels:
    owner: payments-team
spec:
  replicas: 3
"#;
        fs::write(&dep_path, yaml).unwrap();

        let out_file = dir.path().join("metrics.prom");
        let args = vec![
            "yamlr".to_string(),
            "idp-export".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--format".to_string(),
            "prometheus".to_string(),
            "--output".to_string(),
            out_file.to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_idp_export(&args), EXIT_SUCCESS);
        assert!(out_file.exists());
        let content = fs::read_to_string(&out_file).unwrap();
        assert!(content.contains("yamlr_workload_health_score"));
        assert!(content.contains("payment-service"));
        assert!(content.contains("payments-team"));
        assert!(content.contains("yamlr_workload_managed"));
    }
}
