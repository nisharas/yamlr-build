//! Forensic rule explanation and architectural rationale CLI handler.
//!
//! Why: Developer friction is minimized when lint and compliance findings provide
//! self-documenting architectural justifications, CIS references, and actionable fix guidance.

use crate::audit_engine::{get_catalog, get_deprecations};
use crate::cli::{EXIT_SUCCESS, EXIT_VIOLATIONS};
use clap::{Arg, Command};

/// Explains a specific detector ID, deprecation rule, or safety invariant.
///
/// Why: Provides context-rich guidance on why Kubernetes enforces certain constraints
/// (e.g. dropping Linux capabilities, pinning SHA256 digests) and how Yamlr resolves them.
pub fn execute_explain(args: &[String]) -> i32 {
    let matches = match parse_explain_arguments(args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let Some(query) = matches.get_one::<String>("rule") else {
        println!("Yamlr Forensic Rule Explainer");
        println!("Usage: yamlr explain <RULE_ID>");
        println!("Example: yamlr explain SEC-001");
        println!("         yamlr explain CIS-4.2.1");
        println!("         yamlr explain DEP-INGRESS\n");
        println!("Run 'yamlr catalog' to view all available rule IDs.");
        return EXIT_SUCCESS;
    };

    let query = query.trim().to_uppercase();
    let catalog = get_catalog();

    // 1. Search in forensic detectors
    for d in &catalog.detectors {
        if d.id.to_uppercase() == query || d.name.to_uppercase().contains(&query) {
            println!("Rule Definition: {}", d.id);
            println!("==================================================");
            println!("Name:       {}", d.name);
            println!("Category:   {}", d.category);
            println!("Severity:   {}", d.severity);
            println!("\nRationale (Why this matters):");
            println!("  {}", d.rationale);
            println!("\nRemediation Strategy:");
            println!("  Run 'yamlr heal <PATH> --apply' to automatically resolve this");
            println!("  violation with zero comment loss and layout preservation.");
            println!("==================================================");
            return EXIT_SUCCESS;
        }
    }

    // 2. Search in deprecations
    let deprecations = get_deprecations();
    for dep in &deprecations.apis {
        if dep.deprecated_api.to_uppercase().contains(&query) || dep.kind.to_uppercase() == query {
            println!("Kubernetes API Deprecation: {}", dep.kind);
            println!("==================================================");
            println!("Deprecated API:     {}", dep.deprecated_api);
            println!("Replacement API:    {}", dep.replacement_api);
            println!("Removed in Version: Kubernetes v{}", dep.removed_in_version);
            println!("Severity:           {}", dep.severity);
            println!("\nMigration Guidance:");
            println!("  {}", dep.migration_notes);
            println!("\nAutomatic Healing:");
            println!(
                "  Yamlr automatically upgrades '{}' to '{}' during 'yamlr heal'.",
                dep.deprecated_api, dep.replacement_api
            );
            println!("==================================================");
            return EXIT_SUCCESS;
        }
    }

    // 3. Fallback for common builtin rule families
    if query.starts_with("SEC") || query.starts_with("CIS") {
        println!("Security Rule Family: {}", query);
        println!("--------------------------------------------------");
        println!("Category: Security & Pod Hardening");
        println!("Applies CIS Benchmark and Kubernetes Pod Security Standards (PSS Restricted).");
        println!(
            "Yamlr automatically configures: runAsNonRoot: true, allowPrivilegeEscalation: false,"
        );
        println!("readOnlyRootFilesystem: true, and capabilities: drop: [ALL].");
        return EXIT_SUCCESS;
    }

    eprintln!(
        "[ERROR] Unknown rule ID or pattern '{}'. Run 'yamlr catalog' to list available rules.",
        query
    );
    EXIT_VIOLATIONS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_explain_without_args_shows_usage() {
        let args = vec!["yamlr".to_string(), "explain".to_string()];
        assert_eq!(execute_explain(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_explain_known_category_fallback() {
        let args = vec![
            "yamlr".to_string(),
            "explain".to_string(),
            "SEC-001".to_string(),
        ];
        assert_eq!(execute_explain(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_explain_unknown_code_exits_violation() {
        let args = vec![
            "yamlr".to_string(),
            "explain".to_string(),
            "NONEXISTENT_XYZ_999".to_string(),
        ];
        assert_eq!(execute_explain(&args), EXIT_VIOLATIONS);
    }

    #[test]
    fn explain_rejects_unknown_options_and_extra_rule_ids() {
        for tail in [
            vec!["--surprise".to_string()],
            vec!["SEC-001".to_string(), "CIS-1.1".to_string()],
        ] {
            let mut args = vec!["yamlr".to_string(), "explain".to_string()];
            args.extend(tail);
            assert_eq!(execute_explain(&args), crate::cli::EXIT_USAGE);
        }
    }
}

pub(crate) fn parse_explain_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    crate::cli::parse_command_args(
        Command::new("explain").arg(Arg::new("rule").value_name("RULE_ID").num_args(0..=1)),
        args,
    )
}
