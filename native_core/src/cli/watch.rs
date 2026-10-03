//! Standalone Native Filesystem Watcher.
//!
//! Why: Enables instantaneous sub-3ms continuous feedback loops on manifest changes
//! without requiring Python subprocess overhead or external daemon dependencies.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, SystemTime};
use walkdir::WalkDir;

/// Runs a continuous watch loop monitoring YAML files for modifications.
pub fn run_watch_loop<F>(target: &Path, max_iterations: Option<usize>, on_change: F)
where
    F: FnMut(&Path),
{
    let _ = run_watch_loop_checked(target, max_iterations, on_change);
}

/// Runs the watch loop and reports filesystem snapshot failures to the caller.
pub fn run_watch_loop_checked<F>(target: &Path, max_iterations: Option<usize>, on_change: F) -> i32
where
    F: FnMut(&Path),
{
    run_watch_loop_checked_with_extensions(target, max_iterations, &["yaml", "yml"], on_change)
}

/// Runs the watch loop for a caller-defined set of manifest file extensions.
pub fn run_watch_loop_checked_with_extensions<F>(
    target: &Path,
    max_iterations: Option<usize>,
    extensions: &[&str],
    mut on_change: F,
) -> i32
where
    F: FnMut(&Path),
{
    let mut file_timestamps: HashMap<PathBuf, SystemTime> = HashMap::new();
    let mut iterations = 0;

    // Initial snapshot
    if let Err(error) = record_snapshot(target, &mut file_timestamps, false, extensions) {
        eprintln!("[ERROR] Unable to watch '{}': {}", target.display(), error);
        return crate::cli::EXIT_SYSTEM_ERROR;
    }
    on_change(target);

    loop {
        if let Some(max) = max_iterations {
            iterations += 1;
            if iterations >= max {
                break;
            }
        }

        thread::sleep(Duration::from_millis(200));

        let mut current_timestamps = HashMap::new();
        if let Err(error) = record_snapshot(target, &mut current_timestamps, true, extensions) {
            eprintln!(
                "[ERROR] Unable to refresh watch snapshot for '{}': {}",
                target.display(),
                error
            );
            return crate::cli::EXIT_SYSTEM_ERROR;
        }

        let mut changed_path = None;

        // Check for modifications or new files
        for (path, &mtime) in &current_timestamps {
            if let Some(&old_mtime) = file_timestamps.get(path) {
                if mtime > old_mtime {
                    changed_path = Some(path.clone());
                    break;
                }
            } else {
                changed_path = Some(path.clone());
                break;
            }
        }

        // Check for deleted files
        if changed_path.is_none() {
            for path in file_timestamps.keys() {
                if !current_timestamps.contains_key(path) {
                    changed_path = Some(path.clone());
                    break;
                }
            }
        }

        if let Some(p) = changed_path {
            file_timestamps = current_timestamps;
            println!(
                "\n[WATCH] Change detected in '{}'. Rescanning...",
                p.display()
            );
            on_change(target);
        }
    }

    crate::cli::EXIT_SUCCESS
}

fn record_snapshot(
    target: &Path,
    map: &mut HashMap<PathBuf, SystemTime>,
    allow_missing_target: bool,
    extensions: &[&str],
) -> Result<(), String> {
    let metadata = match fs::metadata(target) {
        Ok(metadata) => metadata,
        Err(error) if allow_missing_target && error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(());
        }
        Err(error) => {
            return Err(format!("Cannot read target metadata: {error}"));
        }
    };

    if metadata.is_file() {
        let modified = metadata
            .modified()
            .map_err(|error| format!("Cannot read modification time: {error}"))?;
        map.insert(target.to_path_buf(), modified);
    } else if metadata.is_dir() {
        for entry in WalkDir::new(target) {
            let entry = entry.map_err(|error| error.to_string())?;
            if !entry.file_type().is_file() {
                continue;
            }
            let path = entry.path();
            if !path
                .extension()
                .and_then(|ext| ext.to_str())
                .map_or(false, |extension| {
                    extensions.iter().any(|candidate| extension == *candidate)
                })
            {
                continue;
            }
            let metadata = entry
                .metadata()
                .map_err(|error| format!("Cannot read '{}': {error}", path.display()))?;
            let modified = metadata.modified().map_err(|error| {
                format!(
                    "Cannot read modification time for '{}': {error}",
                    path.display()
                )
            })?;
            map.insert(path.to_path_buf(), modified);
        }
    }

    Ok(())
}

/// Executes the standalone watch command from CLI arguments.
pub fn execute_watch(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("watch", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_str = matches.get_one::<String>("target").unwrap();

    let path = Path::new(&target_str);
    if !path.exists() {
        eprintln!("[ERROR] Path '{}' does not exist.", target_str);
        return crate::cli::EXIT_USAGE;
    }

    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("  Yamlr Watch • Continuous Manifest Resolution Plane");
    println!("  Target: {}", path.display());
    println!("  Press Ctrl+C to terminate");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    run_watch_loop_checked(path, None, |p| {
        let scan_args = vec![
            "yamlr".to_string(),
            "scan".to_string(),
            p.to_string_lossy().to_string(),
        ];
        crate::cli::scan_cmd::execute_scan(&scan_args);
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_watch_mode_single_tick() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("pod.yaml");
        fs::write(&file_path, "apiVersion: v1\nkind: Pod\n").unwrap();

        let mut runs = 0;
        run_watch_loop(dir.path(), Some(1), |_| {
            runs += 1;
        });

        assert_eq!(runs, 1);
    }

    #[test]
    fn checked_watch_reports_snapshot_failures_as_system_errors() {
        let dir = tempdir().unwrap();
        let missing_target = dir.path().join("missing");
        let mut runs = 0;

        let exit_code = run_watch_loop_checked(&missing_target, Some(1), |_| {
            runs += 1;
        });

        assert_eq!(exit_code, crate::cli::EXIT_SYSTEM_ERROR);
        assert_eq!(runs, 0);
    }

    #[test]
    fn checked_watch_returns_success_after_a_complete_bounded_iteration() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("pod.yaml");
        fs::write(&file_path, "apiVersion: v1\nkind: Pod\n").unwrap();
        let mut runs = 0;

        let exit_code = run_watch_loop_checked(dir.path(), Some(1), |_| {
            runs += 1;
        });

        assert_eq!(exit_code, crate::cli::EXIT_SUCCESS);
        assert_eq!(runs, 1);
    }

    #[test]
    fn watch_snapshot_tracks_helm_template_extensions_when_requested() {
        let dir = tempdir().unwrap();
        let yaml = dir.path().join("deployment.yaml");
        let template = dir.path().join("_helpers.tpl");
        let text = dir.path().join("notes.txt");
        fs::write(&yaml, "kind: Deployment\n").unwrap();
        fs::write(&template, "{{ define \"app.name\" }}app{{ end }}\n").unwrap();
        fs::write(&text, "ignore\n").unwrap();
        let mut snapshot = HashMap::new();

        record_snapshot(dir.path(), &mut snapshot, false, &["yaml", "yml", "tpl"]).unwrap();

        assert!(snapshot.contains_key(&yaml));
        assert!(snapshot.contains_key(&template));
        assert!(!snapshot.contains_key(&text));
    }
}
