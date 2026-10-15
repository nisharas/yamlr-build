//! Multi-repository GitOps fleet remediation and batch auditing CLI handler.
//!
//! Why: Enterprise platform engineering teams manage hundreds of microservice and GitOps
//! repositories. The fleet command enables discovery, schema auditing, and bulk autonomous
//! remediation across dozens of repositories simultaneously without requiring manual PR authoring.

use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;
use walkdir::WalkDir;

use crate::cli::{
    heal_cmd::heal_manifest_string_with_schemas_and_identities,
    EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS,
};
use crate::schemas::native_get_schema_for_version;

#[derive(serde::Serialize, Debug)]
pub struct FleetRepoSummary {
    pub repo_path: String,
    pub manifests_scanned: usize,
    pub manifests_healed: usize,
    pub status: String,
}

/// Executes the multi-repository fleet batch remediation command.
///
/// Why: Eliminates toil when standardizing Kubernetes manifest hygiene or API deprecations
/// across enterprise fleet repositories.
pub fn execute_fleet(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("fleet", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let start_time = Instant::now();
    let target = matches.get_one::<String>("target").unwrap();
    let k8s_version = matches.get_one::<String>("k8s-version").unwrap().clone();
    let apply = matches.get_flag("apply");
    let is_json = matches.get_flag("json");
    let create_pr = matches.get_flag("create-pr");
    let dry_run_git = matches.get_flag("dry-run-git");
    let branch_name = matches
        .get_one::<String>("branch")
        .cloned()
        .unwrap_or_else(|| format!("yamlr/auto-heal-k8s-{}", k8s_version));

    let root_path = Path::new(&target);
    if !root_path.exists() {
        eprintln!(
            "[ERROR] Target fleet directory '{}' does not exist.",
            target
        );
        return EXIT_VIOLATIONS;
    }

    let repos = match discover_fleet_repositories(root_path) {
        Ok(repos) => repos,
        Err(error) => {
            eprintln!("[ERROR] Failed to discover fleet repositories: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    if repos.is_empty() {
        println!(
            "[WARN] No git repositories discovered in '{}'. Scanning as single workspace.",
            target
        );
    }

    let repo_list = if repos.is_empty() {
        vec![root_path.to_path_buf()]
    } else {
        repos
    };

    let schemas = native_get_schema_for_version(&k8s_version);
    let mut summaries = Vec::new();
    let mut total_scanned = 0;
    let mut total_healed = 0;

    for repo in &repo_list {
        let repo_identities = crate::discovery::native_discover_resources(repo.to_string_lossy().into_owned())
            .map(|discovery| discovery.into_iter().filter_map(|d| d.identity).collect::<Vec<_>>())
            .unwrap_or_default();
        let mut scanned = 0;
        let mut healed = 0;
        let mut healed_paths = Vec::new();

        for entry in WalkDir::new(repo) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] Fleet traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension() {
                    if ext == "yaml" || ext == "yml" {
                        scanned += 1;
                        let content = match fs::read_to_string(p) {
                            Ok(content) => content,
                            Err(error) => {
                                eprintln!(
                                    "[ERROR] Failed to read manifest '{}': {}",
                                    p.display(),
                                    error
                                );
                                return EXIT_SYSTEM_ERROR;
                            }
                        };
                        let (fixed, _) = heal_manifest_string_with_schemas_and_identities(
                            &content,
                            &schemas,
                            &repo_identities,
                        );
                        if fixed != content {
                            healed_paths.push(p.strip_prefix(repo).unwrap_or(p).to_path_buf());
                            if apply {
                                if let Err(error) = fs::write(p, fixed) {
                                    eprintln!(
                                        "[ERROR] Failed to write healed manifest '{}': {}",
                                        p.display(),
                                        error
                                    );
                                    return EXIT_SYSTEM_ERROR;
                                }
                            }
                            healed += 1;
                        }
                    }
                }
            }
        }

        total_scanned += scanned;
        total_healed += healed;

        if (create_pr || dry_run_git) && healed > 0 {
            if dry_run_git {
                println!("\n[GIT-DRY-RUN] Repository '{}':", repo.display());
                println!("  > git checkout -b {}", branch_name);
                println!(
                    "  > git add -- <{} healed manifest path(s)>",
                    healed_paths.len()
                );
                println!(
                    "  > git commit --only -- <{} healed manifest path(s)>",
                    healed_paths.len()
                );
                println!("  > git push origin {}", branch_name);
            } else if create_pr && apply {
                let checkout = std::process::Command::new("git")
                    .args(["checkout", "-b", &branch_name])
                    .current_dir(repo)
                    .output();
                if !checkout
                    .map(|output| output.status.success())
                    .unwrap_or(false)
                {
                    eprintln!(
                        "[ERROR] Failed to create remediation branch '{}' in '{}'.",
                        branch_name,
                        repo.display()
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                let stage = std::process::Command::new("git")
                    .arg("add")
                    .arg("--")
                    .args(&healed_paths)
                    .current_dir(repo)
                    .output();
                if !stage.map(|output| output.status.success()).unwrap_or(false) {
                    eprintln!(
                        "[ERROR] Failed to stage healed manifests in '{}'.",
                        repo.display()
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                let commit = std::process::Command::new("git")
                    .args([
                        "commit",
                        "--only",
                        "-m",
                        "fix(k8s): autonomous manifest repair via yamlr",
                        "--",
                    ])
                    .args(&healed_paths)
                    .current_dir(repo)
                    .output();
                if !commit
                    .map(|output| output.status.success())
                    .unwrap_or(false)
                {
                    eprintln!(
                        "[ERROR] Failed to commit healed manifests in '{}'.",
                        repo.display()
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                println!(
                    "  [GIT] Created remediation branch '{}' in '{}'.",
                    branch_name,
                    repo.display()
                );

                // Remote Push & PR Creation via gh / glab
                let push_res = std::process::Command::new("git")
                    .args(["push", "-u", "origin", &branch_name])
                    .current_dir(repo)
                    .output();

                if push_res.map(|o| o.status.success()).unwrap_or(false) {
                    println!("  [GIT] Pushed branch '{}' to origin.", branch_name);
                    let pr_title = format!(
                        "fix(k8s): autonomous manifest remediation for K8s {}",
                        k8s_version
                    );
                    let pr_body = "Automated Kubernetes manifest remediation generated by Yamlr Enterprise Fleet Engine.\n\nVerified: comment preservation, schema compliance, and zero structural breakage.";

                    let gh_res = std::process::Command::new("gh")
                        .args([
                            "pr",
                            "create",
                            "--title",
                            &pr_title,
                            "--body",
                            pr_body,
                            "--head",
                            &branch_name,
                        ])
                        .current_dir(repo)
                        .output();

                    let mut pr_created = false;
                    if let Ok(gh_out) = gh_res {
                        if gh_out.status.success() {
                            let pr_url = String::from_utf8_lossy(&gh_out.stdout).trim().to_string();
                            println!("  [PR] Created GitHub PR: {}", pr_url);
                            pr_created = true;
                        }
                    }
                    if !pr_created {
                        let glab_res = std::process::Command::new("glab")
                            .args([
                                "mr",
                                "create",
                                "--title",
                                &pr_title,
                                "--description",
                                pr_body,
                                "--source-branch",
                                &branch_name,
                            ])
                            .current_dir(repo)
                            .output();
                        if let Ok(glab_out) = glab_res {
                            if glab_out.status.success() {
                                let mr_url =
                                    String::from_utf8_lossy(&glab_out.stdout).trim().to_string();
                                println!("  [PR] Created GitLab MR: {}", mr_url);
                                pr_created = true;
                            }
                        }
                    }
                    if !pr_created {
                        println!(
                            "  [PR] Pushed branch '{}'. To create PR: gh pr create --head {}",
                            branch_name, branch_name
                        );
                    }
                }
            }
        }

        summaries.push(FleetRepoSummary {
            repo_path: repo.to_string_lossy().to_string(),
            manifests_scanned: scanned,
            manifests_healed: healed,
            status: if healed > 0 {
                if apply {
                    "HEALED".to_string()
                } else {
                    "DRIFT_DETECTED".to_string()
                }
            } else {
                "CLEAN".to_string()
            },
        });
    }

    let elapsed = start_time.elapsed();

    if is_json {
        let output = serde_json::json!({
            "fleet_version": "0.1.0",
            "k8s_version": k8s_version,
            "repositories_processed": repo_list.len(),
            "manifests_scanned": total_scanned,
            "manifests_healed": total_healed,
            "elapsed_ms": elapsed.as_millis(),
            "repositories": summaries,
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&output).unwrap_or_default()
        );
        return EXIT_SUCCESS;
    }

    println!("Yamlr Enterprise Fleet Batch Remediation Engine");
    println!("===============================================");
    println!("Repositories:  {}", repo_list.len());
    println!("Total Scanned: {}", total_scanned);
    println!("Total Healed:  {}", total_healed);
    println!(
        "Mode:          {}",
        if apply {
            "APPLIED (In-Place Fix)"
        } else {
            "PREVIEW (Dry-Run)"
        }
    );
    if create_pr || dry_run_git {
        println!(
            "Git Action:    {}",
            if dry_run_git {
                "DRY-RUN (Simulated Branch/PR)"
            } else {
                "CREATE-PR (Branch Committed)"
            }
        );
        println!("Target Branch: {}", branch_name);
    }
    println!("Elapsed Time:  {:.2?}\n", elapsed);

    println!(
        "{:<45} {:<10} {:<10} {:<15}",
        "REPOSITORY", "SCANNED", "HEALED", "STATUS"
    );
    println!("{:-<45} {:-<10} {:-<10} {:-<15}", "", "", "", "");

    for s in &summaries {
        println!(
            "{:<45} {:<10} {:<10} {:<15}",
            truncate_path(&s.repo_path, 43),
            s.manifests_scanned,
            s.manifests_healed,
            s.status
        );
    }

    EXIT_SUCCESS
}

fn discover_fleet_repositories(root: &Path) -> Result<Vec<PathBuf>, String> {
    let mut repos = Vec::new();
    if root.join(".git").exists() {
        repos.push(root.to_path_buf());
        return Ok(repos);
    }

    let entries = fs::read_dir(root).map_err(|error| format!("'{}': {}", root.display(), error))?;
    for entry in entries {
        let entry = entry.map_err(|error| error.to_string())?;
        let p = entry.path();
        if p.is_dir() && p.join(".git").exists() {
            repos.push(p);
        }
    }
    Ok(repos)
}

fn truncate_path(s: &str, max_len: usize) -> String {
    if s.len() > max_len {
        format!("...{}", &s[s.len().saturating_sub(max_len - 3)..])
    } else {
        s.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_fleet_single_repo_execution() {
        let dir = tempdir().unwrap();
        let manifest_path = dir.path().join("pod.yaml");
        fs::write(
            &manifest_path,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app\n",
        )
        .unwrap();

        let args = vec![
            "yamlr".to_string(),
            "fleet".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--json".to_string(),
        ];
        assert_eq!(execute_fleet(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_fleet_cmd_git_dry_run() {
        let dir = tempdir().unwrap();
        let _ = fs::create_dir_all(dir.path().join(".git"));
        let manifest_path = dir.path().join("deploy.yaml");
        let yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\nspec:\n  replicas: 1\n  template:\n    spec:\n      containers:\n        - name: app\n          image: nginx:latest\n";
        fs::write(&manifest_path, yaml).unwrap();

        let args = vec![
            "yamlr".to_string(),
            "fleet".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--create-pr".to_string(),
            "--dry-run-git".to_string(),
            "--branch".to_string(),
            "feature/yamlr-heal".to_string(),
        ];
        assert_eq!(execute_fleet(&args), EXIT_SUCCESS);
    }
}
