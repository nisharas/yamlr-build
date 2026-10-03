//! SARIF 2.1 CodeFlows, ThreadFlows, and Graph Serialization.
//!
//! Why: GitHub Advanced Security and enterprise SARIF visualizers require
//! execution and dependency traces (codeFlows and graphs) to illustrate multi-resource
//! root-cause failures (e.g. Service selector -> Deployment label mismatch).

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifPhysicalLocation {
    #[serde(rename = "artifactLocation")]
    pub artifact_location: SarifArtifactLocation,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub region: Option<SarifRegion>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifArtifactLocation {
    pub uri: String,
    #[serde(rename = "uriBaseId", skip_serializing_if = "Option::is_none")]
    pub uri_base_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifRegion {
    #[serde(rename = "startLine")]
    pub start_line: usize,
    #[serde(rename = "startColumn", skip_serializing_if = "Option::is_none")]
    pub start_column: Option<usize>,
    #[serde(rename = "endLine", skip_serializing_if = "Option::is_none")]
    pub end_line: Option<usize>,
    #[serde(rename = "endColumn", skip_serializing_if = "Option::is_none")]
    pub end_column: Option<usize>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifMessage {
    pub text: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifLocation {
    #[serde(rename = "physicalLocation", skip_serializing_if = "Option::is_none")]
    pub physical_location: Option<SarifPhysicalLocation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<SarifMessage>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThreadFlowLocation {
    pub location: SarifLocation,
    #[serde(skip_serializing_if = "Option::is_none")]
    #[serde(rename = "executionOrder")]
    pub step: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub importance: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThreadFlow {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<SarifMessage>,
    pub locations: Vec<ThreadFlowLocation>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CodeFlow {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<SarifMessage>,
    #[serde(rename = "threadFlows")]
    pub thread_flows: Vec<ThreadFlow>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: SarifMessage,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub location: Option<SarifLocation>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphEdge {
    pub id: String,
    #[serde(rename = "sourceNodeId")]
    pub source_node_id: String,
    #[serde(rename = "targetNodeId")]
    pub target_node_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub label: Option<SarifMessage>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SarifGraph {
    pub properties: std::collections::BTreeMap<String, String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<SarifMessage>,
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
}

/// Constructs a SARIF 2.1 codeFlow demonstrating a cross-resource relationship trace.
///
/// Why: GitHub Code Scanning requires repository-relative URIs in artifactLocation.
/// Strips UNC and absolute working directory prefixes to ensure PR annotations succeed.
pub fn build_cross_resource_code_flow(
    source_file: &str,
    source_line: usize,
    source_msg: &str,
    target_file: &str,
    target_line: usize,
    target_msg: &str,
) -> CodeFlow {
    let norm_source = crate::path_utils::relativize_to_workspace(source_file, None);
    let norm_target = crate::path_utils::relativize_to_workspace(target_file, None);

    CodeFlow {
        message: Some(SarifMessage {
            text: "Cross-resource relationship resolution failure".to_string(),
        }),
        thread_flows: vec![ThreadFlow {
            id: Some("flow-1".to_string()),
            message: Some(SarifMessage {
                text: "Resolution chain".to_string(),
            }),
            locations: vec![
                ThreadFlowLocation {
                    location: SarifLocation {
                        physical_location: Some(SarifPhysicalLocation {
                            artifact_location: SarifArtifactLocation {
                                uri: norm_source,
                                uri_base_id: None,
                            },
                            region: Some(SarifRegion {
                                start_line: source_line,
                                start_column: Some(1),
                                end_line: None,
                                end_column: None,
                            }),
                        }),
                        message: Some(SarifMessage {
                            text: source_msg.to_string(),
                        }),
                    },
                    step: Some(1),
                    importance: Some("essential".to_string()),
                },
                ThreadFlowLocation {
                    location: SarifLocation {
                        physical_location: Some(SarifPhysicalLocation {
                            artifact_location: SarifArtifactLocation {
                                uri: norm_target,
                                uri_base_id: None,
                            },
                            region: Some(SarifRegion {
                                start_line: target_line,
                                start_column: Some(1),
                                end_line: None,
                                end_column: None,
                            }),
                        }),
                        message: Some(SarifMessage {
                            text: target_msg.to_string(),
                        }),
                    },
                    step: Some(2),
                    importance: Some("essential".to_string()),
                },
            ],
        }],
    }
}

/// Generates a SARIF graph representation of resource dependency topology.
pub fn build_sarif_graph(graph_id: &str, edges: &[(String, String, String)]) -> SarifGraph {
    let mut nodes = Vec::new();
    let mut seen_nodes = std::collections::HashSet::new();

    for (src, dst, _) in edges {
        if seen_nodes.insert(src.clone()) {
            nodes.push(GraphNode {
                id: src.clone(),
                label: SarifMessage { text: src.clone() },
                location: None,
            });
        }
        if seen_nodes.insert(dst.clone()) {
            nodes.push(GraphNode {
                id: dst.clone(),
                label: SarifMessage { text: dst.clone() },
                location: None,
            });
        }
    }

    let sarif_edges = edges
        .iter()
        .enumerate()
        .map(|(i, (src, dst, label))| GraphEdge {
            id: format!("edge-{}", i),
            source_node_id: src.clone(),
            target_node_id: dst.clone(),
            label: Some(SarifMessage {
                text: label.clone(),
            }),
        })
        .collect();

    SarifGraph {
        properties: std::collections::BTreeMap::from([("id".to_string(), graph_id.to_string())]),
        description: Some(SarifMessage {
            text: "Topology dependency graph".to_string(),
        }),
        nodes,
        edges: sarif_edges,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_code_flow_serialization() {
        let cf = build_cross_resource_code_flow(
            "service.yaml",
            12,
            "Service selects app=web",
            "deployment.yaml",
            24,
            "Deployment labels app=api",
        );
        let json = serde_json::to_string(&cf).expect("Serialize CodeFlow");
        assert!(json.contains("service.yaml"));
        assert!(json.contains("deployment.yaml"));
        assert!(json.contains("threadFlows"));
        assert!(json.contains("essential"));
    }

    #[test]
    fn test_graph_serialization() {
        let edges = vec![
            (
                "Service:api".to_string(),
                "Deployment:api".to_string(),
                "selects".to_string(),
            ),
            (
                "Deployment:api".to_string(),
                "ConfigMap:env".to_string(),
                "mounts".to_string(),
            ),
        ];
        let graph = build_sarif_graph("k8s-topology", &edges);
        assert_eq!(graph.nodes.len(), 3);
        assert_eq!(graph.edges.len(), 2);
        let json = serde_json::to_string(&graph).expect("Serialize Graph");
        assert!(json.contains("Service:api"));
        assert!(json.contains("selects"));
    }

    #[test]
    fn test_code_flow_relativization_windows_unc() {
        let cf = build_cross_resource_code_flow(
            r"\\?\D:\yamlr\k8s\service.yaml",
            10,
            "Target service",
            r"\\?\D:\yamlr\k8s\deployment.yaml",
            20,
            "Source deployment",
        );
        let json = serde_json::to_string(&cf).expect("Serialize CodeFlow");
        assert!(!json.contains(r"\\?\"));
        assert!(json.contains("service.yaml"));
        assert!(json.contains("deployment.yaml"));
    }
}
