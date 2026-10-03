use super::*;
use std::collections::HashMap;

#[test]
fn test_reserved_label_pollution() {
    let mut labels = HashMap::new();
    labels.insert("kubernetes.io/os".to_string(), "linux".to_string());

    let id = NativeIdentity {
        name: "test-pod".into(),
        kind: "Pod".into(),
        api_version: Some("v1".into()),
        namespace: "default".into(),
        owner_refs: vec![],
        labels,
        selector: HashMap::new(),
        config_refs: vec![],
        secret_refs: vec![],
        volume_refs: vec![],
        service_refs: vec![],
        role_refs: vec![],
        cluster_role_refs: vec![],
        service_account: None,
        shadow_fingerprint: "".into(),
        relationships: vec![],
        ports: vec![],
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[id]);
    assert!(violations.iter().any(|v| v.rule_id == "GOV-001"));
}

#[test]
fn test_namespaced_identity_collision() {
    let id1 = NativeIdentity {
        name: "admin-role".into(),
        kind: "Role".into(),
        api_version: Some("rbac.authorization.k8s.io/v1".into()),
        namespace: "default".into(),
        owner_refs: vec![],
        labels: HashMap::new(),
        selector: HashMap::new(),
        config_refs: vec![],
        secret_refs: vec![],
        volume_refs: vec![],
        service_refs: vec![],
        role_refs: vec![],
        cluster_role_refs: vec![],
        service_account: None,
        shadow_fingerprint: "".into(),
        relationships: vec![],
        ports: vec![],
        ..Default::default()
    };

    let id2 = id1.clone(); // Duplicate
    let violations = AuditRegistry::audit_all(&[id1, id2]);
    assert!(violations.iter().any(|v| v.rule_id == "SEC-005"));
}

#[test]
fn test_service_shadowing() {
    let mut selector = HashMap::new();
    selector.insert("app".to_string(), "web".to_string());

    let id1 = NativeIdentity {
        name: "svc1".into(),
        kind: "Service".into(),
        api_version: Some("v1".into()),
        namespace: "default".into(),
        owner_refs: vec![],
        labels: HashMap::new(),
        selector: selector.clone(),
        config_refs: vec![],
        secret_refs: vec![],
        volume_refs: vec![],
        service_refs: vec![],
        role_refs: vec![],
        cluster_role_refs: vec![],
        service_account: None,
        shadow_fingerprint: "".into(),
        relationships: vec![],
        ports: vec![],
        ..Default::default()
    };

    let mut id2 = id1.clone();
    id2.name = "svc2".into();

    let violations = AuditRegistry::audit_all(&[id1, id2]);
    assert!(violations.iter().any(|v| v.rule_id == "NET-001"));
}

#[test]
fn test_dangling_identity() {
    let id1 = NativeIdentity {
        name: "unused-sa".into(),
        kind: "ServiceAccount".into(),
        api_version: Some("v1".into()),
        namespace: "default".into(),
        owner_refs: vec![],
        labels: HashMap::new(),
        selector: HashMap::new(),
        config_refs: vec![],
        secret_refs: vec![],
        volume_refs: vec![],
        service_refs: vec![],
        role_refs: vec![],
        cluster_role_refs: vec![],
        service_account: None,
        shadow_fingerprint: "".into(),
        relationships: vec![],
        ports: vec![],
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[id1]);
    assert!(violations.iter().any(|v| v.rule_id == "SEC-009"));
}

#[test]
fn test_dual_stack_service_audit() {
    let mut annotations = HashMap::new();
    annotations.insert(
        "service.beta.kubernetes.io/aws-load-balancer-type".to_string(),
        "nlb".to_string(),
    );

    let id = NativeIdentity {
        name: "nlb-service".into(),
        kind: "Service".into(),
        api_version: Some("v1".into()),
        namespace: "default".into(),
        annotations,
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[id]);
    assert!(violations.iter().any(|v| v.rule_id == "NET-009"));
}

#[test]
fn test_ingress_snippet_audit() {
    let mut annotations = HashMap::new();
    annotations.insert(
        "nginx.ingress.kubernetes.io/configuration-snippet".to_string(),
        "more_set_headers 'X-Frame-Options: SAMEORIGIN';".to_string(),
    );

    let id = NativeIdentity {
        name: "secure-ingress".into(),
        kind: "Ingress".into(),
        api_version: Some("networking.k8s.io/v1".into()),
        namespace: "default".into(),
        annotations,
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[id]);
    assert!(violations.iter().any(|v| v.rule_id == "SEC-012"));
}

#[test]
fn test_hpa_vpa_contention_audit() {
    let hpa = NativeIdentity {
        name: "app-hpa".into(),
        kind: "HorizontalPodAutoscaler".into(),
        api_version: Some("autoscaling/v2".into()),
        namespace: "default".into(),
        service_refs: vec!["app-deployment".into()],
        ..Default::default()
    };

    let vpa = NativeIdentity {
        name: "app-vpa".into(),
        kind: "VerticalPodAutoscaler".into(),
        api_version: Some("autoscaling.k8s.io/v1".into()),
        namespace: "default".into(),
        service_refs: vec!["app-deployment".into()],
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[hpa, vpa]);
    assert!(violations.iter().any(|v| v.rule_id == "AUT-002"));
}

#[test]
fn test_gitops_and_sync_wave_audit() {
    let crd = NativeIdentity {
        name: "databases.db.example.com".into(),
        kind: "CustomResourceDefinition".into(),
        namespace: "default".into(),
        annotations: HashMap::new(), // Missing sync-wave!
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[crd]);
    assert!(violations.iter().any(|v| v.rule_id == "GTO-002"));
}

#[test]
fn test_statefulset_immutability_audit() {
    let mut ann = HashMap::new();
    ann.insert("yamlr.io/expand-pvc".to_string(), "20Gi".to_string());

    let sts = NativeIdentity {
        name: "es-cluster".into(),
        kind: "StatefulSet".into(),
        namespace: "default".into(),
        annotations: ann,
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[sts]);
    assert!(violations.iter().any(|v| v.rule_id == "STO-003"));
}

#[test]
fn test_protocol_contract_audit() {
    let svc = NativeIdentity {
        name: "grpc-service".into(),
        kind: "Service".into(),
        namespace: "default".into(),
        ports: vec![50051],
        annotations: HashMap::new(), // Missing appProtocol
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[svc]);
    assert!(violations.iter().any(|v| v.rule_id == "NET-007"));
}

#[test]
fn test_gitops_wave_inversion_audit() {
    let mut cfg_ann = HashMap::new();
    cfg_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "0".to_string());

    let cfg = NativeIdentity {
        name: "app-config".into(),
        kind: "ConfigMap".into(),
        namespace: "prod".into(),
        annotations: cfg_ann,
        ..Default::default()
    };

    let mut deploy_ann = HashMap::new();
    deploy_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "0".to_string());

    let deploy = NativeIdentity {
        name: "web-app".into(),
        kind: "Deployment".into(),
        namespace: "prod".into(),
        config_refs: vec!["app-config".into()],
        annotations: deploy_ann,
        ..Default::default()
    };

    let violations = AuditRegistry::audit_all(&[cfg, deploy]);
    assert!(violations.iter().any(|v| v.rule_id == "GTO-003"));
}
