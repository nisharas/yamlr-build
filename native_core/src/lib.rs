#![allow(clippy::all)]

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::wrap_pyfunction;
use std::collections::HashMap;

pub mod audit_engine;
pub mod audit_registry;
pub mod auditors;
pub mod cache;
pub mod cel;
pub mod cli;
pub mod cluster;
pub mod discovery;
pub mod ffi;
pub mod grpc;
pub mod healers;
pub mod healing;
pub mod identity;
pub mod models;
pub mod otel_exporter;
pub mod parsers;
pub mod path_utils;
pub mod pipeline;
pub mod rego;
pub mod remediation_io;
pub mod sarif;
pub mod schemas;
pub mod security;
pub mod sharder;
pub mod shield;
pub mod structurer;
pub mod telemetry;
pub mod telemetry_gate;
pub mod wasm;

use crate::discovery::*;
use crate::identity::*;
use crate::models::*;
#[cfg(feature = "python")]
use crate::pipeline::*;
#[cfg(feature = "python")]
use crate::sharder::*;
use crate::telemetry::*;

#[cfg_attr(feature = "python", pyfunction(name = "native_calculate_blast_radius"))]
pub fn native_calculate_blast_radius_wrapper(
    resource_name: String,
    edges: Vec<NativeEdge>,
) -> NativeBlastRadius {
    crate::discovery::native_calculate_blast_radius(resource_name, edges)
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_record_telemetry(
    mut telemetry: NativeTelemetry,
    event: String,
    risk: f64,
    time_ms: u64,
    _level: String,
) -> NativeTelemetry {
    if event == "SCAN" {
        telemetry.scans_completed += 1;
    } else if event == "HEAL" {
        telemetry.heals_completed += 1;
    }
    telemetry.total_risk_mitigated += risk;
    telemetry.total_time_saved_ms += time_ms;
    telemetry
}

#[cfg_attr(feature = "python", pyfunction(name = "native_audit_forensics"))]
pub fn native_audit_forensics_wrapper(shards: Vec<NativeShard>) -> Vec<IntegrityViolation> {
    let mut integrity_violations = Vec::new();

    // 1. Identity-based Audits (Deprecations) - borrow shards without clone
    if let Some(id) = extract_native_identity_ref(&shards) {
        if let Some(v) =
            crate::audit_engine::audit_manifest(&id.api_version.unwrap_or_default(), &id.kind)
        {
            integrity_violations.push(v);
        }
    }

    // 2. Shard-level Audits (Images, Resources, etc.) - borrow shards without clone
    for shard in &shards {
        if shard.key == "image" && shard.value.is_some() {
            if let Some(v) = crate::audit_engine::audit_image(shard.value.as_ref().unwrap()) {
                integrity_violations.push(v);
            }
        }
    }

    // 3. Structural Audits (e.g., Duplicate Keys) - moves shards, zero clones!
    let manifest = crate::structurer::native_structurize(shards);
    integrity_violations.extend(manifest.integrity_violations);

    integrity_violations
}

#[cfg_attr(feature = "python", pyfunction(name = "native_audit_registry"))]
pub fn native_audit_registry(identities: Vec<NativeIdentity>) -> Vec<IntegrityViolation> {
    crate::audit_registry::AuditRegistry::audit_all(&identities)
}

// Wrapper functions for PyO3 to bridge module-level functions
#[cfg(feature = "python")]
#[pyfunction(name = "native_shard")]
pub fn native_shard_wrapper(py: Python<'_>, content: String) -> Vec<NativeShard> {
    py.allow_threads(|| native_shard(&content))
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_structurize")]
pub fn native_structurize_wrapper(py: Python<'_>, shards: Vec<NativeShard>) -> SemanticManifest {
    py.allow_threads(|| crate::structurer::native_structurize(shards))
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_heal_manifest")]
pub fn native_heal_manifest_wrapper(
    py: Python<'_>,
    mut manifest: SemanticManifest,
    mut telemetry: NativeTelemetry,
) -> (SemanticManifest, NativeTelemetry, Vec<String>) {
    py.allow_threads(|| {
        let changes = crate::healing::native_heal_manifest(&mut manifest, &mut telemetry);
        (manifest, telemetry, changes)
    })
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_reconstruct_from_semantic")]
pub fn native_reconstruct_from_semantic_wrapper(
    py: Python<'_>,
    manifest: SemanticManifest,
) -> String {
    py.allow_threads(|| crate::healing::native_reconstruct_from_semantic(&manifest))
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_reconstruct_yaml")]
pub fn native_reconstruct_yaml_wrapper(py: Python<'_>, shards: Vec<NativeShard>) -> String {
    py.allow_threads(|| native_reconstruct_yaml(&shards))
}

#[cfg_attr(feature = "python", pyfunction(name = "extract_native_identity"))]
pub fn extract_native_identity_wrapper(shards: Vec<NativeShard>) -> Option<NativeIdentity> {
    extract_native_identity(shards)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_discover_resources")]
pub fn native_discover_resources_wrapper(
    root_path: String,
) -> PyResult<Vec<NativeDiscoveryResult>> {
    native_discover_resources(root_path).map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(not(feature = "python"))]
pub fn native_discover_resources_wrapper(
    root_path: String,
) -> Result<Vec<NativeDiscoveryResult>, String> {
    native_discover_resources(root_path)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_build_topology_graph"))]
pub fn native_build_topology_graph_wrapper(
    discovery: Vec<NativeDiscoveryResult>,
) -> Vec<NativeEdge> {
    native_build_topology_graph(discovery)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_apply_fix_atomic")]
#[pyo3(signature = (file_path, field_path, new_value, target_kind=None, target_name=None))]
pub fn native_apply_fix_atomic_wrapper(
    file_path: String,
    field_path: String,
    new_value: String,
    target_kind: Option<String>,
    target_name: Option<String>,
) -> PyResult<bool> {
    crate::remediation_io::native_apply_fix_atomic(
        file_path,
        field_path,
        new_value,
        target_kind,
        target_name,
    )
    .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_log_remediation")]
pub fn native_log_remediation_wrapper(
    journal_path: String,
    resource_key: String,
    remediation: String,
) -> PyResult<()> {
    crate::remediation_io::native_log_remediation(journal_path, resource_key, remediation)
        .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_get_telemetry_dashboard")
)]
pub fn native_get_telemetry_dashboard_wrapper(telemetry: NativeTelemetry) -> String {
    native_get_telemetry_dashboard(&telemetry)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_calculate_dna_hash"))]
pub fn native_calculate_dna_hash_wrapper(content: &str) -> String {
    native_calculate_dna_hash(content)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_record_telemetry"))]
pub fn native_record_telemetry_wrapper(
    telemetry: NativeTelemetry,
    event: String,
    risk: f64,
    time_ms: u64,
    level: String,
) -> NativeTelemetry {
    native_record_telemetry(telemetry, event, risk, time_ms, level)
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_get_schema_for_version(version: String) -> Vec<NativeSchema> {
    crate::schemas::native_get_schema_for_version(&version)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_extract_schema_from_crd")]
pub fn native_extract_schema_from_crd_wrapper(content: String) -> PyResult<Vec<NativeSchema>> {
    crate::schemas::native_extract_schema_from_crd(&content)
        .map_err(pyo3::exceptions::PyValueError::new_err)
}

#[cfg(not(feature = "python"))]
pub fn native_extract_schema_from_crd_wrapper(
    content: String,
) -> Result<Vec<NativeSchema>, String> {
    crate::schemas::native_extract_schema_from_crd(&content)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_distill_crd_file")]
pub fn native_distill_crd_file_wrapper(path: String) -> PyResult<Vec<NativeSchema>> {
    crate::schemas::distill_crd_file(&path).map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(not(feature = "python"))]
pub fn native_distill_crd_file_wrapper(path: String) -> Result<Vec<NativeSchema>, String> {
    crate::schemas::distill_crd_file(&path)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_distill_crd_directory")]
pub fn native_distill_crd_directory_wrapper(dir_path: String) -> PyResult<Vec<NativeSchema>> {
    crate::schemas::distill_crd_directory(&dir_path).map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(not(feature = "python"))]
pub fn native_distill_crd_directory_wrapper(dir_path: String) -> Result<Vec<NativeSchema>, String> {
    crate::schemas::distill_crd_directory(&dir_path)
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_get_build_info() -> HashMap<String, String> {
    let mut info = HashMap::new();
    info.insert("version".to_string(), env!("CARGO_PKG_VERSION").to_string());
    info.insert("standard".to_string(), "v1-42".to_string());
    info.insert("build_id".to_string(), "REL-2026-05-05".to_string());
    info.insert("engine".to_string(), "Rust Native".to_string());
    info
}

#[cfg_attr(feature = "python", pyfunction(name = "native_detect_version_drift"))]
pub fn native_detect_version_drift_wrapper(discovery: Vec<NativeDiscoveryResult>) -> Vec<String> {
    crate::discovery::native_detect_version_drift(discovery)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_detect_dangling_selectors")
)]
pub fn native_detect_dangling_selectors_wrapper(
    discovery: Vec<NativeDiscoveryResult>,
) -> Vec<String> {
    crate::discovery::native_detect_dangling_selectors(&discovery)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_detect_orphaned_resources")
)]
pub fn native_detect_orphaned_resources_wrapper(
    discovery: Vec<NativeDiscoveryResult>,
) -> Vec<String> {
    crate::discovery::native_detect_orphaned_resources(&discovery)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_detect_service_shadowing")
)]
pub fn native_detect_service_shadowing_wrapper(
    discovery: Vec<NativeDiscoveryResult>,
) -> Vec<String> {
    crate::discovery::native_detect_service_shadowing(&discovery)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_detect_circular_dependencies")
)]
pub fn native_detect_circular_dependencies_wrapper(edges: Vec<NativeEdge>) -> Vec<String> {
    crate::discovery::native_detect_circular_dependencies(&edges)
}

#[cfg(feature = "python")]
#[pyfunction]
fn native_cli_run(py: Python<'_>, args: Vec<String>) -> i32 {
    py.allow_threads(|| crate::cli::dispatch::run(&args))
}

#[cfg(feature = "python")]
#[pymodule]
fn yamlr_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_cli_run, m)?)?;
    m.add_class::<NativeShard>()?;
    m.add_class::<NativeIdentity>()?;
    m.add_class::<NativeEdge>()?;
    m.add_class::<NativeDiscoveryResult>()?;
    m.add_class::<NativeBlastRadius>()?;
    m.add_class::<NativeSchema>()?;
    m.add_class::<SchemaProperty>()?;
    m.add_class::<SchemaViolation>()?;
    m.add_class::<IntegrityViolation>()?;
    m.add_class::<NativeTelemetry>()?;
    m.add_class::<ResourceResult>()?;
    m.add_class::<NativeReport>()?;
    m.add_class::<NativeScoringResult>()?;
    m.add_class::<NativeRelationship>()?;
    m.add_class::<RelationshipType>()?;
    m.add_class::<HelmHealResult>()?;
    m.add_class::<RemediationEntry>()?;

    m.add_function(wrap_pyfunction!(native_shard_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_structurize_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_manifest_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(
        native_reconstruct_from_semantic_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(native_reconstruct_yaml_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(extract_native_identity_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_discover_resources_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_build_topology_graph_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_calculate_blast_radius_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_check_schema_violations, m)?)?;
    m.add_function(wrap_pyfunction!(native_generate_schema_fixes, m)?)?;
    m.add_function(wrap_pyfunction!(native_record_telemetry_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_calculate_dna_hash_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_get_telemetry_dashboard_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_run_pipeline, m)?)?;
    m.add_function(wrap_pyfunction!(native_run_pipeline_streaming, m)?)?;
    m.add_function(wrap_pyfunction!(native_apply_fix_atomic_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_log_remediation_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_audit_forensics_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_audit_registry, m)?)?;
    m.add_function(wrap_pyfunction!(native_get_build_info, m)?)?;
    m.add_function(wrap_pyfunction!(native_get_schema_for_version, m)?)?;
    m.add_function(wrap_pyfunction!(native_extract_schema_from_crd_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_distill_crd_file_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_distill_crd_directory_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_get_machine_id_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_verify_token_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_sign_manifest_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_verify_manifest_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_detect_version_drift_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(
        native_detect_dangling_selectors_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        native_detect_orphaned_resources_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        native_detect_service_shadowing_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        native_detect_circular_dependencies_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(native_detect_cluster_version_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_format_yaml_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_schema_typos_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_enum_typos_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_structural_issues_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_service_selectors_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_yaml_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(
        native_generate_default_deny_network_policy,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(native_generate_stub, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_values_yaml, m)?)?;
    m.add_function(wrap_pyfunction!(native_heal_umbrella_chart, m)?)?;
    m.add_function(wrap_pyfunction!(native_harden_security_context_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_rollback_remediation_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_list_remediations_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_vault_evidence_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_stamp_gitops_waves_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_eval_rego_rule_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(
        native_create_cosign_attestation_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        native_convert_service_to_route_wrapper,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(native_export_otel_metrics_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_audit_image_signature_wrapper, m)?)?;
    m.add_function(wrap_pyfunction!(native_export_vap_wrapper, m)?)?;
    Ok(())
}

#[cfg_attr(feature = "python", pyfunction(name = "native_export_otel_metrics"))]
pub fn native_export_otel_metrics_wrapper(telemetry: &NativeTelemetry) -> String {
    crate::otel_exporter::export_otel_metrics(telemetry)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_heal_schema_typos"))]
pub fn native_heal_schema_typos_wrapper(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    crate::healers::typo_healer::heal_schema_typos(manifest, telemetry)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_heal_enum_typos"))]
pub fn native_heal_enum_typos_wrapper(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    crate::healers::enum_healer::heal_enum_typos(manifest, telemetry)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_heal_structural_issues"))]
pub fn native_heal_structural_issues_wrapper(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    crate::healers::structural_healer::heal_structural_issues(manifest, telemetry)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_heal_service_selectors"))]
pub fn native_heal_service_selectors_wrapper(
    manifest: &mut SemanticManifest,
    identities: Vec<NativeIdentity>,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    crate::healers::selector_healer::heal_service_selectors_with_identities(
        manifest,
        &identities,
        telemetry,
    )
}

#[cfg_attr(feature = "python", pyfunction(name = "native_format_yaml"))]
pub fn native_format_yaml_wrapper(content: &str) -> String {
    crate::cli::fmt_cmd::format_manifest_content(content)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_detect_cluster_version"))]
pub fn native_detect_cluster_version_wrapper() -> String {
    crate::cluster::native_detect_cluster_version()
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_heal_yaml")]
#[pyo3(signature = (content, k8s_version="1.30"))]
pub fn native_heal_yaml_wrapper(
    py: Python<'_>,
    content: String,
    k8s_version: &str,
) -> (String, Vec<String>) {
    py.allow_threads(|| {
        crate::cli::heal_cmd::heal_manifest_string_for_version(&content, k8s_version)
    })
}

#[cfg_attr(feature = "python", pyfunction(name = "native_get_machine_id"))]
pub fn native_get_machine_id_wrapper() -> String {
    crate::security::native_get_machine_id()
}

#[cfg_attr(feature = "python", pyfunction(name = "native_verify_token"))]
pub fn native_verify_token_wrapper(token: String, pubkey: String) -> bool {
    crate::security::native_verify_token(&token, &pubkey)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_sign_manifest"))]
pub fn native_sign_manifest_wrapper(content: String, private_key: String) -> String {
    crate::security::native_sign_manifest(&content, &private_key)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_verify_manifest"))]
#[cfg_attr(feature = "python", pyo3(signature = (content, signature, public_key=None)))]
pub fn native_verify_manifest_wrapper(
    content: String,
    signature: String,
    public_key: Option<String>,
) -> bool {
    crate::security::native_verify_manifest(&content, &signature, public_key.as_deref())
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_harden_security_context")
)]
pub fn native_harden_security_context_wrapper(content: String) -> (String, Vec<String>) {
    crate::security::harden_manifest_yaml(&content)
}

#[cfg_attr(
    feature = "python",
    pyfunction(name = "native_generate_default_deny_network_policy")
)]
pub fn native_generate_default_deny_network_policy(namespace: &str) -> String {
    crate::healers::network_policy_healer::generate_default_deny_network_policy(namespace)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_generate_stub"))]
pub fn native_generate_stub(kind: &str, name: &str, namespace: &str) -> String {
    crate::healers::stub_healer::generate_stub_yaml(
        &crate::healers::stub_healer::MissingResourceTarget {
            kind: kind.to_string(),
            name: name.to_string(),
            namespace: namespace.to_string(),
        },
    )
}

#[cfg_attr(feature = "python", pyfunction(name = "native_heal_values_yaml"))]
pub fn native_heal_values_yaml(content: String) -> (String, Vec<String>) {
    crate::parsers::helm::heal_values_yaml(&content)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_heal_umbrella_chart")]
pub fn native_heal_umbrella_chart(root_chart_path: String) -> PyResult<Vec<HelmHealResult>> {
    crate::parsers::helm::heal_umbrella_chart(&root_chart_path)
        .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(not(feature = "python"))]
pub fn native_heal_umbrella_chart(root_chart_path: String) -> Result<Vec<HelmHealResult>, String> {
    crate::parsers::helm::heal_umbrella_chart(&root_chart_path)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_rollback_remediation")]
pub fn native_rollback_remediation_wrapper(
    journal_path: String,
    transaction_id: String,
) -> PyResult<bool> {
    crate::remediation_io::native_rollback_remediation(journal_path, transaction_id)
        .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_list_remediations")]
pub fn native_list_remediations_wrapper(journal_path: String) -> PyResult<Vec<RemediationEntry>> {
    crate::remediation_io::native_list_remediations(journal_path)
        .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_vault_evidence")]
pub fn native_vault_evidence_wrapper(
    journal_path: String,
    output_vault_path: String,
) -> PyResult<String> {
    crate::remediation_io::native_vault_evidence(journal_path, output_vault_path)
        .map_err(pyo3::exceptions::PyIOError::new_err)
}

#[cfg_attr(feature = "python", pyfunction(name = "native_stamp_gitops_waves"))]
pub fn native_stamp_gitops_waves_wrapper(content: String) -> (String, Vec<String>) {
    crate::remediation_io::stamp_gitops_waves_yaml(&content)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_eval_rego_rule")]
pub fn native_eval_rego_rule_wrapper(
    rule_id: String,
    rego_source: String,
    manifest_content: String,
) -> PyResult<Option<IntegrityViolation>> {
    let rule = crate::rego::RegoCompiler::compile(&rule_id, &rego_source)
        .map_err(pyo3::exceptions::PyValueError::new_err)?;
    let shards = crate::sharder::native_shard(&manifest_content);
    Ok(crate::rego::RegoCompiler::evaluate_shards(&rule, &shards))
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_create_cosign_attestation")]
pub fn native_create_cosign_attestation_wrapper(
    manifest_name: String,
    manifest_content: String,
) -> PyResult<String> {
    crate::security::create_cosign_attestation_bundle(&manifest_name, &manifest_content, None)
        .map_err(pyo3::exceptions::PyValueError::new_err)
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_convert_service_to_route")]
pub fn native_convert_service_to_route_wrapper(
    manifest_content: String,
    route_type: String,
) -> PyResult<Option<String>> {
    let shards = crate::sharder::native_shard(&manifest_content);
    let parsed = crate::structurer::native_structurize(shards);
    let mut telemetry = NativeTelemetry::default();
    if route_type.eq_ignore_ascii_case("grpc") {
        Ok(
            crate::healers::gateway_route_healer::convert_service_to_grpcroute(
                &parsed.root,
                &mut telemetry,
            ),
        )
    } else if route_type.eq_ignore_ascii_case("tcp") {
        Ok(
            crate::healers::gateway_route_healer::convert_service_to_tcproute(
                &parsed.root,
                &mut telemetry,
            ),
        )
    } else if route_type.eq_ignore_ascii_case("tls") {
        Ok(
            crate::healers::gateway_route_healer::convert_service_to_tlsroute(
                &parsed.root,
                &mut telemetry,
            ),
        )
    } else {
        Ok(
            crate::healers::gateway_api_healer::convert_ingress_to_httproute(
                &parsed.root,
                &mut telemetry,
            ),
        )
    }
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_audit_image_signature")]
pub fn native_audit_image_signature_wrapper(
    image_ref: String,
    enforce_signature: bool,
) -> PyResult<(bool, Option<String>, Option<String>, Option<String>)> {
    let res = crate::security::audit_container_image_signatures(&image_ref, enforce_signature);
    Ok((res.is_signed, res.digest, res.signature_tag, res.violation))
}

#[cfg(feature = "python")]
#[pyfunction(name = "native_export_vap")]
pub fn native_export_vap_wrapper(policy_name: String) -> PyResult<String> {
    let vap = crate::cli::vap_cmd::generate_validating_admission_policy(&policy_name, None);
    let binding = crate::cli::vap_cmd::generate_policy_binding(
        &policy_name,
        &["kube-system", "kube-public", "kube-node-lease"],
    );
    Ok(format!("{}\n---\n{}", vap.trim(), binding.trim()))
}
