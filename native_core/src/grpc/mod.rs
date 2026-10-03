//! High-Performance ManifestService RPC Engine.
//!
//! Why: Cloud-agnostic platforms (Backstage IDPs, ArgoCD/Flux controllers, Jenkins, GitLab)
//! consume Yamlr as a high-throughput microservice daemon with sub-millisecond response latency.
//! Implements the service contract specified in `proto/yamlr/v1/manifest_service.proto`.

pub mod service;

pub use service::{
    execute_rpc_daemon, DocumentChunk, HealDocumentRequest, HealDocumentResponse,
    NativeManifestService, ScanDocumentRequest, ScanDocumentResponse, SuggestedFix,
    ValidationEvent, ViolationRecord,
};
