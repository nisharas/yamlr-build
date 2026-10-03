//! Native Sprig & Helm Template Functions Engine.
//!
//! Why: Helm charts extensively employ Sprig functions (`toYaml`, `nindent`, `b64enc`, `quote`)
//!      to render nested manifests, labels, and secrets. Evaluating these functions in-memory
//!      ensures accurate AST sharding and zero false-positive syntax rejections during scanning.

use serde_json::Value;

/// Applies a sequence of pipeline functions to an input JSON Value.
pub fn eval_pipeline_step(step: &str, current_val: &mut Option<Value>) -> Option<String> {
    let step_trimmed = step.trim();
    let parts: Vec<&str> = step_trimmed.split_whitespace().collect();
    if parts.is_empty() {
        return None;
    }

    let fn_name = parts[0];
    let arg = parts.get(1).copied().unwrap_or("");

    match fn_name {
        "toYaml" => {
            if let Some(ref v) = current_val {
                if let Ok(yaml_str) = serde_yaml::to_string(v) {
                    let trimmed = yaml_str.trim();
                    *current_val = Some(Value::String(trimmed.to_string()));
                    return Some(trimmed.to_string());
                }
            }
            None
        }
        "toJson" => {
            if let Some(ref v) = current_val {
                if let Ok(json_str) = serde_json::to_string(v) {
                    *current_val = Some(Value::String(json_str.clone()));
                    return Some(json_str);
                }
            }
            None
        }
        "indent" => {
            let count: usize = arg.parse().unwrap_or(2);
            let prefix = " ".repeat(count);
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let indented: Vec<String> = s.lines().map(|l| format!("{}{}", prefix, l)).collect();
                let res = indented.join("\n");
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "nindent" => {
            let count: usize = arg.parse().unwrap_or(2);
            let prefix = " ".repeat(count);
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let indented: Vec<String> = s.lines().map(|l| format!("{}{}", prefix, l)).collect();
                let res = format!("\n{}", indented.join("\n"));
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "b64enc" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let mut enc = Vec::new();
                {
                    // Clean Base64 encoding without external crate dependency
                    const B64_CHARS: &[u8] =
                        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
                    let bytes = s.as_bytes();
                    for chunk in bytes.chunks(3) {
                        let b0 = chunk[0];
                        let b1 = chunk.get(1).copied().unwrap_or(0);
                        let b2 = chunk.get(2).copied().unwrap_or(0);

                        let n = ((b0 as u32) << 16) | ((b1 as u32) << 8) | (b2 as u32);
                        enc.push(B64_CHARS[((n >> 18) & 63) as usize]);
                        enc.push(B64_CHARS[((n >> 12) & 63) as usize]);
                        if chunk.len() > 1 {
                            enc.push(B64_CHARS[((n >> 6) & 63) as usize]);
                        } else {
                            enc.push(b'=');
                        }
                        if chunk.len() > 2 {
                            enc.push(B64_CHARS[(n & 63) as usize]);
                        } else {
                            enc.push(b'=');
                        }
                    }
                }
                let res = String::from_utf8(enc).unwrap_or_default();
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "b64dec" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let clean = s.trim();
                // Simple Base64 decode
                let mut out = Vec::new();
                let b64_index = |c: u8| -> Option<u8> {
                    match c {
                        b'A'..=b'Z' => Some(c - b'A'),
                        b'a'..=b'z' => Some(c - b'a' + 26),
                        b'0'..=b'9' => Some(c - b'0' + 52),
                        b'+' => Some(62),
                        b'/' => Some(63),
                        _ => None,
                    }
                };
                let bytes = clean.as_bytes();
                for chunk in bytes.chunks(4) {
                    if chunk.len() >= 2 {
                        let c0 = b64_index(chunk[0]).unwrap_or(0);
                        let c1 = b64_index(chunk[1]).unwrap_or(0);
                        out.push((c0 << 2) | (c1 >> 4));
                        if chunk.len() > 2 && chunk[2] != b'=' {
                            let c2 = b64_index(chunk[2]).unwrap_or(0);
                            out.push(((c1 & 15) << 4) | (c2 >> 2));
                            if chunk.len() > 3 && chunk[3] != b'=' {
                                let c3 = b64_index(chunk[3]).unwrap_or(0);
                                out.push(((c2 & 3) << 6) | c3);
                            }
                        }
                    }
                }
                let res = String::from_utf8_lossy(&out).to_string();
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "quote" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let res = format!("\"{}\"", s);
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "squote" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let res = format!("'{}'", s);
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "trim" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let res = s.trim().to_string();
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "lower" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let res = s.to_lowercase();
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "upper" => {
            if let Some(ref v) = current_val {
                let s = value_to_string(v);
                let res = s.to_uppercase();
                *current_val = Some(Value::String(res.clone()));
                return Some(res);
            }
            None
        }
        "default" => {
            let is_empty = match current_val {
                None => true,
                Some(Value::Null) => true,
                Some(Value::String(s)) => s.is_empty(),
                _ => false,
            };
            if is_empty {
                let fallback = arg.trim_matches('"').trim_matches('\'').to_string();
                *current_val = Some(Value::String(fallback.clone()));
                return Some(fallback);
            }
            None
        }
        _ => None,
    }
}

fn value_to_string(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Number(n) => n.to_string(),
        Value::Bool(b) => b.to_string(),
        Value::Null => String::new(),
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sprig_quote_and_squote() {
        let mut val = Some(Value::String("hello".to_string()));
        let q = eval_pipeline_step("quote", &mut val);
        assert_eq!(q, Some("\"hello\"".to_string()));

        let mut val2 = Some(Value::String("world".to_string()));
        let sq = eval_pipeline_step("squote", &mut val2);
        assert_eq!(sq, Some("'world'".to_string()));
    }

    #[test]
    fn test_sprig_indent_and_nindent() {
        let mut val = Some(Value::String("key: value".to_string()));
        let ind = eval_pipeline_step("indent 4", &mut val);
        assert_eq!(ind, Some("    key: value".to_string()));

        let mut val2 = Some(Value::String("k: v".to_string()));
        let nind = eval_pipeline_step("nindent 2", &mut val2);
        assert_eq!(nind, Some("\n  k: v".to_string()));
    }

    #[test]
    fn test_sprig_b64enc_b64dec() {
        let mut val = Some(Value::String("secretPassword123".to_string()));
        let enc = eval_pipeline_step("b64enc", &mut val).unwrap();
        assert_eq!(enc, "c2VjcmV0UGFzc3dvcmQxMjM=");

        let mut enc_val = Some(Value::String(enc));
        let dec = eval_pipeline_step("b64dec", &mut enc_val).unwrap();
        assert_eq!(dec, "secretPassword123");
    }

    #[test]
    fn test_sprig_case_transforms() {
        let mut val = Some(Value::String("Prod-Cluster".to_string()));
        let low = eval_pipeline_step("lower", &mut val).unwrap();
        assert_eq!(low, "prod-cluster");

        let mut val2 = Some(Value::String("test".to_string()));
        let up = eval_pipeline_step("upper", &mut val2).unwrap();
        assert_eq!(up, "TEST");
    }
}
