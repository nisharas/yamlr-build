//! Yamlr Topology Graph Engine & Blast Radius Calculator.
//!
//! Why: Builds unified, directed topology graphs connecting Kubernetes resources,
//!      detects architectural circular dependencies, dangling selectors, and orphaned
//!      configurations, and calculates multi-factor blast radius risk assessments.

pub mod analyzers;
pub mod blast_radius;
pub mod builder;
pub mod scanner;

#[cfg(test)]
mod tests;

pub use analyzers::{
    native_detect_circular_dependencies, native_detect_dangling_selectors,
    native_detect_orphaned_resources, native_detect_service_shadowing, native_detect_version_drift,
};
pub use blast_radius::{calculate_blast_radius, native_calculate_blast_radius};
pub use builder::{build_topology_edges, native_build_topology_graph};
pub use scanner::{extract_identities_recursive, native_discover_resources, MAX_FLEET_SIZE};
