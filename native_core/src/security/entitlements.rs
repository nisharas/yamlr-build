//! Local license persistence and tier capability policy.
//!
//! Why: Keeps paid feature access consistent across CLI commands while allowing
//! signed Team seats to move with a developer and Enterprise grants to work offline.

use std::fs;
#[cfg(test)]
use std::fs::OpenOptions;
#[cfg(test)]
use std::io::Write;
use std::path::{Path, PathBuf};

use super::licensing::{native_license_tier, native_verify_token};

const LICENSE_FILE: &str = "license.jwt";
const KEYRING_SERVICE: &str = "yamlr";
const KEYRING_ACCOUNT: &str = "active-license";
pub const EMBEDDED_LICENSE_PUBLIC_KEY: &str = include_str!("public_key.pem");

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LicenseTier {
    Individual,
    Team,
    Enterprise,
}

impl LicenseTier {
    pub fn from_canonical_name(name: &str) -> Self {
        match name.trim().to_ascii_lowercase().as_str() {
            "team" => Self::Team,
            "enterprise" => Self::Enterprise,
            _ => Self::Individual,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Individual => "Individual",
            Self::Team => "Team",
            Self::Enterprise => "Enterprise",
        }
    }

    pub fn includes(self, feature: LicenseFeature) -> bool {
        use LicenseFeature::*;
        match self {
            Self::Individual => matches!(feature, ScanAndHeal | Sarif),
            Self::Team => matches!(
                feature,
                ScanAndHeal | Sarif | FleetGovernance | PolicyRepair
            ),
            Self::Enterprise => matches!(
                feature,
                ScanAndHeal
                    | Sarif
                    | FleetGovernance
                    | PolicyRepair
                    | ComplianceEvidence
                    | ManifestSigning
                    | CustomPolicyVault
                    | OfflineDistribution
                    | PulseTelemetry
            ),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LicenseFeature {
    ScanAndHeal,
    Sarif,
    FleetGovernance,
    PolicyRepair,
    ComplianceEvidence,
    ManifestSigning,
    CustomPolicyVault,
    OfflineDistribution,
    PulseTelemetry,
}

pub fn required_feature_for_args(args: &[String]) -> Option<LicenseFeature> {
    let option_end = args
        .iter()
        .skip(2)
        .position(|arg| arg == "--")
        .map(|index| index + 2)
        .unwrap_or(args.len());
    let args = &args[..option_end];
    let command = args.get(1)?.to_ascii_lowercase();
    match command.as_str() {
        "fleet" => Some(LicenseFeature::FleetGovernance),
        "evidence" => Some(LicenseFeature::ComplianceEvidence),
        "sign" => Some(LicenseFeature::ManifestSigning),
        "scan" if args.iter().any(|arg| arg == "--push-telemetry") => {
            Some(LicenseFeature::PulseTelemetry)
        }
        "scan" | "lint" | "audit" if requests_sarif_output(args) => Some(LicenseFeature::Sarif),
        "heal"
            if args.iter().any(|arg| {
                matches!(
                    arg.as_str(),
                    "--from-report" | "--ingest-opa" | "--ingest-kyverno"
                ) || arg.starts_with("--ingest-opa=")
                    || arg.starts_with("--ingest-kyverno=")
            }) =>
        {
            Some(LicenseFeature::PolicyRepair)
        }
        _ => None,
    }
}

/// Capabilities compose: disabling optional telemetry must not disable SARIF licensing.
pub fn required_features_for_args(args: &[String]) -> Vec<LicenseFeature> {
    let mut features: Vec<_> = required_feature_for_args(args).into_iter().collect();
    if args.get(1).is_some_and(|command| {
        matches!(
            command.to_ascii_lowercase().as_str(),
            "scan" | "lint" | "audit"
        )
    }) && requests_sarif_output(args)
        && !features.contains(&LicenseFeature::Sarif)
    {
        features.push(LicenseFeature::Sarif);
    }
    features
}

fn requests_sarif_output(args: &[String]) -> bool {
    args.iter()
        .enumerate()
        .skip(2)
        .take_while(|(_, argument)| argument.as_str() != "--")
        .any(|(index, argument)| {
            if argument.eq_ignore_ascii_case("--sarif") {
                return true;
            }

            let inline_format = argument
                .strip_prefix("--output=")
                .or_else(|| argument.strip_prefix("-o="))
                .or_else(|| argument.strip_prefix("-o"));
            if inline_format.is_some_and(|format| format.eq_ignore_ascii_case("sarif")) {
                return true;
            }

            matches!(argument.as_str(), "--output" | "-o")
                && args
                    .get(index + 1)
                    .is_some_and(|format| format.eq_ignore_ascii_case("sarif"))
        })
}

pub fn default_license_path() -> Option<PathBuf> {
    dirs::config_dir()
        .or_else(dirs::home_dir)
        .map(|root| root.join("yamlr").join(LICENSE_FILE))
}

#[cfg(test)]
pub fn activate_license_at(token: &str, public_key: &str, path: &Path) -> Result<(), String> {
    if !native_verify_token(token, public_key) {
        return Err("The license token is invalid, expired, or not supported.".to_string());
    }

    let parent = path
        .parent()
        .ok_or_else(|| "Invalid license path.".to_string())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("Cannot create license directory: {error}"))?;
    restrict_license_directory(parent)?;
    let temp_path = path.with_extension(format!("jwt-{}", uuid::Uuid::new_v4()));
    let write_result = write_license_atomically(token, &temp_path, path);
    if write_result.is_err() {
        let _ = fs::remove_file(&temp_path);
    }
    write_result
}

#[cfg(not(target_arch = "wasm32"))]
fn license_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_ACCOUNT)
        .map_err(|error| format!("Cannot access the operating system credential store: {error}"))
}

