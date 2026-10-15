use super::*;

#[test]
fn test_levenshtein_distance() {
    assert_eq!(levenshtein("continers", "containers"), 1);
    assert_eq!(levenshtein("replica", "replicas"), 1);
    assert_eq!(levenshtein("laels", "labels"), 1);
    assert_eq!(levenshtein("label", "labels"), 1);
    assert_eq!(levenshtein("selectr", "selector"), 1);
}

#[test]
fn test_category_1_port_vs_ports() {
    // Service spec: ports (plural)
    assert_eq!(fuzzy_match_property("port", SERVICE_SPEC_KEYS), Some("ports"));
    assert_eq!(fuzzy_match_property("ports", SERVICE_SPEC_KEYS), None);

    // ServicePort item: port (singular)
    assert_eq!(fuzzy_match_property("port", SERVICE_PORT_KEYS), None);
    assert_eq!(fuzzy_match_property("targetport", SERVICE_PORT_KEYS), Some("targetPort"));
    assert_eq!(fuzzy_match_property("nodeport", SERVICE_PORT_KEYS), Some("nodePort"));

    // Container: ports (plural)
    assert_eq!(fuzzy_match_property("port", CONTAINER_KEYS), Some("ports"));
    assert_eq!(fuzzy_match_property("ports", CONTAINER_KEYS), None);

    // ContainerPort item: containerPort (NOT port or ports!)
    assert_eq!(fuzzy_match_property("continerPort", CONTAINER_PORT_KEYS), Some("containerPort"));
    assert_eq!(fuzzy_match_property("containerport", CONTAINER_PORT_KEYS), Some("containerPort"));
    assert_eq!(fuzzy_match_property("hostport", CONTAINER_PORT_KEYS), Some("hostPort"));

    // Probe httpGet / tcpSocket / grpc: port (singular)
    assert_eq!(fuzzy_match_property("port", HTTP_GET_KEYS), None);
    assert_eq!(fuzzy_match_property("port", TCP_SOCKET_KEYS), None);
    assert_eq!(fuzzy_match_property("port", GRPC_PROBE_KEYS), None);
    assert_eq!(fuzzy_match_property("ports", GRPC_PROBE_KEYS), Some("port"));

    // Ingress backend service port: number / name
    assert_eq!(fuzzy_match_property("number", INGRESS_SERVICE_PORT_KEYS), None);
    assert_eq!(fuzzy_match_property("numbr", INGRESS_SERVICE_PORT_KEYS), Some("number"));
}

#[test]
fn test_category_2_resource_vs_resources() {
    // Container: resources (plural)
    assert_eq!(fuzzy_match_property("resource", CONTAINER_KEYS), Some("resources"));
    assert_eq!(fuzzy_match_property("resources", CONTAINER_KEYS), None);

    // RBAC PolicyRule: resources (plural)
    assert_eq!(fuzzy_match_property("resource", RBAC_RULE_KEYS), Some("resources"));
    assert_eq!(fuzzy_match_property("resources", RBAC_RULE_KEYS), None);
    assert_eq!(fuzzy_match_property("apigroup", RBAC_RULE_KEYS), Some("apiGroups"));

    // HPA metric: resource (singular)
    assert_eq!(fuzzy_match_property("resources", HPA_METRIC_KEYS), Some("resource"));
    assert_eq!(fuzzy_match_property("resource", HPA_METRIC_KEYS), None);
}

#[test]
fn test_category_3_selector_vs_selectors_vs_nodeselector() {
    // Workload spec: selector (singular)
    assert_eq!(fuzzy_match_property("selectors", WORKLOAD_SPEC_KEYS), Some("selector"));
    assert_eq!(fuzzy_match_property("selector", WORKLOAD_SPEC_KEYS), None);

    // Service spec: selector (singular)
    assert_eq!(fuzzy_match_property("selectors", SERVICE_SPEC_KEYS), Some("selector"));
    assert_eq!(fuzzy_match_property("selector", SERVICE_SPEC_KEYS), None);

    // Pod spec: nodeSelector (singular)
    assert_eq!(fuzzy_match_property("nodeselector", POD_SPEC_KEYS), Some("nodeSelector"));
    assert_eq!(fuzzy_match_property("nodeSelectors", POD_SPEC_KEYS), Some("nodeSelector"));

    // Workload selector: matchLabels
    assert_eq!(fuzzy_match_property("matchLabel", WORKLOAD_SELECTOR_KEYS), Some("matchLabels"));
    assert_eq!(fuzzy_match_property("matchExpressions", WORKLOAD_SELECTOR_KEYS), None);

    // NetworkPolicy spec: podSelector
    assert_eq!(fuzzy_match_property("podSelectors", NETWORK_POLICY_SPEC_KEYS), Some("podSelector"));
}

#[test]
fn test_category_4_label_vs_labels_vs_matchlabels() {
    // Metadata: labels (plural)
    assert_eq!(fuzzy_match_property("label", METADATA_KEYS), Some("labels"));
    assert_eq!(fuzzy_match_property("laels", METADATA_KEYS), Some("labels"));
    assert_eq!(fuzzy_match_property("labels", METADATA_KEYS), None);
}

