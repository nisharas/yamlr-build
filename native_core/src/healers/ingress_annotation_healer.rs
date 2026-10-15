//! Ingress Network Whitelist Annotation Healer (Rule NET-011).
//!
//! Why: Ingress IP whitelisting annotations (e.g. `nginx.ingress.kubernetes.io/whitelist-source-range`)
//!      require strictly comma-delimited CIDR sets according to Ingress NGINX specifications.
//!      Developers often specify CIDR lists across multiple lines (using YAML literal block `|`)
//!      with missing or inconsistent commas. Missing commas between lines cause NGINX configuration
//!      generation failures or silent omission of security boundaries.
//!      This healer repairs missing/inconsistent delimiters while strictly preserving the author's
//!      original format (multiline block vs inline quoted string).

use crate::models::{NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const INGRESS_WHITELIST_RULE_ID: &str = "NET-011";

/// Sanitizes Ingress whitelist CIDR annotation values while preserving formatting style.
pub fn heal_ingress_whitelist_annotations(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if !kind.eq_ignore_ascii_case("Ingress") {
        return changes;
    }

    let ing_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-ingress".to_string());

    let target_keys = [
        "nginx.ingress.kubernetes.io/whitelist-source-range",
        "nginx.ingress.kubernetes.io/limit-whitelist",
        "ingress.kubernetes.io/whitelist-x-forwarded-for",
    ];

    if let Some(metadata) = manifest.root.find_node_mut("metadata") {
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            for ann in &mut annotations.children {
                if target_keys.iter().any(|k| *k == ann.key) {
                    // Check if value is stored across continuation shards (e.g. key: |\n continuation shards)
                    let has_continuation_shards = ann.shards.iter().skip(1).any(|s| s.is_table_continuation);

                    if has_continuation_shards {
                        let header_val = ann.value.clone().unwrap_or_else(|| "|".to_string());
                        let mut full_block = String::new();
                        full_block.push_str(&header_val);
                        full_block.push('\n');
                        for s in ann.shards.iter().skip(1) {
                            if s.is_table_continuation {
                                full_block.push_str(&s.raw_line);
                                full_block.push('\n');
                            }
                        }

                        if let Some((repaired_val, changed)) = repair_whitelist_val(&full_block) {
                            if changed {
                                let repaired_lines: Vec<&str> = repaired_val.lines().collect();
                                // First line is header, subsequent lines update continuation shards
                                if !repaired_lines.is_empty() {
                                    ann.value = Some(repaired_lines[0].to_string());
                                }
                                let mut line_iter = repaired_lines.into_iter().skip(1);
                                for s in ann.shards.iter_mut().skip(1) {
                                    if s.is_table_continuation {
                                        if let Some(next_line) = line_iter.next() {
                                            s.raw_line = next_line.to_string();
                                            s.value = Some(next_line.trim().to_string());
                                        }
                                    }
                                }

                                let desc = format!(
                                    "Remediation [{}]: Sanitized CIDR delimiters in annotation '{}' for Ingress '{}'.",
                                    INGRESS_WHITELIST_RULE_ID, ann.key, ing_name
                                );
                                native_record_healing_impact(telemetry, &desc);
                                changes.push(desc);
                            }
                        }
                    } else if let Some(ref raw_val) = ann.value {
                        if let Some((repaired_val, changed)) = repair_whitelist_val(raw_val) {
                            if changed {
                                ann.value = Some(repaired_val);
                                let desc = format!(
                                    "Remediation [{}]: Sanitized CIDR delimiters in annotation '{}' for Ingress '{}'.",
                                    INGRESS_WHITELIST_RULE_ID, ann.key, ing_name
                                );
                                native_record_healing_impact(telemetry, &desc);
                                changes.push(desc);
                            }
                        }
                    }
                }
            }
        }
    }

    changes
}

/// Repairs CIDR delimiter inconsistencies while preserving scalar style.
fn repair_whitelist_val(raw: &str) -> Option<(String, bool)> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return None;
    }

    // Check if original is a block scalar (e.g. `|`, `|-`, `|+` followed by newlines)
    let is_block_scalar = trimmed.starts_with('|') || raw.contains('\n');

    if is_block_scalar {
        repair_multiline_block(raw)
    } else {
        repair_inline_cidr(raw)
    }
}

