//! Parser definitions for diagnostics, onboarding, and informational commands.
//! Dispatch validates these before licensing, network access, or daemon startup.

use clap::{Arg, ArgAction, ArgMatches, Command};

fn flag(name: &'static str, short: Option<char>) -> Arg {
    let arg = Arg::new(name).long(name).action(ArgAction::SetTrue);
    match short {
        Some(short) => arg.short(short),
        None => arg,
    }
}

fn target() -> Arg {
    Arg::new("target")
        .default_value(".")
        .value_parser(clap::builder::NonEmptyStringValueParser::new())
}

fn value(name: &'static str, short: Option<char>) -> Arg {
    let arg = Arg::new(name)
        .long(name)
        .value_parser(clap::builder::NonEmptyStringValueParser::new());
    match short {
        Some(short) => arg.short(short),
        None => arg,
    }
}

pub fn definition(name: &str) -> Option<Command> {
    let command = match name {
        "webhook" => Command::new("webhook")
            .about("Start the mutating admission HTTP listener; terminate TLS at a trusted proxy or provide certificates")
            .arg(
                Arg::new("port")
                    .long("port")
                    .default_value("8443")
                    .value_parser(clap::value_parser!(u16).range(1..)),
            )
            .arg(value("tls-cert", None))
            .arg(value("tls-key", None))
            .arg(flag("dry-run", None)),
        "rpc" | "service" | "daemon" => Command::new(match name {
            "service" => "service",
            "daemon" => "daemon",
            _ => "rpc",
        })
        .about("Inspect manifest RPC configuration; a network listener is not implemented")
        .arg(
            Arg::new("port")
                .long("port")
                .short('p')
                .default_value("50051")
                .value_parser(clap::value_parser!(u16).range(1..)),
        )
        .arg(flag("dry-run", None).visible_alias("test"))
        .arg(flag("serve", None).visible_alias("listen")),
        "subscribe" => Command::new("subscribe")
            .about("Show subscription status or activate a signed token")
            .arg(value("key", Some('k'))),
        "upgrade" => Command::new("upgrade").about("Show offline release upgrade instructions"),
        "auth" => Command::new("auth")
            .about("Inspect or activate local signed licenses")
            .subcommand(Command::new("status").about("Show local license status"))
            .subcommand(
                Command::new("activate")
                    .about("Verify and activate a signed token")
                    .arg(
                        Arg::new("token")
                            .value_parser(clap::builder::NonEmptyStringValueParser::new())
                            .conflicts_with("key"),
                    )
                    .arg(value("key", Some('k')))
                    .group(
                        clap::ArgGroup::new("license-token")
                            .args(["token", "key"])
                            .required(true),
                    ),
            ),
        "admin" => Command::new("admin")
            .about("Perform explicitly requested local maintenance")
            .subcommand_required(true)
            .subcommand(Command::new("cache-clear").about("Remove Yamlr's schema cache"))
            .subcommand(
                Command::new("journal-prune").about("Remove workspace remediation journals"),
            )
            .subcommand(Command::new("config-reset").about("Remove workspace configuration")),
        "vap" | "export-vap" => Command::new(if name == "export-vap" {
            "export-vap"
        } else {
            "vap"
        })
        .about("Export a policy bundle or inspect an input policy")
        .arg(Arg::new("mode").value_parser(["export", "ingest"]))
        .arg(
            Arg::new("file-target")
                .value_parser(clap::builder::NonEmptyStringValueParser::new())
                .conflicts_with("file"),
        )
        .arg(flag("ingest", None).conflicts_with("mode"))
        .arg(value("file", Some('f')))
        .arg(value("name", None).default_value("yamlr-workload-integrity"))
        .arg(value("output", Some('o'))),
        "sign" => Command::new("sign")
            .about("Preview or write HMAC manifest signatures")
            .arg(target())
            .arg(value("key", Some('k')))
            .arg(flag("write", Some('w')).visible_alias("in-place")),
        "verify" => Command::new("verify")
            .about("Verify HMAC manifest signatures")
            .arg(target())
            .arg(value("key", Some('k'))),
        "graph" => Command::new("graph")
            .about("Show resource dependency edges")
            .arg(target())
            .arg(value("focus", Some('f'))),
        "drift" => Command::new("drift")
            .about("Inspect topology and version drift")
            .arg(target()),
        "rollback" | "restore" => Command::new(if name == "restore" {
            "restore"
        } else {
            "rollback"
        })
        .about("List remediation transactions or restore one transaction")
        .arg(value("journal", Some('j')))
        .arg(flag("list", Some('l')).conflicts_with("transaction"))
        .arg(Arg::new("transaction").value_parser(clap::builder::NonEmptyStringValueParser::new())),
        "roi" | "impact" | "pulse" | "metrics" | "stats" => {
            let name = match name {
                "roi" => "roi",
                "impact" => "impact",
                "pulse" => "pulse",
                "stats" => "stats",
                _ => "metrics",
            };
            Command::new(name)
                .about("Report resource and engineering metrics")
                .arg(target())
                .arg(
                    Arg::new("output")
                        .long("output")
                        .short('o')
                        .default_value("text")
                        .value_parser(["text", "json"]),
                )
                .arg(flag("json", None).conflicts_with("output"))
        }
        "secure" => Command::new("secure")
            .about("Generate workload network policies")
            .arg(target())
            .arg(value("output", Some('o'))),
        "evidence" => Command::new("evidence")
            .about("Export local remediation evidence")
            .arg(target())
            .arg(value("output", Some('o')).default_value("yamlr-evidence.tar.gz"))
            .arg(flag("json", Some('j'))),
        "idp-export" => Command::new("idp-export")
            .about("Export a developer portal resource catalog")
            .arg(target())
            .arg(value("output", Some('o')))
            .arg(
                Arg::new("format")
                    .long("format")
                    .short('f')
                    .default_value("backstage")
                    .value_parser(["backstage", "port", "prometheus", "metrics", "otel"])
                    .ignore_case(true),
            ),
        "watch" => Command::new("watch")
            .about("Watch manifests and rescan changes")
            .arg(target()),
        "fleet" => Command::new("fleet")
            .about("Inspect or explicitly heal repositories")
            .arg(target())
            .arg(
                value("k8s-version", Some('k'))
                    .default_value("1.30")
                    .value_parser(crate::schemas::validate_k8s_version),
            )
            .arg(value("branch", None))
            .arg(flag("apply", Some('a')))
            .arg(flag("json", Some('j')))
            .arg(flag("create-pr", None))
            .arg(flag("dry-run-git", None)),
        "legal" => Command::new("legal").about("Show license terms and dependency notices"),
        "manual" | "man" => Command::new("manual").about("Show the built-in manual"),
        "migrate" => Command::new("migrate").about("Inspect workspace configuration migration"),
        "rules" => Command::new("rules").about("Show rule registry information"),
        "welcome" => Command::new("welcome").about("Show onboarding instructions"),
        "features" => Command::new("features").about("List healing stages"),
        "status" => Command::new("status").about("Inspect workspace status"),
        "demo" => Command::new("demo").about("Run the built-in manifest demonstration"),
        "lsp" => Command::new("lsp").about("Start the stdio language server"),
        "mcp" => Command::new("mcp")
            .about("Start the stdio model context server")
            .arg(flag("install-config", None))
            .arg(flag("config", None)),
        "install" => Command::new("install")
            .about("Show installation instructions or explicitly install Git hooks")
            .arg(flag("git-hook", Some('g'))),
        "doctor" | "diagnose" => Command::new(if name == "diagnose" {
            "diagnose"
        } else {
            "doctor"
        })
        .about("Check engine and environment health")
        .arg(flag("verbose", Some('v'))),
        "version" | "--version" | "-v" => Command::new("version")
            .about("Show binary version and architecture")
            .arg(flag("json", Some('j'))),
        "help" | "--help" | "-h" => Command::new("help").about("Show top-level usage"),
        "completion" => Command::new("completion")
            .about("Generate a shell completion script")
            .arg(Arg::new("shell").required(true).value_parser([
                "bash",
                "zsh",
                "fish",
                "powershell",
                "pwsh",
            ])),
        "guide" => Command::new("guide")
            .about("Show a technical concept guide")
            .arg(Arg::new("topic").value_parser(clap::builder::NonEmptyStringValueParser::new())),
        "init" => Command::new("init")
            .about("Initialize workspace configuration")
            .arg(
                Arg::new("target")
                    .default_value(".")
                    .value_parser(clap::builder::NonEmptyStringValueParser::new()),
            )
            .arg(flag("force", Some('f'))),
        "dna" => Command::new("dna")
            .about("Fingerprint manifest structure")
            .arg(
                Arg::new("target")
                    .default_value(".")
                    .value_parser(clap::builder::NonEmptyStringValueParser::new()),
            )
            .arg(flag("json", Some('j')))
            .arg(flag("full", None)),
        _ => return None,
    };
    Some(command)
}

