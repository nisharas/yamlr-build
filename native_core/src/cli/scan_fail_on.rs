//! Severity threshold handling for scan command exit status.

use super::ViolationRecord;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum FailOn {
    Error,
    Warning,
    Note,
    None,
}

impl FailOn {
    pub(crate) fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "error" => Some(Self::Error),
            "warning" => Some(Self::Warning),
            "note" | "any" | "info" => Some(Self::Note),
            "none" => Some(Self::None),
            _ => None,
        }
    }

    pub(crate) fn is_triggered_by(self, results: &[ViolationRecord]) -> bool {
        let threshold = match self {
            Self::Error => 3,
            Self::Warning => 2,
            Self::Note => 1,
            Self::None => return false,
        };

        results
            .iter()
            .any(|result| severity_rank(&result.severity) >= threshold)
    }
}

fn severity_rank(severity: &str) -> u8 {
    match severity.trim().to_ascii_lowercase().as_str() {
        "critical" | "high" | "error" => 3,
        "medium" | "warning" => 2,
        _ => 1,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn finding(severity: &str) -> ViolationRecord {
        ViolationRecord {
            file: "manifest.yaml".to_string(),
            check_type: "test".to_string(),
            rule_id: "TEST-001".to_string(),
            message: "test finding".to_string(),
            severity: severity.to_string(),
            line: 1,
        }
    }

    #[test]
    fn thresholds_match_the_requested_severity_or_higher() {
        assert!(!FailOn::Error.is_triggered_by(&[finding("medium")]));
        assert!(FailOn::Error.is_triggered_by(&[finding("HIGH")]));
        assert!(FailOn::Warning.is_triggered_by(&[finding("medium")]));
        assert!(FailOn::Warning.is_triggered_by(&[finding("error")]));
        assert!(FailOn::Note.is_triggered_by(&[finding("info")]));
        assert!(FailOn::Note.is_triggered_by(&[finding("warning")]));
        assert!(!FailOn::None.is_triggered_by(&[finding("critical")]));
    }

    #[test]
    fn threshold_aliases_are_case_insensitive_and_invalid_values_are_rejected() {
        assert_eq!(FailOn::parse("WARNING"), Some(FailOn::Warning));
        assert_eq!(FailOn::parse("any"), Some(FailOn::Note));
        assert_eq!(FailOn::parse("info"), Some(FailOn::Note));
        assert_eq!(FailOn::parse("none"), Some(FailOn::None));
        assert_eq!(FailOn::parse("unknown"), None);
    }
}
