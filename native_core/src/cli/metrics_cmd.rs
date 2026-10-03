//! Engineering Quality Metrics and ROI CLI Command Handler.
//!
//! Why: Provides sub-50ms instant calculation of engineering ROI, blast radius,
//! and compliance metrics without Python overhead. Strictly < 500 lines.

use crate::cli::{EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_SYSTEM_ERROR};
use crate::discovery::{calculate_blast_radius, native_discover_resources};
use std::path::Path;

/// Executes the standalone `yamlr roi` / `yamlr pulse` / `yamlr metrics` command.
pub fn execute_metrics(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("metrics", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_path = matches.get_one::<String>("target").unwrap().clone();
    let json_format =
        matches.get_flag("json") || matches.get_one::<String>("output").unwrap() == "json";

    let p = Path::new(&target_path);
    if !p.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target_path);
        return EXIT_CONFIG_ERROR;
    }

    let discovery = match native_discover_resources(target_path.clone()) {
        Ok(discovery) => discovery,
        Err(error) => {
            eprintln!("[ERROR] Resource discovery failed: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    let total_resources = discovery.len();

    let mut workload_count = 0;
    let mut config_count = 0;
    let mut network_count = 0;
    let mut total_blast_risk: f64 = 0.0;

    let identities: Vec<_> = discovery
        .iter()
        .filter_map(|d| d.identity.clone())
        .collect();
    let edges = crate::discovery::build_topology_edges(&identities);

    for d in &discovery {
        if let Some(ref id) = d.identity {
            match id.kind.as_str() {
                "Deployment" | "StatefulSet" | "DaemonSet" | "Pod" | "Job" | "CronJob" => {
                    workload_count += 1;
                }
                "ConfigMap" | "Secret" | "PersistentVolumeClaim" => {
                    config_count += 1;
                }
                "Service" | "Ingress" | "NetworkPolicy" | "HTTPRoute" | "Gateway" => {
                    network_count += 1;
                }
                _ => {}
            }
            let res_key = format!("{}/{}/{}", id.kind, id.namespace, id.name);
            let blast = calculate_blast_radius(&res_key, &edges);
            total_blast_risk += blast.risk_score;
        }
    }

    let avg_blast = if total_resources > 0 {
        total_blast_risk / total_resources as f64
    } else {
        0.0
    };

    // Engineering hours saved estimate: 0.25 hrs per managed resource auto-validated
    let hours_saved = (total_resources as f64 * 0.25).round();
    let dollars_saved = hours_saved * 85.0; // $85/hr DevOps standard rate

    if json_format {
        let json_obj = serde_json::json!({
            "target_path": target_path,
            "total_resources": total_resources,
            "workloads": workload_count,
            "configurations": config_count,
            "networking": network_count,
            "avg_blast_radius_risk": format!("{:.1}%", avg_blast),
            "estimated_engineering_hours_saved": hours_saved,
            "estimated_financial_value_usd": dollars_saved
        });
        println!("{}", serde_json::to_string_pretty(&json_obj).unwrap());
    } else {
        let is_pulse = args.len() > 1 && args[1].to_lowercase() == "pulse";
        if is_pulse {
            println!("=== Yamlr Fleet Pulse & Health Telemetry ===");
        } else {
            println!("=== Yamlr Engineering Quality & ROI Metrics ===");
        }
        println!("Analyzed Fleet Path:       {}", target_path);
        println!("Total Discovered Resources: {}", total_resources);
        println!("  - Workloads:             {}", workload_count);
        println!("  - Configurations:        {}", config_count);
        println!("  - Networking/Ingress:    {}", network_count);
        println!("Average Fleet Blast Radius: {:.1}%", avg_blast);
        println!("{:-<50}", "");
        println!("Estimated Dev Hours Saved: ~{:.0} hrs", hours_saved);
        println!("Estimated Direct ROI Value: ~${:.0} USD", dollars_saved);
        println!("\nEngine: Zero-Copy AST Resolution Plane");
    }

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn test_execute_metrics_text_and_json() {
        let dir = tempdir().unwrap();
        let pod_path = dir.path().join("pod.yaml");
        fs::write(
            &pod_path,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app\n",
        )
        .unwrap();

        let args_text = vec![
            "yamlr".to_string(),
            "pulse".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_metrics(&args_text), EXIT_SUCCESS);

        let args_json = vec![
            "yamlr".to_string(),
            "roi".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--json".to_string(),
        ];
        assert_eq!(execute_metrics(&args_json), EXIT_SUCCESS);
    }
}
