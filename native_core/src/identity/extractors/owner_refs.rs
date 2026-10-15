//! OwnerReference Extractor
//!
//! Why: Extracts controller and ownerReferences to distinguish user-managed root
//! workloads from controller-managed leaf pods/replicasets, preventing false alarms.
//! Handles arbitrary key ordering within ownerReferences list items.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeShard};

pub struct OwnerRefExtractor;

impl NativeMetadataExtractor for OwnerRefExtractor {
    fn name(&self) -> &'static str {
        "OwnerRefExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let mut in_owner_refs = false;
        let mut owner_indent = 0;
        let mut owner_kind: Option<String> = None;
        let mut owner_name: Option<String> = None;

        let flush = |kind: &mut Option<String>, name: &mut Option<String>, id: &mut NativeIdentity| {
            if let (Some(k), Some(n)) = (kind.take(), name.take()) {
                if !k.is_empty() && !n.is_empty() {
                    let desc = format!("{}/{}", k, n);
                    if !id.owner_refs.contains(&desc) {
                        id.owner_refs.push(desc);
                    }
                    if !id.owner_refs.contains(&"MANAGED".to_string()) {
                        id.owner_refs.push("MANAGED".to_string());
                    }
                }
            }
            *kind = None;
            *name = None;
        };

        for s in shards {
            if s.key.eq_ignore_ascii_case("ownerReferences") && s.value.is_none() {
                flush(&mut owner_kind, &mut owner_name, identity);
                in_owner_refs = true;
                owner_indent = s.indent;
                continue;
            }

            if in_owner_refs {
                if s.indent <= owner_indent && !s.is_list_item && !s.key.is_empty() {
                    flush(&mut owner_kind, &mut owner_name, identity);
                    in_owner_refs = false;
                    continue;
                }

                if s.is_list_item {
                    flush(&mut owner_kind, &mut owner_name, identity);
                }

                if s.key.eq_ignore_ascii_case("kind") {
                    if let Some(val) = &s.value {
                        owner_kind = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                } else if s.key.eq_ignore_ascii_case("name") {
                    if let Some(val) = &s.value {
                        owner_name = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                }
            }
        }
        flush(&mut owner_kind, &mut owner_name, identity);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_owner_refs_arbitrary_key_ordering() {
        // Name before kind, and uid before name
        let raw = r#"
apiVersion: v1
kind: Pod
metadata:
  name: pod-abcde
  ownerReferences:
  - name: pod-abc
    controller: true
    kind: ReplicaSet
"#;
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod-abcde".to_string(),
            ..Default::default()
        };
        OwnerRefExtractor.extract(&shards, &mut id);
        assert!(id.owner_refs.contains(&"ReplicaSet/pod-abc".to_string()));
        assert!(id.owner_refs.contains(&"MANAGED".to_string()));
    }
}
