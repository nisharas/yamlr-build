pub mod anchor_resolver;
pub mod helm;
pub mod heuristics;
pub mod interner;
pub mod kustomize;
pub mod layout_grafter;
pub mod reconstructor;
pub mod streaming;
pub mod terraform;

pub mod shard_finder;

pub use anchor_resolver::*;
pub use interner::*;
pub use reconstructor::*;
pub use shard_finder::*;
pub use streaming::*;

/// Configuration parser trait for multi-format manifest support.
pub trait ConfigurationParser {
    /// Detects structural or semantic violations in the given raw content.
    fn detect_violations(&self, content: &str) -> Result<Vec<String>, String>;

    /// Heals the configuration non-destructively, preserving comments.
    fn heal_non_destructive(&self, content: &str, patch: &str) -> Result<String, String>;

    /// Identifies the dialect this parser handles (e.g., "helm", "terraform", "k8s").
    fn dialect(&self) -> &str;
}
