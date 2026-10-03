//! Healing engine features and stage registry CLI handler.
//!
//! Why: Transparently communicates all 21 autonomous healing stages, their security tiers,
//! safety defaults, and activation criteria to platform engineers and M&A auditors.

use crate::cli::EXIT_SUCCESS;

pub struct HealerFeature {
    pub stage: u8,
    pub name: &'static str,
    pub category: &'static str,
    pub safety_default: &'static str,
    pub description: &'static str,
}

pub const HEALER_REGISTRY: &[HealerFeature] = &[
    HealerFeature {
        stage: 1,
        name: "QuoteBooleans",
        category: "Heuristic",
        safety_default: "Safe (S0)",
        description: "Quotes YAML 1.1 Norway problem booleans (no, yes, on, off)",
    },
    HealerFeature {
        stage: 2,
        name: "EvenIndentation",
        category: "Heuristic",
        safety_default: "Safe (S0)",
        description: "Normalizes irregular 3-space / odd indents to 2-space grid",
    },
    HealerFeature {
        stage: 3,
        name: "MissingColons",
        category: "Heuristic",
        safety_default: "Safe (S0)",
        description: "Restores accidental missing colons after mapping keys",
    },
    HealerFeature {
        stage: 4,
        name: "QuoteBalancing",
        category: "Heuristic",
        safety_default: "Safe (S0)",
        description: "Closes unescaped or unclosed single/double quote sequences",
    },
    HealerFeature {
        stage: 5,
        name: "FlowSanitizer",
        category: "Heuristic",
        safety_default: "Safe (S0)",
        description: "Cleans trailing commas and invalid flow mappings/sequences",
    },
    HealerFeature {
        stage: 6,
        name: "DnaIntegrity",
        category: "Governance",
        safety_default: "Safe (S0)",
        description: "Validates semantic DNA fingerprint invariants",
    },
    HealerFeature {
        stage: 7,
        name: "ApiDeprecationUpgrade",
        category: "Lifecycle",
        safety_default: "Safe (S0)",
        description:
            "Upgrades removed APIs (e.g. Ingress extensions/v1beta1 -> networking.k8s.io/v1)",
    },
    HealerFeature {
        stage: 8,
        name: "ImagePinning",
        category: "Supply Chain",
        safety_default: "Safe (S0)",
        description: "Pins mutable floating tags (:latest) or flags missing digests",
    },
    HealerFeature {
        stage: 9,
        name: "SecurityContextHardening",
        category: "Security",
        safety_default: "Safe (S0)",
        description: "Enforces runAsNonRoot, drops ALL capabilities, read-only rootfs",
    },
    HealerFeature {
        stage: 10,
        name: "ResourceLimitsBalancer",
        category: "Reliability",
        safety_default: "Safe (S0)",
        description: "Corrects inverted CPU/memory requests and limits",
    },
    HealerFeature {
        stage: 11,
        name: "ServicePortAlignment",
        category: "Networking",
        safety_default: "Safe (S0)",
        description: "Resolves mismatched Service targetPorts against container ports",
    },
    HealerFeature {
        stage: 12,
        name: "ProbeTimeouts",
        category: "Reliability",
        safety_default: "Safe (S0)",
        description: "Ensures timeoutSeconds < periodSeconds on liveness/readiness probes",
    },
    HealerFeature {
        stage: 13,
        name: "IngressTlsCert",
        category: "Security",
        safety_default: "Safe (S0)",
        description: "Fixes missing TLS hosts or secret references in Ingress specs",
    },
    HealerFeature {
        stage: 14,
        name: "GitOpsWaveStamping",
        category: "GitOps",
        safety_default: "Safe (S0)",
        description: "Applies 7-tier argocd.argoproj.io/sync-wave annotations",
    },
    HealerFeature {
        stage: 15,
        name: "CrdDistillation",
        category: "Schema",
        safety_default: "Safe (S0)",
        description: "Extracts and caches OpenAPI v3 schemas from CRD definitions",
    },
    HealerFeature {
        stage: 16,
        name: "StubGeneration",
        category: "Topology",
        safety_default: "Opt-In (S2)",
        description: "Generates missing ConfigMap/Secret stubs referenced by workloads",
    },
    HealerFeature {
        stage: 17,
        name: "OciRegistryPinning",
        category: "Supply Chain",
        safety_default: "Safe (S0)",
        description: "Validates OCI registry domain hygiene",
    },
    HealerFeature {
        stage: 18,
        name: "PdbQuorumGuard",
        category: "Reliability",
        safety_default: "Safe (S0)",
        description: "Prevents PodDisruptionBudgets with maxUnavailable: 100%",
    },
    HealerFeature {
        stage: 19,
        name: "HpaMetricSync",
        category: "Reliability",
        safety_default: "Safe (S0)",
        description: "Corrects HPA target utilization and deprecated metrics APIs",
    },
    HealerFeature {
        stage: 20,
        name: "LayoutGrafter",
        category: "AST Engine",
        safety_default: "Safe (S0)",
        description: "Guarantees 100% comment, whitespace, and layout preservation",
    },
    HealerFeature {
        stage: 21,
        name: "AtomicWalJournal",
        category: "Safety",
        safety_default: "Safe (S0)",
        description: "Write-Ahead Log rollback journal guaranteeing zero data loss",
    },
];

/// Displays the table of all 21 autonomous healing stages.
///
/// Why: Provides an authoritative scorecard reference for enterprise platform teams.
pub fn execute_features(_args: &[String]) -> i32 {
    println!("Yamlr Autonomous Healing Engine Feature Scorecard");
    println!("================================================================================");
    println!(
        "{:<4} {:<26} {:<14} {:<14} {:<20}",
        "STG", "HEALER NAME", "CATEGORY", "SAFETY", "DESCRIPTION"
    );
    println!("{:-<4} {:-<26} {:-<14} {:-<14} {:-<20}", "", "", "", "", "");

    for f in HEALER_REGISTRY {
        println!(
            "{:<4} {:<26} {:<14} {:<14} {:<20}",
            f.stage, f.name, f.category, f.safety_default, f.description
        );
    }

    println!("================================================================================");
    println!("Total Stages: 21 | Zero Comment Loss Pillar: 100% Active | Memory Safety: Rust\n");
    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_features_scorecard_has_21_stages() {
        assert_eq!(HEALER_REGISTRY.len(), 21);
        let args = vec!["yamlr".to_string(), "features".to_string()];
        assert_eq!(execute_features(&args), EXIT_SUCCESS);
    }
}
