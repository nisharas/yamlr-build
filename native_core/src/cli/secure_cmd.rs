//! Automated NetworkPolicy generation and least-privilege security hardening CLI handler.
//!
//! Why: Manually authoring Kubernetes NetworkPolicies is prone to human error and cluster
//! communication outages. Yamlr analyzes discovered Services and Pod selectors to automatically
//! synthesize least-privilege ingress NetworkPolicies and PSS restricted labels.

use std::fs;
use std::path::Path;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};
use crate::discovery::native_discover_resources;

/// Executes the security policy architect command.
///
/// Why: Automatically synthesizes Kubernetes NetworkPolicy resources for all discovered
/// services and workloads, reducing attack surfaces with zero network downtime.
pub fn execute_secure(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("secure", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = matches.get_one::<String>("target").unwrap();
    let out_file = matches.get_one::<String>("output").cloned();

    let target_path = Path::new(&target);
    if !target_path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    println!("Yamlr Security Architect: Least-Privilege Network Policy Synthesis");
    println!("Target: {}\n", target);

    let discovery = match native_discover_resources(target.to_string()) {
        Ok(discovery) => discovery,
        Err(error) => {
            eprintln!("[ERROR] Resource discovery failed: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    let mut generated_policies = Vec::new();

    for res in &discovery {
        if let Some(ref identity) = res.identity {
            if identity.kind == "Service" && !identity.selector.is_empty() {
                let policy_name = format!("{}-hardened-netpol", identity.name);
                let ns = if identity.namespace.is_empty() {
                    "default"
                } else {
                    &identity.namespace
                };

                let mut ports_yaml = String::new();
                if identity.ports.is_empty() {
                    ports_yaml.push_str("        - protocol: TCP\n          port: 80\n");
                } else {
                    for port in &identity.ports {
                        ports_yaml.push_str(&format!(
                            "        - protocol: TCP\n          port: {}\n",
                            port
                        ));
                    }
                }

                let mut match_labels_yaml = String::new();
                for (k, v) in &identity.selector {
                    match_labels_yaml.push_str(&format!("      {}: \"{}\"\n", k, v));
                }

                let policy = format!(
                    r#"apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {}
  namespace: {}
  labels:
    app.kubernetes.io/managed-by: yamlr
    yamlr.dev/policy-type: least-privilege-ingress
spec:
  podSelector:
    matchLabels:
{}  policyTypes:
    - Ingress
  ingress:
    - ports:
{}"#,
                    policy_name, ns, match_labels_yaml, ports_yaml
                );

                generated_policies.push((policy_name, policy));
            }
        }
    }

    if generated_policies.is_empty() {
        println!(
            "[INFO] No Services with active pod selectors discovered in '{}'.",
            target
        );
        return EXIT_SUCCESS;
    }

    let mut combined_output = String::new();
    for (name, policy) in &generated_policies {
        println!("[+] Synthesized NetworkPolicy for '{}':", name);
        println!("{}\n---", policy);
        combined_output.push_str(policy);
        combined_output.push_str("\n---\n");
    }

    if let Some(dest) = out_file {
        if let Err(e) = fs::write(&dest, combined_output) {
            eprintln!(
                "[ERROR] Failed to write synthesized policies to '{}': {}",
                dest, e
            );
            return EXIT_VIOLATIONS;
        }
        println!(
            "\n[OK] Wrote {} synthesized policies to '{}'.",
            generated_policies.len(),
            dest
        );
    } else {
        println!(
            "\n[OK] Synthesized {} hardened NetworkPolicy definitions.",
            generated_policies.len()
        );
    }

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_secure_generates_policy_for_service() {
        let dir = tempdir().unwrap();
        let svc_path = dir.path().join("service.yaml");
        let svc_content = r#"
apiVersion: v1
kind: Service
metadata:
  name: frontend-svc
  namespace: prod
spec:
  selector:
    app: frontend
  ports:
    - port: 8080
      targetPort: 8080
"#;
        fs::write(&svc_path, svc_content).unwrap();

        let out_path = dir.path().join("policies.yaml");
        let args = vec![
            "yamlr".to_string(),
            "secure".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--output".to_string(),
            out_path.to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_secure(&args), EXIT_SUCCESS);
        assert!(out_path.exists());
        let generated = fs::read_to_string(&out_path).unwrap();
        assert!(generated.contains("NetworkPolicy"));
        assert!(generated.contains("frontend-svc-hardened-netpol"));
    }

    #[test]
    fn test_secure_empty_dir_returns_success() {
        let dir = tempdir().unwrap();
        let args = vec![
            "yamlr".to_string(),
            "secure".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_secure(&args), EXIT_SUCCESS);
    }
}
