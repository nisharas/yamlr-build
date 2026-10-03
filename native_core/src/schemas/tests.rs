//! Comprehensive Unit Tests for Schema and CRD Intelligence Engine.

#[cfg(test)]
mod unit_tests {
    use super::super::bundler::*;
    use super::super::distiller::*;
    use super::super::validator::*;
    use crate::models::{NativeSchema, SchemaProperty};
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_schema_bundle_loaded() {
        let bundle = get_bundle();
        assert!(bundle.contains_key("1.21"));
        assert!(bundle.contains_key("1.25"));
        assert!(bundle.contains_key("1.30"));
        assert!(bundle.contains_key("1.36"));
        assert!(bundle.contains_key("1.37"));
    }

    #[test]
    fn test_get_schema_for_version() {
        let schemas = native_get_schema_for_version("1.30");
        assert!(!schemas.is_empty());
        let pod_schema = schemas.iter().find(|s| s.kind == "Pod");
        assert!(pod_schema.is_some());
        let ps = pod_schema.unwrap();
        assert!(ps
            .properties
            .iter()
            .any(|p| p.name == "metadata" && p.required));
        assert!(ps.properties.iter().any(|p| p.name == "spec" && p.required));
    }

    #[test]
    fn test_validate_ast_against_schema_missing_spec() {
        let yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test-pod\n";
        let shards = native_shard(yaml);
        let manifest = native_structurize(shards);
        let schemas = native_get_schema_for_version("1.30");

        let violations = native_validate_ast_against_schema(&manifest, &schemas);
        assert!(violations.iter().any(|v| v.field_path == "spec"));
        assert!(!violations.iter().any(|v| v.field_path == "metadata"));
        assert!(!violations.iter().any(|v| v.field_path == "apiVersion"));
    }

    #[test]
    fn test_comment_false_positive_resistance() {
        let yaml = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: my-config\n# kind: Pod\ndata:\n  key: value\n";
        let shards = native_shard(yaml);
        let manifest = native_structurize(shards);
        let schemas = native_get_schema_for_version("1.30");

        let violations = native_validate_ast_against_schema(&manifest, &schemas);
        assert!(!violations
            .iter()
            .any(|v| v.message.contains("for Kind 'Pod'")));
    }

    #[test]
    fn test_forward_compatible_schema_v1_38_plus() {
        let schemas_38 = native_get_schema_for_version("1.38");
        assert!(!schemas_38.is_empty());
        assert!(schemas_38.iter().any(|s| s.kind == "Deployment"));

        let schemas_40 = native_get_schema_for_version("v1.40.1");
        assert!(!schemas_40.is_empty());
        assert!(schemas_40.iter().any(|s| s.kind == "Pod"));
    }

    #[test]
    fn test_embedded_cncf_crds_loaded() {
        let crd_schemas = get_cncf_crd_schemas();
        assert!(!crd_schemas.is_empty());
        assert!(crd_schemas.iter().any(|s| s.kind == "ServiceMonitor"));
        assert!(crd_schemas.iter().any(|s| s.kind == "Certificate"));
        assert!(crd_schemas.iter().any(|s| s.kind == "VirtualService"));
        assert!(crd_schemas.iter().any(|s| s.kind == "HTTPRoute"));
        assert!(crd_schemas.iter().any(|s| s.kind == "Rollout"));
        assert!(crd_schemas.iter().any(|s| s.kind == "Application"));
        // Check new 10 CNCF additions
        assert!(crd_schemas.iter().any(|s| s.kind == "ExternalSecret"));
        assert!(crd_schemas.iter().any(|s| s.kind == "SecretStore"));
        assert!(crd_schemas.iter().any(|s| s.kind == "ClusterSecretStore"));
        assert!(crd_schemas.iter().any(|s| s.kind == "CiliumNetworkPolicy"));
        assert!(crd_schemas
            .iter()
            .any(|s| s.kind == "CiliumClusterwideNetworkPolicy"));
        assert!(crd_schemas.iter().any(|s| s.kind == "IngressRoute"));
        assert!(crd_schemas.iter().any(|s| s.kind == "Workflow"));
        assert!(crd_schemas.iter().any(|s| s.kind == "CronWorkflow"));
        assert!(crd_schemas.iter().any(|s| s.kind == "Provider"));
        assert!(crd_schemas.iter().any(|s| s.kind == "PodMonitor"));
    }

