//! Missing Target Auto-Stub Generation Engine (Feature 8 of 15).
//!
//! Why: When manifests reference ConfigMaps, Secrets, PVCs, or ServiceAccounts that do
//! not exist in the repository, CI pipelines fail with unresolved reference errors.
//!
//! This module generates deterministic, safe, OpenAPI-compliant YAML stubs for missing
//! target resources, allowing pipelines and GitOps validators to pass without manual scaffolding.

use crate::models::{NativeIdentity, NativeTelemetry};
use crate::telemetry::native_record_healing_impact;
use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct MissingResourceTarget {
    pub kind: String,
    pub name: String,
    pub namespace: String,
}

/// Generates safe, valid Kubernetes YAML stub for a missing resource.
pub fn generate_stub_yaml(target: &MissingResourceTarget) -> String {
    match target.kind.as_str() {
        "ConfigMap" => format!(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: {}\n  namespace: {}\n  annotations:\n    yamlr.dev/generated-stub: \"true\"\n    yamlr.io/generated-stub: \"true\"\ndata:\n  placeholder: \"auto-generated-by-yamlr\"\n",
            target.name, target.namespace
        ),
        "Secret" => format!(
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: {}\n  namespace: {}\n  annotations:\n    yamlr.dev/generated-stub: \"true\"\n    yamlr.io/generated-stub: \"true\"\ntype: Opaque\nstringData:\n  placeholder: \"auto-generated-by-yamlr\"\n",
            target.name, target.namespace
        ),
        "PersistentVolumeClaim" => format!(
            "apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: {}\n  namespace: {}\n  annotations:\n    yamlr.dev/generated-stub: \"true\"\n    yamlr.io/generated-stub: \"true\"\nspec:\n  accessModes:\n    - ReadWriteOnce\n  resources:\n    requests:\n      storage: 1Gi\n",
            target.name, target.namespace
        ),
        "ServiceAccount" => format!(
            "apiVersion: v1\nkind: ServiceAccount\nmetadata:\n  name: {}\n  namespace: {}\n  annotations:\n    yamlr.dev/generated-stub: \"true\"\n    yamlr.io/generated-stub: \"true\"\n",
            target.name, target.namespace
        ),
        _ => format!(
            "apiVersion: v1\nkind: {}\nmetadata:\n  name: {}\n  namespace: {}\n  annotations:\n    yamlr.dev/generated-stub: \"true\"\n    yamlr.io/generated-stub: \"true\"\n",
            target.kind, target.name, target.namespace
        ),
    }
}

/// Primary Entrypoint: Identifies missing consumed targets across identities and generates stubs.
pub fn generate_stubs_for_missing_targets(
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> (Vec<String>, Vec<String>) {
    let mut generated_yamls = Vec::new();
    let mut changes = Vec::new();
    let mut existing_keys = HashSet::new();

    for id in identities {
        existing_keys.insert(format!("{}:{}:{}", id.kind, id.namespace, id.name));
    }

    let mut generated_keys = HashSet::new();

    for id in identities {
        // Check ConfigMap references
        for cm in &id.config_refs {
            let key = format!("ConfigMap:{}:{}", id.namespace, cm);
            if !existing_keys.contains(&key) && !generated_keys.contains(&key) {
                let target = MissingResourceTarget {
                    kind: "ConfigMap".to_string(),
                    name: cm.clone(),
                    namespace: id.namespace.clone(),
                };
                let yaml = generate_stub_yaml(&target);
                generated_yamls.push(yaml);
                generated_keys.insert(key);

                let msg = format!(
                    "Remediation [REL-005]: Generated safe placeholder stub for missing ConfigMap '{}/{}'.",
                    id.namespace, cm
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }

        // Check Secret references
        for sec in &id.secret_refs {
            let key = format!("Secret:{}:{}", id.namespace, sec);
            if !existing_keys.contains(&key) && !generated_keys.contains(&key) {
                let target = MissingResourceTarget {
                    kind: "Secret".to_string(),
                    name: sec.clone(),
                    namespace: id.namespace.clone(),
                };
                let yaml = generate_stub_yaml(&target);
                generated_yamls.push(yaml);
                generated_keys.insert(key);

                let msg = format!(
                    "Remediation [REL-005]: Generated safe placeholder stub for missing Secret '{}/{}'.",
                    id.namespace, sec
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }

        // Check PVC references
        for pvc in &id.volume_refs {
            let key = format!("PersistentVolumeClaim:{}:{}", id.namespace, pvc);
            if !existing_keys.contains(&key) && !generated_keys.contains(&key) {
                let target = MissingResourceTarget {
                    kind: "PersistentVolumeClaim".to_string(),
                    name: pvc.clone(),
                    namespace: id.namespace.clone(),
                };
                let yaml = generate_stub_yaml(&target);
                generated_yamls.push(yaml);
                generated_keys.insert(key);

                let msg = format!(
                    "Remediation [REL-005]: Generated safe placeholder stub for missing PVC '{}/{}'.",
                    id.namespace, pvc
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    (generated_yamls, changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_configmap_stub() {
        let target = MissingResourceTarget {
            kind: "ConfigMap".to_string(),
            name: "app-cfg".to_string(),
            namespace: "prod".to_string(),
        };
        let yaml = generate_stub_yaml(&target);
        assert!(yaml.contains("kind: ConfigMap"));
        assert!(yaml.contains("name: app-cfg"));
        assert!(yaml.contains("namespace: prod"));
        assert!(yaml.contains("yamlr.io/generated-stub"));
    }

    #[test]
    fn test_generate_secret_stub() {
        let target = MissingResourceTarget {
            kind: "Secret".to_string(),
            name: "db-auth".to_string(),
            namespace: "default".to_string(),
        };
        let yaml = generate_stub_yaml(&target);
        assert!(yaml.contains("kind: Secret"));
        assert!(yaml.contains("type: Opaque"));
        assert!(yaml.contains("stringData:"));
    }
}
