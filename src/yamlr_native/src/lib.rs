use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use regex::Regex;
use lazy_static::lazy_static;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use rayon::prelude::*;

lazy_static! {
    static ref RE_KIND: Regex = Regex::new(r#"(?i)^kind:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
    static ref RE_API: Regex = Regex::new(r#"(?i)^apiVersion:\s*['"]?([a-zA-Z0-9./-]+)['"]?"#).unwrap();
    static ref RE_NAME: Regex = Regex::new(r#"(?i)^name:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
    static ref RE_NS: Regex = Regex::new(r#"(?i)^namespace:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct NativeShard {
    #[pyo3(get)]
    pub line_no: usize,
    #[pyo3(get)]
    pub indent: usize,
    #[pyo3(get)]
    pub key: String,
    #[pyo3(get)]
    pub value: Option<String>,
    #[pyo3(get)]
    pub is_list_item: bool,
    #[pyo3(get)]
    pub is_block: bool,
    #[pyo3(get)]
    pub is_doc_boundary: bool,
    #[pyo3(get)]
    pub comment: String,
    #[pyo3(get)]
    pub is_flow_style: bool,
}

#[pyfunction]
/// Breaks raw YAML into Shards ultra-fast.
fn native_shard(content: &str) -> PyResult<Vec<NativeShard>> {
    let mut shards = Vec::new();
    let mut in_block = false;
    let mut block_indent = 0;

    for (i, line) in content.lines().enumerate() {
        let trimmed_left = line.trim_start();
        let indent = line.len() - trimmed_left.len();
        let line_no = i + 1;

        // Document boundary
        let is_doc = trimmed_left.starts_with("---");
        if is_doc {
            in_block = false;
            block_indent = 0;
        }

        // Basic comment split (simplified for speed, doesn't handle escaped # in quotes yet)
        let (code_part, comment) = if let Some(idx) = trimmed_left.find('#') {
            (&trimmed_left[..idx].trim(), trimmed_left[idx+1..].trim().to_string())
        } else {
            (&trimmed_left.trim(), String::new())
        };

        if code_part.is_empty() && !in_block && !is_doc {
             continue; // Skip empty lines unless in block
        }

        // Block state management
        if code_part.ends_with('|') || code_part.ends_with('>') {
            in_block = true;
            block_indent = indent + 1;
        } else if in_block && !is_doc && indent < block_indent && !code_part.is_empty() {
            in_block = false;
        }

        let mut key = String::new();
        let mut value = None;
        let mut is_list = false;
        let mut is_flow = false;

        if in_block && !is_doc {
            value = Some(code_part.to_string());
        } else {
            let mut work_part = *code_part;
            if work_part.starts_with('-') && !is_doc {
                is_list = true;
                work_part = work_part[1..].trim();
            }

            if let Some(idx) = work_part.find(':') {
                key = work_part[..idx].trim().trim_matches(|c| c == '"' || c == '\'').to_string();
                let v = work_part[idx+1..].trim();
                if !v.is_empty() {
                    value = Some(v.to_string());
                    if (v.starts_with('{') && v.ends_with('}')) || (v.starts_with('[') && v.ends_with(']')) {
                        is_flow = true;
                    }
                }
            } else {
                value = Some(work_part.to_string());
            }
        }

        shards.push(NativeShard {
            line_no,
            indent,
            key,
            value,
            is_list_item: is_list,
            is_block: in_block,
            is_doc_boundary: is_doc,
            comment,
            is_flow_style: is_flow,
        });
    }

    Ok(shards)
}

#[pyfunction]
/// Extracts identity markers from content ultra-fast.
fn fast_scan(content: &str) -> PyResult<Vec<PyObject>> {
    let mut results = Vec::new();
    Python::with_gil(|py| {
        for doc in content.split("---") {
            if doc.trim().is_empty() { continue; }
            
            let mut kind = None;
            let mut api = None;
            let mut name = None;
            let mut ns = None;

            for line in doc.lines() {
                let trimmed = line.trim();
                if kind.is_none() { if let Some(c) = RE_KIND.captures(trimmed) { kind = Some(c[1].to_string()); } }
                if api.is_none() { if let Some(c) = RE_API.captures(trimmed) { api = Some(c[1].to_string()); } }
                if name.is_none() { if let Some(c) = RE_NAME.captures(trimmed) { name = Some(c[1].to_string()); } }
                if ns.is_none() { if let Some(c) = RE_NS.captures(trimmed) { ns = Some(c[1].to_string()); } }
            }

            if kind.is_some() && api.is_some() {
                let dict = PyDict::new_bound(py);
                dict.set_item("kind", kind).unwrap();
                dict.set_item("api_version", api).unwrap();
                dict.set_item("name", name).unwrap();
                dict.set_item("namespace", ns).unwrap();
                results.push(dict.to_object(py));
            }
        }
        Ok(results)
    })
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeIdentity {
    #[pyo3(get, set)]
    pub kind: String,
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub namespace: String,
    #[pyo3(get, set)]
    pub labels: HashMap<String, String>,
    #[pyo3(get, set)]
    pub selector: HashMap<String, String>,
    #[pyo3(get, set)]
    pub config_refs: Vec<String>,
    #[pyo3(get, set)]
    pub secret_refs: Vec<String>,
    #[pyo3(get, set)]
    pub volume_refs: Vec<String>,
    #[pyo3(get, set)]
    pub service_refs: Vec<String>,
    #[pyo3(get, set)]
    pub role_refs: Vec<String>,
    #[pyo3(get, set)]
    pub cluster_role_refs: Vec<String>,
    #[pyo3(get, set)]
    pub service_account: Option<String>,
}

#[pymethods]
impl NativeIdentity {
    #[new]
    #[pyo3(signature = (kind, name, namespace, labels=None, selector=None, config_refs=None, secret_refs=None, volume_refs=None, service_refs=None, role_refs=None, cluster_role_refs=None, service_account=None))]
    fn new(
        kind: String,
        name: String,
        namespace: String,
        labels: Option<Bound<'_, PyDict>>,
        selector: Option<Bound<'_, PyDict>>,
        config_refs: Option<Bound<'_, PyList>>,
        secret_refs: Option<Bound<'_, PyList>>,
        volume_refs: Option<Bound<'_, PyList>>,
        service_refs: Option<Bound<'_, PyList>>,
        role_refs: Option<Bound<'_, PyList>>,
        cluster_role_refs: Option<Bound<'_, PyList>>,
        service_account: Option<String>,
    ) -> Self {
        fn to_map(d: Option<Bound<'_, PyDict>>) -> HashMap<String, String> {
            let mut map = HashMap::new();
            if let Some(d) = d {
                for (k, v) in d {
                    if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
                        map.insert(ks, vs);
                    }
                }
            }
            map
        }
        fn to_vec(l: Option<Bound<'_, PyList>>) -> Vec<String> {
            let mut vec = Vec::new();
            if let Some(l) = l {
                for item in l {
                    if let Ok(s) = item.extract::<String>() {
                        vec.push(s);
                    }
                }
            }
            vec
        }

        Self {
            kind,
            name,
            namespace,
            labels: to_map(labels),
            selector: to_map(selector),
            config_refs: to_vec(config_refs),
            secret_refs: to_vec(secret_refs),
            volume_refs: to_vec(volume_refs),
            service_refs: to_vec(service_refs),
            role_refs: to_vec(role_refs),
            cluster_role_refs: to_vec(cluster_role_refs),
            service_account,
        }
    }
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeEdge {
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub edge_type: String,
}

#[pyfunction]
fn build_graph_edges(identities: Vec<NativeIdentity>) -> PyResult<Vec<NativeEdge>> {
    let mut edges = Vec::new();
    
    // 1. Index all identities for O(1) specific lookup
    let mut index = HashMap::new();
    for i in &identities {
        let key = format!("{}/{}/{}", i.kind, i.namespace, i.name);
        index.insert(key, i);
    }

    // 2. Parallel Edge Building via Rayon
    let result_edges: Vec<Vec<NativeEdge>> = identities.par_iter().map(|i| {
        let mut local_edges = Vec::new();
        let source_key = format!("{}/{}/{}", i.kind, i.namespace, i.name);

        // -- SELECTOR MATCH (Selector logic) --
        if !i.selector.is_empty() {
             for target in &identities {
                 if target.kind == "Pod" || target.kind == "Deployment" || target.kind == "StatefulSet" {
                     if i.namespace == target.namespace && labels_match(&i.selector, &target.labels) {
                         local_edges.push(NativeEdge {
                             source: source_key.clone(),
                             target: format!("{}/{}/{}", target.kind, target.namespace, target.name),
                             edge_type: "SELECTOR_MATCH".to_string(),
                         });
                     }
                 }
             }
        }

        // -- HARD REFERENCES (ConfigMap, Secret, PVC, etc.) --
        let ref_checks = vec![
            (&i.config_refs, "ConfigMap", "CONFIG_REF"),
            (&i.secret_refs, "Secret", "SECRET_REF"),
            (&i.volume_refs, "PersistentVolumeClaim", "PVC_REF"),
            (&i.service_refs, "Service", "SERVICE_REF"),
            (&i.role_refs, "Role", "ROLE_REF"),
            (&i.cluster_role_refs, "ClusterRole", "CLUSTER_ROLE_REF"),
        ];

        for (refs, target_kind, edge_type) in ref_checks {
            for ref_name in refs {
                let lookup_ns = if target_kind == "ClusterRole" { "default" } else { &i.namespace };
                let target_key = format!("{}/{}/{}", target_kind, lookup_ns, ref_name);
                if index.contains_key(&target_key) {
                    local_edges.push(NativeEdge {
                        source: source_key.clone(),
                        target: target_key,
                        edge_type: edge_type.to_string(),
                    });
                }
            }
        }

        // -- SERVICE ACCOUNT --
        if let Some(sa) = &i.service_account {
            let target_key = format!("ServiceAccount/{}/{}", i.namespace, sa);
            if index.contains_key(&target_key) {
                local_edges.push(NativeEdge {
                    source: source_key.clone(),
                    target: target_key,
                    edge_type: "SERVICE_ACCOUNT_REF".to_string(),
                });
            }
        }

        local_edges
    }).collect();

    for batch in result_edges {
        edges.extend(batch);
    }

    Ok(edges)
}

fn labels_match(selector: &HashMap<String, String>, labels: &HashMap<String, String>) -> bool {
    if selector.is_empty() { return false; }
    for (k, v) in selector {
        if labels.get(k) != Some(v) {
            return false;
        }
    }
    true
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct RustFinding {
    stage: String,
    action_type: String,
    target: String,
    description: String,
    severity: String,
    rule_id: String,
    line_number: usize,
}

impl RustFinding {
    fn to_py(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);
        dict.set_item("stage", &self.stage)?;
        dict.set_item("action_type", &self.action_type)?;
        dict.set_item("target", &self.target)?;
        dict.set_item("description", &self.description)?;
        dict.set_item("severity", &self.severity)?;
        dict.set_item("rule_id", &self.rule_id)?;
        dict.set_item("line_number", self.line_number)?;
        Ok(dict.to_object(py))
    }
}

fn do_fast_audit(content: &str) -> Vec<RustFinding> {
    let mut findings = Vec::new();
    if content.starts_with('\u{feff}') {
        findings.push(RustFinding {
            stage: "Lexer".into(), action_type: "BOM_DETECTED".into(), target: "Line 1".into(),
            description: "BOM found at start of file".into(), severity: "WARNING".into(),
            rule_id: "yaml/bom".into(), line_number: 1
        });
    }
    if content.contains("\r\n") {
        findings.push(RustFinding {
            stage: "Lexer".into(), action_type: "CRLF_DETECTED".into(), target: "Document".into(),
            description: "CRLF line endings detected".into(), severity: "INFO".into(),
            rule_id: "yaml/crlf".into(), line_number: 1
        });
    }
    
    for document in serde_yaml::Deserializer::from_str(content) {
        if let Err(e) = serde_yaml::Value::deserialize(document) {
            let line = e.location().map(|l| l.line()).unwrap_or(1);
            findings.push(RustFinding {
                stage: "Structurer".into(), action_type: "YAML_ERROR".into(), target: format!("Line {}", line),
                description: format!("Structural Error: {}", e), severity: "ERROR".into(),
                rule_id: "yaml/parse-error".into(), line_number: line as usize
            });
        }
    }
    findings
}

#[pyfunction]
/// Ultra-fast auditing of YAML manifests in Rust.
fn native_fast_audit(py: Python<'_>, content: &str) -> PyResult<PyObject> {
    let findings = do_fast_audit(content);
    let list = PyList::new_bound(py, findings.iter().map(|f| f.to_py(py).unwrap()).collect::<Vec<_>>());
    Ok(list.to_object(py))
}

#[pyfunction]
/// Batch processes multiple files in parallel in Rust (VAL-02-6).
fn native_batch_fast_audit(py: Python<'_>, paths: Vec<String>) -> PyResult<Vec<Vec<PyObject>>> {
    let raw_results: Vec<Vec<RustFinding>> = paths.par_iter().map(|path| {
        match std::fs::read_to_string(path) {
            Ok(content) => do_fast_audit(&content),
            Err(_) => Vec::new(), 
        }
    }).collect();
    
    let mut final_results = Vec::new();
    for findings in raw_results {
        let mut py_findings = Vec::new();
        for f in findings {
            py_findings.push(f.to_py(py)?);
        }
        final_results.push(py_findings);
    }
    Ok(final_results)
}

fn value_to_py(py: Python<'_>, value: &serde_yaml::Value) -> PyResult<PyObject> {
    match value {
        serde_yaml::Value::Null => Ok(py.None()),
        serde_yaml::Value::Bool(b) => Ok(b.to_object(py)),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_object(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.to_object(py))
            } else {
                Ok(py.None())
            }
        }
        serde_yaml::Value::String(s) => Ok(s.to_object(py)),
        serde_yaml::Value::Sequence(seq) => {
            let list = PyList::empty_bound(py);
            for v in seq {
                list.append(value_to_py(py, v)?)?;
            }
            Ok(list.to_object(py))
        }
        serde_yaml::Value::Mapping(map) => {
            let dict = PyDict::new_bound(py);
            for (k, v) in map {
                let key = value_to_py(py, k)?;
                let val = value_to_py(py, v)?;
                dict.set_item(key, val)?;
            }
            Ok(dict.to_object(py))
        }
        serde_yaml::Value::Tagged(tagged) => {
             value_to_py(py, &tagged.value)
        }
    }
}

#[pyfunction]
/// Parses YAML into Python dictionaries ultra-fast in Rust.
/// Why: Avoids the overhead of Python-based parsing for read-only validation (VAL-02-6).
fn native_parse_to_dict(py: Python<'_>, content: &str) -> PyResult<Vec<PyObject>> {
    let mut results = Vec::new();
    for document in serde_yaml::Deserializer::from_str(content) {
        match serde_yaml::Value::deserialize(document) {
            Ok(val) => {
                results.push(value_to_py(py, &val)?);
            }
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("YAML Parse Error: {}", e)));
            }
        }
    }
    Ok(results)
}