#[cfg(not(target_arch = "wasm32"))]
pub fn activate_license(token: &str, public_key: &str) -> Result<(), String> {
    if !native_verify_token(token, public_key) {
        return Err("The license token is invalid, expired, or not supported.".to_string());
    }
    license_entry()?.set_password(token).map_err(|error| {
        format!("Cannot save license in the operating system credential store: {error}")
    })?;
    if let Some(path) = default_license_path() {
        if path.exists() {
            fs::remove_file(path)
                .map_err(|error| format!("License was saved securely, but the legacy plaintext token could not be removed: {error}"))?;
        }
    }
    Ok(())
}

#[cfg(not(target_arch = "wasm32"))]
pub fn stored_license_token(public_key: &str) -> Result<Option<String>, String> {
    let entry = license_entry()?;
    match entry.get_password() {
        Ok(token) => Ok(native_verify_token(&token, public_key).then_some(token)),
        Err(keyring::Error::NoEntry) => migrate_legacy_license(&entry, public_key),
        Err(error) => Err(format!(
            "Cannot read the operating system credential store: {error}"
        )),
    }
}

#[cfg(target_arch = "wasm32")]
pub fn stored_license_token(_public_key: &str) -> Result<Option<String>, String> {
    Ok(None)
}

#[cfg(not(target_arch = "wasm32"))]
fn migrate_legacy_license(
    entry: &keyring::Entry,
    public_key: &str,
) -> Result<Option<String>, String> {
    let Some(path) = default_license_path() else {
        return Ok(None);
    };
    migrate_legacy_license_at(&path, public_key, |token| {
        entry.set_password(token).map_err(|error| {
            format!("Cannot migrate license into the operating system credential store: {error}")
        })
    })
}

fn migrate_legacy_license_at(
    path: &Path,
    public_key: &str,
    store: impl FnOnce(&str) -> Result<(), String>,
) -> Result<Option<String>, String> {
    let token = match fs::read_to_string(&path) {
        Ok(token) => token,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(format!("Cannot read the legacy license token: {error}")),
    };
    if !native_verify_token(&token, public_key) {
        return Ok(None);
    }
    store(&token)?;
    fs::remove_file(path)
        .map_err(|error| format!("License was migrated securely, but the legacy plaintext token could not be removed: {error}"))?;
    Ok(Some(token))
}

#[cfg(unix)]
#[cfg(all(test, unix))]
fn restrict_license_directory(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    let permissions = fs::Permissions::from_mode(0o700);
    fs::set_permissions(path, permissions)
        .map_err(|error| format!("Cannot restrict license directory permissions: {error}"))
}

#[cfg(not(unix))]
#[cfg(all(test, not(unix)))]
fn restrict_license_directory(_path: &Path) -> Result<(), String> {
    // On Windows, the application configuration directory inherits the current
    // user's profile ACL. Other platforms use their standard private config dir.
    Ok(())
}

#[cfg(test)]
fn write_license_atomically(token: &str, temp_path: &Path, path: &Path) -> Result<(), String> {
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options
        .open(temp_path)
        .map_err(|error| format!("Cannot stage license: {error}"))?;
    file.write_all(token.as_bytes())
        .map_err(|error| format!("Cannot write license: {error}"))?;
    file.sync_all()
        .map_err(|error| format!("Cannot flush license: {error}"))?;
    fs::rename(temp_path, path).map_err(|error| format!("Cannot activate license: {error}"))
}