#[test]
fn test_category_5_volume_vs_volumes_vs_volumemounts() {
    // Pod spec: volumes (plural)
    assert_eq!(fuzzy_match_property("volume", POD_SPEC_KEYS), Some("volumes"));
    assert_eq!(fuzzy_match_property("volumes", POD_SPEC_KEYS), None);

    // Container: volumeMounts & volumeDevices
    assert_eq!(fuzzy_match_property("volumeMount", CONTAINER_KEYS), Some("volumeMounts"));
    assert_eq!(fuzzy_match_property("volumedevices", CONTAINER_KEYS), Some("volumeDevices"));

    // VolumeMount item: mountPath, readOnly
    assert_eq!(fuzzy_match_property("mountpath", VOLUME_MOUNT_KEYS), Some("mountPath"));
    assert_eq!(fuzzy_match_property("readonly", VOLUME_MOUNT_KEYS), Some("readOnly"));
}

#[test]
fn test_category_6_serviceaccount_vs_serviceaccountname() {
    // Pod spec: serviceAccountName
    assert_eq!(fuzzy_match_property("serviceaccountname", POD_SPEC_KEYS), Some("serviceAccountName"));
}

#[test]
fn test_category_7_env_vs_envfrom() {
    // Short key 'env' (len 3) is guarded and preserved
    assert_eq!(fuzzy_match_property("env", CONTAINER_KEYS), None);
    assert_eq!(fuzzy_match_property("envfrom", CONTAINER_KEYS), Some("envFrom"));

    // envFrom item: configMapRef, secretRef
    assert_eq!(fuzzy_match_property("configmapref", ENV_FROM_KEYS), Some("configMapRef"));
    assert_eq!(fuzzy_match_property("secretref", ENV_FROM_KEYS), Some("secretRef"));
}

#[test]
fn test_category_8_secret_keywords() {
    // Ingress TLS: secretName
    assert_eq!(fuzzy_match_property("secretname", INGRESS_TLS_KEYS), Some("secretName"));
    assert_eq!(fuzzy_match_property("secrtName", INGRESS_TLS_KEYS), Some("secretName"));

    // Volume secret: secretName
    assert_eq!(fuzzy_match_property("secretname", VOLUME_SECRET_KEYS), Some("secretName"));

    // env valueFrom secretKeyRef: key, name
    assert_eq!(fuzzy_match_property("name", KEY_REF_KEYS), None);
    assert_eq!(fuzzy_match_property("optional", KEY_REF_KEYS), None);
}

#[test]
fn test_full_ast_container_port_auto_repair() {
    // Both 'port: 8080' and 'ports: 8080' inside container ports must heal to 'containerPort'
    let mut manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "kind".into(),
                    value: Some("Deployment".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "spec".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "template".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "spec".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "containers".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "-".into(),
                                    value: None,
                                    children: vec![SemanticNode {
                                        key: "ports".into(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "-".into(),
                                                value: None,
                                                children: vec![SemanticNode {
                                                    key: "port".into(),
                                                    value: Some("8080".into()),
                                                    children: vec![],
                                                    shards: vec![],
                                                    indent: 14,
                                                    is_empty_flow: false,
                                                }],
                                                shards: vec![],
                                                indent: 12,
                                                is_empty_flow: false,
                                            },
                                            SemanticNode {
                                                key: "-".into(),
                                                value: None,
                                                children: vec![SemanticNode {
                                                    key: "ports".into(),
                                                    value: Some("9090".into()),
                                                    children: vec![],
                                                    shards: vec![],
                                                    indent: 14,
                                                    is_empty_flow: false,
                                                }],
                                                shards: vec![],
                                                indent: 12,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: 10,
                                        is_empty_flow: false,
                                    }],
                                    shards: vec![],
                                    indent: 8,
                                    is_empty_flow: false,
                                }],
                                shards: vec![],
                                indent: 6,
                                is_empty_flow: false,
                            }],
                            shards: vec![],
                            indent: 4,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    }],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![],
    };

    let mut telemetry = NativeTelemetry::default();
    let changes = heal_schema_typos(&mut manifest, &mut telemetry);
    assert_eq!(changes.len(), 2);
    assert!(changes[0].contains("containerPort"));
    assert!(changes[1].contains("containerPort"));

    let port_nodes = manifest.root.find_nodes_by_key_recursive("containerPort");
    assert_eq!(port_nodes.len(), 2);
}

#[test]
fn test_payload_data_and_service_selector_zero_overhealing() {
    // ConfigMap data payload and Service selector arbitrary labels must never be mutated
    let mut manifest = SemanticManifest {
        root: SemanticNode {
            key: "root".into(),
            value: None,
            children: vec![
                SemanticNode {
                    key: "kind".into(),
                    value: Some("ConfigMap".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
                SemanticNode {
                    key: "data".into(),
                    value: None,
                    children: vec![
                        SemanticNode {
                            key: "port".into(),
                            value: Some("80".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        },
                        SemanticNode {
                            key: "resource".into(),
                            value: Some("cpu".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        },
                    ],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                },
            ],
            shards: vec![],
            indent: 0,
            is_empty_flow: false,
        },
        indent_step: 2,
        integrity_violations: vec![],
    };

    let mut telemetry = NativeTelemetry::default();
    let changes = heal_schema_typos(&mut manifest, &mut telemetry);
    assert_eq!(changes.len(), 0); // ZERO changes to payload data!
}

#[test]
fn test_resource_field_ref_singular_preserved() {
    // In container env valueFrom.resourceFieldRef, 'resource: limits.cpu' is singular and must NOT be converted to 'resources'
    assert_eq!(fuzzy_match_property("resource", RESOURCE_FIELD_REF_KEYS), None);
    assert_eq!(fuzzy_match_property("resourc", RESOURCE_FIELD_REF_KEYS), Some("resource"));
    assert_eq!(fuzzy_match_property("containerName", RESOURCE_FIELD_REF_KEYS), None);
    assert_eq!(fuzzy_match_property("divisor", RESOURCE_FIELD_REF_KEYS), None);
}
