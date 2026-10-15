//! UTF-16 and Encoding Transcoder Healer (Rule ENC-001 / Trap 70).
//!
//! Why: In enterprise and GitOps repositories (especially Windows PowerShell workflows,
//! Helm packaging, or Visual Studio exports), manifest files and secrets are frequently
//! saved with UTF-16 Little Endian (LE) or Big Endian (BE) encodings.
//! Standard Kubernetes YAML scanners and apiservers expect standard UTF-8 text and
//! instantly crash on UTF-16 byte streams with:
//! `unacceptable character #x0000: special characters are not allowed`.
//!
//! This module transparently detects UTF-16 BOMs (0xFF 0xFE or 0xFE 0xFF) or null-interleaved
//! ASCII byte streams and normalizes the payload to valid UTF-8.

pub const RULE_ENC_001: &str = "ENC-001";

/// Checks if raw bytes represent a UTF-16 encoded document.
pub fn is_utf16_encoded(bytes: &[u8]) -> Option<bool> {
    if bytes.len() >= 2 {
        // UTF-16 LE BOM: 0xFF 0xFE
        if bytes[0] == 0xFF && bytes[1] == 0xFE {
            return Some(true); // true = Little Endian
        }
        // UTF-16 BE BOM: 0xFE 0xFF
        if bytes[0] == 0xFE && bytes[1] == 0xFF {
            return Some(false); // false = Big Endian
        }
    }
    // Heuristic without BOM: check if first few characters alternate with null bytes
    if bytes.len() >= 4 {
        if bytes[1] == 0x00 && bytes[3] == 0x00 {
            return Some(true); // likely LE
        }
        if bytes[0] == 0x00 && bytes[2] == 0x00 {
            return Some(false); // likely BE
        }
    }
    None
}

/// Transcodes UTF-16 byte slices into clean UTF-8 string with remediation message.
pub fn transcode_utf16_to_utf8(bytes: &[u8]) -> Option<(String, String)> {
    if let Some(is_le) = is_utf16_encoded(bytes) {
        let (content_bytes, endian_str) = if bytes.len() >= 2 && ((bytes[0] == 0xFF && bytes[1] == 0xFE) || (bytes[0] == 0xFE && bytes[1] == 0xFF)) {
            (&bytes[2..], if is_le { "LE with BOM" } else { "BE with BOM" })
        } else {
            (bytes, if is_le { "LE" } else { "BE" })
        };

        let u16_vec: Vec<u16> = content_bytes
            .chunks_exact(2)
            .map(|chunk| {
                if is_le {
                    u16::from_le_bytes([chunk[0], chunk[1]])
                } else {
                    u16::from_be_bytes([chunk[0], chunk[1]])
                }
            })
            .collect();

        if let Ok(decoded) = String::from_utf16(&u16_vec) {
            let change = format!(
                "Remediation [{}]: Transcoded UTF-16 ({}) manifest to canonical UTF-8.",
                RULE_ENC_001, endian_str
            );
            return Some((decoded, change));
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_transcodes_utf16_le_with_bom() {
        // "apiVersion: v1" in UTF-16 LE
        let mut bytes = vec![0xFF, 0xFE];
        for b in "apiVersion: v1".bytes() {
            bytes.push(b);
            bytes.push(0x00);
        }

        let res = transcode_utf16_to_utf8(&bytes);
        assert!(res.is_some());
        let (content, change) = res.unwrap();
        assert_eq!(content, "apiVersion: v1");
        assert!(change.contains(RULE_ENC_001));
    }
}