#[derive(Deserialize)]
struct MinimalMetadata {
    name: Option<String>,
    namespace: Option<String>,
    labels: Option<HashMap<String, serde_yaml::Value>>,
}

#[derive(Deserialize)]
struct MinimalResource {
    kind: Option<String>,
    #[serde(rename = "apiVersion")]
    api_version: Option<String>,
    metadata: Option<MinimalMetadata>,
}

#[pyfunction]
/// Extracts only the metadata (kind, apiVersion, name, namespace, labels) ultra-fast.
/// Why: Avoids 10GB+ RAM explosion by skipping full tree construction (VAL-02-6).
fn native_extract_metadata(py: Python<'_>, content: &str) -> PyResult<Vec<PyObject>> {
    let mut results = Vec::new();
    for document in serde_yaml::Deserializer::from_str(content) {
        // Use MinimalResource to only deserialize what we need (Sovereign extraction)
        if let Ok(val) = MinimalResource::deserialize(document) {
            let dict = PyDict::new_bound(py);
            
            // Top-level identity
            if let Some(kind) = val.kind {
                dict.set_item("kind", kind)?;
            }
            if let Some(api) = val.api_version {
                dict.set_item("apiVersion", api)?;
            }
            
            // Metadata block (Sovereign Alignment)
            if let Some(meta) = val.metadata {
                let py_meta = PyDict::new_bound(py);
                if let Some(name) = meta.name {
                    py_meta.set_item("name", name)?;
                }
                if let Some(ns) = meta.namespace {
                    py_meta.set_item("namespace", ns)?;
                }
                
                // Extract labels (critical for Relational Surgery)
                if let Some(labels) = meta.labels {
                    let py_labels = PyDict::new_bound(py);
                    for (lk, lv) in labels {
                        let v = match lv {
                            serde_yaml::Value::String(s) => s.clone(),
                            serde_yaml::Value::Number(n) => n.to_string(),
                            serde_yaml::Value::Bool(b) => b.to_string(),
                            _ => "".to_string(),
                        };
                        py_labels.set_item(lk, v)?;
                    }
                    py_meta.set_item("labels", py_labels)?;
                }
                dict.set_item("metadata", py_meta)?;
            }
            results.push(dict.to_object(py));
        }
    }
    Ok(results)
}

#[pymodule]
fn yamlr_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_shard, m)?)?;
    m.add_function(wrap_pyfunction!(native_fast_audit, m)?)?;
    m.add_function(wrap_pyfunction!(native_batch_fast_audit, m)?)?;
    m.add_function(wrap_pyfunction!(native_parse_to_dict, m)?)?;
    m.add_function(wrap_pyfunction!(native_extract_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(fast_scan, m)?)?;
    m.add_function(wrap_pyfunction!(build_graph_edges, m)?)?;
    m.add_class::<NativeShard>()?;
    m.add_class::<NativeEdge>()?;
    m.add_class::<NativeIdentity>()?;
    Ok(())
}
