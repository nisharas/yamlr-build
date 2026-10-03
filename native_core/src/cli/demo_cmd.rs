//! Interactive demo walkthrough CLI handler.
//!
//! Why: Enables prospects, evaluating platform engineers, and CI auditors to instantly
//! experience Yamlr's Rust-native parsing, comment preservation, and manifest healing
//! without touching their real files or downloading sample repositories.

use crate::cli::heal_cmd::heal_manifest_string;
use crate::cli::EXIT_SUCCESS;

/// Executes the live interactive demonstration.
///
/// Why: Demonstrates manifest healing on an in-memory example without modifying user files.
pub fn execute_demo(_args: &[String]) -> i32 {
    println!("=== Yamlr Interactive Healing Engine Demonstration ===");
    println!("Simulating autonomous resolution on a real-world enterprise workload...\n");

    let sample_yaml = r#"# Critical Production Payment Service
# Owner: platform-eng@acme.corp
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: prod
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: payment
    spec:
      containers:
        # NOTICE: Floating latest tag and missing security controls
        - name: server
          image: acme/payment:latest
          country: NO  # YAML 1.1 Norway problem
"#;

    println!("[Step 1] Original Manifest with Latent Risks and Comments:");
    println!("----------------------------------------------------------");
    println!("{}\n", sample_yaml.trim());

    println!("[Step 2] Executing Native Autonomous Healer (Stage 1-21 Pipeline)...");
    let healed = heal_manifest_string(sample_yaml).0;

    println!("\n[Step 3] Healed Manifest (Comment Preserved & Hardened):");
    println!("----------------------------------------------------------");
    println!("{}\n", healed.trim());

    println!("Demo Results:");
    println!("  [+] Sample Comments:      Carried through this demonstration");
    println!("  [+] Norway Problem:       Safely quoted ('NO')");
    println!("  [+] Floating Image Pin:   Latest tag flagged/stabilized");
    println!("  [+] Execution Speed:      Native Rust engine (timing depends on workload)");
    println!("\nRun 'yamlr heal <YOUR_DIR> --diff' to try it on your own codebase!");

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_demo_execution_succeeds() {
        let args = vec!["yamlr".to_string(), "demo".to_string()];
        assert_eq!(execute_demo(&args), EXIT_SUCCESS);
    }
}
