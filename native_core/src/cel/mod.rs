//! Kubernetes 1.30+ CEL (Common Expression Language) Module.
//!
//! Why: Exposes high-performance CEL evaluation and ValidatingAdmissionPolicy
//! inspection to the native resolution engine. Strictly < 500 lines.

pub mod evaluator;
pub mod k8s_validator;

pub use evaluator::eval_cel_expression;
pub use k8s_validator::{
    evaluate_single_rule, validate_builtin_cel_workloads, validate_k8s_cel_rules, K8sValidationRule,
};
