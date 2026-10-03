//! In-memory Kustomize Directory Loader and Overlay Renderer.
//!
//! Why: Traverses local Kustomize overlay directories, resolves referenced base manifests
//! and resource files hermetically, and renders the composite multi-document stream.

use crate::parsers::kustomize::renderer::render_kustomization;
use std::fs;
use std::path::Path;

/// Reads and renders a Kustomize overlay directory into a combined multi-document YAML.
pub fn render_kustomize_directory(dir: &Path) -> Result<String, String> {
    let kustomization_names = ["kustomization.yaml", "kustomization.yml", "Kustomization"];
    let mut kustomization_path = None;
    for name in &kustomization_names {
        let p = dir.join(name);
        if p.is_file() {
            kustomization_path = Some(p);
            break;
        }
    }

    let kustomization_file = kustomization_path.ok_or_else(|| {
        format!(
            "No kustomization.yaml found in directory '{}'",
            dir.display()
        )
    })?;

    let kustomization_content = fs::read_to_string(&kustomization_file)
        .map_err(|e| format!("Failed to read {}: {}", kustomization_file.display(), e))?;

    let mut named_resources: Vec<(String, String)> = Vec::new();

    // Read resources in directory
    for entry in walkdir::WalkDir::new(dir) {
        let entry = entry.map_err(|error| {
            format!(
                "Failed to traverse Kustomize directory '{}': {}",
                dir.display(),
                error
            )
        })?;
        let p = entry.path();
        if p.is_file() && p != kustomization_file {
            if let Some(ext) = p.extension() {
                if ext == "yaml" || ext == "yml" {
                    let content = fs::read_to_string(p).map_err(|error| {
                        format!(
                            "Failed to read Kustomize resource '{}': {}",
                            p.display(),
                            error
                        )
                    })?;
                    let rel_name = p
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("resource.yaml")
                        .to_string();
                    named_resources.push((rel_name, content));
                }
            }
        }
    }

    let ref_slice: Vec<(&str, &str)> = named_resources
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();

    render_kustomization(&kustomization_content, &ref_slice)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_render_kustomize_directory() {
        let dir = tempdir().unwrap();
        let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namePrefix: test-
resources:
  - deploy.yaml
"#;
        let deploy = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 1
"#;
        fs::write(dir.path().join("kustomization.yaml"), kustomization).unwrap();
        fs::write(dir.path().join("deploy.yaml"), deploy).unwrap();

        let rendered = render_kustomize_directory(dir.path()).unwrap();
        assert!(rendered.contains("test-api"));
        assert!(rendered.contains("kind: Deployment"));
    }
}
