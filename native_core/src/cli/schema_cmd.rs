//! Native CRD schema distillation and schema listing CLI handler.

use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

use crate::cli::{
    parse_command_args, EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_USAGE, EXIT_VIOLATIONS,
};
use clap::{Arg, ArgAction, Command};

pub fn execute_schema(args: &[String]) -> i32 {
    let matches = match parse_schema_arguments(args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };

    match matches.subcommand() {
        Some(("ingest", submatches)) => {
            ingest_crds(submatches.get_one::<String>("target").unwrap())
        }
        Some(("fetch", submatches)) => {
            let version = submatches.get_one::<String>("version").unwrap();
            let offline = submatches.get_flag("offline");
            match crate::schemas::fetch_k8s_schema(version, offline) {
                Ok(path) => {
                    println!(
                        "[SUCCESS] Successfully cached schema for Kubernetes v{} -> {}",
                        version,
                        path.display()
                    );
                    EXIT_SUCCESS
                }
                Err(err) => {
                    eprintln!("[ERROR] {}", err);
                    EXIT_USAGE
                }
            }
        }
        Some(("list", _)) => list_schemas(),
        Some(("clean", _)) => clean_schemas(),
        _ => unreachable!("Clap enforces a supported schema subcommand"),
    }
}

fn get_schemas_dir() -> PathBuf {
    PathBuf::from(".yamlr").join("schemas")
}

fn ingest_crds(target: &str) -> i32 {
    let p = Path::new(target);
    let out_dir = get_schemas_dir();
    if let Err(error) = fs::create_dir_all(&out_dir) {
        eprintln!(
            "[ERROR] Failed to create schema directory '{}': {}",
            out_dir.display(),
            error
        );
        return EXIT_SYSTEM_ERROR;
    }

    let mut count = 0;
    if p.is_file() {
        count = match distill_crd_file(p, &out_dir) {
            Ok(count) => count,
            Err((code, error)) => {
                eprintln!("[ERROR] {}", error);
                return code;
            }
        };
    } else if p.is_dir() {
        for entry in WalkDir::new(p) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] CRD directory traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let fp = entry.path();
            if fp.is_file() {
                if let Some(ext) = fp.extension() {
                    if ext == "yaml" || ext == "yml" {
                        match distill_crd_file(fp, &out_dir) {
                            Ok(generated) => count += generated,
                            Err((code, error)) => {
                                eprintln!("[ERROR] {}", error);
                                return code;
                            }
                        }
                    }
                }
            }
        }
    } else {
        eprintln!("[ERROR] Path '{}' does not exist.", target);
        return EXIT_USAGE;
    }

    if count == 0 {
        eprintln!("[ERROR] No CRD schemas were generated from '{}'.", target);
        return EXIT_VIOLATIONS;
    }
    println!(
        "[SUCCESS] Ingested {} CRD schema(s) into {}",
        count,
        out_dir.display()
    );
    EXIT_SUCCESS
}

fn distill_crd_file(path: &Path, out_dir: &Path) -> Result<usize, (i32, String)> {
    let content = fs::read_to_string(path).map_err(|error| {
        (
            EXIT_SYSTEM_ERROR,
            format!("Failed to read CRD input '{}': {}", path.display(), error),
        )
    })?;

    let mut generated = 0;
    for doc in content.split("---") {
        let trimmed = doc.trim();
        if trimmed.is_empty() {
            continue;
        }
        let val = serde_yaml::from_str::<serde_json::Value>(trimmed).map_err(|error| {
            (
                EXIT_VIOLATIONS,
                format!("Invalid YAML in CRD input '{}': {}", path.display(), error),
            )
        })?;

        let kind = val.get("kind").and_then(|k| k.as_str()).unwrap_or("");
        if kind != "CustomResourceDefinition" {
            continue;
        }

        let crd_name = val
            .pointer("/spec/names/kind")
            .and_then(|k| k.as_str())
            .unwrap_or("CustomResource");
        let global_schema = val.pointer("/spec/validation/openAPIV3Schema");

        let mut version_list: Vec<(String, Option<&serde_json::Value>)> = Vec::new();
        if let Some(versions) = val.pointer("/spec/versions").and_then(|v| v.as_array()) {
            for v in versions {
                let v_name = v
                    .get("name")
                    .and_then(|n| n.as_str())
                    .unwrap_or("v1")
                    .to_string();
                let schema = v.pointer("/schema/openAPIV3Schema").or(global_schema);
                version_list.push((v_name, schema));
            }
        } else if let Some(legacy_version) = val.pointer("/spec/version").and_then(|v| v.as_str()) {
            version_list.push((legacy_version.to_string(), global_schema));
        }

        for (v_name, maybe_schema) in version_list {
            let filename = format!("{}_{}.json", crd_name.to_lowercase(), v_name);
            let out_path = out_dir.join(filename);

            let schema_content = if let Some(schema) = maybe_schema {
                match serde_json::to_string_pretty(schema) {
                    Ok(s) => s,
                    Err(e) => {
                        return Err((
                            EXIT_SYSTEM_ERROR,
                            format!(
                                "Failed to serialize schema for {} ({}): {}",
                                crd_name, v_name, e
                            ),
                        ));
                    }
                }
            } else {
                serde_json::json!({
                    "type": "object",
                    "properties": {
                        "apiVersion": { "type": "string" },
                        "kind": { "type": "string" },
                        "metadata": { "type": "object" },
                        "spec": { "type": "object" },
                        "status": { "type": "object" }
                    }
                })
                .to_string()
            };

            fs::write(&out_path, schema_content).map_err(|error| {
                (
                    EXIT_SYSTEM_ERROR,
                    format!(
                        "Failed to write distilled schema '{}': {}",
                        out_path.display(),
                        error
                    ),
                )
            })?;
            println!(
                "  [COMPILED] {} (v{}) -> {}",
                crd_name,
                v_name,
                out_path.display()
            );
            generated += 1;
        }
    }
    Ok(generated)
}

