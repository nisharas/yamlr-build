//! OwnerReference Extractor
//!
//! Why: Extracts controller and ownerReferences to distinguish user-managed root
//! workloads from controller-managed leaf pods/replicasets, preventing false alarms.

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
        let mut owner_kind = String::new();
        let mut owner_name = String::new();

        for s in shards {
            if s.key.eq_ignore_ascii_case("ownerReferences") {
                in_owner_refs = true;
                owner_indent = s.indent;
                continue;
            }
            if in_owner_refs {
                if s.indent <= owner_indent && !s.is_list_item && !s.key.is_empty() {
                    in_owner_refs = false;
                } else {
                    if s.key == "kind" {
                        if let Some(val) = &s.value {
                            owner_kind = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        }
                    } else if s.key == "name" {
                        if let Some(val) = &s.value {
                            owner_name = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        }
                    }
                    if !owner_kind.is_empty() && !owner_name.is_empty() {
                        let desc = format!("{}/{}", owner_kind, owner_name);
                        if !identity.owner_refs.contains(&desc) {
                            identity.owner_refs.push(desc);
                        }
                        if !identity.owner_refs.contains(&"MANAGED".to_string()) {
                            identity.owner_refs.push("MANAGED".to_string());
                        }
                        owner_kind.clear();
                        owner_name.clear();
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_owner_refs() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod-abcde\n  ownerReferences:\n  - apiVersion: apps/v1\n    kind: ReplicaSet\n    name: pod-abc";
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