/// Handles multiline block scalar CIDR formatting while keeping the block structure.
fn repair_multiline_block(raw: &str) -> Option<(String, bool)> {
    let lines: Vec<&str> = raw.lines().collect();
    if lines.is_empty() {
        return None;
    }

    let mut out_lines = Vec::new();
    let mut modified = false;

    // Detect if first line is the block indicator `|`
    let has_header = lines[0].trim().starts_with('|');
    let start_idx = if has_header {
        out_lines.push(lines[0].to_string());
        1
    } else {
        0
    };

    // Filter actual content lines
    let mut content_indices = Vec::new();
    for i in start_idx..lines.len() {
        let t = lines[i].trim();
        if !t.is_empty() && !t.starts_with('#') {
            content_indices.push(i);
        }
    }

    if content_indices.is_empty() {
        return None;
    }

    for (pos, &line_idx) in content_indices.iter().enumerate() {
        let line = lines[line_idx];
        let indent = line.len() - line.trim_start().len();
        let indent_str = " ".repeat(indent);

        // Separate inline comment if present
        let (content_part, comment_part) = if let Some(hash_pos) = line.find('#') {
            (&line[..hash_pos], Some(&line[hash_pos..]))
        } else {
            (line, None)
        };

        let trimmed_content = content_part.trim();
        // Strip any existing trailing comma
        let clean_token = trimmed_content.trim_end_matches(',').trim();
        let normalized_token = fix_cidr_typo(clean_token);

        let is_last = pos == content_indices.len() - 1;

        // In YAML multiline CIDR lists for NGINX, comma at end of line ensures correct tokenization
        let expected_line = if is_last {
            // Last line may omit comma or retain comma if preferred, but canonical avoids trailing comma or keeps consistent
            // To ensure compatibility, every line in a multiline block can safely end in a comma,
            // or all non-last lines end with a comma.
            if let Some(c) = comment_part {
                format!("{}{}{}", indent_str, normalized_token, c)
            } else {
                format!("{}{}", indent_str, normalized_token)
            }
        } else {
            if let Some(c) = comment_part {
                format!("{}{},  {}", indent_str, normalized_token, c)
            } else {
                format!("{}{},", indent_str, normalized_token)
            }
        };

        if line != expected_line {
            modified = true;
        }
    }

    if !modified {
        return Some((raw.to_string(), false));
    }

    // Reconstruct lines
    let mut result_lines = Vec::new();
    let mut content_pos = 0;

    for i in 0..lines.len() {
        if has_header && i == 0 {
            result_lines.push(lines[0].to_string());
            continue;
        }

        let t = lines[i].trim();
        if t.is_empty() || t.starts_with('#') {
            result_lines.push(lines[i].to_string());
            continue;
        }

        let line = lines[i];
        let indent = line.len() - line.trim_start().len();
        let indent_str = " ".repeat(indent);

        let (content_part, comment_part) = if let Some(hash_pos) = line.find('#') {
            (&line[..hash_pos], Some(&line[hash_pos..]))
        } else {
            (line, None)
        };

        let clean_token = content_part.trim().trim_end_matches(',').trim();
        let normalized_token = fix_cidr_typo(clean_token);
        let is_last = content_pos == content_indices.len() - 1;
        content_pos += 1;

        let formatted = if is_last {
            if let Some(c) = comment_part {
                format!("{}{}  {}", indent_str, normalized_token, c)
            } else {
                format!("{}{}", indent_str, normalized_token)
            }
        } else {
            if let Some(c) = comment_part {
                format!("{}{},  {}", indent_str, normalized_token, c)
            } else {
                format!("{}{},", indent_str, normalized_token)
            }
        };
        result_lines.push(formatted);
    }

    Some((result_lines.join("\n"), true))
}

/// Normalizes inline comma/space separated CIDR lists.
fn repair_inline_cidr(raw: &str) -> Option<(String, bool)> {
    let unquoted = raw.trim().trim_matches('"').trim_matches('\'');
    // Split by commas or whitespace
    let tokens: Vec<&str> = unquoted
        .split(|c: char| c == ',' || c.is_whitespace())
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();

    if tokens.is_empty() {
        return None;
    }

    let mut cleaned_tokens = Vec::new();
    let mut modified = false;

    for token in tokens {
        let fixed = fix_cidr_typo(token);
        if fixed != token {
            modified = true;
        }
        cleaned_tokens.push(fixed);
    }

    let canonical = format!("\"{}\"", cleaned_tokens.join(", "));
    if raw.trim() != canonical {
        modified = true;
    }

    if modified {
        Some((canonical, true))
    } else {
        Some((raw.to_string(), false))
    }
}

