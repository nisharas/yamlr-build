//! Comprehensive Unit Tests for Discovery, Topology Graph, and Blast Radius.

#[cfg(test)]
mod tests {
    use super::super::analyzers::*;
    use super::super::blast_radius::*;
    use super::super::builder::*;
    use crate::models::{NativeDiscoveryResult, NativeEdge, NativeIdentity};
    use std::collections::HashMap;

    #[test]
    fn test_native_build_topology_graph_basic() {
        let id1 = NativeIdentity {
            name: "pod1".into(),
            kind: "Pod".into(),
            api_version: Some("v1".into()),
            namespace: "default".into(),
            config_refs: vec!["my-config".into()],
            secret_refs: vec!["my-secret".into()],
            ..Default::default()
        };
        let id2 = NativeIdentity {
            name: "my-config".into(),
            kind: "ConfigMap".into(),
            api_version: Some("v1".into()),
            namespace: "default".into(),
            ..Default::default()
        };
        let id3 = NativeIdentity {
            name: "my-secret".into(),
            kind: "Secret".into(),
            api_version: Some("v1".into()),
            namespace: "default".into(),
            ..Default::default()
        };

        let discovery = vec![
            NativeDiscoveryResult {
                file_path: "".into(),
                identity: Some(id1),
                shard_count: 0,
            },
            NativeDiscoveryResult {
                file_path: "".into(),
                identity: Some(id2),
                shard_count: 0,
            },
            NativeDiscoveryResult {
                file_path: "".into(),
                identity: Some(id3),
                shard_count: 0,
            },
        ];

        let edges = native_build_topology_graph(discovery);
        assert_eq!(edges.len(), 2);
        assert!(edges
            .iter()
            .any(|e| e.edge_type == "ConfigRef" && e.to_resource == "ConfigMap/default/my-config"));
        assert!(edges
            .iter()
            .any(|e| e.edge_type == "SecretRef" && e.to_resource == "Secret/default/my-secret"));
    }

    #[test]
    fn test_service_selector_and_ingress_edge_building() {
        let mut wl_labels = HashMap::new();
        wl_labels.insert("app".to_string(), "api".to_string());

        let mut svc_selector = HashMap::new();
        svc_selector.insert("app".to_string(), "api".to_string());

        let deployment = NativeIdentity {
            name: "api-deploy".into(),
            kind: "Deployment".into(),
            namespace: "prod".into(),
            labels: wl_labels,
            ports: vec![8080],
            ..Default::default()
        };

        let service = NativeIdentity {
            name: "api-svc".into(),
            kind: "Service".into(),
            namespace: "prod".into(),
            selector: svc_selector,
            ports: vec![8080],
            ..Default::default()
        };

        let ingress = NativeIdentity {
            name: "api-ingress".into(),
            kind: "Ingress".into(),
            namespace: "prod".into(),
            service_refs: vec!["api-svc".into()],
            ..Default::default()
        };

        let edges = build_topology_edges(&[deployment, service, ingress]);
        assert!(edges.iter().any(|e| e.edge_type == "SelectorMatch"
            && e.from_resource == "Service/prod/api-svc"
            && e.to_resource == "Deployment/prod/api-deploy"));
        assert!(edges.iter().any(|e| e.edge_type == "IngressBackend"
            && e.from_resource == "Ingress/prod/api-ingress"
            && e.to_resource == "Service/prod/api-svc"));
    }

    #[test]
    fn test_native_detect_circular_dependencies() {
        let edges = vec![
            NativeEdge {
                from_resource: "A".into(),
                to_resource: "B".into(),
                edge_type: "Ref".into(),
            },
            NativeEdge {
                from_resource: "B".into(),
                to_resource: "C".into(),
                edge_type: "Ref".into(),
            },
            NativeEdge {
                from_resource: "C".into(),
                to_resource: "A".into(),
                edge_type: "Ref".into(),
            },
        ];

        let cycles = native_detect_circular_dependencies(&edges);
        assert!(!cycles.is_empty());
        assert!(cycles[0].contains("Circular Dependency Loop"));
    }

    #[test]
    fn test_native_detect_version_drift() {
        let id1 = NativeIdentity {
            name: "dep1".into(),
            kind: "Deployment".into(),
            api_version: Some("apps/v1".into()),
            namespace: "default".into(),
            ..Default::default()
        };
        let mut id2 = id1.clone();
        id2.api_version = Some("extensions/v1beta1".into());

        let discovery = vec![
            NativeDiscoveryResult {
                file_path: "f1".into(),
                identity: Some(id1),
                shard_count: 0,
            },
            NativeDiscoveryResult {
                file_path: "f2".into(),
                identity: Some(id2),
                shard_count: 0,
            },
        ];

        let drifts = native_detect_version_drift(discovery);
        assert_eq!(drifts.len(), 1);
        assert!(drifts[0].contains("Architectural Drift"));
    }

