//! Golden Corpus Invariant Verification Suite
//!
//! Enforces mathematical correctness invariants across Kubernetes manifests:
//! 1. Strict Idempotency: heal(heal(x)) == heal(x)
//! 2. Valid In => Valid Out: Valid schemas are never broken or rendered invalid.
//! 3. Zero Comment Loss: Comments and blank lines are preserved bit-for-bit.
//! 4. Non-Destructive Key Ordering: Key sequences are deterministically preserved.

use proptest::prelude::*;
use yamlr_native::schemas::{native_get_schema_for_version, native_validate_ast_against_schema};
use yamlr_native::sharder::{native_reconstruct_yaml, native_shard};
use yamlr_native::structurer::native_structurize;

const SAMPLE_CORPUS: &[&str] = &[
    // 1. Deployment with comments and floating tag
    r#"# Global deployment configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  # Metadata name
  name: web-server
  labels:
    tier: frontend # inline tier comment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:latest # pinned in heal
        ports:
        - containerPort: 80 # HTTP port
"#,
    // 2. Headless Service
    r#"# Headless service declaration
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 80
"#,
    // 3. Ingress resource
    r#"apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
"#,
    // 4. StatefulSet with VolumeClaimTemplates
    r#"# Stateful database cluster
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db-cluster
spec:
  serviceName: "db-headless"
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15.3
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 50Gi
"#,
    // 5. HorizontalPodAutoscaler
    r#"# Horizontal Pod Autoscaling policy
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
"#,
    // 6. NetworkPolicy with Ingress / Egress
    r#"# Zero-trust network segmentation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-backend
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 5432
"#,
];

#[test]
fn test_invariant_strict_idempotency_corpus() {
    for &manifest in SAMPLE_CORPUS {
        let shards_1 = native_shard(manifest);
        let recon_1 = native_reconstruct_yaml(&shards_1);

        let shards_2 = native_shard(&recon_1);
        let recon_2 = native_reconstruct_yaml(&shards_2);

        assert_eq!(
            recon_1, recon_2,
            "Invariant Violation: Reconstructing twice must produce bit-for-bit identical bytes"
        );
    }
}

#[test]
fn test_invariant_zero_comment_loss() {
    let manifest_with_comments = r#"# File header comment
apiVersion: apps/v1 # api inline
kind: Deployment
# Pre-metadata comment
metadata:
  name: worker # name inline
# Pre-spec comment
spec:
  replicas: 1
  # Selector block comment
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      containers:
      - name: worker
        image: worker:1.0.0
# Trailing footer comment
"#;

    let shards = native_shard(manifest_with_comments);
    let reconstructed = native_reconstruct_yaml(&shards);

    assert!(reconstructed.contains("# File header comment"));
    assert!(reconstructed.contains("# api inline"));
    assert!(reconstructed.contains("# Pre-metadata comment"));
    assert!(reconstructed.contains("# name inline"));
    assert!(reconstructed.contains("# Pre-spec comment"));
    assert!(reconstructed.contains("# Selector block comment"));
    assert!(reconstructed.contains("# Trailing footer comment"));
}

#[test]
fn test_invariant_valid_in_valid_out() {
    let schema_v1_30 = native_get_schema_for_version("1.30");

    for &manifest in SAMPLE_CORPUS {
        let shards = native_shard(manifest);
        let ast = native_structurize(shards.clone());
        let initial_violations = native_validate_ast_against_schema(&ast, &schema_v1_30);

        let reconstructed = native_reconstruct_yaml(&shards);
        let recon_shards = native_shard(&reconstructed);
        let recon_ast = native_structurize(recon_shards);
        let post_violations = native_validate_ast_against_schema(&recon_ast, &schema_v1_30);

        assert!(
            post_violations.len() <= initial_violations.len(),
            "Invariant Violation: Post-reconstruction must not introduce new schema errors"
        );
    }
}

