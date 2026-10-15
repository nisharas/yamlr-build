use crate::models::{NativeScoringResult, NativeTelemetry};
use std::collections::HashMap;

pub fn native_calculate_dna_hash(content: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    content.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}

pub fn native_get_telemetry_dashboard(telemetry: &NativeTelemetry) -> String {
    let total_minutes = (telemetry.scans_completed as u32).saturating_mul(5);
    let hours = total_minutes as f64 / 60.0;
    let value_cents = total_minutes.saturating_mul(250);
    let dollars = value_cents / 100;
    let cents = value_cents % 100;
    format!(
        "\n--- Yamlr Value Dashboard ---\n\
         [+] Toil Mitigation:   {:.2} hours\n\
         [+] Risk Neutralized:  {:.2} units\n\
         [!] Outages Prevented: {}\n\
         [+] Debt Resolved:     {:.0} violations\n\
         ---------------------------------------\n\
         Estimated Value:      ${}.{:02}\n",
        hours,
        telemetry.total_risk_mitigated,
        telemetry.potential_outages_prevented,
        telemetry.architectural_debt_reduced,
        dollars,
        cents
    )
}

pub fn native_record_healing_impact(telemetry: &mut NativeTelemetry, change: &str) {
    if change.contains("REF-")
        || change.contains("ConfigMap")
        || change.contains("Secret")
        || change.contains("PersistentVolumeClaim")
        || change.contains("claimName")
    {
        telemetry.total_risk_mitigated += 15.0;
        telemetry.potential_outages_prevented += 1;
    } else if change.contains("NET-")
        || change.contains("REL-011")
        || change.contains("targetPort")
        || change.contains("selector")
    {
        telemetry.total_risk_mitigated += 15.0;
        telemetry.potential_outages_prevented += 1;
    } else if change.contains("RBAC-")
        || change.contains("SEC-011")
        || change.contains("ServiceAccount")
        || change.contains("roleRef")
    {
        telemetry.total_risk_mitigated += 10.0;
        telemetry.potential_outages_prevented += 1;
    } else if change.contains("PDB-")
        || change.contains("deadlock")
        || change.contains("PodDisruptionBudget")
    {
        telemetry.total_risk_mitigated += 25.0;
        telemetry.potential_outages_prevented += 1;
    } else if change.contains("SEC-")
        || change.contains("securityContext")
        || change.contains("readOnlyRootFilesystem")
        || change.contains("runAsNonRoot")
    {
        telemetry.total_risk_mitigated += 20.0;
    } else if change.contains("resource limits") || change.contains("RES-") {
        telemetry.total_risk_mitigated += 20.0;
        telemetry.potential_outages_prevented += 2;
    } else if change.contains("SCHEMA-")
        || change.contains("PRO-")
        || change.contains("MIG-")
        || change.contains("TOPOLOGY-")
        || change.contains("GTO-")
        || change.contains("AUT-")
        || change.contains("Auditor")
        || change.contains("Aesthetics")
        || change.contains("deprecated")
    {
        telemetry.total_risk_mitigated += 5.0;
        telemetry.architectural_debt_reduced += 1.0;
    } else {
        telemetry.total_risk_mitigated += 5.0;
    }
}

pub fn native_calculate_scoring(violations_count: usize) -> NativeScoringResult {
    let mut breakdown = HashMap::new();
    let score = if violations_count == 0 {
        100.0
    } else {
        (100.0 - (violations_count as f64 * 5.0)).max(0.0)
    };
    breakdown.insert("SchemaHealth".to_string(), score);

    let level = if score > 90.0 {
        "Healthy".to_string()
    } else if score > 70.0 {
        "Hardened".to_string()
    } else {
        "Exposed".to_string()
    };

    NativeScoringResult {
        score,
        level,
        breakdown,
    }
}
