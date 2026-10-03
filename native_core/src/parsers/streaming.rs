//! Streaming Multi-Document Lexer Module
//!
//! Why: In large multi-document manifests (e.g., Helm release dumps, CRD bundles,
//! monolithic cluster manifests exceeding 50MB+), eager full-manifest sharding
//! allocates millions of AST shards simultaneously in heap memory.
//! `NativeDocumentSliceStream` exposes borrowed document slices one at a time,
//! avoiding a separate text-buffer allocation for each document. Downstream
//! tokenization and AST construction still create owned shard data, so the
//! complete parsing pipeline is not zero-copy.

use crate::models::NativeShard;
use crate::sharder::native_shard;

/// Iterator yielding borrowed YAML document slices from raw input without copying document text.
///
/// Why: Allows scanning and preliminary inspection of multi-document manifests
/// without allocating a separate text buffer for each document.
pub struct NativeDocumentSliceStream<'a> {
    content: &'a str,
    byte_offset: usize,
    finished: bool,
}

impl<'a> NativeDocumentSliceStream<'a> {
    pub fn new(content: &'a str) -> Self {
        Self {
            content,
            byte_offset: 0,
            finished: false,
        }
    }
}

impl<'a> Iterator for NativeDocumentSliceStream<'a> {
    type Item = &'a str;

    fn next(&mut self) -> Option<Self::Item> {
        if self.finished || self.byte_offset >= self.content.len() {
            return None;
        }

        let bytes = self.content.as_bytes();
        let len = bytes.len();
        let mut doc_start = self.byte_offset;

        // Skip leading whitespace / blank lines / leading document markers
        while doc_start < len {
            let is_at_line_start = doc_start == 0 || bytes[doc_start - 1] == b'\n';
            if is_at_line_start && bytes[doc_start..].starts_with(b"---") {
                let mut line_end = doc_start + 3;
                while line_end < len && bytes[line_end] != b'\n' {
                    line_end += 1;
                }
                if line_end < len && bytes[line_end] == b'\n' {
                    line_end += 1;
                }
                doc_start = line_end;
                continue;
            }

            if bytes[doc_start] == b'\r'
                || bytes[doc_start] == b'\n'
                || bytes[doc_start] == b' '
                || bytes[doc_start] == b'\t'
            {
                let mut next_line = doc_start;
                while next_line < len
                    && (bytes[next_line] == b' '
                        || bytes[next_line] == b'\t'
                        || bytes[next_line] == b'\r')
                {
                    next_line += 1;
                }
                if next_line < len && bytes[next_line] == b'\n' {
                    doc_start = next_line + 1;
                    continue;
                }
            }
            break;
        }

        if doc_start >= len {
            self.finished = true;
            return None;
        }

        let mut curr = doc_start;
        let mut doc_end = len;

        while curr < len {
            let is_line_start = curr == 0 || bytes[curr - 1] == b'\n';
            if is_line_start && bytes[curr..].starts_with(b"---") {
                let after_three = curr + 3;
                let is_valid_boundary = after_three == len
                    || bytes[after_three] == b'\n'
                    || bytes[after_three] == b'\r'
                    || bytes[after_three] == b' '
                    || bytes[after_three] == b'\t'
                    || bytes[after_three] == b'#';

                if is_valid_boundary {
                    doc_end = curr;
                    break;
                }
            }
            curr += 1;
        }

        let doc_slice = &self.content[doc_start..doc_end];
        self.byte_offset = doc_end;

        if doc_end == len {
            self.finished = true;
        }

        if doc_slice.trim().is_empty() {
            self.next()
        } else {
            Some(doc_slice)
        }
    }
}

/// Streaming iterator yielding sharded documents on demand from raw YAML content.
pub struct NativeShardStream<'a> {
    inner: NativeDocumentSliceStream<'a>,
}

impl<'a> NativeShardStream<'a> {
    /// Creates a new streaming lexer over the provided raw content.
    pub fn new(content: &'a str) -> Self {
        Self {
            inner: NativeDocumentSliceStream::new(content),
        }
    }
}

impl<'a> Iterator for NativeShardStream<'a> {
    type Item = Vec<NativeShard>;

    fn next(&mut self) -> Option<Self::Item> {
        self.inner.next().map(native_shard)
    }
}

/// Convenience function returning a zero-copy streaming iterator over document slices.
pub fn stream_document_slices<'a>(content: &'a str) -> NativeDocumentSliceStream<'a> {
    NativeDocumentSliceStream::new(content)
}

/// Convenience function returning a streaming iterator over documents.
pub fn native_shard_stream<'a>(content: &'a str) -> NativeShardStream<'a> {
    NativeShardStream::new(content)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stream_single_doc() {
        let yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test-pod";
        let docs: Vec<_> = native_shard_stream(yaml).collect();
        assert_eq!(docs.len(), 1);
        assert!(docs[0]
            .iter()
            .any(|s| s.key == "kind" && s.value.as_deref() == Some("Pod")));
    }

    #[test]
    fn test_stream_multi_docs_basic() {
        let yaml = r#"
apiVersion: v1
kind: Service
metadata:
  name: test-svc
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-dep
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-cm
"#;
        let docs: Vec<_> = native_shard_stream(yaml).collect();
        assert_eq!(docs.len(), 3);
        assert!(docs[0]
            .iter()
            .any(|s| s.key == "kind" && s.value.as_deref() == Some("Service")));
        assert!(docs[1]
            .iter()
            .any(|s| s.key == "kind" && s.value.as_deref() == Some("Deployment")));
        assert!(docs[2]
            .iter()
            .any(|s| s.key == "kind" && s.value.as_deref() == Some("ConfigMap")));
    }

    #[test]
    fn test_stream_empty_and_trailing_boundaries() {
        let yaml = "---\n---\napiVersion: v1\nkind: Pod\n---\n---\n";
        let docs: Vec<_> = native_shard_stream(yaml).collect();
        assert_eq!(docs.len(), 1);
        assert!(docs[0]
            .iter()
            .any(|s| s.key == "kind" && s.value.as_deref() == Some("Pod")));
    }

    #[test]
    fn test_stream_document_slices_zero_copy() {
        let yaml = "apiVersion: v1\nkind: Pod\n---\napiVersion: v1\nkind: Service\n";
        let slices: Vec<&str> = stream_document_slices(yaml).collect();
        assert_eq!(slices.len(), 2);
        assert!(slices[0].contains("kind: Pod"));
        assert!(slices[1].contains("kind: Service"));
    }
}
