//! SARIF 2.1 Standard Serialization and Diagnostics.
//!
//! Why: Provides OASIS SARIF 2.1 compliance for GitHub Code Scanning,
//! IDE code actions, and CI security dashboards with codeFlows and graphs.

pub mod code_flows;

pub use code_flows::*;
