//! Helm Forensic Validation Rules & Change Message Formatters.
//!
//! Why: Centralizes rule IDs and messages for Helm values.yaml healing, ensuring
//!      exact match with test suites and SARIF forensic compliance.

pub const RULE_OPS_002: &str = "Helm [OPS-002]";
pub const RULE_SEC_001: &str = "Helm [SEC-001]";
pub const RULE_SEC_002: &str = "Helm [SEC-002]";
pub const RULE_SEC_003: &str = "Helm [SEC-003]";
pub const RULE_SEC_004: &str = "Helm [SEC-004]";
pub const RULE_REL_005: &str = "Helm [REL-005]";
pub const RULE_ING_001: &str = "Helm [ING-001]";
pub const RULE_HPA_001: &str = "Helm [HPA-001]";
pub const RULE_RES_001: &str = "Helm [RES-001]";
pub const RULE_PROBE_001: &str = "Helm [PROBE-001]";
pub const RULE_DEP_001: &str = "Helm [DEP-001]";
pub const RULE_TYP_001: &str = "Helm [TYP-001]";

pub fn msg_pinned_tag(old_tag: &str) -> String {
    format!(
        "{}: Pinned floating image tag '{}' to 'stable-pinned' in values.yaml.",
        RULE_OPS_002, old_tag
    )
}

pub fn msg_pinned_image() -> String {
    format!(
        "{}: Pinned floating image ':latest' to ':stable-pinned' in values.yaml.",
        RULE_OPS_002
    )
}

pub fn msg_pull_policy_always() -> String {
    format!(
        "{}: Enforced container pullPolicy: Always in values.yaml.",
        RULE_SEC_002
    )
}

pub fn msg_neutralize_privileged() -> String {
    format!(
        "{}: Neutralized insecure 'privileged: true' securityContext in values.yaml.",
        RULE_SEC_001
    )
}

pub fn msg_non_root_uid() -> String {
    format!(
        "{}: Corrected root runAsUser: 0 to non-root UID 10001 in values.yaml.",
        RULE_SEC_004
    )
}

pub fn msg_enforce_run_as_non_root() -> String {
    format!(
        "{}: Enforced runAsNonRoot: true in values.yaml.",
        RULE_SEC_004
    )
}

pub fn msg_pdb_min_available() -> String {
    format!(
        "{}: Corrected PDB minAvailable: 100% to 50% to prevent node drain deadlock in values.yaml.",
        RULE_REL_005
    )
}

pub fn msg_pdb_max_unavailable() -> String {
    format!(
        "{}: Corrected PDB maxUnavailable: 0 to 1 to prevent eviction deadlock in values.yaml.",
        RULE_REL_005
    )
}

pub fn msg_modernize_ingress_class() -> String {
    format!(
        "{}: Modernized deprecated kubernetes.io/ingress.class annotation to ingressClassName in values.yaml.",
        RULE_ING_001
    )
}

pub fn msg_annotate_secret() -> String {
    format!(
        "{}: Annotated hardcoded plaintext credential in values.yaml.",
        RULE_SEC_003
    )
}

pub fn msg_inverted_hpa() -> String {
    format!(
        "{}: Corrected inverted autoscaling replicas (minReplicas > maxReplicas) in values.yaml.",
        RULE_HPA_001
    )
}

pub fn msg_inverted_cpu() -> String {
    format!(
        "{}: Aligned inverted resource allocation (requests.cpu > limits.cpu) in values.yaml.",
        RULE_RES_001
    )
}

pub fn msg_probe_timeout() -> String {
    format!(
        "{}: Normalized probe timeoutSeconds to be <= periodSeconds in values.yaml.",
        RULE_PROBE_001
    )
}

pub fn msg_normalize_oci_registry(repo: &str) -> String {
    format!(
        "{}: Recognized modern OCI registry URI scheme '{}' in values.yaml.",
        RULE_DEP_001, repo
    )
}

pub fn msg_normalize_ambiguous_boolean(key: &str, old_val: &str, new_val: &str) -> String {
    format!(
        "{}: Normalized ambiguous string boolean '{}' to literal '{}' on key '{}' to prevent Go template truthiness errors in values.yaml.",
        RULE_TYP_001, old_val, new_val, key
    )
}
