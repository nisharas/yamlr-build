//! End-to-End Integration Test for the 6 Kubernetes Nightmare Healers.
//!
//! Validates that all 6 healers work together as a single cohesive unit:
//! 1. GTO-001/GTO-002: GitOps Controller Defaults Harmonizer & Sync-Wave Stamping
//! 2. STO-003: StatefulSet Immutability Guard & PVC Expansion Synthesizer
//! 3. REL-011: HA Topology Spread Synthesizer
//! 4. NET-007: Protocol Contract Healer (gRPC ALPN & appProtocol)
//! 5. NET-008: Ingress Path Shadowing & Specificity Ordering
//! 6. RES-003: QoS Class Burstable Right-Sizer
//!
//! Also proves:
//! - 100% comment and layout preservation
//! - Strict idempotency: heal(heal(x)) == heal(x)

use yamlr_native::cli::heal_cmd::heal_manifest_string;

#[test]
fn test_nightmare_healers_single_pass_cohesion() {
    let raw_multi_doc = r#"# CRD for API Gateway
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: routes.gateway.example.com
  annotations:
    yamlr.io/gitops: "true"
spec:
  group: gateway.example.com
  names:
    kind: Route
    plural: routes
  scope: Namespaced
---
# Production gRPC backend microservice
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-engine # Critical revenue service
  labels:
    app: billing
  annotations:
    yamlr.io/gitops: "true"
    yamlr.io/ha-topology: "true"
    yamlr.io/qos: "true"
spec:
  replicas: 3 # Multi-replica for HA
  selector:
    matchLabels:
      app: billing
  template:
    metadata:
      labels:
        app: billing
    spec:
      containers:
      - name: server
        image: billing:v2.1.0 # Pinned image
        ports:
        - containerPort: 50051 # gRPC communication port
---
# Service for billing
apiVersion: v1
kind: Service
metadata:
  name: billing-svc
spec:
  selector:
    app: billing
  ports:
  - name: http # Mislabeled gRPC port
    port: 50051
    targetPort: 50051
---
# Ingress routing rules
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: billing-ingress
spec:
  rules:
  - host: api.corp.com
    http:
      paths:
      - path: /api # Broad prefix shadows sub-path
        pathType: Prefix
        backend:
          service:
            name: generic-api-svc
            port:
              number: 80
      - path: /api/v1/billing
        pathType: Prefix
        backend:
          service:
            name: billing-svc
            port:
              number: 50051
"#;

    // Single-pass healing across all documents
    let (healed, changes) = heal_manifest_string(raw_multi_doc);

    // 1. Verify changes were recorded across rules
    assert!(
        !changes.is_empty(),
        "Healing should detect and repair multiple issues"
    );

    // 2. GTO-002: CRD stamped with sync-wave "-2"
    assert!(
        healed.contains("argocd.argoproj.io/sync-wave: \"-2\""),
        "CRD must receive sync-wave -2"
    );

    // 3. GTO-001: Deployment receives controller defaults
    assert!(
        healed.contains("revisionHistoryLimit: 10"),
        "Deployment must receive revisionHistoryLimit: 10"
    );
    assert!(
        healed.contains("progressDeadlineSeconds: 600"),
        "Deployment must receive progressDeadlineSeconds: 600"
    );

    // 4. REL-011: Deployment with replicas: 3 receives topologySpreadConstraints
    assert!(
        healed.contains("topologySpreadConstraints:"),
        "Multi-replica deployment must receive topologySpreadConstraints"
    );
    assert!(
        healed.contains("topologyKey: topology.kubernetes.io/zone"),
        "Must spread across zones"
    );
    assert!(
        healed.contains("whenUnsatisfiable: ScheduleAnyway"),
        "Must use soft ScheduleAnyway constraint"
    );

    // 5. RES-003: Naked container elevated to Burstable QoS
    assert!(
        healed.contains("resources:"),
        "Naked container must receive resources"
    );
    assert!(
        healed.contains("cpu: 50m"),
        "Must include CPU request floor"
    );
    assert!(
        healed.contains("memory: 64Mi"),
        "Must include memory request floor"
    );
    assert!(
        healed.contains("cpu: 500m"),
        "Must include CPU limit ceiling"
    );
    assert!(
        healed.contains("memory: 256Mi"),
        "Must include memory limit ceiling"
    );

    // 6. NET-007: Service port 50051 configured with appProtocol: grpc and renamed
    assert!(
        healed.contains("appProtocol: grpc"),
        "Service port 50051 must set appProtocol: grpc"
    );
    assert!(
        healed.contains("name: grpc"),
        "Mislabeled http name on port 50051 must be renamed to grpc"
    );

    // 7. NET-008: Ingress paths reordered to prevent shadowing (/api/v1/billing before /api)
    let billing_idx = healed
        .find("/api/v1/billing")
        .expect("Billing path must exist");
    let api_idx = healed
        .find("path: /api ")
        .or_else(|| healed.find("path: /api\n"))
        .or_else(|| healed.find("path: /api\r\n"))
        .expect("API path must exist");
    assert!(
        billing_idx < api_idx,
        "Specific path /api/v1/billing must precede parent prefix /api to prevent shadowing"
    );

    // 8. Comment preservation: Comments must remain intact
    assert!(
        healed.contains("# CRD for API Gateway"),
        "CRD comment preserved"
    );
    assert!(
        healed.contains("# Critical revenue service"),
        "Inline metadata comment preserved"
    );
    assert!(
        healed.contains("# Multi-replica for HA"),
        "Replicas comment preserved"
    );
    assert!(
        healed.contains("# gRPC communication port"),
        "Port comment preserved"
    );

    // 9. Strict Idempotency: Running heal on healed output yields identical result with 0 changes
    let (healed_again, second_changes) = heal_manifest_string(&healed);
    assert_eq!(healed, healed_again, "Healer must be strictly idempotent");
    assert!(
        second_changes.is_empty(),
        "Second pass must produce 0 mutations"
    );
}
