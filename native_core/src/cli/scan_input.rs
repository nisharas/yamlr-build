//! Bounded UTF-8 input reading for native manifest scans.

use std::fmt;
use std::io::Read;

pub(super) const MAX_MANIFEST_BYTES: usize = 10 * 1024 * 1024;

#[derive(Debug, PartialEq, Eq)]
pub(super) enum ScanError {
    System(String),
    Input(String),
}

impl ScanError {
    pub(super) fn exit_code(&self) -> i32 {
        match self {
            Self::System(_) => crate::cli::EXIT_SYSTEM_ERROR,
            Self::Input(_) => 2,
        }
    }
}

impl fmt::Display for ScanError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::System(message) | Self::Input(message) => formatter.write_str(message),
        }
    }
}

pub(super) fn read_limited<R: Read>(reader: &mut R, source: &str) -> Result<String, ScanError> {
    read_limited_to(reader, source, MAX_MANIFEST_BYTES)
}

fn read_limited_to<R: Read>(
    reader: &mut R,
    source: &str,
    max_bytes: usize,
) -> Result<String, ScanError> {
    let mut content = Vec::new();
    reader
        .take(max_bytes.saturating_add(1) as u64)
        .read_to_end(&mut content)
        .map_err(|error| {
            ScanError::System(format!(
                "Unable to read UTF-8 YAML from {}: {}",
                source, error
            ))
        })?;
    if content.len() > max_bytes {
        return Err(ScanError::Input(format!(
            "{} exceeds the {} MiB scan limit; no results were produced",
            source,
            max_bytes / (1024 * 1024)
        )));
    }
    String::from_utf8(content).map_err(|_| {
        ScanError::Input(format!(
            "Unable to read UTF-8 YAML from {}: stream did not contain valid UTF-8",
            source
        ))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn reader_stops_after_one_byte_beyond_the_configured_limit() {
        let mut reader = Cursor::new(b"12345678901".to_vec());

        let error = read_limited_to(&mut reader, "test input", 10).unwrap_err();

        assert!(error.to_string().contains("test input exceeds"));
        assert_eq!(error.exit_code(), 2);
        assert_eq!(reader.position(), 11);
    }

    #[test]
    fn reader_accepts_content_at_the_limit() {
        let mut reader = Cursor::new(b"1234567890".to_vec());

        let content = read_limited_to(&mut reader, "test input", 10).unwrap();

        assert_eq!(content, "1234567890");
        assert_eq!(reader.position(), 10);
    }

    #[test]
    fn reader_rejects_invalid_utf8() {
        let mut reader = Cursor::new(vec![0xff]);

        let error = read_limited_to(&mut reader, "test input", 10).unwrap_err();

        assert!(error.to_string().contains("Unable to read UTF-8 YAML"));
        assert_eq!(error.exit_code(), 2);
    }

    #[test]
    fn reader_classifies_invalid_data_io_failures_as_system_errors() {
        struct FailingReader;

        impl Read for FailingReader {
            fn read(&mut self, _buffer: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    "device returned invalid data",
                ))
            }
        }

        let error = read_limited_to(&mut FailingReader, "test input", 10).unwrap_err();

        assert!(error.to_string().contains("device returned invalid data"));
        assert_eq!(error.exit_code(), crate::cli::EXIT_SYSTEM_ERROR);
    }
}
