use super::*;
use serde::Deserialize;
use std::fs;
use tempfile::tempdir;

#[test]
fn heal_parser_uses_compact_options_and_rejects_duplicate_aliases() {
    let args = [
        "yamlr",
        "heal",
        "-k1.31",
        "-otext",
        "-ad",
        "--",
        "-manifest.yaml",
    ]
    .map(str::to_string);
    let parsed = parse_heal_arguments(&args).unwrap();
    assert_eq!(parsed.get_one::<String>("k8s-version").unwrap(), "1.31");
    assert_eq!(
        parsed.get_one::<String>("target").unwrap(),
        "-manifest.yaml"
    );
    assert!(parsed.get_flag("apply"));
    assert!(parsed.get_flag("dry-run"));
    for tail in [
        vec!["--unknown"],
        vec!["--ingest-opa"],
        vec!["--k8s-version", "1.30", "-k1.31"],
        vec!["one.yaml", "two.yaml"],
    ] {
        let args = [vec!["yamlr", "heal"], tail]
            .concat()
            .into_iter()
            .map(str::to_string)
            .collect::<Vec<_>>();
        assert!(parse_heal_arguments(&args).is_err());
    }
}

#[test]
fn apply_with_dry_run_never_writes_generated_stubs() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("deployment.yaml");
    let yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: nginx\n          envFrom:\n            - secretRef:\n                name: missing-secret\n";
    fs::write(&manifest, yaml).unwrap();
    let args = vec![
        "yamlr".into(),
        "heal".into(),
        dir.path().to_str().unwrap().into(),
        "-ad".into(),
        "--generate-stubs".into(),
        "--exit-zero".into(),
    ];
    assert_eq!(execute_heal(&args), EXIT_SUCCESS);
    assert_eq!(fs::read_to_string(manifest).unwrap(), yaml);
    assert!(!dir.path().join("yamlr_generated_stubs.yaml").exists());
}

#[test]
fn test_heal_manifest_string_preserves_comments() {
    let yaml = "# Header Comment\napiVersion: v1\nkind: Service\nmetadata:\n  name: app\nspec:\n  ports:\n    - port: 80\n";
    let (healed, _) = heal_manifest_string(yaml);
    assert!(healed.contains("# Header Comment"));
}

#[test]
fn heal_rejects_unsupported_output_with_usage_exit_code() {
    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        "missing-target.yaml".to_string(),
        "--output".to_string(),
        "xml".to_string(),
    ];

    assert_eq!(execute_heal(&args), EXIT_USAGE);
}

#[test]
fn healing_preserves_complex_yaml_and_is_idempotent() {
    let yaml = concat!(
        "# Keep this note\r\n",
        "apiVersion: v1\r\n",
        "kind: Pod\r\n",
        "metadata:\r\n",
        "  name: sample\r\n",
        "  annotations:\r\n",
        "    \"quoted:key\": &note |-\r\n",
        "      first line\r\n",
        "      # scalar content\r\n",
        "    copied-note: *note\r\n",
        "    yamlr.dev/pin-tags: \"true\"\r\n",
        "spec:\r\n",
        "  containers:\r\n",
        "    - name: app\r\n",
        "      image: nginx:latest\r\n",
    );

    let original_value: serde_yaml::Value = serde_yaml::from_str(yaml).unwrap();
    let (healed, changes) = heal_manifest_string(yaml);
    assert!(
        !changes.is_empty(),
        "fixture must exercise an actual repair"
    );
    assert!(healed.contains("# Keep this note"));
    assert!(
        healed.contains("\"quoted:key\": &note |-"),
        "healed YAML changed the quoted anchored block scalar: {healed:?}"
    );
    assert!(healed.contains("copied-note: *note"));
    assert!(healed.contains("      # scalar content"));
    assert!(!healed.replace("\r\n", "").contains('\n'));

    let healed_value: serde_yaml::Value = serde_yaml::from_str(&healed).unwrap();
    assert_ne!(
        healed_value, original_value,
        "the image tag should be repaired"
    );

    let (healed_again, second_changes) = heal_manifest_string(&healed);
    assert_eq!(healed_again, healed);
    assert!(second_changes.is_empty());
}

