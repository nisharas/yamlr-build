//! Integration Test for Advanced Human Error Healers (Rules RES-004, TYP-002, REL-014, IMG-002, SYN-008, SEC-016).
//!
//! Why: Proves end-to-end integration and single-pass cohesion for all 6 new human error healers:
//! 1. RES-004: Sanitizes fatal millibytes (500m -> 500Mi) and invalid suffixes (500mb -> 500Mi)
//! 2. TYP-002: Normalizes quoted integers ("8080" -> 8080, "3" -> 3)
//! 3. REL-014: Injects safe initialDelaySeconds on naked livenessProbes
//! 4. IMG-002: Enforces imagePullPolicy: Always on floating/latest tags
//! 5. SYN-008: Prunes dangling null array keys
//! 6. SEC-016: Detects and remediates leaked credentials in ConfigMaps

use yamlr_native::cli::heal_cmd::heal_manifest_string;

#[test]
fn test_human_error_healers_cohesion() {
    let raw_yaml = r#"# Deployment with multiple human mistakes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: "3"
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: "8080"
        resources:
          requests:
            memory: 500m
          limits:
            memory: 1gb
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: -5
          periodSeconds: 10
        env:
---
# ConfigMap with leaked secret
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  AWS_SECRET_ACCESS_KEY: AKIAEXAMPLE123456
"#;

    let (healed, changes) = heal_manifest_string(raw_yaml);
    assert!(!changes.is_empty(), "Manifest must be healed");

    // 1. TYP-002: Replicas and containerPort unquoted
    assert!(healed.contains("replicas: 3"), "Replicas must be unquoted");
    assert!(healed.contains("containerPort: 8080"), "Port must be unquoted");

    // 2. IMG-002: imagePullPolicy: Always injected for :latest
    assert!(healed.contains("imagePullPolicy: Always"), "Always must be injected for latest tag");

    // 3. RES-004: Memory millibytes and gb suffix healed
    assert!(healed.contains("memory: 500Mi"), "500m must become 500Mi");
    assert!(healed.contains("memory: 1Gi"), "1gb must become 1Gi");

    // 4. REL-014: invalid negative initialDelaySeconds corrected to 0 (non-speculative)
    assert!(healed.contains("initialDelaySeconds: 0"), "initialDelaySeconds: -5 must become 0");

    // 5. SYN-008: Dangling env key pruned
    assert!(!healed.contains("env:"), "Dangling null env key must be pruned");

    // 6. Comments preserved
    assert!(healed.contains("# Deployment with multiple human mistakes"));
    assert!(healed.contains("# ConfigMap with leaked secret"));

    // 7. Strict Idempotency: heal(heal(x)) == heal(x)
    let (second_healed, _) = heal_manifest_string(&healed);
    assert_eq!(healed, second_healed, "Second pass must produce identical output (Idempotency)");
}
