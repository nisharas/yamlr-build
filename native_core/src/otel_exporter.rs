//! OpenTelemetry (OTel) Metric Exporter.
//!
//! Why: Enterprise platforms require standard Prometheus/OTel metric exposition to observe
//! automated manifest healing throughput, risk reduction, and outage prevention in Grafana.
//! This module formats native Yamlr telemetry metrics into Prometheus exposition format.

use crate::models::NativeTelemetry;

/// Formats native Yamlr telemetry metrics into OpenTelemetry / Prometheus text exposition format.
pub fn export_otel_metrics(telemetry: &NativeTelemetry) -> String {
    let mut out = String::new();

    // 1. yamlr_scans_total
    out.push_str("# HELP yamlr_scans_total Total number of Kubernetes manifest scans completed.\n");
    out.push_str("# TYPE yamlr_scans_total counter\n");
    out.push_str(&format!(
        "yamlr_scans_total {}\n\n",
        telemetry.scans_completed
    ));

    // 2. yamlr_heals_total
    out.push_str(
        "# HELP yamlr_heals_total Total number of automated manifest remediations performed.\n",
    );
    out.push_str("# TYPE yamlr_heals_total counter\n");
    out.push_str(&format!(
        "yamlr_heals_total {}\n\n",
        telemetry.heals_completed
    ));

    // 3. yamlr_risk_mitigated_total
    out.push_str("# HELP yamlr_risk_mitigated_total Cumulative risk score neutralized by automated healing.\n");
    out.push_str("# TYPE yamlr_risk_mitigated_total counter\n");
    out.push_str(&format!(
        "yamlr_risk_mitigated_total {:.2}\n\n",
        telemetry.total_risk_mitigated
    ));

    // 4. yamlr_time_saved_seconds_total
    out.push_str(
        "# HELP yamlr_time_saved_seconds_total Total developer toil time saved in seconds.\n",
    );
    out.push_str("# TYPE yamlr_time_saved_seconds_total counter\n");
    let seconds_saved = (telemetry.total_time_saved_ms as f64) / 1000.0;
    out.push_str(&format!(
        "yamlr_time_saved_seconds_total {:.3}\n\n",
        seconds_saved
    ));

    // 5. yamlr_potential_outages_prevented_total
    out.push_str("# HELP yamlr_potential_outages_prevented_total High-severity cluster outage vectors intercepted.\n");
    out.push_str("# TYPE yamlr_potential_outages_prevented_total counter\n");
    out.push_str(&format!(
        "yamlr_potential_outages_prevented_total {}\n\n",
        telemetry.potential_outages_prevented
    ));

    // 6. yamlr_architectural_debt_reduced_total
    out.push_str("# HELP yamlr_architectural_debt_reduced_total Total deprecated fields or anti-patterns modernized.\n");
    out.push_str("# TYPE yamlr_architectural_debt_reduced_total counter\n");
    out.push_str(&format!(
        "yamlr_architectural_debt_reduced_total {:.0}\n",
        telemetry.architectural_debt_reduced
    ));

    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_export_otel_metrics() {
        let mut telemetry = NativeTelemetry::default();
        telemetry.scans_completed = 42;
        telemetry.heals_completed = 15;
        telemetry.total_risk_mitigated = 120.5;
        telemetry.total_time_saved_ms = 45000;
        telemetry.potential_outages_prevented = 3;
        telemetry.architectural_debt_reduced = 8.0;

        let metrics = export_otel_metrics(&telemetry);
        assert!(metrics.contains("yamlr_scans_total 42"));
        assert!(metrics.contains("yamlr_heals_total 15"));
        assert!(metrics.contains("yamlr_risk_mitigated_total 120.50"));
        assert!(metrics.contains("yamlr_time_saved_seconds_total 45.000"));
        assert!(metrics.contains("yamlr_potential_outages_prevented_total 3"));
        assert!(metrics.contains("yamlr_architectural_debt_reduced_total 8"));
        assert!(metrics.contains("# TYPE yamlr_scans_total counter"));
    }
}