fn list_schemas() -> i32 {
    let local_dir = get_schemas_dir();
    let user_dir = match crate::schemas::get_user_schema_cache_dir() {
        Ok(dir) => dir,
        Err(error) => {
            eprintln!("[ERROR] {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };

    println!("=== Yamlr Cached Schemas ===");
    let mut total_found = 0;

    for (label, dir) in [("Local", &local_dir), ("Global User", &user_dir)] {
        let entries = match fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
            Err(error) => {
                eprintln!(
                    "[ERROR] Failed to list schema directory '{}': {}",
                    dir.display(),
                    error
                );
                return EXIT_SYSTEM_ERROR;
            }
        };
        println!("  [{}] {}", label, dir.display());
        for entry in entries {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!(
                        "[ERROR] Failed to read an entry in '{}': {}",
                        dir.display(),
                        error
                    );
                    return EXIT_SYSTEM_ERROR;
                }
            };
            if let Some(name) = entry.file_name().to_str() {
                if name.ends_with(".json") {
                    total_found += 1;
                    println!("    - {}", name);
                }
            }
        }
    }

    if total_found == 0 {
        println!("  (No custom or dynamically fetched schemas cached. Embedded baseline v1.21-v1.37 active.)");
    }
    EXIT_SUCCESS
}

fn clean_schemas() -> i32 {
    let out_dir = get_schemas_dir();
    if out_dir.exists() {
        if let Err(error) = fs::remove_dir_all(&out_dir) {
            eprintln!(
                "[ERROR] Failed to clear schema cache '{}': {}",
                out_dir.display(),
                error
            );
            return EXIT_SYSTEM_ERROR;
        }
        println!(
            "[SUCCESS] Cleared cached schemas from {}",
            out_dir.display()
        );
    } else {
        println!("[INFO] Schemas cache already clean.");
    }
    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schema_parser_rejects_unknown_options_extra_positionals_and_missing_values() {
        for args in [
            vec!["yamlr", "schema", "list", "--surprise"],
            vec!["yamlr", "schema", "ingest", "crd.yaml", "extra.yaml"],
            vec!["yamlr", "schema", "fetch"],
        ] {
            assert_eq!(
                execute_schema(&args.into_iter().map(str::to_string).collect::<Vec<_>>()),
                EXIT_USAGE
            );
        }
    }
}

pub(crate) fn parse_schema_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    let command = Command::new("schema")
        .subcommand_required(true)
        .subcommand(
            Command::new("ingest").arg(
                Arg::new("target")
                    .value_name("PATH")
                    .required(true)
                    .num_args(1),
            ),
        )
        .subcommand(
            Command::new("fetch")
                .arg(
                    Arg::new("version")
                        .value_name("VERSION")
                        .required(true)
                        .num_args(1),
                )
                .arg(
                    Arg::new("offline")
                        .long("offline")
                        .action(ArgAction::SetTrue),
                ),
        )
        .subcommand(Command::new("list"))
        .subcommand(Command::new("clean"));
    parse_command_args(command, args)
}