#[test]
fn healing_multi_document_crlf_stream_preserves_line_endings() {
    let yaml = concat!(
        "# Configuration\r\n",
        "apiVersion: v1\r\n",
        "kind: ConfigMap\r\n",
        "metadata:\r\n",
        "  name: settings\r\n",
        "data:\r\n",
        "  mode: safe\r\n",
        "---\r\n",
        "apiVersion: v1\r\n",
        "kind: Pod\r\n",
        "metadata:\r\n",
        "  name: sample\r\n",
        "  annotations:\r\n",
        "    yamlr.dev/pin-tags: \"true\"\r\n",
        "spec:\r\n",
        "  containers:\r\n",
        "    - name: app\r\n",
        "      image: nginx:latest\r\n",
    );

    let (healed, changes) = heal_manifest_string(yaml);
    assert!(
        !changes.is_empty(),
        "fixture must exercise an actual repair"
    );
    assert!(!healed.replace("\r\n", "").contains('\n'));
    assert!(healed.contains("# Configuration\r\n"));
    assert_eq!(
        serde_yaml::Deserializer::from_str(&healed)
            .map(|document| serde_yaml::Value::deserialize(document).unwrap())
            .count(),
        2
    );

    let (healed_again, second_changes) = heal_manifest_string(&healed);
    assert_eq!(healed_again, healed);
    assert!(second_changes.is_empty());
}

#[test]
fn test_versioned_healing_uses_schema_api_version_only_when_missing() {
    let schemas = vec![crate::models::NativeSchema {
        kind: "Widget".into(),
        api_version: "example.io/v1alpha1".into(),
        properties: Vec::new(),
    }];
    let (healed, changes) = heal_manifest_string_with_schemas("kind: Widget\n", &schemas);
    assert!(!crate::sharder::native_shard(&healed).is_empty());
    assert!(healed.contains("apiVersion: example.io/v1alpha1"));
    assert_eq!(changes.len(), 1);

    let explicit = "apiVersion: example.io/v1\nkind: Widget\n";
    let (unchanged, changes) = heal_manifest_string_with_schemas(explicit, &schemas);
    assert_eq!(unchanged, explicit);
    assert!(changes.is_empty());
}

#[test]
fn test_execute_heal_dry_run_exits_success() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("pod.yaml");
    fs::write(
        &file_path,
        "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n",
    )
    .unwrap();

    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--exit-zero".to_string(),
    ];
    assert_eq!(execute_heal(&args), EXIT_SUCCESS);
}

#[test]
fn test_execute_heal_generate_stubs_flag() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("workload.yaml");
    let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  template:
    spec:
      containers:
        - name: app
          image: nginx:1.25
          envFrom:
            - configMapRef:
                name: missing-api-config
"#;
    fs::write(&file_path, yaml).unwrap();

    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--generate-stubs".to_string(),
        "--apply".to_string(),
    ];
    let code = execute_heal(&args);
    assert_eq!(code, EXIT_SUCCESS);
    assert!(dir.path().join("yamlr_generated_stubs.yaml").exists());
}

#[test]
fn test_execute_heal_create_stubs_synonym() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("workload.yaml");
    let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template:
    spec:
      containers:
        - name: app
          image: nginx
          envFrom:
            - secretRef:
                name: missing-secret
"#;
    fs::write(&file_path, yaml).unwrap();

    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--create-stubs".to_string(),
        "--apply".to_string(),
    ];
    let code = execute_heal(&args);
    assert_eq!(code, EXIT_SUCCESS);
    assert!(dir.path().join("yamlr_generated_stubs.yaml").exists());
}

