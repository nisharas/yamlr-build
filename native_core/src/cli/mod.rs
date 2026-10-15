//! Yamlr Native CLI Modules
//!
//! Standalone binary implementation for CI gates, Git hooks, and developer IDEs.
//! Runtime depends on the workload; measure it using the native CLI benchmark.

use clap::{ArgMatches, Command};

pub mod admin_cmd;
pub mod audit_cmd;
pub mod baseline_cmd;
pub mod check_cmd;
pub mod completion_cmd;
pub mod demo_cmd;
pub mod diff_viewer;
pub mod dispatch;
pub mod dna_cmd;
pub mod doctor_cmd;
pub mod evidence_cmd;
pub mod explain_cmd;
pub mod features_cmd;
pub mod fleet_cmd;
pub mod fmt_cmd;
pub mod graph_cmd;
pub mod guide_cmd;
pub mod heal_cmd;
pub(crate) mod heal_adapters;
pub(crate) mod heal_args;
pub(crate) mod heal_topology;
pub(crate) mod heal_writer;
pub mod idp_export_cmd;
pub mod init_cmd;
pub mod lsp_server;
pub mod mcp_server;
pub mod metrics_cmd;
pub mod rollback_cmd;
pub mod scan_cmd;
pub(crate) mod scan_args;
pub(crate) mod scan_render;
#[path = "scan_telemetry.rs"]
pub(crate) mod scan_telemetry;
pub mod schema_cmd;
pub mod secure_cmd;
pub mod sign_cmd;
pub mod status_cmd;
pub mod subscription_cmd;
pub(crate) mod support_contract;
pub mod utility_cmds;
pub mod vap_cmd;
pub mod watch;
pub mod webhook_cmd;

pub const EXIT_SUCCESS: i32 = 0;
pub const EXIT_VIOLATIONS: i32 = 1;
pub const EXIT_SYNTAX_ERROR: i32 = 2;
pub const EXIT_CONFIG_ERROR: i32 = 3;
pub const EXIT_SYSTEM_ERROR: i32 = 4;
pub const EXIT_USAGE: i32 = EXIT_CONFIG_ERROR;

pub(crate) fn parse_severity_threshold(value: &str) -> Result<String, String> {
    scan_cmd::scan_fail_on::FailOn::parse(value)
        .map(|_| value.to_owned())
        .ok_or_else(|| "Expected error, warning, note, info, any, or none".to_string())
}

/// Validate every registered command before licensing, I/O, or service startup.
/// Execution handlers use these same definitions; this is not a second grammar.
pub(crate) fn validate_command_arguments(
    name: &str,
    args: &[String],
) -> Option<Result<(), clap::Error>> {
    if support_contract::definition(name).is_some() {
        return Some(support_contract::parse(name, args).map(|_| ()));
    }
    Some(match name {
        "scan" | "lint" => scan_cmd::parse_scan_arguments(args).map(|_| ()),
        "heal" | "fix" => heal_cmd::parse_heal_arguments(args).map(|_| ()),
        "check" => check_cmd::parse_check_arguments(args).map(|_| ()),
        "diff" => diff_viewer::parse_diff_arguments(args).map(|_| ()),
        "schema" => schema_cmd::parse_schema_arguments(args).map(|_| ()),
        "explain" => explain_cmd::parse_explain_arguments(args).map(|_| ()),
        "audit" => audit_cmd::parse_audit_arguments(args).map(|_| ()),
        "catalog" => audit_cmd::parse_catalog_arguments(args).map(|_| ()),
        "baseline" => baseline_cmd::parse_baseline_args(args).map(|_| ()),
        "fmt" => fmt_cmd::parse_fmt_args(args).map(|_| ()),
        _ => return None,
    })
}

/// Parses one command's arguments using its Clap definition. The process name
/// and top-level command occupy the first two entries in the native dispatch
/// vector, so only command-specific arguments are passed to the subcommand parser.
pub fn parse_command_args(command: Command, args: &[String]) -> Result<ArgMatches, clap::Error> {
    let command_name = command.get_name().to_owned();
    command.try_get_matches_from(std::iter::once(command_name).chain(args.iter().skip(2).cloned()))
}

