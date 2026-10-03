//! Directory traversal helpers for manifest scanning.

use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug, PartialEq, Eq)]
pub(super) enum ScanWalkError {
    Traversal(String),
    Visit(super::scan_input::ScanError),
}

impl ScanWalkError {
    pub(super) fn exit_code(&self) -> i32 {
        match self {
            Self::Traversal(_) => crate::cli::EXIT_SYSTEM_ERROR,
            Self::Visit(error) => error.exit_code(),
        }
    }
}

impl std::fmt::Display for ScanWalkError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Traversal(message) => formatter.write_str(message),
            Self::Visit(error) => write!(formatter, "{error}"),
        }
    }
}

pub(super) fn visit_matching_files<F>(
    root: &Path,
    extensions: &[&str],
    mut visit: F,
) -> Result<(), ScanWalkError>
where
    F: FnMut(&Path) -> Result<(), super::scan_input::ScanError>,
{
    for entry in WalkDir::new(root) {
        let entry = entry.map_err(|error| ScanWalkError::Traversal(error.to_string()))?;
        if !entry.file_type().is_file() {
            continue;
        }

        let path = entry.path();
        if path.extension().map_or(false, |extension| {
            extensions.iter().any(|candidate| extension == *candidate)
        }) {
            visit(path).map_err(ScanWalkError::Visit)?;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn traversal_error_is_returned_to_the_caller() {
        let dir = tempdir().unwrap();
        let missing_root = dir.path().join("missing");

        let error = visit_matching_files(&missing_root, &["yaml", "yml"], |_| Ok(())).unwrap_err();

        assert!(error.to_string().contains("missing"));
    }

    #[test]
    fn visits_only_files_with_requested_extensions() {
        let dir = tempdir().unwrap();
        let yaml = dir.path().join("manifest.yaml");
        let text = dir.path().join("notes.txt");
        fs::write(&yaml, "kind: Pod\n").unwrap();
        fs::write(&text, "skip\n").unwrap();
        let mut visited = Vec::new();

        visit_matching_files(dir.path(), &["yaml", "yml"], |path| {
            visited.push(path.file_name().unwrap().to_owned());
            Ok(())
        })
        .unwrap();

        assert_eq!(visited, vec![yaml.file_name().unwrap().to_owned()]);
    }

    #[test]
    fn traversal_includes_hidden_and_vendor_directories_without_implicit_exclusions() {
        let dir = tempdir().unwrap();
        fs::create_dir_all(dir.path().join(".hidden/vendor")).unwrap();
        let yaml = dir.path().join(".hidden/vendor/manifest.yaml");
        fs::write(&yaml, "kind: Pod\n").unwrap();
        let mut visited = Vec::new();
        visit_matching_files(dir.path(), &["yaml"], |path| {
            visited.push(path.to_path_buf());
            Ok(())
        })
        .unwrap();
        assert_eq!(visited, vec![yaml]);
    }

    #[cfg(unix)]
    #[test]
    fn recursive_traversal_skips_file_and_directory_symlinks() {
        use std::os::unix::fs::symlink;
        let root = tempdir().unwrap();
        let external = tempdir().unwrap();
        let yaml = external.path().join("external.yaml");
        fs::write(&yaml, "kind: Pod\n").unwrap();
        symlink(&yaml, root.path().join("linked.yaml")).unwrap();
        symlink(external.path(), root.path().join("linked-directory")).unwrap();
        let mut visited = Vec::new();
        visit_matching_files(root.path(), &["yaml"], |path| {
            visited.push(path.to_path_buf());
            Ok(())
        })
        .unwrap();
        assert!(visited.is_empty());
    }

    #[test]
    fn visitor_error_stops_traversal_and_reaches_the_caller() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("manifest.yaml"), "kind: Pod\n").unwrap();

        let error = visit_matching_files(dir.path(), &["yaml"], |_| {
            Err(crate::cli::scan_cmd::scan_input::ScanError::Input(
                "manifest invalid".to_string(),
            ))
        })
        .unwrap_err();

        assert_eq!(error.to_string(), "manifest invalid");
    }

    #[test]
    fn traversal_failures_use_system_error_and_visit_failures_keep_scan_error() {
        assert_eq!(
            ScanWalkError::Traversal("directory unavailable".to_string()).exit_code(),
            crate::cli::EXIT_SYSTEM_ERROR
        );
        assert_eq!(
            ScanWalkError::Visit(crate::cli::scan_cmd::scan_input::ScanError::Input(
                "manifest invalid".to_string()
            ))
            .exit_code(),
            2
        );
        assert_eq!(
            ScanWalkError::Visit(crate::cli::scan_cmd::scan_input::ScanError::System(
                "read failed".to_string()
            ))
            .exit_code(),
            crate::cli::EXIT_SYSTEM_ERROR
        );
    }
}
