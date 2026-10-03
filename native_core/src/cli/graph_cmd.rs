//! Graph and Topology Drift CLI Command Handler for Standalone Rust Binary.
//!
//! Why: High-speed relational topology analysis, circular dependency detection,
//! dangling selector analysis, and version drift checks in pure Rust. Strictly < 500 lines.

use crate::cli::{EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};
use crate::discovery::{
    build_topology_edges, native_detect_circular_dependencies, native_detect_dangling_selectors,
    native_detect_orphaned_resources, native_detect_service_shadowing, native_detect_version_drift,
    native_discover_resources,
};
use std::path::Path;

/// Executes the standalone `yamlr graph` command.
pub fn execute_graph(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("graph", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_path = matches.get_one::<String>("target").unwrap().clone();
    let focus = matches.get_one::<String>("focus").cloned();

    let p = Path::new(&target_path);
    if !p.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target_path);
        return EXIT_CONFIG_ERROR;
    }

    let discovery = match native_discover_resources(target_path) {
        Ok(discovery) => discovery,
        Err(error) => {
            eprintln!("[ERROR] Resource discovery failed: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    let identities: Vec<_> = discovery
        .iter()
        .filter_map(|d| d.identity.clone())
        .collect();
    let edges = build_topology_edges(&identities);

    println!("=== Yamlr Topology Dependency Graph ===");
    println!("Discovered Resources: {}", identities.len());
    println!("Relational Edges:     {}", edges.len());
    println!("{:-<75}", "");

    let mut printed_count = 0;
    for edge in &edges {
        if let Some(ref f) = focus {
            if !edge.from_resource.contains(f) && !edge.to_resource.contains(f) {
                continue;
            }
        }
        println!(
            "{:<32} --[{:^12}]--> {}",
            edge.from_resource, edge.edge_type, edge.to_resource
        );
        printed_count += 1;
    }

    if printed_count == 0 && focus.is_some() {
        println!(
            "[INFO] No graph edges matched focus filter '{}'.",
            focus.unwrap()
        );
    }

    EXIT_SUCCESS
}

/// Executes the standalone `yamlr drift` command.
pub fn execute_drift(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("drift", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_path = matches.get_one::<String>("target").unwrap().clone();

    let p = Path::new(&target_path);
    if !p.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target_path);
        return EXIT_CONFIG_ERROR;
    }

    let discovery = match native_discover_resources(target_path) {
        Ok(discovery) => discovery,
        Err(error) => {
            eprintln!("[ERROR] Resource discovery failed: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    let identities: Vec<_> = discovery
        .iter()
        .filter_map(|d| d.identity.clone())
        .collect();
    let edges = build_topology_edges(&identities);

    let circular = native_detect_circular_dependencies(&edges);
    let dangling = native_detect_dangling_selectors(&discovery);
    let orphaned = native_detect_orphaned_resources(&discovery);
    let shadowing = native_detect_service_shadowing(&discovery);
    let version_drift = native_detect_version_drift(discovery);

    println!("=== Yamlr Fleet Architecture & Drift Audit ===");
    let mut violation_count = 0;

    if !version_drift.is_empty() {
        println!("\n[!] API Version Inconsistencies:");
        for v in &version_drift {
            println!("  - {}", v);
            violation_count += 1;
        }
    }

    if !circular.is_empty() {
        println!("\n[!] Circular Dependency Loops:");
        for c in &circular {
            println!("  - {}", c);
            violation_count += 1;
        }
    }

    if !dangling.is_empty() {
        println!("\n[!] Dangling Selectors (Missing Workloads):");
        for d in &dangling {
            println!("  - {}", d);
            violation_count += 1;
        }
    }

    if !shadowing.is_empty() {
        println!("\n[!] Service Collision / Shadowing:");
        for s in &shadowing {
            println!("  - {}", s);
            violation_count += 1;
        }
    }

    if !orphaned.is_empty() {
        println!("\n[i] Orphaned ConfigMaps & Secrets:");
        for o in &orphaned {
            println!("  - {}", o);
        }
    }

    if violation_count == 0 {
        println!("\n[PASS] No architectural drifts, cycles, or dangling selectors detected.");
        EXIT_SUCCESS
    } else {
        println!("\n[FAIL] Found {} architectural issues.", violation_count);
        EXIT_VIOLATIONS
    }
}
