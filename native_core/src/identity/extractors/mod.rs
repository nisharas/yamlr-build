//! Native Metadata Extractors Module
//!
//! Why: Modular, single-responsibility extractors that analyze Kubernetes AST shards
//! and populate identity, selectors, references, ports, and cross-resource dependency edges.

use crate::models::{NativeIdentity, NativeShard};

pub mod annotations;
pub mod cluster_role_bindings;
pub mod configmap_refs;
pub mod container_env;
pub mod container_images;
pub mod container_ports;
pub mod daemonset_selectors;
pub mod deployment_selectors;
pub mod ingress_backends;
pub mod ingress_tls;
pub mod job_selectors;
pub mod namespaces;
pub mod owner_refs;
pub mod pod_security;
pub mod pvc_refs;
pub mod role_bindings;
pub mod secret_refs;
pub mod service_accounts;
pub mod service_ports;
pub mod service_selectors;
pub mod statefulset_selectors;
pub mod vpa_targets;

pub use annotations::AnnotationExtractor;
pub use cluster_role_bindings::ClusterRoleBindingExtractor;
pub use configmap_refs::ConfigMapKeyRefExtractor;
pub use container_env::ContainerEnvExtractor;
pub use container_images::ContainerImageExtractor;
pub use container_ports::ContainerPortExtractor;
pub use daemonset_selectors::DaemonSetSelectorExtractor;
pub use deployment_selectors::DeploymentSelectorExtractor;
pub use ingress_backends::IngressBackendExtractor;
pub use ingress_tls::IngressTlsExtractor;
pub use job_selectors::JobSelectorExtractor;
pub use namespaces::NamespaceExtractor;
pub use owner_refs::OwnerRefExtractor;
pub use pod_security::PodSecurityContextExtractor;
pub use pvc_refs::PvcRefExtractor;
pub use role_bindings::RoleBindingExtractor;
pub use secret_refs::SecretRefExtractor;
pub use service_accounts::ServiceAccountExtractor;
pub use service_ports::ServicePortExtractor;
pub use service_selectors::ServiceSelectorExtractor;
pub use statefulset_selectors::StatefulSetSelectorExtractor;
pub use vpa_targets::VpaTargetExtractor;

/// Trait implemented by all discrete metadata extractors.
pub trait NativeMetadataExtractor: Send + Sync {
    /// Human-readable identifier for the extractor.
    fn name(&self) -> &'static str;

    /// Analyzes the shards of a single Kubernetes document and updates the NativeIdentity.
    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity);
}

/// Returns the registry of all 21 discrete metadata extractors.
pub fn get_all_extractors() -> Vec<Box<dyn NativeMetadataExtractor>> {
    vec![
        Box::new(AnnotationExtractor),
        Box::new(ClusterRoleBindingExtractor),
        Box::new(ConfigMapKeyRefExtractor),
        Box::new(ContainerEnvExtractor),
        Box::new(ContainerImageExtractor),
        Box::new(ContainerPortExtractor),
        Box::new(DaemonSetSelectorExtractor),
        Box::new(DeploymentSelectorExtractor),
        Box::new(IngressBackendExtractor),
        Box::new(IngressTlsExtractor),
        Box::new(JobSelectorExtractor),
        Box::new(NamespaceExtractor),
        Box::new(OwnerRefExtractor),
        Box::new(PodSecurityContextExtractor),
        Box::new(PvcRefExtractor),
        Box::new(RoleBindingExtractor),
        Box::new(SecretRefExtractor),
        Box::new(ServiceAccountExtractor),
        Box::new(ServicePortExtractor),
        Box::new(ServiceSelectorExtractor),
        Box::new(StatefulSetSelectorExtractor),
        Box::new(VpaTargetExtractor),
    ]
}

/// Runs all discrete extractors in sequence against the shards for the given identity.
pub fn run_all_extractors(shards: &[NativeShard], identity: &mut NativeIdentity) {
    let extractors = get_all_extractors();
    for ext in extractors {
        ext.extract(shards, identity);
    }
}

/// Helper function to build dot-path tuples for every shard in a document.
pub fn iter_shard_paths<'a>(shards: &'a [NativeShard]) -> Vec<(String, &'a NativeShard)> {
    let mut results = Vec::with_capacity(shards.len());
    let mut stack: Vec<(usize, String)> = Vec::new();
    for s in shards {
        while !stack.is_empty() {
            let top_indent = stack.last().unwrap().0;
            if s.is_list_item {
                if top_indent > s.indent {
                    stack.pop();
                } else {
                    break;
                }
            } else if top_indent >= s.indent {
                stack.pop();
            } else {
                break;
            }
        }
        let segment = if s.is_list_item {
            if s.key.is_empty() {
                "[0]".to_string()
            } else {
                format!("[0].{}", s.key)
            }
        } else {
            s.key.clone()
        };
        let parent_path = stack.last().map(|(_, p)| p.as_str()).unwrap_or("");
        let current_path = if parent_path.is_empty() {
            segment
        } else if segment.is_empty() {
            parent_path.to_string()
        } else {
            format!("{}.{}", parent_path, segment)
        };
        results.push((current_path.clone(), s));
        if s.value.is_none() || s.is_block {
            stack.push((s.indent, current_path));
        } else if s.is_list_item {
            let list_scope = if parent_path.is_empty() {
                "[0]".to_string()
            } else {
                format!("{}.[0]", parent_path)
            };
            stack.push((s.indent, list_scope));
        }
    }
    results
}