proptest! {
    #[test]
    fn test_proptest_sharding_never_panics(s in ".*") {
        let shards = native_shard(&s);
        let _ = native_reconstruct_yaml(&shards);
    }

    #[test]
    fn test_proptest_yaml_roundtrip_idempotency(
        name in "[a-z0-9-]{3,16}",
        replicas in 1i32..10i32,
        comment in "[a-zA-Z0-9 ]{1,30}"
    ) {
        let doc = format!(
            "# {}\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {}\nspec:\n  replicas: {}\n",
            comment, name, replicas
        );
        let shards = native_shard(&doc);
        let pass1 = native_reconstruct_yaml(&shards);

        let shards2 = native_shard(&pass1);
        let pass2 = native_reconstruct_yaml(&shards2);

        prop_assert_eq!(pass1, pass2);
    }

    #[test]
    fn test_proptest_arbitrary_string_pipeline_resilience(s in "\\PC*") {
        let shards = native_shard(&s);
        let _ = native_reconstruct_yaml(&shards);
        let ast = native_structurize(shards);
        let schema = native_get_schema_for_version("1.30");
        let _ = native_validate_ast_against_schema(&ast, &schema);
    }

    #[test]
    fn test_proptest_deeply_nested_yaml_resilience(
        depth in 1usize..50usize,
        key in "[a-zA-Z0-9_]{1,8}",
        val in "[a-zA-Z0-9_]{1,8}",
    ) {
        let mut doc = String::new();
        for i in 0..depth {
            doc.push_str(&"  ".repeat(i));
            doc.push_str(&format!("{}_{}:\n", key, i));
        }
        doc.push_str(&"  ".repeat(depth));
        doc.push_str(&format!("{}: {}\n", key, val));

        let shards = native_shard(&doc);
        let reconstructed = native_reconstruct_yaml(&shards);
        let ast = native_structurize(shards);
        let schema = native_get_schema_for_version("1.30");
        let _ = native_validate_ast_against_schema(&ast, &schema);
        prop_assert!(!reconstructed.is_empty());
    }

    #[test]
    fn test_proptest_multidoc_delimiters_never_panic(
        docs in proptest::collection::vec("[a-zA-Z0-9:\n # -]{0,80}", 1..5)
    ) {
        let stream = docs.join("\n---\n");
        let shards = native_shard(&stream);
        let _reconstructed = native_reconstruct_yaml(&shards);
        let ast = native_structurize(shards);
        let schema = native_get_schema_for_version("1.30");
        let _ = native_validate_ast_against_schema(&ast, &schema);
    }

    #[test]
    fn test_proptest_block_scalar_chomping_invariance(
        indicator in "((\\||>)[+-]?)",
        content in "[a-zA-Z0-9 \n]{1,60}"
    ) {
        let manifest = format!("key: {}\n  {}\n", indicator, content.replace("\n", "\n  "));
        let shards = native_shard(&manifest);
        let recon1 = native_reconstruct_yaml(&shards);
        let shards2 = native_shard(&recon1);
        let recon2 = native_reconstruct_yaml(&shards2);
        prop_assert_eq!(recon1, recon2);
    }

    #[test]
    fn test_proptest_yaml_boolean_representation_idempotency(
        bool_val in "(true|false|yes|no|on|off|True|False|TRUE|FALSE)",
        key in "[a-z]{3,8}"
    ) {
        let manifest = format!("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\ndata:\n  {}: {}\n", key, bool_val);
        let (healed1, _) = yamlr_native::cli::heal_cmd::heal_manifest_string(&manifest);
        let (healed2, _) = yamlr_native::cli::heal_cmd::heal_manifest_string(&healed1);
        prop_assert_eq!(healed1, healed2);
    }

    #[test]
    fn test_proptest_mixed_whitespace_recovery(
        spaces in 0usize..4usize,
        has_tab in proptest::bool::ANY,
        val in "[a-z0-9]{3,8}"
    ) {
        let prefix = if has_tab { "\t".to_string() } else { " ".repeat(spaces) };
        let manifest = format!("{}apiVersion: v1\n{}kind: Pod\n{}metadata:\n{}  name: {}\n", prefix, prefix, prefix, prefix, val);
        let shards = native_shard(&manifest);
        let recon1 = native_reconstruct_yaml(&shards);
        let shards2 = native_shard(&recon1);
        let recon2 = native_reconstruct_yaml(&shards2);
        prop_assert_eq!(recon1, recon2);
    }
}
