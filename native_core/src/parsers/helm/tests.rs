//! Unit Tests for Helm values and Umbrella Chart Healer.

#[cfg(test)]
mod tests {
    use super::super::umbrella::*;
    use super::super::values::*;
    use std::fs;

    #[test]
    fn test_heal_values_floating_tags_and_pull_policy() {
        let raw = r#"# Main application image
image:
  repository: nginx
  tag: latest # Should be pinned
  pullPolicy: IfNotPresent
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("OPS-002")));
        assert!(changes.iter().any(|c| c.contains("SEC-002")));
        assert!(healed.contains("tag: stable-pinned"));
        assert!(healed.contains("pullPolicy: Always"));
        assert!(healed.contains("# Main application image"));
        assert!(healed.contains("# Should be pinned"));

        // Idempotency check
        let (pass2, changes2) = heal_values_yaml(&healed);
        assert!(changes2.is_empty());
        assert_eq!(pass2, healed);
    }

    #[test]
    fn test_combined_image_latest_pinning() {
        let raw = r#"service:
  image: "myregistry.io/app/frontend:latest"
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("OPS-002")));
        assert!(healed.contains("myregistry.io/app/frontend:stable-pinned"));
    }

    #[test]
    fn test_heal_values_security_context_and_pdb() {
        let raw = r#"securityContext:
  privileged: true
  runAsUser: 0
  runAsNonRoot: false

pdb:
  enabled: true
  minAvailable: 100%
  maxUnavailable: 0
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("SEC-001")));
        assert!(changes.iter().any(|c| c.contains("SEC-004")));
        assert!(changes.iter().any(|c| c.contains("REL-005")));
        assert!(healed.contains("privileged: false"));
        assert!(healed.contains("runAsUser: 10001"));
        assert!(healed.contains("runAsNonRoot: true"));
        assert!(healed.contains("minAvailable: 50%"));
        assert!(healed.contains("maxUnavailable: 1"));
    }

    #[test]
    fn test_heal_values_hpa_and_probe_timeouts() {
        let raw = r#"autoscaling:
  enabled: true
  minReplicas: 10
  maxReplicas: 3

livenessProbe:
  httpGet:
    path: /healthz
  timeoutSeconds: 15
  periodSeconds: 10
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("HPA-001")));
        assert!(changes.iter().any(|c| c.contains("PROBE-001")));
        assert!(healed.contains("minReplicas: 3"));
        assert!(healed.contains("timeoutSeconds: 10"));
    }

    #[test]
    fn test_heal_values_inverted_resources() {
        let raw = r#"resources:
  limits:
    cpu: 500m
  requests:
    cpu: 1000m
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("RES-001")));
        assert!(healed.contains("cpu: 500m"));
    }

    #[test]
    fn test_heal_values_ingress_and_secrets() {
        let raw = r#"ingress:
  annotations:
    kubernetes.io/ingress.class: nginx

database:
  user: app
  password: "supersecretpassword123"
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("ING-001")));
        assert!(changes.iter().any(|c| c.contains("SEC-003")));
        assert!(healed.contains("ingressClassName: nginx"));
        assert!(healed.contains("# yamlr [SEC-003]:"));
    }

    #[test]
    fn test_is_helm_values_detection() {
        assert!(is_helm_values_content(
            "replicaCount: 3\nimage:\n  repository: nginx\n"
        ));
        assert!(!is_helm_values_content(
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\n"
        ));
    }

    #[test]
    fn test_umbrella_subcharts_traversal_and_healing() {
        let temp_dir = std::env::temp_dir().join("yamlr_test_umbrella");
        let _ = fs::remove_dir_all(&temp_dir);
        let sub_dir = temp_dir.join("charts").join("sub-service");
        fs::create_dir_all(&sub_dir).unwrap();

        let root_values = "image:\n  tag: latest\n";
        let sub_values = "securityContext:\n  runAsUser: 0\n";

        fs::write(temp_dir.join("values.yaml"), root_values).unwrap();
        fs::write(sub_dir.join("values.yaml"), sub_values).unwrap();

        let results = heal_umbrella_chart(temp_dir.to_str().unwrap()).unwrap();
        assert_eq!(results.len(), 2);
        assert!(results
            .iter()
            .any(|r| r.healed_yaml.contains("tag: stable-pinned")));
        assert!(results
            .iter()
            .any(|r| r.healed_yaml.contains("runAsUser: 10001")));

        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_heal_values_oci_registry() {
        let raw = "repository: oci://ghcr.io/org/charts/mychart\n";
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("DEP-001")));
        assert!(
            healed.contains("validated oci registry") || healed.contains("Validated OCI registry")
        );
    }

    #[test]
    fn test_heal_values_ambiguous_boolean_strings() {
        let raw = r#"# Feature toggles
enabled: "false"
create: 'false'
active: "true"
otherString: "false" # Arbitrary string, should NOT be normalized
"#;
        let (healed, changes) = heal_values_yaml(raw);
        assert!(changes.iter().any(|c| c.contains("TYP-001")));
        assert!(healed.contains("enabled: false"));
        assert!(healed.contains("create: false"));
        assert!(healed.contains("active: true"));
        assert!(healed.contains("otherString: \"false\""));

        // Idempotency check
        let (pass2, changes2) = heal_values_yaml(&healed);
        assert!(changes2.is_empty());
        assert_eq!(pass2, healed);
    }
}
