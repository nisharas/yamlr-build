//! Argument contract definitions, validation, and normalization for native scan CLI.

use clap::{Arg, ArgAction, Command};

pub fn scan_command() -> Command {
    Command::new("scan")
        .disable_version_flag(true)
        .arg(Arg::new("target").value_name("PATH").num_args(0..=1))
        .arg(Arg::new("oci-layer").long("oci-layer").value_name("PATH"))
        .arg(
            Arg::new("k8s-version")
                .long("k8s-version")
                .visible_alias("kube-version")
                .short('k')
                .value_name("VERSION")
                .value_parser(crate::schemas::validate_k8s_version),
        )
        .arg(
            Arg::new("output")
                .long("output")
                .short('o')
                .value_name("FORMAT")
                .value_parser(["text", "json", "sarif"])
                .ignore_case(true),
        )
        .arg(
            Arg::new("output-file")
                .long("output-file")
                .short('f')
                .value_name("PATH"),
        )
        .arg(
            Arg::new("fail-on")
                .long("fail-on")
                .value_name("SEVERITY")
                .value_parser(crate::cli::parse_severity_threshold),
        )
        .arg(Arg::new("crd").long("crd").value_name("PATH"))
        .arg(
            Arg::new("json")
                .long("json")
                .short('j')
                .action(ArgAction::SetTrue),
        )
        .arg(Arg::new("sarif").long("sarif").action(ArgAction::SetTrue))
        .arg(
            Arg::new("quiet")
                .long("quiet")
                .short('q')
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("watch")
                .long("watch")
                .short('w')
                .action(ArgAction::SetTrue),
        )
        .arg(Arg::new("helm").long("helm").action(ArgAction::SetTrue))
        .arg(
            Arg::new("kustomize")
                .long("kustomize")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("exit-zero")
                .long("exit-zero")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("push-telemetry")
                .long("push-telemetry")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("no-telemetry")
                .long("no-telemetry")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("disable-telemetry")
                .long("disable-telemetry")
                .action(ArgAction::SetTrue),
        )
        .arg(Arg::new("otel").long("otel").action(ArgAction::SetTrue))
        .arg(
            Arg::new("export-metrics")
                .long("export-metrics")
                .action(ArgAction::SetTrue),
        )
}

pub(crate) fn parse_scan_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    crate::cli::parse_command_args(
        scan_command()
            .group(clap::ArgGroup::new("report-format").args(["output", "json", "sarif"]))
            .group(clap::ArgGroup::new("source-adapter").args(["helm", "kustomize", "oci-layer"])),
        args,
    )
}

pub(crate) fn normalize_scan_options(parsed: &clap::ArgMatches) -> Vec<String> {
    let mut args = vec!["yamlr".into(), "scan".into()];
    for argument in scan_command().get_arguments() {
        let Some(long) = argument.get_long() else {
            continue;
        };
        let id = argument.get_id().as_str();
        match argument.get_action() {
            ArgAction::SetTrue if parsed.get_flag(id) => args.push(format!("--{long}")),
            ArgAction::Set => {
                if let Some(value) = parsed.get_one::<String>(id) {
                    args.push(format!("--{long}"));
                    args.push(value.clone());
                }
            }
            _ => {}
        }
    }
    args
}

#[cfg(test)]
pub(crate) fn validate_scan_arguments(args: &[String]) -> Result<(), String> {
    parse_scan_arguments(args)
        .map(|_| ())
        .map_err(|error| error.to_string())
}
