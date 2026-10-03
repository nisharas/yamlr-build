//! Stdin input adapter for native manifest scanning.

use crate::models::NativeSchema;

use super::ViolationRecord;

pub(super) fn process_stdin<R: std::io::Read>(
    reader: &mut R,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
) -> Result<(), super::scan_input::ScanError> {
    let content = super::scan_input::read_limited(reader, "stdin")?;
    super::process_manifest_string(
        &content,
        "<stdin>",
        schemas,
        total_violations,
        total_integrity,
        results,
    )
    .map_err(super::scan_input::ScanError::Input)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn scans_utf8_stdin_content_and_returns_findings() {
        let content = "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: sample\n";
        let schemas = [NativeSchema {
            kind: "Widget".to_string(),
            api_version: "example.test/v1".to_string(),
            properties: vec![crate::models::SchemaProperty {
                name: "spec".to_string(),
                prop_type: "object".to_string(),
                required: true,
                description: "Widget specification".to_string(),
                enum_values: Vec::new(),
            }],
        }];
        let mut reader = Cursor::new(content.as_bytes());
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        process_stdin(
            &mut reader,
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap();

        assert_eq!(total_violations, 1);
        assert_eq!(results[0].file, "<stdin>");
    }

    #[test]
    fn rejects_non_utf8_stdin_without_partial_findings() {
        let mut reader = Cursor::new([0xff, 0xfe]);
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        let error = process_stdin(
            &mut reader,
            &[],
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap_err();

        assert!(error.to_string().contains("UTF-8 YAML from stdin"));
        assert_eq!(error.exit_code(), 2);
        assert_eq!(total_violations, 0);
        assert_eq!(total_integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn stdin_read_failures_use_system_error() {
        struct FailingReader;

        impl std::io::Read for FailingReader {
            fn read(&mut self, _buffer: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::Error::new(
                    std::io::ErrorKind::Other,
                    "stdin unavailable",
                ))
            }
        }

        let mut reader = FailingReader;
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();
        let error = process_stdin(
            &mut reader,
            &[],
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap_err();

        assert!(error.to_string().contains("stdin unavailable"));
        assert_eq!(error.exit_code(), crate::cli::EXIT_SYSTEM_ERROR);
        assert_eq!(total_violations, 0);
        assert_eq!(total_integrity, 0);
        assert!(results.is_empty());
    }
}
