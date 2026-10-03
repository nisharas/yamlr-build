//! Comprehensive Helm configuration parser and values healer for `values.yaml` files.
//!
//! Why: Provides surgical, comment-preserving healing for Helm `values.yaml` files
//!      and multi-tier umbrella subcharts across 10 security and reliability rules.

pub mod expander;
pub mod oci;
pub mod rules;
pub mod schema_validator;
pub mod sprig;
pub mod umbrella;
pub mod values;

#[cfg(test)]
mod tests;

pub use expander::expand_helm_template;
pub use oci::{is_oci_uri, parse_oci_uri, unpack_oci_chart_layer, OciChartContents, OciReference};
pub use rules::*;
pub use schema_validator::{
    heal_helm_values_against_schema, validate_helm_values_against_schema, HelmSchemaViolation,
};
pub use sprig::*;
pub use umbrella::{heal_umbrella_chart, HelmHealResult};
pub use values::{heal_values_yaml, is_helm_values_content};

use super::ConfigurationParser;

/// Comprehensive Helm configuration parser and values healer for `values.yaml` files.
pub struct HelmParser;

impl ConfigurationParser for HelmParser {
    fn detect_violations(&self, content: &str) -> Result<Vec<String>, String> {
        let (_, changes) = heal_values_yaml(content);
        Ok(changes)
    }

    fn heal_non_destructive(&self, content: &str, _patch: &str) -> Result<String, String> {
        let (healed, _) = heal_values_yaml(content);
        Ok(healed)
    }

    fn dialect(&self) -> &str {
        "helm"
    }
}
