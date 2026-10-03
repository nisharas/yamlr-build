//! Path-based shard lookup and multi-document chunk segmenter.
//!
//! Why: Enables fast dot-path traversal through flattened YAML shards
//! without constructing the entire semantic AST tree. Strictly < 500 lines.

use crate::models::NativeShard;

/// Finds the shard index corresponding to a dot-delimited path (e.g. `metadata.name`).
pub fn native_find_shard_by_path(shards: &[NativeShard], path: &str) -> Option<usize> {
    if shards.is_empty() {
        return None;
    }
    let min_indent = shards.iter().map(|s| s.indent).min().unwrap_or(0);
    let mut stack: Vec<(usize, String)> = Vec::new();

    for (i, s) in shards.iter().enumerate() {
        while !stack.is_empty() && stack.last().unwrap().0 >= s.indent {
            stack.pop();
        }

        let segment = if s.is_list_item {
            format!("[0].{}", s.key)
        } else {
            s.key.clone()
        };

        let is_new_list_scope =
            s.is_list_item && (stack.is_empty() || !stack.last().unwrap().1.ends_with(".[0]"));

        let parent_path = stack.last().map(|(_, p)| p.as_str()).unwrap_or("");
        let current_full_path = if parent_path.is_empty() {
            segment
        } else {
            format!("{}.{}", parent_path, segment)
        };

        if current_full_path == path || (s.key == path && s.indent == min_indent) {
            return Some(i);
        }

        if s.value.is_none() || s.is_block || is_new_list_scope {
            stack.push((s.indent, current_full_path.clone()));
        }
    }
    None
}

/// Splits multi-document shards into discrete document chunks separated by `---`.
pub fn native_shard_doc_chunks(shards: &[NativeShard]) -> Vec<Vec<NativeShard>> {
    let mut docs = Vec::new();
    let mut current_doc = Vec::new();

    for shard in shards {
        if shard.is_doc_boundary {
            if !current_doc.is_empty() {
                docs.push(current_doc);
                current_doc = Vec::new();
            }
        } else {
            current_doc.push(shard.clone());
        }
    }

    if !current_doc.is_empty() {
        docs.push(current_doc);
    }

    docs
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;

    #[test]
    fn test_find_shard_by_path() {
        let yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test-pod\n";
        let shards = native_shard(yaml);
        let idx = native_find_shard_by_path(&shards, "metadata.name");
        assert!(idx.is_some());
        assert_eq!(shards[idx.unwrap()].value.as_deref(), Some("test-pod"));
    }

    #[test]
    fn test_shard_doc_chunks_split() {
        let yaml = "apiVersion: v1\nkind: Pod\n---\napiVersion: v1\nkind: Service\n";
        let shards = native_shard(yaml);
        let docs = native_shard_doc_chunks(&shards);
        assert_eq!(docs.len(), 2);
    }
}
