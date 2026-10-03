//! Kustomize parser and overlay renderer.
//!
//! Why: Enables evaluation and healing of multi-tier Kustomize overlays
//! (bases, components, transformers, and strategic merge patches) without
//! requiring an external `kustomize` or `kubectl` subprocess.

pub mod directory_renderer;
pub mod merge_matrix;
pub mod renderer;

pub use directory_renderer::render_kustomize_directory;
pub use merge_matrix::{
    apply_replacements, extract_field_value, merge_overlays_tiered, merge_strategic,
    set_field_value,
};
pub use renderer::{render_kustomization, KustomizationConfig};
