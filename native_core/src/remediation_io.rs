//! Atomic File I/O, Remediation Journaling, Evidence Vault, and GitOps Stamping.
//!
//! Why: Separates filesystem side-effects (file locks, safe atomic writes, fsync,
//! journal scrubbing, and evidence vaults) from pure semantic AST healing logic per the Agent Modularity Protocol.

pub mod gitops;
pub mod journal;
pub mod policy_adapter;
#[cfg(test)]
pub mod tests;
pub mod vault;

pub use gitops::*;
pub use journal::*;
pub use policy_adapter::*;
pub use vault::*;