    #[test]
    fn test_native_detect_orphaned_resources() {
        let id = NativeIdentity {
            name: "unused-cm".into(),
            kind: "ConfigMap".into(),
            api_version: Some("v1".into()),
            namespace: "default".into(),
            ..Default::default()
        };
        let discovery = vec![NativeDiscoveryResult {
            file_path: "".into(),
            identity: Some(id),
            shard_count: 0,
        }];

        let orphans = native_detect_orphaned_resources(&discovery);
        assert_eq!(orphans.len(), 1);
        assert!(orphans[0].contains("Orphaned ConfigMap"));
    }

    #[test]
    fn test_native_detect_dangling_selectors() {
        let mut sel = HashMap::new();
        sel.insert("app".to_string(), "nonexistent".to_string());

        let id = NativeIdentity {
            name: "orphan-svc".into(),
            kind: "Service".into(),
            namespace: "default".into(),
            selector: sel,
            ..Default::default()
        };
        let discovery = vec![NativeDiscoveryResult {
            file_path: "".into(),
            identity: Some(id),
            shard_count: 0,
        }];

        let dangling = native_detect_dangling_selectors(&discovery);
        assert_eq!(dangling.len(), 1);
        assert!(dangling[0].contains("Dangling Service Selector"));
    }

    #[test]
    fn test_native_detect_service_shadowing() {
        let mut sel = HashMap::new();
        sel.insert("app".to_string(), "web".to_string());

        let s1 = NativeIdentity {
            name: "svc-primary".into(),
            kind: "Service".into(),
            namespace: "default".into(),
            selector: sel.clone(),
            ..Default::default()
        };
        let s2 = NativeIdentity {
            name: "svc-shadow".into(),
            kind: "Service".into(),
            namespace: "default".into(),
            selector: sel,
            ..Default::default()
        };

        let discovery = vec![
            NativeDiscoveryResult {
                file_path: "".into(),
                identity: Some(s1),
                shard_count: 0,
            },
            NativeDiscoveryResult {
                file_path: "".into(),
                identity: Some(s2),
                shard_count: 0,
            },
        ];

        let shadows = native_detect_service_shadowing(&discovery);
        assert_eq!(shadows.len(), 1);
        assert!(shadows[0].contains("Service Shadowing"));
    }

    #[test]
    fn test_calculate_blast_radius_multi_hop_and_risk() {
        let edges = vec![
            NativeEdge {
                from_resource: "Ingress/prod/frontend".into(),
                to_resource: "Service/prod/web".into(),
                edge_type: "IngressBackend".into(),
            },
            NativeEdge {
                from_resource: "Service/prod/web".into(),
                to_resource: "Deployment/prod/web".into(),
                edge_type: "SelectorMatch".into(),
            },
            NativeEdge {
                from_resource: "Deployment/prod/web".into(),
                to_resource: "ConfigMap/prod/web-config".into(),
                edge_type: "ConfigRef".into(),
            },
        ];

        // Focus on ConfigMap: impacted should include Deployment, Service, and Ingress
        let blast = calculate_blast_radius("ConfigMap/prod/web-config", &edges);
        assert_eq!(blast.target_resource, "ConfigMap/prod/web-config");
        assert_eq!(blast.impacted_resources.len(), 3);
        assert_eq!(blast.depth, 3);
        assert!(blast.risk_score > 5.0);
        assert!(blast.risk_level == "HIGH" || blast.risk_level == "CRITICAL");
    }

    #[test]
    fn test_vpa_target_ref_edge_building() {
        let deployment = NativeIdentity {
            name: "api-workload".into(),
            kind: "Deployment".into(),
            namespace: "prod".into(),
            ..Default::default()
        };

        let vpa = NativeIdentity {
            name: "api-vpa".into(),
            kind: "VerticalPodAutoscaler".into(),
            namespace: "prod".into(),
            service_refs: vec!["api-workload".into()],
            ..Default::default()
        };

        let edges = build_topology_edges(&[deployment, vpa]);
        assert!(edges.iter().any(|e| e.edge_type == "VpaTargetRef"
            && e.from_resource == "VerticalPodAutoscaler/prod/api-vpa"
            && e.to_resource == "Deployment/prod/api-workload"));
    }

    #[test]
    fn test_autoscaler_contention_edge_building() {
        let deployment = NativeIdentity {
            name: "api-workload".into(),
            kind: "Deployment".into(),
            namespace: "prod".into(),
            ..Default::default()
        };

        let hpa = NativeIdentity {
            name: "api-hpa".into(),
            kind: "HorizontalPodAutoscaler".into(),
            namespace: "prod".into(),
            service_refs: vec!["api-workload".into()],
            ..Default::default()
        };

        let vpa = NativeIdentity {
            name: "api-vpa".into(),
            kind: "VerticalPodAutoscaler".into(),
            namespace: "prod".into(),
            service_refs: vec!["api-workload".into()],
            ..Default::default()
        };

        let edges = build_topology_edges(&[deployment, hpa, vpa]);
        assert!(edges.iter().any(|e| e.edge_type == "AutoscalerContention"
            && e.from_resource == "VerticalPodAutoscaler/prod/api-vpa"
            && e.to_resource == "HorizontalPodAutoscaler/prod/api-hpa"));
    }
}
