use crate::models::*;
use crate::shield::{native_apply_shield, ShieldConfig};
use crate::telemetry::native_record_healing_impact;

pub fn native_heal_manifest(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    native_heal_manifest_with_identities(manifest, &[], telemetry)
}

pub fn native_heal_manifest_with_identities(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    native_heal_manifest_with_schemas(manifest, identities, telemetry, &[])
}

pub fn native_heal_manifest_with_schemas(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
    schemas: &[NativeSchema],
) -> Vec<String> {
    let mut changes = Vec::new();

    // --- STAGE 1: Schema & Enum Typo Correction (Features 1 & 2 of 15) ---
    // Corrects misspelled schema property keys before structural & security passes
    let typo_changes = crate::healers::typo_healer::heal_schema_typos(manifest, telemetry);
    changes.extend(typo_changes);

    // Normalizes enum casing and fuzzy repairs enum value typos (Feature 2 of 15)
    let enum_changes = crate::healers::enum_healer::heal_enum_typos(manifest, telemetry);
    changes.extend(enum_changes);

    // Normalizes structural misnesting & lifts misplaced fields (Feature 3 of 15)
    let structural_changes =
        crate::healers::structural_healer::heal_structural_issues(manifest, telemetry);
    changes.extend(structural_changes);

    // Injects missing apiVersion inferred from Kind (Feature 9 of 15)
    let api_changes = crate::healers::api_infer_healer::heal_missing_api_version_with_schemas(
        manifest, telemetry, schemas,
    );
    changes.extend(api_changes);

    // Sanitizes and repairs resource limits and flat mappings (Feature 12 of 15)
    let res_changes =
        crate::healers::resource_sanitizer::heal_resource_sanitization(manifest, telemetry);
    changes.extend(res_changes);

    // Heals PodDisruptionBudget deadlocks (Feature 16)
    let pdb_changes = crate::healers::pdb_healer::heal_pdb_deadlocks(manifest, telemetry);
    changes.extend(pdb_changes);

    // Upgrades legacy sidecars to K8s 1.28+ native sidecars (Feature 17)
    let sidecar_changes = crate::healers::sidecar_healer::heal_legacy_sidecars(manifest, telemetry);
    changes.extend(sidecar_changes);

    // Synthesizes /tmp emptyDir mounts and non-root UIDs for securityContext (Feature 18)
    let sec_changes =
        crate::healers::security_context_healer::heal_security_context_issues(manifest, telemetry);
    changes.extend(sec_changes);

    // Ephemeral Container Security & Target Synchronization (Rule SEC-012)
    let ephem_changes =
        crate::healers::ephemeral_container_healer::heal_ephemeral_containers(manifest, telemetry);
    changes.extend(ephem_changes);

    // Synchronizes terminationGracePeriodSeconds with preStop hooks (Feature 20)
    let lifecycle_changes =
        crate::healers::lifecycle_healer::heal_lifecycle_grace_periods(manifest, telemetry);
    changes.extend(lifecycle_changes);

    // GitOps Controller Default Harmonizer & Sync-Wave Stamping (Rules GTO-001 & GTO-002) - Opt-in
    let gitops_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/gitops")
        .or_else(|| manifest.root.find_annotation("yamlr.io/gitops"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/sync-wave"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/sync-wave"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if gitops_opt_in {
        let gitops_changes =
            crate::healers::gitops_healer::heal_gitops_manifest(manifest, telemetry);
        changes.extend(gitops_changes);
    }

    // StatefulSet Immutability Guard & PVC Expansion Synthesizer (Rule STO-003)
    let sts_changes =
        crate::healers::statefulset_immutability_healer::heal_statefulset_immutability(
            manifest, telemetry,
        );
    changes.extend(sts_changes);

    // HA Topology Spread Synthesizer (Rule REL-011) - Opt-in
    let topo_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/ha-topology")
        .or_else(|| manifest.root.find_annotation("yamlr.io/ha-topology"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/topology-spread"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/topology-spread"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if topo_opt_in {
        let topo_changes =
            crate::healers::topology_spread_healer::heal_topology_spread(manifest, telemetry);
        changes.extend(topo_changes);
    }

    // QoS Alignment & Burstable Right-Sizer (Rule RES-003) - Opt-in
    let qos_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/qos")
        .or_else(|| manifest.root.find_annotation("yamlr.io/qos"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/burstable"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/burstable"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if qos_opt_in {
        let qos_changes = crate::healers::qos_healer::heal_qos_alignment(manifest, telemetry);
        changes.extend(qos_changes);
    }

    // Probes Best Practice Auto-Healer (Feature 11 of 15) - Opt-in via annotation
    let probe_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/probes")
        .or_else(|| manifest.root.find_annotation("yamlr.io/probes"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if probe_opt_in {
        let probe_changes = crate::healers::probe_healer::heal_probes(manifest, telemetry);
        changes.extend(probe_changes);
    }

    // Gateway API HTTPRoute/GRPCRoute/TCPRoute Modernizer (Rules MIG-002, MIG-003, MIG-004) - Opt-in via annotation
    let gw_opt_in = manifest
        .root
        .find_annotation("yamlr.dev/gateway-api")
        .or_else(|| manifest.root.find_annotation("yamlr.io/gateway-api"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if gw_opt_in {
        if let Some(httproute_yaml) =
            crate::healers::gateway_api_healer::convert_ingress_to_httproute(
                &manifest.root,
                telemetry,
            )
        {
            let shards = crate::sharder::native_shard(&httproute_yaml);
            let parsed = crate::structurer::native_structurize(shards);
            manifest.root = parsed.root;
            changes.push(
                "Remediation [MIG-002]: Converted Ingress into Gateway API HTTPRoute.".to_string(),
            );
        } else if let Some(grpcroute_yaml) =
            crate::healers::gateway_route_healer::convert_service_to_grpcroute(
                &manifest.root,
                telemetry,
            )
        {
            let shards = crate::sharder::native_shard(&grpcroute_yaml);
            let parsed = crate::structurer::native_structurize(shards);
            manifest.root = parsed.root;
            changes.push(
                "Remediation [MIG-003]: Converted gRPC Service into Gateway API GRPCRoute."
                    .to_string(),
            );
        } else if let Some(tcproute_yaml) =
            crate::healers::gateway_route_healer::convert_service_to_tcproute(
                &manifest.root,
                telemetry,
            )
        {
            let shards = crate::sharder::native_shard(&tcproute_yaml);
            let parsed = crate::structurer::native_structurize(shards);
            manifest.root = parsed.root;
            changes.push(
                "Remediation [MIG-004]: Converted TCP Service into Gateway API TCPRoute."
                    .to_string(),
            );
        }
    }

    // Proactively detect API deprecations and floating tags if not already populated
    let cur_api = manifest.root.find_value("apiVersion").unwrap_or_default();
    let cur_knd = manifest.root.find_value("kind").unwrap_or_default();
    if !cur_api.is_empty()
        && !manifest
            .integrity_violations
            .iter()
            .any(|v| v.rule_id == "PRO-001")
    {
        if let Some(v) = crate::audit_engine::audit_manifest(&cur_api, &cur_knd) {
            manifest.integrity_violations.push(v);
        }
    }
    if !manifest
        .integrity_violations
        .iter()
        .any(|v| v.rule_id == "OPS-002")
    {
        for c in manifest.root.find_nodes_by_key_recursive("image") {
            if let Some(img) = &c.value {
                if img
                    .trim_matches('"')
                    .trim_matches('\'')
                    .ends_with(":latest")
                {
                    manifest
                        .integrity_violations
                        .push(crate::models::IntegrityViolation {
                            rule_id: "OPS-002".into(),
                            check_name: "Floating Tag".into(),
                            message: "Use pinned tag".into(),
                            severity: "MEDIUM".into(),
                            line_no: 0,
                        });
                    break;
                }
            }
        }
    }

    // Remediation (auto-repair for integrity violations)
    let violation_changes =
        crate::healers::violation_remediator::remediate_integrity_violations(manifest, telemetry);
    changes.extend(violation_changes);

    // --- STAGE 2.3: Shield Engine (Policy Enforcement) ---
    let shield_config = ShieldConfig::default();
    let shield_changes = native_apply_shield(manifest, &shield_config);
    for change in &shield_changes {
        native_record_healing_impact(telemetry, change);
    }
    changes.extend(shield_changes);

    // Audit Suppression Engine
    let suppression_list = manifest
        .root
        .find_annotation("yamlr.dev/suppress")
        .or_else(|| manifest.root.find_annotation("yamlr.io/suppress"))
        .unwrap_or_default();
    let suppressed_rules: Vec<&str> = suppression_list.split(',').map(|s| s.trim()).collect();

    // --- STAGE 2.3: Prophetic Auditor (Deprecation & Immutability Check) ---
    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if let Some(violation) = crate::audit_engine::audit_manifest(&api_version, &kind) {
        if !suppressed_rules.contains(&violation.check_name.as_str())
            && !manifest
                .integrity_violations
                .iter()
                .any(|v| v.rule_id == violation.rule_id)
        {
            let msg = format!("Auditor [{}]: {}", violation.severity, violation.message);
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
            manifest.integrity_violations.push(violation);
        }
    }

    // Traversal for Images
    for container in manifest.root.find_nodes_by_key_recursive("image") {
        if let Some(image_val) = &container.value {
            if let Some(violation) = crate::audit_engine::audit_image(image_val) {
                if !suppressed_rules.contains(&violation.check_name.as_str())
                    && !manifest
                        .integrity_violations
                        .iter()
                        .any(|v| v.rule_id == violation.rule_id)
                {
                    let msg = format!("Auditor [{}]: {}", violation.severity, violation.message);
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                    manifest.integrity_violations.push(violation);
                }
            }
        }
    }

    // Traversal for Flow-Style
    native_audit_flow_style_recursive(
        &manifest.root,
        &mut manifest.integrity_violations,
        telemetry,
        &mut changes,
        &suppressed_rules,
    );

    // Cross-resource selector alignment (Feature 4 of 15)
    let sel_changes = crate::healers::selector_healer::heal_service_selectors_with_identities(
        manifest, identities, telemetry,
    );
    changes.extend(sel_changes);

    // Cross-resource port alignment (Feature 5 of 15)
    let port_changes =
        crate::healers::port_healer::heal_service_ports(manifest, identities, telemetry);
    changes.extend(port_changes);

    // Cross-resource referential alignment (Feature 7 of 15)
    let ref_changes =
        crate::healers::referential_healer::heal_referential_links(manifest, identities, telemetry);
    changes.extend(ref_changes);

    // Cross-resource RBAC alignment (Feature 6 of 15)
    let rbac_changes =
        crate::healers::rbac_healer::heal_rbac_references(manifest, identities, telemetry);
    changes.extend(rbac_changes);

    // Cross-resource CRD alignment (Feature 14 of 15)
    let crd_changes =
        crate::healers::crd_healer::heal_crd_semantics(manifest, identities, telemetry);
    changes.extend(crd_changes);

    // Cross-resource PDB replica alignment (Feature 16)
    let pdb_rep_changes = crate::healers::pdb_healer::heal_pdb_with_workload_replicas(
        manifest, identities, telemetry,
    );
    changes.extend(pdb_rep_changes);

    // Cross-resource secret store resolution within self-contained manifest
    let ext_targets =
        crate::healers::secret_store_healer::extract_external_secret_targets(&manifest.root);
    if !ext_targets.is_empty() {
        let sec_store_changes = crate::healers::secret_store_healer::heal_secret_store_refs(
            manifest,
            &ext_targets,
            telemetry,
        );
        changes.extend(sec_store_changes);
    }

    // Cross-resource Protocol Contract Alignment (Rule NET-007)
    let proto_changes = crate::healers::protocol_contract_healer::heal_protocol_contracts(
        manifest, identities, telemetry,
    );
    changes.extend(proto_changes);

    // Ingress Path Shadowing & Specificity Ordering (Rule NET-008)
    let shadow_changes =
        crate::healers::ingress_shadow_healer::heal_ingress_shadowing(manifest, telemetry);
    changes.extend(shadow_changes);

    // --- STAGE 2.3.5: Reference & Operational Healers (Phase 3) ---
    let ds_update_changes = crate::healers::daemonset_update_healer::heal_daemonset_update_strategy(
        manifest, telemetry,
    );
    changes.extend(ds_update_changes);

    let rev_changes = crate::healers::deployment_revision_healer::heal_deployment_revision_limits(
        manifest, telemetry,
    );
    changes.extend(rev_changes);

    let cron_changes =
        crate::healers::cronjob_schedule_healer::heal_cronjob_schedules(manifest, telemetry);
    changes.extend(cron_changes);

    let netpol_egress_changes =
        crate::healers::network_policy_egress_healer::heal_network_policy_egress(
            manifest, telemetry,
        );
    changes.extend(netpol_egress_changes);

    let proto_app_changes =
        crate::healers::app_protocol_healer::heal_app_protocols(manifest, telemetry);
    changes.extend(proto_app_changes);

    let target_port_changes = crate::healers::service_target_port_healer::heal_service_target_ports(
        manifest, identities, telemetry,
    );
    changes.extend(target_port_changes);

    let sa_changes = crate::healers::service_account_healer::heal_service_account_references(
        manifest, identities, telemetry,
    );
    changes.extend(sa_changes);

    let cm_changes = crate::healers::configmap_healer::heal_configmap_references(
        manifest, identities, telemetry,
    );
    changes.extend(cm_changes);

    let sec_ref_changes =
        crate::healers::secret_healer::heal_secret_references(manifest, identities, telemetry);
    changes.extend(sec_ref_changes);

    let pvc_changes =
        crate::healers::pvc_healer::heal_pvc_references(manifest, identities, telemetry);
    changes.extend(pvc_changes);

    let ing_tls_changes = crate::healers::ingress_tls_healer::heal_ingress_tls_secrets(
        manifest, identities, telemetry,
    );
    changes.extend(ing_tls_changes);

    let cert_mgr_changes = crate::healers::cert_manager_healer::heal_cert_manager_issuers(
        manifest, identities, telemetry,
    );
    changes.extend(cert_mgr_changes);

    let ext_sec_changes = crate::healers::external_secret_healer::heal_external_secrets(
        manifest, identities, telemetry,
    );
    changes.extend(ext_sec_changes);

    let hpa_changes =
        crate::healers::hpa_target_healer::heal_hpa_target_refs(manifest, identities, telemetry);
    changes.extend(hpa_changes);

    let pdb_unavail_changes = crate::healers::pdb_max_unavailable_healer::heal_pdb_max_unavailable(
        manifest, identities, telemetry,
    );
    changes.extend(pdb_unavail_changes);

    let crb_subj_changes = crate::healers::crb_subject_healer::heal_cluster_role_binding_subjects(
        manifest, identities, telemetry,
    );
    changes.extend(crb_subj_changes);

    let rb_subj_changes = crate::healers::rb_subject_healer::heal_role_binding_subjects(
        manifest, identities, telemetry,
    );
    changes.extend(rb_subj_changes);

    // Dual-Stack IPv6 Service CIDR Clashes & Policy Alignment (Rule NET-009)
    let dual_stack_changes =
        crate::healers::dual_stack_healer::heal_dual_stack_services(manifest, telemetry);
    changes.extend(dual_stack_changes);

    // Ingress NGINX Snippet Deprecations (Rule SEC-012)
    let snippet_changes =
        crate::healers::ingress_snippet_healer::heal_ingress_snippets(manifest, telemetry);
    changes.extend(snippet_changes);

    // Autoscaler Metric Contention: HPA vs VPA Conflict Arbitrator (Rule AUT-002)
    let autoscaler_changes =
        crate::healers::autoscaler_arbitration_healer::heal_autoscaler_arbitration(
            manifest, identities, telemetry,
        );
    changes.extend(autoscaler_changes);

    // --- STAGE 2.3.6: Ecosystem Auto-Healers (Phase 7) ---
    let istio_changes = crate::healers::istio_healer::heal_istio_manifests(manifest, telemetry);
    changes.extend(istio_changes);

    let linkerd_changes =
        crate::healers::linkerd_healer::heal_linkerd_manifests(manifest, telemetry);
    changes.extend(linkerd_changes);

    let pipeline_changes =
        crate::healers::pipeline_healer::heal_pipeline_manifests(manifest, telemetry);
    changes.extend(pipeline_changes);

    let velero_changes = crate::healers::velero_healer::heal_velero_manifests(manifest, telemetry);
    changes.extend(velero_changes);

    let crossplane_changes =
        crate::healers::crossplane_healer::heal_crossplane_manifests(manifest, telemetry);
    changes.extend(crossplane_changes);

    let fed_changes =
        crate::healers::federation_healer::heal_federation_manifests(manifest, telemetry);
    changes.extend(fed_changes);

    // StorageClass volumeBindingMode Alignment (Rule STR-004)
    let sc_changes =
        crate::healers::pvc_healer::heal_storage_class_binding_modes(manifest, telemetry);
    changes.extend(sc_changes);

    // Dynamic Resource Allocation (DRA) Healer (K8s 1.30+ / Rule DRA-001)
    let dra_changes =
        crate::healers::dra_healer::heal_dynamic_resource_allocation(manifest, telemetry);
    changes.extend(dra_changes);

    // Gateway API TLSRoute Modernizer (Rule MIG-005)
    let tls_route_changes =
        crate::healers::gateway_tls_healer::heal_tls_routes(manifest, telemetry);
    changes.extend(tls_route_changes);

    // BackendTLSPolicy & Service Mesh Protocol Healer (Rule SEC-015)
    let backend_tls_changes =
        crate::healers::gateway_tls_healer::heal_backend_tls_policies(manifest, telemetry);
    changes.extend(backend_tls_changes);

    // --- STAGE 2.4: Professional Key Sorter ---
    // Key sorting belongs to 'yamlr fmt', or opt-in via annotation 'yamlr.io/sort-keys: true'
    let should_sort = manifest
        .root
        .find_annotation("yamlr.io/sort-keys")
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);
    if should_sort && native_sort_keys(&mut manifest.root, 0) {
        let aesthetic_msg = "Aesthetics: Applied 'Golden Standard' key ordering.".to_string();
        native_record_healing_impact(telemetry, &aesthetic_msg);
        changes.push(aesthetic_msg);
    }

    // --- STAGE 2.5: DNA Safety Seal (Authority Pillar) ---
    if !changes.is_empty() {
        if let Some(seal_msg) = native_apply_dna_seal(&mut manifest.root) {
            native_record_healing_impact(telemetry, &seal_msg);
            changes.push(seal_msg);
        }
    }

    changes
}

pub use crate::healers::dna_healer::native_apply_dna_seal;

fn native_audit_flow_style_recursive(
    node: &SemanticNode,
    violations: &mut Vec<crate::models::IntegrityViolation>,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
    suppressed_rules: &[&str],
) {
    if node.is_empty_flow {
        if let Some(violation) = crate::audit_engine::audit_flow_style(node.key.as_str()) {
            if !suppressed_rules.contains(&violation.check_name.as_str()) {
                let msg = format!("Auditor [{}]: {}", violation.severity, violation.message);
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
                violations.push(violation);
            }
        }
    }
    for child in &node.children {
        native_audit_flow_style_recursive(child, violations, telemetry, changes, suppressed_rules);
    }
}

pub use crate::healers::key_sorter::native_sort_keys;

// Re-export AST reconstructor from parsers module
pub use crate::parsers::reconstructor::native_reconstruct_from_semantic;

pub use crate::remediation_io::{native_apply_fix_atomic, native_log_remediation};

#[cfg(test)]
#[path = "healing_tests.rs"]
mod tests;
