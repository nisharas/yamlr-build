//! License subscription and engine upgrade CLI handler.
//!
//! Why: Manages commercial license activation, subscription entitlements, and engine update verification
//! without requiring external network dependencies in air-gapped secure enclaves.

use crate::cli::{EXIT_SUCCESS, EXIT_VIOLATIONS};
use crate::security::{activate_license, stored_tier, LicenseTier, EMBEDDED_LICENSE_PUBLIC_KEY};

/// Executes the subscribe or upgrade command.
///
/// Why: Provides an auditable entry point for commercial license keys and version tracking.
pub fn execute_subscription(args: &[String]) -> i32 {
    let cmd = if args.len() > 1 {
        args[1].to_lowercase()
    } else {
        "subscribe".to_string()
    };

    let matches = match crate::cli::support_contract::parse(&cmd, args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };

    if cmd == "upgrade" {
        println!("Yamlr Engine Version Check & Upgrade");
        println!("===================================");
        println!(
            "Current Version: v{} (Rust Native Core)",
            env!("CARGO_PKG_VERSION")
        );
        println!("Latest Release:  Not checked (upgrade is offline and does not download files)");
        println!("\nTo upgrade, download a release from:");
        println!("  https://github.com/yamlr/yamlr/releases");
        println!("Follow that release's artifact verification instructions before installing.");
        return EXIT_SUCCESS;
    }

    // Subscribe / License activation
    let key = matches.get_one::<String>("key").cloned();

    match key {
        Some(license_key) => activate(&license_key),
        None => {
            println!("Yamlr License & Subscription Status");
            println!("===================================");
            print_tier(stored_tier(EMBEDDED_LICENSE_PUBLIC_KEY));
            println!("\nTo activate a Team seat or Enterprise organization grant:");
            println!("  yamlr subscribe --key <SIGNED_LICENSE_TOKEN>");
            EXIT_SUCCESS
        }
    }
}

/// Executes the `yamlr auth [activate <KEY> | status]` command.
pub fn execute_auth(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("auth", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let subcmd = matches.subcommand_name().unwrap_or("status");
    match subcmd {
        "activate" => {
            let activation = matches.subcommand_matches("activate").unwrap();
            let key = activation
                .get_one::<String>("token")
                .or_else(|| activation.get_one::<String>("key"))
                .unwrap();
            activate(key)
        }

        "status" => {
            println!("Yamlr Authentication & License Status");
            println!("=====================================");
            print_tier(stored_tier(EMBEDDED_LICENSE_PUBLIC_KEY));
            println!("\nTo activate a paid license:");
            println!("  yamlr auth activate <SIGNED_LICENSE_TOKEN>");
            EXIT_SUCCESS
        }
        _ => {
            println!("Usage: yamlr auth [activate <KEY> | status]");
            EXIT_SUCCESS
        }
    }
}

fn activate(token: &str) -> i32 {
    match activate_license(token, EMBEDDED_LICENSE_PUBLIC_KEY) {
        Ok(()) => {
            println!("[OK] Signed license verified and activated.");
            print_tier(stored_tier(EMBEDDED_LICENSE_PUBLIC_KEY));
            EXIT_SUCCESS
        }
        Err(error) => {
            eprintln!("[ERROR] {error}");
            EXIT_VIOLATIONS
        }
    }
}

fn print_tier(tier: LicenseTier) {
    println!("Active Tier:   {}", tier.name());
    match tier {
        LicenseTier::Individual => println!("Entitlements:  Individual scanning and free healing"),
        LicenseTier::Team => println!("Entitlements:  Individual features plus Team governance"),
        LicenseTier::Enterprise => {
            println!("Entitlements:  Team features plus Enterprise capabilities")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_subscription_status_success() {
        let args = vec!["yamlr".to_string(), "subscribe".to_string()];
        assert_eq!(execute_subscription(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_upgrade_instructions_success() {
        let args = vec!["yamlr".to_string(), "upgrade".to_string()];
        assert_eq!(execute_subscription(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_subscription_rejects_unsigned_or_malformed_keys() {
        let valid_args = vec![
            "yamlr".to_string(),
            "subscribe".to_string(),
            "--key".to_string(),
            "YAMLR-PRO-ENTERPRISE-2026-ACTIVE".to_string(),
        ];
        assert_eq!(execute_subscription(&valid_args), EXIT_VIOLATIONS);

        let invalid_args = vec![
            "yamlr".to_string(),
            "subscribe".to_string(),
            "--key".to_string(),
            "short".to_string(),
        ];
        assert_eq!(execute_subscription(&invalid_args), EXIT_VIOLATIONS);
    }

    #[test]
    fn test_auth_status_success() {
        let args = vec![
            "yamlr".to_string(),
            "auth".to_string(),
            "status".to_string(),
        ];
        assert_eq!(execute_auth(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_auth_activate_rejects_unsigned_tokens() {
        let args = vec![
            "yamlr".to_string(),
            "auth".to_string(),
            "activate".to_string(),
            "YAMLR-PRO-CORP-UNLIMITED-LICENSE".to_string(),
        ];
        assert_eq!(execute_auth(&args), EXIT_VIOLATIONS);

        let invalid_args = vec![
            "yamlr".to_string(),
            "auth".to_string(),
            "activate".to_string(),
            "bad".to_string(),
        ];
        assert_eq!(execute_auth(&invalid_args), EXIT_VIOLATIONS);
    }
}