    #[test]
    fn test_cncf_crd_missing_required_spec() {
        let yaml = "apiVersion: monitoring.coreos.com/v1\nkind: ServiceMonitor\nmetadata:\n  name: prometheus-monitor\n";
        let shards = native_shard(yaml);
        let manifest = native_structurize(shards);
        let schemas = native_get_schema_for_version("1.30");

        let violations = native_validate_ast_against_schema(&manifest, &schemas);
        assert!(violations
            .iter()
            .any(|v| v.field_path == "spec" && v.message.contains("ServiceMonitor")));
    }

    #[test]
    fn test_distill_crd_content_v1() {
        let crd_yaml = r#"
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  names:
    kind: CronTab
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec"]
              properties:
                cronSpec:
                  type: string
                replicas:
                  type: integer
"#;
        let schemas = distill_crd_content(crd_yaml).unwrap();
        assert_eq!(schemas.len(), 1);
        let s = &schemas[0];
        assert_eq!(s.kind, "CronTab");
        assert_eq!(s.api_version, "stable.example.com/v1");
        assert!(s.properties.iter().any(|p| p.name == "spec" && p.required));
    }

    #[test]
    fn test_distill_crd_content_v1beta1() {
        let crd_yaml = r#"
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: legacycrds.example.com
spec:
  group: example.com
  version: v1beta1
  names:
    kind: LegacyCRD
  validation:
    openAPIV3Schema:
      type: object
      properties:
        spec:
          type: object
          properties:
            mode:
              type: string
              enum: ["Fast", "Safe", "Strict"]
"#;
        let schemas = distill_crd_content(crd_yaml).unwrap();
        assert_eq!(schemas.len(), 1);
        let s = &schemas[0];
        assert_eq!(s.kind, "LegacyCRD");
        assert_eq!(s.api_version, "example.com/v1beta1");
        assert!(s.properties.iter().any(|p| p.name == "spec"));
    }

    #[test]
    fn test_distill_crd_multi_doc() {
        let yaml = r#"
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crd1.example.com
spec:
  group: example.com
  names:
    kind: FirstCRD
  versions:
    - name: v1
      schema:
        openAPIV3Schema:
          type: object
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crd2.example.com
spec:
  group: example.com
  names:
    kind: SecondCRD
  versions:
    - name: v1alpha1
      schema:
        openAPIV3Schema:
          type: object
"#;
        let schemas = distill_crd_content(yaml).unwrap();
        assert_eq!(schemas.len(), 2);
        assert_eq!(schemas[0].kind, "FirstCRD");
        assert_eq!(schemas[1].kind, "SecondCRD");
    }

    #[test]
    fn test_ast_type_and_enum_validation() {
        let custom_schema = NativeSchema {
            kind: "AppConfig".to_string(),
            api_version: "custom/v1".to_string(),
            properties: vec![
                SchemaProperty {
                    name: "port".to_string(),
                    prop_type: "integer".to_string(),
                    required: true,
                    description: "Port number".to_string(),
                    enum_values: Vec::new(),
                },
                SchemaProperty {
                    name: "active".to_string(),
                    prop_type: "boolean".to_string(),
                    required: false,
                    description: "Active flag".to_string(),
                    enum_values: Vec::new(),
                },
                SchemaProperty {
                    name: "environment".to_string(),
                    prop_type: "string".to_string(),
                    required: false,
                    description: "Deployment env".to_string(),
                    enum_values: vec!["production".to_string(), "staging".to_string()],
                },
            ],
        };

        let yaml = "apiVersion: custom/v1\nkind: AppConfig\nport: \"not-a-number\"\nactive: not-bool\nenvironment: development\n";
        let shards = native_shard(yaml);
        let manifest = native_structurize(shards);

        let violations = native_validate_ast_against_schema(&manifest, &[custom_schema.clone()]);
        assert!(violations
            .iter()
            .any(|v| v.field_path == "port" && v.message.contains("Type mismatch")));
        assert!(violations
            .iter()
            .any(|v| v.field_path == "active" && v.message.contains("Type mismatch")));
        assert!(violations
            .iter()
            .any(|v| v.field_path == "environment" && v.message.contains("Invalid value")));
        let empty_enum = yaml.replace("environment: development", "environment: \"\"");
        let empty_manifest = native_structurize(native_shard(&empty_enum));
        assert!(
            native_validate_ast_against_schema(&empty_manifest, &[custom_schema])
                .iter()
                .any(|violation| violation.field_path == "environment"
                    && violation.message.contains("Invalid value"))
        );
    }