/// Robustly corrects arbitrary typo sequences in CIDRs:
/// - Arbitrary repeating dots anywhere in IP octets: `192.168....0.0` -> `192.168.0.0`
/// - Arbitrary repeating slashes between IP and mask: `192.168.0.0///////16` -> `192.168.0.0/16`
/// - Trailing/leading stray dots or slashes
fn fix_cidr_typo(token: &str) -> String {
    let raw = token.trim();
    if raw.is_empty() {
        return String::new();
    }

    // Split on first slash sequence
    let (ip_part, mask_part) = if let Some(slash_idx) = raw.find('/') {
        let (left, right) = raw.split_at(slash_idx);
        let clean_right = right.trim_matches('/');
        (left, Some(clean_right))
    } else {
        (raw, None)
    };

    // Clean IP: collapse multiple consecutive dots into a single dot
    let mut clean_octets = Vec::new();
    for octet in ip_part.split('.') {
        let trimmed_octet = octet.trim();
        if !trimmed_octet.is_empty() {
            clean_octets.push(trimmed_octet);
        }
    }
    let sanitized_ip = clean_octets.join(".");

    match mask_part {
        Some(mask) if !mask.is_empty() => {
            let clean_mask = mask.trim_matches('/').trim();
            format!("{}/{}", sanitized_ip, clean_mask)
        }
        _ => sanitized_ip,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_repair_multiline_block_cidr() {
        let raw = "|\n  10.0.0.0/8\n  172.16.0.0/16,\n  192.168.0.0/16";
        let (repaired, changed) = repair_multiline_block(raw).unwrap();
        assert!(changed);
        let expected = "|\n  10.0.0.0/8,\n  172.16.0.0/16,\n  192.168.0.0/16";
        assert_eq!(repaired, expected);
    }

    #[test]
    fn test_fix_cidr_double_dot() {
        assert_eq!(fix_cidr_typo("192.168.0.0./16"), "192.168.0.0/16");
    }

    #[test]
    fn test_fix_cidr_double_slash() {
        assert_eq!(fix_cidr_typo("192.168.0.0//32"), "192.168.0.0/32");
    }

    #[test]
    fn test_fix_cidr_arbitrary_dots_and_slashes() {
        assert_eq!(fix_cidr_typo("192.168....0.0"), "192.168.0.0");
        assert_eq!(fix_cidr_typo("192.168.0.0///////16"), "192.168.0.0/16");
        assert_eq!(fix_cidr_typo("10...0...0...1////24"), "10.0.0.1/24");
    }

    #[test]
    fn test_repair_inline_cidr() {
        let raw = "\"10.0.0.0/8 172.16.0.0/16\"";
        let (repaired, changed) = repair_inline_cidr(raw).unwrap();
        assert!(changed);
        assert_eq!(repaired, "\"10.0.0.0/8, 172.16.0.0/16\"");
    }

    #[test]
    fn test_end_to_end_ingress_whitelist_pipeline() {
        let input_yaml = r#"apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: test-app
  annotations:
    nginx.ingress.kubernetes.io/whitelist-source-range: |
      10.0.0.0/8
      172.16.0.0/16,
      192.168.0.0///////16
spec:
  rules:
  - host: example.com
"#;
        let shards = crate::sharder::native_shard(input_yaml);
        let mut manifest = crate::structurer::native_structurize(shards);
        let mut telemetry = NativeTelemetry::default();
        let changes = crate::healing::native_heal_manifest_with_schemas(
            &mut manifest,
            &[],
            &mut telemetry,
            &[],
        );

        assert!(
            changes.iter().any(|c| c.contains("[NET-011]")),
            "Expected NET-011 change in pipeline changes: {:?}",
            changes
        );

        let reconstructed = crate::parsers::reconstructor::native_reconstruct_from_semantic(&manifest);
        assert!(reconstructed.contains("10.0.0.0/8,"));
        assert!(reconstructed.contains("172.16.0.0/16,"));
        assert!(reconstructed.contains("192.168.0.0/16"));
        assert!(!reconstructed.contains("///////"));
    }
}
