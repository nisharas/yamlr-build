//! Modular Healing Subsystem for Yamlr Native Core.
//! Each feature is isolated into its own module (< 500 lines) following the Modularity Enforcement Protocol.

pub mod api_infer_healer;
pub mod crd_healer;
pub mod dna_healer;
pub mod dra_healer;
pub mod enum_healer;
pub mod ephemeral_container_healer;
pub mod gateway_api_healer;
pub mod gateway_route_healer;
pub mod gateway_tls_healer;
pub mod gitops_healer;
pub mod ingress_shadow_healer;
pub mod lifecycle_healer;
pub mod network_policy_healer;
pub mod pdb_healer;
pub mod port_healer;
pub mod probe_healer;
pub mod protocol_contract_healer;
pub mod qos_healer;
pub mod rbac_healer;
pub mod referential_healer;
pub mod resource_sanitizer;
pub mod secret_store_healer;
pub mod security_context_healer;
pub mod selector_healer;
pub mod sidecar_healer;
pub mod statefulset_immutability_healer;
pub mod structural_healer;
pub mod stub_healer;
pub mod template_masker;
pub mod topology_spread_healer;
pub mod typo_dictionaries;
pub mod typo_healer;

// Reference & Operational Healing Subsystem (Phase 3)
pub mod api_deprecation_healer;
pub mod app_protocol_healer;
pub mod autoscaler_arbitration_healer;
pub mod cert_manager_healer;
pub mod configmap_healer;
pub mod crb_subject_healer;
pub mod cronjob_schedule_healer;
pub mod daemonset_update_healer;
pub mod deployment_revision_healer;
pub mod dual_stack_healer;
pub mod external_secret_healer;
pub mod hpa_target_healer;
pub mod ingress_annotation_healer;
pub mod ingress_snippet_healer;
pub mod ingress_tls_healer;
pub mod kustomize_healer;
pub mod network_policy_egress_healer;
pub mod pdb_max_unavailable_healer;
pub mod pvc_healer;
pub mod rb_subject_healer;
pub mod secret_healer;
pub mod service_account_healer;
pub mod service_target_port_healer;

// Ecosystem Healing Subsystem (Phase 7)
pub mod crossplane_healer;
pub mod federation_healer;
pub mod istio_healer;
pub mod key_sorter;
pub mod linkerd_healer;
pub mod pipeline_healer;
pub mod velero_healer;
pub mod violation_remediator;

// Advanced Human Error & Type Safety Healers (Phase 8)
pub mod cis_security_healer;
pub mod cluster_dump_healer;
pub mod configmap_secret_healer;
pub mod dangling_key_healer;
pub mod dns_network_healer;
pub mod downward_api_healer;
pub mod graceful_rollout_healer;
pub mod image_pull_healer;
pub mod memory_unit_healer;
pub mod numeric_type_healer;
pub mod storage_ops_healer;
pub mod annotation_contract_healer;
pub mod node_selector_healer;
pub mod topology_key_healer;
pub mod session_affinity_healer;
pub mod job_contract_healer;
pub mod volume_contract_healer;
pub mod service_network_contract_healer;
pub mod block_scalar_healer;
pub mod encoding_transcoder_healer;
pub mod orphaned_indent_healer;
pub mod sequence_indent_healer;
pub mod anchor_declaration_healer;