pub fn parse(name: &str, args: &[String]) -> Result<ArgMatches, clap::Error> {
    let matches =
        super::parse_command_args(definition(name).expect("registered support command"), args)?;
    if matches!(name, "vap" | "export-vap") {
        let ingest = matches.get_flag("ingest")
            || matches
                .get_one::<String>("mode")
                .is_some_and(|mode| mode == "ingest");
        let has_file = matches.get_one::<String>("file-target").is_some()
            || matches.get_one::<String>("file").is_some();
        let explicit_name =
            matches.value_source("name") == Some(clap::parser::ValueSource::CommandLine);
        if (ingest && (!has_file || explicit_name || matches.get_one::<String>("output").is_some()))
            || (!ingest && has_file)
        {
            return Err(clap::Error::raw(clap::error::ErrorKind::ArgumentConflict,
                "Policy ingestion requires a file and cannot specify export name/output; export cannot specify an input file.\n"));
        }
    }
    Ok(matches)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn support_commands_reject_unknown_options_and_extra_positionals() {
        for name in [
            "legal", "manual", "man", "migrate", "rules", "welcome", "features", "status", "demo",
            "lsp", "mcp", "install", "doctor", "diagnose", "version", "help",
        ] {
            for tail in ["--unknown", "unexpected-path"] {
                let args = ["yamlr", name, tail].map(str::to_string);
                assert!(parse(name, &args).is_err(), "{name} accepted {tail}");
            }
        }
    }

    #[test]
    fn flags_are_not_read_from_literal_target_names() {
        let args = ["yamlr", "init", "--", "--force"].map(str::to_string);
        let matches = parse("init", &args).unwrap();
        assert!(!matches.get_flag("force"));
        assert_eq!(matches.get_one::<String>("target").unwrap(), "--force");
        let args = ["yamlr", "dna", "--", "--json"].map(str::to_string);
        assert!(!parse("dna", &args).unwrap().get_flag("json"));
    }

    #[test]
    fn duplicate_boolean_aliases_and_extra_targets_are_errors() {
        for args in [
            vec!["yamlr", "install", "-g", "--git-hook"],
            vec!["yamlr", "version", "-j", "--json"],
            vec!["yamlr", "init", "-f", "--force"],
            vec!["yamlr", "dna", "one", "two"],
            vec!["yamlr", "completion", "bash", "zsh"],
        ] {
            let args: Vec<String> = args.into_iter().map(str::to_string).collect();
            assert!(parse(&args[1], &args).is_err());
        }
    }

    #[test]
    fn operational_targets_and_values_come_from_the_parser() {
        let args = ["yamlr", "sign", "-kfixture", "--", "--write"].map(str::to_string);
        let parsed = parse("sign", &args).unwrap();
        assert_eq!(parsed.get_one::<String>("target").unwrap(), "--write");
        assert_eq!(parsed.get_one::<String>("key").unwrap(), "fixture");
        assert!(!parsed.get_flag("write"));
        let args = ["yamlr", "fleet", "--", "--apply"].map(str::to_string);
        assert!(!parse("fleet", &args).unwrap().get_flag("apply"));
        let args = ["yamlr", "rollback", "--", "--list"].map(str::to_string);
        let parsed = parse("rollback", &args).unwrap();
        assert_eq!(parsed.get_one::<String>("transaction").unwrap(), "--list");
        assert!(!parsed.get_flag("list"));
    }

    #[test]
    fn invalid_admin_arguments_cannot_reset_configuration() {
        let args = ["yamlr", "admin", "config-reset", "--unknown"].map(str::to_string);
        assert!(parse("admin", &args).is_err());
    }

    #[test]
    fn policy_modes_reject_ambiguous_export_and_ingest_options() {
        for tail in [
            vec!["ingest"],
            vec!["export", "input.yaml"],
            vec!["ingest", "input.yaml", "--name=x"],
            vec!["ingest", "input.yaml", "--output=x"],
        ] {
            let args: Vec<String> = ["yamlr", "vap"]
                .into_iter()
                .chain(tail)
                .map(str::to_string)
                .collect();
            assert!(parse("vap", &args).is_err());
        }
        let args = ["yamlr", "vap", "--ingest", "--file=input.yaml"].map(str::to_string);
        assert!(parse("vap", &args).is_ok());
    }
}
