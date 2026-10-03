#[cfg(feature = "python")]
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeShard {
    pub line_no: usize,
    pub indent: usize,
    pub key: String,
    pub value: Option<String>,
    pub is_list_item: bool,
    pub is_doc_boundary: bool,
    pub is_block: bool,
    pub is_flow_style: bool,
    pub raw_line: String,
    pub comment: String,
    pub layout_sequence: Vec<String>,
    pub trailing_layout_sequence: Vec<String>,
    pub is_table_continuation: bool,
    pub original_indent: usize,
    pub line_ending: String,
}

impl Default for NativeShard {
    fn default() -> Self {
        Self {
            line_no: 0,
            indent: 0,
            key: String::new(),
            value: None,
            is_list_item: false,
            is_doc_boundary: false,
            is_block: false,
            is_flow_style: false,
            raw_line: String::new(),
            comment: String::new(),
            layout_sequence: Vec::new(),
            trailing_layout_sequence: Vec::new(),
            is_table_continuation: false,
            original_indent: 0,
            line_ending: "\n".to_string(),
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeIdentity {
    pub kind: String,
    pub api_version: Option<String>,
    pub name: String,
    pub namespace: String,
    pub owner_refs: Vec<String>,
    pub labels: HashMap<String, String>,
    pub selector: HashMap<String, String>,
    pub config_refs: Vec<String>,
    pub secret_refs: Vec<String>,
    pub volume_refs: Vec<String>,
    pub service_refs: Vec<String>,
    pub role_refs: Vec<String>,
    pub cluster_role_refs: Vec<String>,
    pub service_account: Option<String>,
    pub shadow_fingerprint: String,
    pub relationships: Vec<NativeRelationship>,
    pub ports: Vec<i32>,
    #[serde(default)]
    pub annotations: HashMap<String, String>,
    #[serde(default)]
    pub container_images: Vec<String>,
    #[serde(default)]
    pub container_envs: HashMap<String, String>,
    #[serde(default)]
    pub security_context: HashMap<String, String>,
    #[serde(default)]
    pub container_port_defs: Vec<(Option<String>, i32)>,
    #[serde(default)]
    pub replicas: Option<i32>,
}

impl Default for NativeIdentity {
    fn default() -> Self {
        Self {
            kind: String::new(),
            api_version: None,
            name: String::new(),
            namespace: "default".to_string(),
            owner_refs: Vec::new(),
            labels: HashMap::new(),
            selector: HashMap::new(),
            config_refs: Vec::new(),
            secret_refs: Vec::new(),
            volume_refs: Vec::new(),
            service_refs: Vec::new(),
            role_refs: Vec::new(),
            cluster_role_refs: Vec::new(),
            service_account: None,
            shadow_fingerprint: String::new(),
            relationships: Vec::new(),
            ports: Vec::new(),
            annotations: HashMap::new(),
            container_images: Vec::new(),
            container_envs: HashMap::new(),
            security_context: HashMap::new(),
            container_port_defs: Vec::new(),
            replicas: None,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NativeEdge {
    pub from_resource: String,
    pub to_resource: String,
    pub edge_type: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl NativeEdge {
    #[new]
    #[pyo3(signature = (from_resource, to_resource, edge_type))]
    pub fn new(from_resource: String, to_resource: String, edge_type: String) -> Self {
        Self {
            from_resource,
            to_resource,
            edge_type,
        }
    }

    #[getter]
    pub fn source(&self) -> String {
        self.from_resource.clone()
    }

    #[getter]
    pub fn target(&self) -> String {
        self.to_resource.clone()
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticNode {
    pub key: String,
    pub value: Option<String>,
    pub children: Vec<SemanticNode>,
    pub shards: Vec<NativeShard>,
    pub indent: usize,
    pub is_empty_flow: bool,
}

impl SemanticNode {
    pub fn find_node(&self, key: &str) -> Option<&SemanticNode> {
        if self.key == key {
            return Some(self);
        }
        self.children.iter().find(|c| c.key == key)
    }

    pub fn find_node_mut(&mut self, key: &str) -> Option<&mut SemanticNode> {
        if self.key == key {
            return Some(self);
        }
        self.children.iter_mut().find(|c| c.key == key)
    }

    pub fn find_value(&self, key: &str) -> Option<String> {
        if self.key == key {
            return self.value.clone();
        }
        self.children
            .iter()
            .find(|c| c.key == key)
            .and_then(|c| c.value.clone())
    }

    pub fn find_annotation(&self, ann_key: &str) -> Option<String> {
        self.find_node("metadata")
            .and_then(|m| m.find_node("annotations"))
            .and_then(|a| a.find_value(ann_key))
    }

    pub fn find_node_by_path_mut(&mut self, path: &[&str]) -> Option<&mut SemanticNode> {
        let mut current = self;
        for &key in path {
            let mut found = false;
            if let Some(idx) = current.children.iter().position(|c| c.key == key) {
                current = &mut current.children[idx];
                found = true;
            }
            if !found {
                return None;
            }
        }
        Some(current)
    }

    pub fn find_nodes_by_key_recursive(&self, target_key: &str) -> Vec<&SemanticNode> {
        let mut results = Vec::new();
        if self.key == target_key {
            results.push(self);
        }
        for child in &self.children {
            results.extend(child.find_nodes_by_key_recursive(target_key));
        }
        results
    }

    pub fn find_nodes_by_key_recursive_mut(&mut self, target_key: &str) -> Vec<&mut SemanticNode> {
        let mut results = Vec::new();
        // Base case: If this node matches, we add it.
        // Note: To satisfy the borrow checker, we only return either the node OR its children.
        if self.key == target_key {
            results.push(self);
        } else {
            for child in &mut self.children {
                results.extend(child.find_nodes_by_key_recursive_mut(target_key));
            }
        }
        results
    }

    /// Finds all Pod spec nodes (nodes containing 'containers') without borrow conflicts.
    pub fn find_pod_specs_mut(&mut self) -> Vec<&mut SemanticNode> {
        let mut results = Vec::new();
        if self.children.iter().any(|c| c.key == "containers") {
            results.push(self);
            return results;
        }
        for child in &mut self.children {
            if child.key == "spec" || child.key == "template" || child.key == "jobTemplate" {
                results.extend(child.find_pod_specs_mut());
            }
        }
        results
    }

    /// Finds all Pod spec nodes (read-only).
    pub fn find_pod_specs(&self) -> Vec<&SemanticNode> {
        let mut results = Vec::new();
        if self.children.iter().any(|c| c.key == "containers") {
            results.push(self);
            return results;
        }
        for child in &self.children {
            if child.key == "spec" || child.key == "template" || child.key == "jobTemplate" {
                results.extend(child.find_pod_specs());
            }
        }
        results
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticManifest {
    pub root: SemanticNode,
    pub indent_step: usize,
    pub integrity_violations: Vec<IntegrityViolation>,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NativeDiscoveryResult {
    pub file_path: String,
    pub identity: Option<NativeIdentity>,
    pub shard_count: usize,
}

#[cfg(feature = "python")]
#[pymethods]
impl NativeDiscoveryResult {
    #[new]
    #[pyo3(signature = (file_path, identity, shard_count))]
    pub fn new(file_path: String, identity: Option<NativeIdentity>, shard_count: usize) -> Self {
        Self {
            file_path,
            identity,
            shard_count,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NativeBlastRadius {
    pub target_resource: String,
    pub impacted_resources: Vec<String>,
    pub risk_score: f64,
    #[serde(default)]
    pub depth: usize,
    #[serde(default)]
    pub risk_level: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl NativeBlastRadius {
    #[new]
    #[pyo3(signature = (target_resource, impacted_resources, risk_score, depth=0, risk_level="LOW".to_string()))]
    pub fn new(
        target_resource: String,
        impacted_resources: Vec<String>,
        risk_score: f64,
        depth: usize,
        risk_level: String,
    ) -> Self {
        Self {
            target_resource,
            impacted_resources,
            risk_score,
            depth,
            risk_level,
        }
    }

    #[getter]
    pub fn source(&self) -> String {
        self.target_resource.clone()
    }

    #[getter]
    pub fn affected_count(&self) -> usize {
        self.impacted_resources.len()
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NativeSchema {
    pub kind: String,
    pub api_version: String,
    pub properties: Vec<SchemaProperty>,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaProperty {
    pub name: String,
    pub prop_type: String,
    pub required: bool,
    pub description: String,
    #[serde(default)]
    pub enum_values: Vec<String>,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaViolation {
    pub field_path: String,
    pub message: String,
    pub severity: String,
    pub suggested_value: String,
    #[serde(default)]
    pub line_no: usize,
}

#[cfg(feature = "python")]
#[pymethods]
impl SchemaViolation {
    #[new]
    #[pyo3(signature = (field_path, message, severity, suggested_value, line_no=0))]
    pub fn new(
        field_path: String,
        message: String,
        severity: String,
        suggested_value: String,
        line_no: usize,
    ) -> Self {
        Self {
            field_path,
            message,
            severity,
            suggested_value,
            line_no,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct IntegrityViolation {
    pub check_name: String,
    pub message: String,
    pub severity: String,
    pub rule_id: String,
    pub line_no: usize,
}

#[cfg(feature = "python")]
#[pymethods]
impl IntegrityViolation {
    #[new]
    #[pyo3(signature = (check_name, message, severity, rule_id, line_no=0))]
    pub fn new(
        check_name: String,
        message: String,
        severity: String,
        rule_id: String,
        line_no: usize,
    ) -> Self {
        Self {
            check_name,
            message,
            severity,
            rule_id,
            line_no,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct HelmHealResult {
    pub file_path: String,
    pub healed_yaml: String,
    pub changes: Vec<String>,
    pub had_changes: bool,
}

#[cfg(feature = "python")]
#[pymethods]
impl HelmHealResult {
    #[new]
    #[pyo3(signature = (file_path, healed_yaml, changes, had_changes))]
    pub fn new(
        file_path: String,
        healed_yaml: String,
        changes: Vec<String>,
        had_changes: bool,
    ) -> Self {
        Self {
            file_path,
            healed_yaml,
            changes,
            had_changes,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct NativeTelemetry {
    pub scans_completed: usize,
    pub heals_completed: usize,
    pub total_risk_mitigated: f64,
    pub potential_outages_prevented: usize,
    pub architectural_debt_reduced: f64,
    pub total_time_saved_ms: u64,
}

impl NativeTelemetry {
    pub fn new() -> Self {
        Self::default()
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl NativeTelemetry {
    #[new]
    pub fn py_new() -> Self {
        Self::new()
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", eq, eq_int))]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RelationshipType {
    SELECTS,
    CONSUMES,
    BINDS,
    MOUNTS,
    CONNECTS,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeRelationship {
    pub rel_type: RelationshipType,
    pub target_kind: String,
    pub target_name: String,
    pub target_namespace: Option<String>,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ResourceResult {
    pub file_path: String,
    pub identity: Option<NativeIdentity>,
    pub violations: Vec<SchemaViolation>,
    pub integrity_violations: Vec<IntegrityViolation>,
    pub health_score: f64,
    pub suggested_fixes: Vec<SchemaViolation>,
    pub relationships: Vec<NativeRelationship>,
}

#[cfg(feature = "python")]
#[pymethods]
impl ResourceResult {
    #[new]
    #[pyo3(signature = (file_path, identity, violations, integrity_violations, health_score, suggested_fixes, relationships))]
    pub fn new(
        file_path: String,
        identity: Option<NativeIdentity>,
        violations: Vec<SchemaViolation>,
        integrity_violations: Vec<IntegrityViolation>,
        health_score: f64,
        suggested_fixes: Vec<SchemaViolation>,
        relationships: Vec<NativeRelationship>,
    ) -> Self {
        Self {
            file_path,
            identity,
            violations,
            integrity_violations,
            health_score,
            suggested_fixes,
            relationships,
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeReport {
    pub total_files: usize,
    pub results: Vec<ResourceResult>,
    pub total_time_ms: u64,
    pub telemetry: NativeTelemetry,
}

#[cfg(feature = "python")]
#[pymethods]
impl NativeReport {
    #[new]
    #[pyo3(signature = (total_files, results, total_time_ms))]
    pub fn new(total_files: usize, results: Vec<ResourceResult>, total_time_ms: u64) -> Self {
        Self {
            total_files,
            results,
            total_time_ms,
            telemetry: NativeTelemetry::new(),
        }
    }
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeScoringResult {
    pub score: f64,
    pub level: String,
    pub breakdown: HashMap<String, f64>,
}

#[cfg_attr(feature = "python", pyclass(module = "yamlr_native", get_all, set_all))]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RemediationEntry {
    pub transaction_id: String,
    pub timestamp: String,
    pub file_path: String,
    pub resource_key: String,
    pub field_path: String,
    pub previous_value: Option<String>,
    pub new_value: String,
    pub before_snapshot: String,
    pub after_snapshot: String,
    pub status: String,
}

#[cfg(feature = "python")]
#[pymethods]
impl RemediationEntry {
    #[new]
    #[pyo3(signature = (transaction_id, timestamp, file_path, resource_key, field_path, previous_value, new_value, before_snapshot, after_snapshot, status))]
    pub fn new(
        transaction_id: String,
        timestamp: String,
        file_path: String,
        resource_key: String,
        field_path: String,
        previous_value: Option<String>,
        new_value: String,
        before_snapshot: String,
        after_snapshot: String,
        status: String,
    ) -> Self {
        Self {
            transaction_id,
            timestamp,
            file_path,
            resource_key,
            field_path,
            previous_value,
            new_value,
            before_snapshot,
            after_snapshot,
            status,
        }
    }
}
