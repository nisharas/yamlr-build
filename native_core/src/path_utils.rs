//! Path Sanitization and Normalization Utilities.
//!
//! Why: Windows file paths often contain extended-length UNC prefixes (`\\?\` or `\\?\UNC\`),
//! which confuse terminal users, SARIF artifact locations, and JSON journal logs.
//! This module provides deterministic, cross-platform path normalization.

use std::path::{Component, Path};

/// Strips Windows extended-length prefix (`\\?\` and `\\?\UNC\`) and normalizes path separators.
pub fn normalize_display_path<P: AsRef<Path>>(path: P) -> String {
    let s = path.as_ref().to_string_lossy();
    let stripped = if let Some(unc) = s.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{}", unc)
    } else if let Some(normal) = s.strip_prefix(r"\\?\") {
        normal.to_string()
    } else {
        s.into_owned()
    };

    // Normalize forward slashes for unified reporting across POSIX and Windows
    stripped.replace('\\', "/")
}

/// Normalizes and relativizes a file path to the workspace root for GitHub Code Scanning / SARIF compatibility.
pub fn relativize_to_workspace<P: AsRef<Path>>(path: P, workspace_root: Option<&Path>) -> String {
    let norm = normalize_display_path(&path);
    let ws_root = match workspace_root {
        Some(w) => normalize_display_path(w),
        None => {
            if let Ok(cwd) = std::env::current_dir() {
                normalize_display_path(cwd)
            } else {
                String::new()
            }
        }
    };

    let relative = if ws_root.is_empty() {
        None
    } else {
        Path::new(&norm).strip_prefix(Path::new(&ws_root)).ok()
    };
    let mut rel = relative
        .filter(|path| {
            !path
                .components()
                .any(|component| component == Component::ParentDir)
        })
        .map(normalize_display_path)
        .unwrap_or(norm);

    if rel.starts_with("./") {
        rel = rel[2..].to_string();
    }

    rel
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_unc_path() {
        assert_eq!(
            normalize_display_path(r"\\?\C:\Users\Yamlr\manifest.yaml"),
            "C:/Users/Yamlr/manifest.yaml"
        );
        assert_eq!(
            normalize_display_path(r"\\?\UNC\server\share\manifest.yaml"),
            "//server/share/manifest.yaml"
        );
        assert_eq!(
            normalize_display_path("relative/path/to/deploy.yaml"),
            "relative/path/to/deploy.yaml"
        );
    }

    #[test]
    fn test_relativize_to_workspace() {
        let ws = Path::new("D:/project/repo");
        let target = Path::new("D:/project/repo/k8s/deploy.yaml");
        assert_eq!(relativize_to_workspace(target, Some(ws)), "k8s/deploy.yaml");

        let rel_target = Path::new("./deploy.yaml");
        assert_eq!(relativize_to_workspace(rel_target, Some(ws)), "deploy.yaml");
    }

    #[test]
    fn test_sibling_directory_is_not_treated_as_inside_workspace() {
        let ws = Path::new("D:/project/repo");
        let sibling = Path::new("D:/project/repository/secrets.yaml");

        assert_eq!(
            relativize_to_workspace(sibling, Some(ws)),
            "D:/project/repository/secrets.yaml"
        );
    }

    #[test]
    fn different_windows_drives_are_not_relativized_into_the_workspace() {
        let ws = Path::new(r"D:\project\repo");
        let target = Path::new(r"E:\project\repo\manifest.yaml");

        assert_eq!(
            relativize_to_workspace(target, Some(ws)),
            "E:/project/repo/manifest.yaml"
        );
    }

    #[test]
    fn unc_paths_are_relativized_by_components_and_server_share() {
        let ws = Path::new(r"\\server\share\repo");
        let inside = Path::new(r"\\server\share\repo\charts\pod.yaml");
        let sibling = Path::new(r"\\server\share\repository\pod.yaml");
        let other_share = Path::new(r"\\server\other-share\repo\pod.yaml");

        assert_eq!(relativize_to_workspace(inside, Some(ws)), "charts/pod.yaml");
        assert_eq!(
            relativize_to_workspace(sibling, Some(ws)),
            "//server/share/repository/pod.yaml"
        );
        assert_eq!(
            relativize_to_workspace(other_share, Some(ws)),
            "//server/other-share/repo/pod.yaml"
        );
    }

    #[test]
    fn test_parent_traversal_is_not_returned_as_workspace_relative() {
        let ws = Path::new("D:/project/repo");
        let traversal = Path::new("D:/project/repo/../outside/file.yaml");

        assert_eq!(
            relativize_to_workspace(traversal, Some(ws)),
            "D:/project/repo/../outside/file.yaml"
        );
    }
}
