//! Security, Enterprise Hardening, Licensing, and Cryptographic Signatures.
//!
//! Why: Ensures end-to-end security compliance, tamper-proof GitOps manifests,
//! signed licensing entitlements, and Pod Security Standards enforcement.

pub mod attestation;
pub mod entitlements;
pub mod hardening;
pub mod licensing;
pub mod signature;
#[cfg(not(target_arch = "wasm32"))]
pub mod team_refresh;
#[cfg(test)]
pub mod tests;

pub use attestation::*;
pub use entitlements::*;
pub use hardening::*;
pub use licensing::*;
pub use signature::*;
#[cfg(not(target_arch = "wasm32"))]
pub use team_refresh::*;