#[test]
fn test_execute_heal_ingest_opa() {
    let dir = tempdir().unwrap();
    let manifest_path = dir.path().join("deploy.yaml");
    let yaml =
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-app\nspec:\n  replicas: 1\n";
    fs::write(&manifest_path, yaml).unwrap();

    let opa_report = dir.path().join("opa.json");
    let report_json = r#"{
        "violations": [
            {
                "constraint": "require-labels",
                "resource": { "kind": "Deployment", "name": "my-app" },
                "message": "Missing label"
            }
        ]
    }"#;
    fs::write(&opa_report, report_json).unwrap();

    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--ingest-opa".to_string(),
        opa_report.to_str().unwrap().to_string(),
        "--apply".to_string(),
        "--exit-zero".to_string(),
    ];
    let code = execute_heal(&args);
    assert_eq!(code, EXIT_SUCCESS);
}

#[test]
fn test_multidoc_transactional_abort_on_corrupt_doc() {
    // If one document is corrupted or fails verification, the whole transaction must abort
    let yaml = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm\n---\n:::invalid_yaml:::\n";
    let (healed, changes) = heal_manifest_string(yaml);
    assert!(changes.is_empty());
    assert_eq!(healed, yaml);
}

#[test]
fn test_crd_topological_dependency_ordering() {
    // Multi-doc where CustomResource appears BEFORE CustomResourceDefinition
    let yaml = "apiVersion: mygroup.io/v1\nkind: MyCustomResource\nmetadata:\n  name: my-cr\n---\napiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\nmetadata:\n  name: mycustomresources.mygroup.io\n";
    let (healed, changes) = heal_manifest_string(yaml);
    assert!(!changes.is_empty());
    assert!(changes.iter().any(|c| c.contains("[TOPOLOGY-001]")));
    // The CRD must appear first in healed output
    let crd_pos = healed.find("CustomResourceDefinition").unwrap();
    let cr_pos = healed.find("MyCustomResource").unwrap();
    assert!(
        crd_pos < cr_pos,
        "CRD must be emitted before CustomResource instance"
    );
}

#[test]
fn test_execute_heal_rejects_admission_review_output() {
    for format in ["admission-review", "json", "sarif"] {
        let args = vec![
            "yamlr".to_string(),
            "heal".to_string(),
            "missing-target-must-not-be-read".to_string(),
            "--output".to_string(),
            format.to_string(),
        ];
        assert_eq!(
            execute_heal(&args),
            EXIT_USAGE,
            "format {format} must be rejected"
        );
    }
}

#[test]
fn test_directory_mode_multi_file_identity_graph_cross_healing() {
    let dir = tempdir().unwrap();
    let deploy_file = dir.path().join("deployment.yaml");
    let svc_file = dir.path().join("service.yaml");

    let deploy_yaml = r#"apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: prod
  labels:
    app: payment-processor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: payment-processor
  template:
    metadata:
      labels:
        app: payment-processor
    spec:
      containers:
        - name: payment
          image: payments:1.0.0
          ports:
            - containerPort: 8080
              name: http
"#;

    let svc_yaml = r#"apiVersion: v1
kind: Service
metadata:
  name: payment-api-svc
  namespace: prod
spec:
  selector:
    app: payment-processr
  ports:
    - port: 80
      targetPort: 80
"#;

    fs::write(&deploy_file, deploy_yaml).unwrap();
    fs::write(&svc_file, svc_yaml).unwrap();

    let args = vec![
        "yamlr".to_string(),
        "heal".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--apply".to_string(),
        "--exit-zero".to_string(),
    ];

    let code = execute_heal(&args);
    assert_eq!(code, EXIT_SUCCESS);

    let healed_svc = fs::read_to_string(&svc_file).unwrap();
    assert!(
        healed_svc.contains("payment-processor"),
        "Service selector must be aligned across files using workspace identity graph"
    );
    assert!(
        healed_svc.contains("targetPort: 8080"),
        "Service targetPort must be aligned to containerPort 8080 across files"
    );
}

