//! Heal Command Line Argument Parser.
//!
//! Why: Isolates CLI parsing logic from the healing orchestration engine to
//! guarantee strict modularity and prevent God Objects (< 500 lines).

use clap::{Arg, ArgAction, Command};

pub(crate) fn parse_heal_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    let command_name = if args
        .get(1)
        .is_some_and(|arg| arg.eq_ignore_ascii_case("fix"))
    {
        "fix"
    } else {
        "heal"
    };
    let mut command = Command::new(command_name)
        .disable_version_flag(true)
        .arg(Arg::new("target").value_name("PATH").num_args(0..=1))
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
        .arg(Arg::new("ingest-opa").long("ingest-opa").value_name("PATH"))
        .arg(
            Arg::new("ingest-kyverno")
                .long("ingest-kyverno")
                .value_name("PATH"),
        )
        .arg(
            Arg::new("apply")
                .long("apply")
                .short('a')
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("dry-run")
                .long("dry-run")
                .short('d')
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("generate-stubs")
                .long("generate-stubs")
                .visible_alias("create-stubs")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("otel")
                .long("otel")
                .visible_alias("export-metrics")
                .action(ArgAction::SetTrue),
        );
    for name in ["diff", "helm", "kustomize", "exit-zero", "summary", "verify-kubectl"] {
        command = command.arg(Arg::new(name).long(name).action(ArgAction::SetTrue));
    }
    crate::cli::parse_command_args(
        command.group(clap::ArgGroup::new("source-adapter").args(["helm", "kustomize"])),
        args,
    )
}