#[cfg(test)]
pub fn stored_tier_at(public_key: &str, path: &Path) -> LicenseTier {
    let Ok(token) = fs::read_to_string(path) else {
        return LicenseTier::Individual;
    };
    native_license_tier(&token, public_key)
        .as_deref()
        .map(LicenseTier::from_canonical_name)
        .unwrap_or(LicenseTier::Individual)
}

pub fn stored_tier(public_key: &str) -> LicenseTier {
    stored_license_token(public_key)
        .ok()
        .flatten()
        .and_then(|token| native_license_tier(&token, public_key))
        .as_deref()
        .map(LicenseTier::from_canonical_name)
        .unwrap_or(LicenseTier::Individual)
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
    use serde::Serialize;

    const PRIVATE_KEY: &str = include_str!("../../tests/fixtures/licensing_test_private.pem");
    const PUBLIC_KEY: &str = include_str!("../../tests/fixtures/licensing_test_public.pem");

    #[derive(Serialize)]
    struct TeamClaims<'a> {
        license_version: u32,
        sub: &'a str,
        email: &'a str,
        iat: usize,
        exp: usize,
        tier: &'a str,
        iss: &'a str,
        aud: &'a str,
        org_id: &'a str,
        seats: u32,
        org_seats: u32,
    }

    fn valid_team_token() -> String {
        let now = chrono::Utc::now().timestamp() as usize;
        let claims = TeamClaims {
            license_version: 1,
            sub: "developer@example.test",
            email: "developer@example.test",
            iat: now,
            exp: now + 3600,
            tier: "team",
            iss: "yamlr-entitlement",
            aud: "yamlr",
            org_id: "org-1",
            seats: 1,
            org_seats: 5,
        };
        encode(
            &Header::new(Algorithm::RS256),
            &claims,
            &EncodingKey::from_rsa_pem(PRIVATE_KEY.as_bytes()).unwrap(),
        )
        .unwrap()
    }

    #[test]
    fn canonical_tiers_and_legacy_names_are_mapped_safely() {
        assert_eq!(LicenseTier::from_canonical_name("team"), LicenseTier::Team);
        assert_eq!(LicenseTier::from_canonical_name("TEAM"), LicenseTier::Team);
        assert_eq!(
            LicenseTier::from_canonical_name("enterprise"),
            LicenseTier::Enterprise
        );
        assert_eq!(
            LicenseTier::from_canonical_name("pro"),
            LicenseTier::Individual
        );
        assert_eq!(
            LicenseTier::from_canonical_name("unknown"),
            LicenseTier::Individual
        );
    }

    #[test]
    fn individual_includes_only_core_scan_and_healing() {
        assert!(LicenseTier::Individual.includes(LicenseFeature::ScanAndHeal));
        assert!(LicenseTier::Individual.includes(LicenseFeature::Sarif));
        for feature in [
            LicenseFeature::FleetGovernance,
            LicenseFeature::PolicyRepair,
            LicenseFeature::ComplianceEvidence,
            LicenseFeature::ManifestSigning,
            LicenseFeature::CustomPolicyVault,
            LicenseFeature::OfflineDistribution,
            LicenseFeature::PulseTelemetry,
        ] {
            assert!(!LicenseTier::Individual.includes(feature));
        }
    }

    #[test]
    fn team_includes_team_features_but_not_enterprise_features() {
        for feature in [
            LicenseFeature::ScanAndHeal,
            LicenseFeature::Sarif,
            LicenseFeature::FleetGovernance,
            LicenseFeature::PolicyRepair,
        ] {
            assert!(LicenseTier::Team.includes(feature));
        }
        for feature in [
            LicenseFeature::ComplianceEvidence,
            LicenseFeature::ManifestSigning,
            LicenseFeature::CustomPolicyVault,
            LicenseFeature::OfflineDistribution,
            LicenseFeature::PulseTelemetry,
        ] {
            assert!(!LicenseTier::Team.includes(feature));
        }
    }

    #[test]
    fn enterprise_includes_all_published_features() {
        for feature in [
            LicenseFeature::ScanAndHeal,
            LicenseFeature::Sarif,
            LicenseFeature::FleetGovernance,
            LicenseFeature::PolicyRepair,
            LicenseFeature::ComplianceEvidence,
            LicenseFeature::ManifestSigning,
            LicenseFeature::CustomPolicyVault,
            LicenseFeature::OfflineDistribution,
            LicenseFeature::PulseTelemetry,
        ] {
            assert!(LicenseTier::Enterprise.includes(feature));
        }
    }

    #[test]
    fn activation_persists_only_a_valid_signed_token() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("yamlr").join(LICENSE_FILE);
        let token = valid_team_token();
        activate_license_at(&token, PUBLIC_KEY, &path).unwrap();
        activate_license_at(&token, PUBLIC_KEY, &path).unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), token);
        assert_eq!(stored_tier_at(PUBLIC_KEY, &path), LicenseTier::Team);
    }

    #[test]
    fn legacy_token_is_removed_only_after_secure_store_accepts_it() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(LICENSE_FILE);
        let token = valid_team_token();
        fs::write(&path, &token).unwrap();
        let mut stored = None;

        let migrated = migrate_legacy_license_at(&path, PUBLIC_KEY, |value| {
            stored = Some(value.to_string());
            Ok(())
        })
        .unwrap();

        assert_eq!(migrated.as_deref(), Some(token.as_str()));
        assert_eq!(stored.as_deref(), Some(token.as_str()));
        assert!(!path.exists());
    }

    #[test]
    fn legacy_token_remains_when_secure_store_migration_fails() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(LICENSE_FILE);
        let token = valid_team_token();
        fs::write(&path, &token).unwrap();

        let error = migrate_legacy_license_at(&path, PUBLIC_KEY, |_| {
            Err("credential store unavailable".to_string())
        })
        .unwrap_err();

        assert!(error.contains("credential store unavailable"));
        assert_eq!(fs::read_to_string(path).unwrap(), token);
    }

    #[cfg(unix)]
    #[test]
    fn activation_restricts_license_directory_and_file_permissions() {
        use std::os::unix::fs::PermissionsExt;

        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("yamlr").join(LICENSE_FILE);
        activate_license_at(&valid_team_token(), PUBLIC_KEY, &path).unwrap();

        assert_eq!(
            fs::metadata(path.parent().unwrap())
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o600
        );
    }

    #[test]
    fn invalid_token_is_not_written_or_allowed_to_replace_license() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("yamlr").join(LICENSE_FILE);
        let valid_token = valid_team_token();
        activate_license_at(&valid_token, PUBLIC_KEY, &path).unwrap();
        assert!(activate_license_at("not-a-jwt", PUBLIC_KEY, &path).is_err());
        assert_eq!(fs::read_to_string(&path).unwrap(), valid_token);
    }

    #[test]
    fn missing_or_invalid_stored_token_falls_back_to_individual() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(LICENSE_FILE);
        assert_eq!(stored_tier_at(PUBLIC_KEY, &path), LicenseTier::Individual);
        fs::write(&path, "invalid").unwrap();
        assert_eq!(stored_tier_at(PUBLIC_KEY, &path), LicenseTier::Individual);
    }

    #[test]
    fn default_path_uses_application_configuration_directory() {
        assert!(default_license_path().is_some());
    }

    #[test]
    fn paid_cli_commands_map_to_their_published_capabilities() {
        let args = |items: &[&str]| {
            items
                .iter()
                .map(|item| item.to_string())
                .collect::<Vec<_>>()
        };
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "fleet"])),
            Some(LicenseFeature::FleetGovernance)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "evidence"])),
            Some(LicenseFeature::ComplianceEvidence)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "sign"])),
            Some(LicenseFeature::ManifestSigning)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "scan", "--sarif"])),
            Some(LicenseFeature::Sarif)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "scan", "--push-telemetry"])),
            Some(LicenseFeature::PulseTelemetry)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "scan", "--sarif", "--push-telemetry"])),
            Some(LicenseFeature::PulseTelemetry)
        );
        assert_eq!(
            required_feature_for_args(&args(&["yamlr", "heal", "--from-report"])),
            Some(LicenseFeature::PolicyRepair)
        );
        assert_eq!(required_feature_for_args(&args(&["yamlr", "scan"])), None);
        assert_eq!(required_feature_for_args(&args(&["yamlr", "heal"])), None);
    }

    #[test]
    fn compact_output_and_composed_features_cannot_skip_sarif_entitlement() {
        for output in ["-osarif", "-o=sarif", "--output=sarif"] {
            let args = vec![
                "yamlr".into(),
                "scan".into(),
                output.into(),
                "--push-telemetry".into(),
            ];
            assert_eq!(
                required_features_for_args(&args),
                vec![LicenseFeature::PulseTelemetry, LicenseFeature::Sarif]
            );
        }
        let args = vec!["yamlr".into(), "scan".into(), "--".into(), "-osarif".into()];
        assert!(required_features_for_args(&args).is_empty());
    }
}