/// Clap help is successful stdout output; malformed arguments are usage errors.
pub fn report_argument_error(error: clap::Error) -> i32 {
    if matches!(
        error.kind(),
        clap::error::ErrorKind::DisplayHelp | clap::error::ErrorKind::DisplayVersion
    ) {
        print!("{error}");
        EXIT_SUCCESS
    } else {
        eprint!("{error}");
        EXIT_USAGE
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OutputFormat {
    Text,
    Json,
    Sarif,
}

impl OutputFormat {
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "text" => Some(OutputFormat::Text),
            "json" => Some(OutputFormat::Json),
            "sarif" => Some(OutputFormat::Sarif),
            _ => None,
        }
    }
}

#[cfg(test)]
mod output_format_tests {
    use super::{parse_single_target, OutputFormat};

    #[test]
    fn output_format_parser_accepts_supported_formats_case_insensitively() {
        assert_eq!(OutputFormat::parse("text"), Some(OutputFormat::Text));
        assert_eq!(OutputFormat::parse("JSON"), Some(OutputFormat::Json));
        assert_eq!(OutputFormat::parse("sarif"), Some(OutputFormat::Sarif));
    }

    #[test]
    fn output_format_parser_rejects_unsupported_formats() {
        assert_eq!(OutputFormat::parse("xml"), None);
        assert_eq!(OutputFormat::parse("admission-review"), None);
        assert_eq!(OutputFormat::parse("admissionreview"), None);
        assert_eq!(OutputFormat::parse(""), None);
    }

    #[test]
    fn single_target_parser_accepts_options_before_and_after_target() {
        let args = [
            "yamlr",
            "example",
            "--json",
            "--output",
            "report.json",
            "manifests",
        ]
        .map(str::to_string);
        assert_eq!(
            parse_single_target(&args, "example", &["--output"], &["--json"]),
            Ok("manifests".to_string())
        );
    }

    #[test]
    fn single_target_parser_rejects_unknown_options_and_extra_targets() {
        let unknown = ["yamlr", "example", "--surprise", "manifests"].map(str::to_string);
        assert!(parse_single_target(&unknown, "example", &[], &[])
            .unwrap_err()
            .contains("Unsupported example option"));

        let multiple = ["yamlr", "example", "one", "two"].map(str::to_string);
        assert!(parse_single_target(&multiple, "example", &[], &[])
            .unwrap_err()
            .contains("only one target path"));
    }
}

pub fn get_flag_value(args: &[String], flag: &str) -> Option<String> {
    for i in 0..args.len() {
        if args[i] == flag && i + 1 < args.len() {
            return Some(args[i + 1].clone());
        }
        if args[i].starts_with(&format!("{}=", flag)) {
            return Some(args[i].split_at(flag.len() + 1).1.to_string());
        }
    }
    None
}

/// Parses one positional target path while allowing command options in any order.
///
/// `value_options` lists options that consume the following argument; boolean
/// options consume only themselves. Unknown options and extra positional values
/// are rejected so a command cannot silently operate on the default directory.
pub fn parse_single_target(
    args: &[String],
    command: &str,
    value_options: &[&str],
    boolean_options: &[&str],
) -> Result<String, String> {
    let mut target = None;
    let mut index = 2;
    while index < args.len() {
        let argument = args[index].as_str();
        if let Some((option, value)) = argument.split_once('=') {
            if value_options.contains(&option) {
                if value.is_empty() {
                    return Err(format!("{} requires a value for '{}'.", command, option));
                }
                index += 1;
                continue;
            }
        }
        if value_options.contains(&argument) {
            if index + 1 >= args.len() {
                return Err(format!("{} requires a value for '{}'.", command, argument));
            }
            index += 2;
            continue;
        }
        if boolean_options.contains(&argument) {
            index += 1;
            continue;
        }
        if argument.starts_with('-') && argument != "-" {
            return Err(format!("Unsupported {} option '{}'.", command, argument));
        }
        if target.replace(argument.to_string()).is_some() {
            return Err(format!("{} accepts only one target path.", command));
        }
        index += 1;
    }
    Ok(target.unwrap_or_else(|| ".".to_string()))
}
