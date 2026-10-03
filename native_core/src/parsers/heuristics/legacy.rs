//! Legacy Marker Heuristic
//!
//! Why: Legacy Kubernetes manifests often contain YAML markers (such as YAML 1.1 merge keys `<<:`,
//! document directives `%YAML`, or complex mapping keys `? `) that are valid YAML syntax
//! but not part of standard OpenAPI schemas. This heuristic identifies and tags them
//! to prevent premature parser rejection.

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LegacyMarkerType {
    MergeKey,
    Directive,
    ComplexKey,
    None,
}

/// Identifies if a line contains a legacy YAML marker.
pub fn identify_legacy_marker(line: &str) -> LegacyMarkerType {
    let stripped = line.trim_start();
    if stripped.starts_with("<<:") || stripped.starts_with("<< :") {
        LegacyMarkerType::MergeKey
    } else if stripped.starts_with('%') {
        LegacyMarkerType::Directive
    } else if stripped.starts_with("? ") {
        LegacyMarkerType::ComplexKey
    } else {
        LegacyMarkerType::None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identifies_legacy_markers() {
        assert_eq!(
            identify_legacy_marker("  <<: *base_config"),
            LegacyMarkerType::MergeKey
        );
        assert_eq!(
            identify_legacy_marker("%YAML 1.2"),
            LegacyMarkerType::Directive
        );
        assert_eq!(
            identify_legacy_marker("? complex_key: val"),
            LegacyMarkerType::ComplexKey
        );
        assert_eq!(
            identify_legacy_marker("apiVersion: v1"),
            LegacyMarkerType::None
        );
    }
}
