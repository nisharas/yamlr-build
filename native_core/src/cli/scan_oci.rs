//! Local OCI chart-layer loading for the scan command.

use crate::parsers::helm::{unpack_oci_chart_layer, OciChartContents};
use std::fmt;
use std::fs::File;
use std::io::Read;

const MAX_COMPRESSED_OCI_LAYER_BYTES: u64 = 100 * 1024 * 1024;

#[derive(Debug, PartialEq, Eq)]
pub(super) enum OciLayerError {
    Read(String),
    Invalid(String),
}

impl OciLayerError {
    pub(super) fn exit_code(&self) -> i32 {
        match self {
            Self::Read(_) => crate::cli::EXIT_SYSTEM_ERROR,
            Self::Invalid(_) => 2,
        }
    }
}

impl fmt::Display for OciLayerError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Read(message) | Self::Invalid(message) => formatter.write_str(message),
        }
    }
}

pub(super) fn load_chart_layer(path: &str) -> Result<OciChartContents, OciLayerError> {
    let layer_file = File::open(path).map_err(|error| {
        OciLayerError::Read(format!(
            "Failed to read OCI chart layer '{}': {}",
            path, error
        ))
    })?;
    let metadata = layer_file.metadata().map_err(|error| {
        OciLayerError::Read(format!(
            "Failed to inspect OCI chart layer '{}': {}",
            path, error
        ))
    })?;
    if metadata.len() > MAX_COMPRESSED_OCI_LAYER_BYTES {
        return Err(compressed_layer_too_large(path));
    }

    let mut layer_bytes = Vec::new();
    layer_file
        .take(MAX_COMPRESSED_OCI_LAYER_BYTES.saturating_add(1))
        .read_to_end(&mut layer_bytes)
        .map_err(|error| {
            OciLayerError::Read(format!(
                "Failed to read OCI chart layer '{}': {}",
                path, error
            ))
        })?;
    if layer_bytes.len() as u64 > MAX_COMPRESSED_OCI_LAYER_BYTES {
        return Err(compressed_layer_too_large(path));
    }

    let contents = unpack_oci_chart_layer(&layer_bytes).map_err(|error| {
        OciLayerError::Invalid(format!(
            "Failed to unpack OCI chart layer '{}': {}",
            path, error
        ))
    })?;

    if contents.templates_yaml.trim().is_empty() {
        return Err(OciLayerError::Invalid(format!(
            "OCI chart layer '{}' contains no YAML templates to scan.",
            path
        )));
    }

    Ok(contents)
}

fn compressed_layer_too_large(path: &str) -> OciLayerError {
    OciLayerError::Invalid(format!(
        "OCI chart layer '{}' exceeds the {} MiB compressed input limit",
        path,
        MAX_COMPRESSED_OCI_LAYER_BYTES / (1024 * 1024)
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn missing_layer_returns_a_read_error() {
        let dir = tempdir().unwrap();
        let missing_layer = dir.path().join("missing.tgz");

        let error = load_chart_layer(missing_layer.to_str().unwrap()).unwrap_err();

        assert!(error.to_string().contains("Failed to read OCI chart layer"));
        assert_eq!(error.exit_code(), crate::cli::EXIT_SYSTEM_ERROR);
    }

    #[test]
    fn malformed_layer_content_keeps_the_input_error_code() {
        let dir = tempdir().unwrap();
        let malformed_layer = dir.path().join("malformed.tgz");
        std::fs::write(&malformed_layer, [0, 1, 2]).unwrap();

        let error = load_chart_layer(malformed_layer.to_str().unwrap()).unwrap_err();

        assert!(error
            .to_string()
            .contains("Failed to unpack OCI chart layer"));
        assert_eq!(error.exit_code(), 2);
    }

    #[test]
    fn oversized_compressed_layer_is_rejected_before_reading() {
        let dir = tempdir().unwrap();
        let oversized_layer = dir.path().join("oversized.tgz");
        let file = std::fs::File::create(&oversized_layer).unwrap();
        file.set_len(MAX_COMPRESSED_OCI_LAYER_BYTES + 1).unwrap();

        let error = load_chart_layer(oversized_layer.to_str().unwrap()).unwrap_err();

        assert!(error.to_string().contains("compressed input limit"));
        assert_eq!(error.exit_code(), 2);
    }
}