    #[test]
    fn test_openapi_v31_structural_unions() {
        let union_schema = NativeSchema {
            kind: "ModernApp".to_string(),
            api_version: "apps/v1".to_string(),
            properties: vec![
                SchemaProperty {
                    name: "targetPort".to_string(),
                    prop_type: "[\"integer\", \"string\"]".to_string(),
                    required: true,
                    description: "IntOrString port".to_string(),
                    enum_values: Vec::new(),
                },
                SchemaProperty {
                    name: "replicas".to_string(),
                    prop_type: "[\"integer\", \"null\"]".to_string(),
                    required: false,
                    description: "Nullable integer".to_string(),
                    enum_values: Vec::new(),
                },
            ],
        };

        // Test with integer targetPort and null replicas
        let yaml_int = "apiVersion: apps/v1\nkind: ModernApp\ntargetPort: 8080\nreplicas: null\n";
        let manifest_int = native_structurize(native_shard(yaml_int));
        let violations_int =
            native_validate_ast_against_schema(&manifest_int, &[union_schema.clone()]);
        assert_eq!(violations_int.len(), 0);

        // Test with string targetPort and integer replicas
        let yaml_str =
            "apiVersion: apps/v1\nkind: ModernApp\ntargetPort: \"http-web\"\nreplicas: 3\n";
        let manifest_str = native_structurize(native_shard(yaml_str));
        let violations_str =
            native_validate_ast_against_schema(&manifest_str, &[union_schema.clone()]);
        assert_eq!(violations_str.len(), 0);
    }

    #[test]
    fn test_all_versions_v1_21_through_v1_37_resolvable() {
        for minor in 21..=37 {
            let ver = format!("1.{}", minor);
            let schemas = native_get_schema_for_version(&ver);
            assert!(
                !schemas.is_empty(),
                "Failed to resolve embedded schema for v{}",
                ver
            );
            assert!(
                schemas.iter().any(|s| s.kind == "Pod"),
                "Missing Pod in v{}",
                ver
            );
        }
    }

    #[test]
    fn test_tier1_cache_resolution() {
        let temp_dir = tempfile::tempdir().unwrap();
        let custom_schema_file = temp_dir.path().join("k8s_v1.99_distilled.json");
        let fake_schema = r#"{
            "CustomFutureKind": {
                "apiVersion": "future.io/v1",
                "fields": {
                    "spec": { "type": "object" }
                }
            }
        }"#;
        std::fs::write(&custom_schema_file, fake_schema).unwrap();

        // Test with YAMLR_SCHEMA_DIR pointing to temp_dir (Tier 2)
        std::env::set_var("YAMLR_SCHEMA_DIR", temp_dir.path().to_str().unwrap());
        let schemas = native_get_schema_for_version("1.99");
        std::env::remove_var("YAMLR_SCHEMA_DIR");

        assert!(schemas.iter().any(|s| s.kind == "CustomFutureKind"));
    }

    #[test]
    fn test_tier4_future_version_resolution() {
        // Test v1.38 fallback to v1.37 baseline
        let schemas_38 = native_get_schema_for_version("1.38");
        assert!(!schemas_38.is_empty());
        assert!(schemas_38.iter().any(|s| s.kind == "Pod"));
        assert!(schemas_38
            .iter()
            .any(|s| s.kind == "ValidatingAdmissionPolicy"));

        // Test v1.45 forward-compatible fallback
        let schemas_45 = native_get_schema_for_version("v1.45.0");
        assert!(!schemas_45.is_empty());
        assert!(schemas_45.iter().any(|s| s.kind == "Deployment"));
    }
}
