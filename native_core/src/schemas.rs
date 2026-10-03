//! Yamlr Schema & CRD Intelligence Engine.
//!
//! Why: Provides high-performance, deterministic Kubernetes manifest schema validation
//!      against pre-compiled OpenAPI definitions and dynamic CustomResourceDefinitions.
//!      Validation coverage depends on the schema definitions and supported constraints.

pub mod bundler;
pub mod constraints;
pub mod crd_validator;
pub mod distiller;
pub mod fetcher;
mod nested;
pub mod validator;

#[cfg(test)]
mod tests;

pub use bundler::{
    get_bundle, get_cncf_crd_schemas, native_get_schema_for_version, parse_raw_schemas,
};
pub use constraints::{
    validate_array_constraints, validate_constraints, validate_k8s_builtin_constraints,
    PropertyConstraints,
};
pub use crd_validator::{validate_crd_immutability, validate_crd_instance, CrdValidationRule};
pub use distiller::{
    distill_crd_content, distill_crd_directory, distill_crd_file, native_extract_schema_from_crd,
};
pub use fetcher::{
    fetch_k8s_schema, get_user_schema_cache_dir, normalize_k8s_version, validate_k8s_version,
};
pub use validator::{
    default_value_for_type, load_schema_from_path, native_validate_ast_against_schema,
};
