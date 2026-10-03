//! Interactive Terminal Guide and Concept Tour CLI Handler.
//!
//! Why: Eliminates onboarding friction by guiding platform engineers through
//! Yamlr's 42 forensic rules, zero-comment-loss healing architecture, and GitOps workflows.

use crate::cli::EXIT_SUCCESS;

/// Executes the `yamlr guide [TOPIC]` command.
pub fn execute_guide(args: &[String]) -> i32 {
    let matches = match super::support_contract::parse("guide", args) {
        Ok(matches) => matches,
        Err(error) => return super::report_argument_error(error),
    };
    let topic = matches
        .get_one::<String>("topic")
        .map(|topic| topic.to_lowercase());

    match topic.as_deref() {
        Some("security") | Some("sec") => {
            println!("Yamlr Architecture Guide: Container & Manifest Security");
            println!("========================================================");
            println!("* SEC-001: Disallows privileged containers and caps permissions.");
            println!("* SEC-002: Enforces 'imagePullPolicy: Always' to prevent stale image substitution.");
            println!(
                "* SEC-004: Automatically synthesizes readOnlyRootFilesystem with /tmp emptyDir."
            );
            println!(
                "* SEC-005: Drops all default Linux capabilities (ALL) and adds minimal subsets."
            );
            println!("* SEC-014: Cosign image signature verification and in-toto provenance attestation.");
            println!("\nRun 'yamlr explain <RULE_ID>' (e.g., 'yamlr explain SEC-001') for deeper rationale.");
        }
        Some("network") | Some("net") => {
            println!("Yamlr Architecture Guide: Networking & Ingress Contracts");
            println!("=========================================================");
            println!(
                "* NET-001: Synchronizes Service targetPort with Container port specifications."
            );
            println!(
                "* NET-002: Realizes Gateway API modernizations (Ingress -> HTTPRoute, GRPCRoute)."
            );
            println!("* NET-007: Enforces Cross-Resource Protocol Contract alignment.");
            println!("* NET-008: Resolves Ingress Path Shadowing by sorting by path specificity.");
            println!("* NET-009: Detects and heals Dual-Stack IPv6 CIDR clashes.");
        }
        Some("gitops") => {
            println!("Yamlr Architecture Guide: GitOps Sync-Waves & Atomic Rollback");
            println!("=============================================================");
            println!("* GTO-001: Sync-Wave Stamping automatically calculates 7-tier deployment ordering.");
            println!("* GTO-002: Generates immutable cryptographic WAL journals for instant atomic rollback.");
            println!("* GTO-003: Embeds SHA-256 state signatures into manifest metadata.");
            println!(
                "\nEnable automatic sync-wave stamping via annotation 'yamlr.io/gitops: true'."
            );
        }
        Some("rules") | Some("catalog") => {
            println!("Yamlr Forensic Rules Overview");
            println!("=============================");
            println!("Yamlr enforces 42 built-in forensic rules across 6 core pillars:");
            println!("  1. Workload Safety (SCH, TYP, ENM, STR)");
            println!("  2. Reliability & High Availability (REL, PDB, TOPO)");
            println!("  3. Container & Pod Security (SEC, CAP, CIS)");
            println!("  4. Network Contracts (NET, GW, SVC)");
            println!("  5. Storage & Persistence (STO, STR, PVC)");
            println!("  6. GitOps Governance (GTO, VAP, SIG)");
            println!("\nRun 'yamlr catalog' to view the complete catalog of rules.");
        }
        Some(unknown) => {
            println!("Yamlr Technical Concept Guide: '{}'", unknown);
            println!("==================================================");
            println!("To view documentation on a specific rule or topic:");
            println!("  yamlr guide security   - Container security & least-privilege standards");
            println!("  yamlr guide network    - Gateway API and service selector contracts");
            println!("  yamlr guide gitops     - ArgoCD/Flux sync-waves & atomic rollback WAL");
            println!("  yamlr guide rules      - Forensic rule catalog overview");
            println!(
                "  yamlr explain <RULE>   - Specific rule deep-dive (e.g. yamlr explain SEC-001)"
            );
        }
        None => {
            println!("Yamlr — Interactive Knowledge & Architecture Guide");
            println!("===================================================");
            println!("Yamlr is an autonomous resolution engine for Kubernetes manifests.");
            println!("Unlike passive linters, Yamlr safely auto-repairs configurations");
            println!("while preserving 100% of human comments, spacing, and layout.\n");
            println!("EXPLORE TOPICS:");
            println!("  yamlr guide security   Container & pod hardening (SEC, CIS, Cosign)");
            println!("  yamlr guide network    Gateway API modernizer & port contracts (NET)");
            println!("  yamlr guide gitops     ArgoCD/Flux sync-waves & atomic rollback (GTO)");
            println!("  yamlr guide rules      Catalog of 42 deterministic rules\n");
            println!("QUICK REFERENCE:");
            println!("  yamlr scan .           Audit manifests for schema and integrity issues");
            println!("  yamlr heal . --diff    Preview proposed surgical auto-repairs");
            println!("  yamlr heal . --apply   Apply safe auto-repairs with zero comment loss");
            println!("  yamlr explain <ID>     Deep-dive rationale for any rule (e.g. SEC-001)");
        }
    }

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_guide_cmd_executes_successfully() {
        let args = vec!["yamlr".to_string(), "guide".to_string()];
        assert_eq!(execute_guide(&args), EXIT_SUCCESS);

        let sec_args = vec![
            "yamlr".to_string(),
            "guide".to_string(),
            "security".to_string(),
        ];
        assert_eq!(execute_guide(&sec_args), EXIT_SUCCESS);

        let net_args = vec![
            "yamlr".to_string(),
            "guide".to_string(),
            "network".to_string(),
        ];
        assert_eq!(execute_guide(&net_args), EXIT_SUCCESS);

        let gitops_args = vec![
            "yamlr".to_string(),
            "guide".to_string(),
            "gitops".to_string(),
        ];
        assert_eq!(execute_guide(&gitops_args), EXIT_SUCCESS);
    }
}
