//! Punctuation Heuristics: Magic Colon, Quote Balancing, Spacing
//!
//! Why: Developers frequently omit colons (`image nginx`), forget closing quotes
//! (`name: "web`), or omit required whitespace after markers (`-item` or `key:value`).
//! These heuristics safely repair syntax while protecting English descriptions and comments.

use lazy_static::lazy_static;
use regex::Regex;
use std::collections::HashSet;
use crate::healers::typo_dictionaries::{METADATA_KEYS, ROOT_KEYS};

lazy_static! {
    static ref COMMON_ENGLISH_STOPWORDS: HashSet<&'static str> = {
        let mut s = HashSet::new();
        s.insert("This");
        s.insert("The");
        s.insert("A");
        s.insert("An");
        s.insert("It");
        s.insert("If");
        s.insert("if");
        s.insert("fi");
        s.insert("then");
        s.insert("else");
        s.insert("elif");
        s.insert("for");
        s.insert("do");
        s.insert("done");
        s.insert("while");
        s.insert("case");
        s.insert("esac");
        s.insert("cp");
        s.insert("mv");
        s.insert("rm");
        s.insert("mkdir");
        s.insert("sh");
        s.insert("bash");
        s.insert("echo");
        s.insert("set");
        s.insert("export");
        s.insert("When");
        s.insert("Then");
        s.insert("For");
        s.insert("To");
        s.insert("Note");
        s.insert("But");
        s.insert("And");
        s.insert("Or");
        s
    };
    static ref RE_MAGIC_COLON: Regex = Regex::new(r"^(-\s+)?([a-zA-Z0-9_\-\.]+)\s+(.+)$").unwrap();
}

/// Known Kubernetes sequence mapping properties.
/// When a line starts with a list dash (`- `), a colon is ONLY injected if `key`
/// matches a recognized Kubernetes sequence mapping property. This guarantees that
/// commands, script args, and CLI binaries (python, node, git, cp, rm, envoy, etc.)
/// are never corrupted into dictionaries.
const SAFE_SEQUENCE_MAPPING_KEYS: &[&str] = &[
    // Root & Object metadata
    "apiVersion",
    "kind",
    // Containers & Pod specs
    "name",
    "image",
    "command",
    "args",
    "workingDir",
    "ports",
    "env",
    "envFrom",
    "resources",
    "volumeMounts",
    "volumeDevices",
    "livenessProbe",
    "readinessProbe",
    "startupProbe",
    "lifecycle",
    "terminationMessagePath",
    "terminationMessagePolicy",
    "imagePullPolicy",
    "securityContext",
    "stdin",
    "stdinOnce",
    "tty",
    // Ports
    "containerPort",
    "port",
    "protocol",
    "hostPort",
    "hostIP",
    "targetPort",
    "nodePort",
    "appProtocol",
    // Env & Config references
    "value",
    "valueFrom",
    "fieldRef",
    "resourceFieldRef",
    "configMapKeyRef",
    "secretKeyRef",
    "configMapRef",
    "secretRef",
    "prefix",
    // Volume mounts & devices
    "mountPath",
    "subPath",
    "subPathExpr",
    "readOnly",
    "mountPropagation",
    "devicePath",
    // Volumes
    "configMap",
    "secret",
    "emptyDir",
    "persistentVolumeClaim",
    "hostPath",
    "projected",
    "csi",
    "nfs",
    "iscsi",
    "downwardAPI",
    // Tolerations & Scheduling
    "key",
    "operator",
    "effect",
    "tolerationSeconds",
    "ip",
    "hostnames",
    "maxSkew",
    "topologyKey",
    "whenUnsatisfiable",
    "labelSelector",
    // RBAC & Policies
    "verbs",
    "apiGroups",
    "resources",
    "resourceNames",
    "nonResourceURLs",
    "kind",
    "apiGroup",
    "namespace",
    // Ingress & Networking
    "host",
    "http",
    "hosts",
    "secretName",
    "path",
    "pathType",
    "backend",
    "podSelector",
    "namespaceSelector",
    "ipBlock",
    "values",
    // Metrics & Webhooks
    "type",
    "pods",
    "object",
    "external",
    "containerResource",
    "rules",
    "clientConfig",
];

/// Injects missing colons in `key value` lines (e.g., `image nginx` -> `image: nginx`).
pub fn apply_magic_colon(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation {
        return line.to_string();
    }

    let indent_len = line.len() - line.trim_start().len();
    let indent_str = &line[..indent_len];
    let code_part = line.trim_start();

    if code_part.is_empty() || code_part.starts_with('#') || code_part.contains(':') {
        return line.to_string();
    }

    if let Some(caps) = RE_MAGIC_COLON.captures(code_part) {
        let dash_prefix = caps.get(1).map_or("", |m| m.as_str());
        let key = &caps[2];
        let val = &caps[3];

        // Guards against CLI flags (-flag, --flag), negative numbers, or private keys
        if key == "-" || key.starts_with('-') || key.starts_with('_') || val.starts_with('-') {
            return line.to_string();
        }

        // For sequence items (`- key val`) or bare mapping lines (`key val`):
        // ONLY inject colon if key is a known Kubernetes/Helm mapping property.
        // This permanently protects multi-line prose, descriptions, changelogs, commands,
        // and arguments from being corrupted into synthetic key-value dictionaries.
        if !SAFE_SEQUENCE_MAPPING_KEYS.contains(&key) && !ROOT_KEYS.contains(&key) && !METADATA_KEYS.contains(&key) {
            return line.to_string();
        }

        // For bare mapping lines (`key val`): protect English stopwords and short abbreviations
        if dash_prefix.is_empty()
            && (COMMON_ENGLISH_STOPWORDS.contains(key)
                || (key.len() <= 2 && key.chars().all(|c| c.is_uppercase())))
        {
            return line.to_string();
        }

        let mut out =
            String::with_capacity(indent_len + dash_prefix.len() + key.len() + 2 + val.len());
        out.push_str(indent_str);
        out.push_str(dash_prefix);
        out.push_str(key);
        out.push_str(": ");
        out.push_str(val);
        return out;
    }

    line.to_string()
}

/// Automatically balances unclosed quotes, mismatched quotes, unescaped nested quotes,
/// and redundant triple quotes at the end of YAML values or sequence items.
pub fn apply_quote_balancing(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation {
        return line.to_string();
    }

    let stripped = line.trim_start();
    let indent_len = line.len() - stripped.len();
    let indent_str = &line[..indent_len];

    // Check if line has a list item marker `- ` or a key delimiter `:`
    let (prefix, val_raw, comment_part) = if stripped.starts_with("- ") {
        let after_dash = &stripped[2..];
        if let Some(colon_idx) = after_dash.find(':') {
            // e.g. "- name: val"
            let pre = &stripped[..2 + colon_idx + 1];
            let rest = &after_dash[colon_idx + 1..];
            let (v, c) = split_comment(rest);
            (pre, v, c)
        } else {
            // e.g. "- \"sh\"" or "- \"-c'"
            let (v, c) = split_comment(after_dash);
            ("- ", v, c)
        }
    } else if let Some(colon_idx) = stripped.find(':') {
        let pre = &stripped[..colon_idx + 1];
        let rest = &stripped[colon_idx + 1..];
        let (v, c) = split_comment(rest);
        (pre, v, c)
    } else {
        return line.to_string();
    };

    let val_trimmed = val_raw.trim();
    if val_trimmed.is_empty() {
        return line.to_string();
    }

    let repaired_val = repair_quote_syntax(val_trimmed);
    if repaired_val == val_trimmed {
        return line.to_string();
    }

    let mut out = String::with_capacity(indent_len + prefix.len() + 1 + repaired_val.len() + comment_part.len());
    out.push_str(indent_str);
    out.push_str(prefix);
    if !prefix.ends_with(' ') {
        out.push(' ');
    }
    out.push_str(&repaired_val);
    if !comment_part.is_empty() {
        out.push(' ');
        out.push_str(comment_part.trim_start());
    }
    out
}

fn split_comment(text: &str) -> (&str, &str) {
    if let Some(hash_idx) = text.find('#') {
        (&text[..hash_idx], &text[hash_idx..])
    } else {
        (text, "")
    }
}

/// Core quote repair logic:
/// 1. Strips redundant triple quotes: `"""val"""` -> `"val"`
/// 2. Repairs mismatched boundary quotes: `"-c'` -> `"-c"` or `'val"` -> `'val'`
/// 3. Repairs unescaped nested double quotes in shell one-liners: `"echo "starting..." && exec"` -> `"echo 'starting...' && exec"`
/// 4. Balances hanging unclosed quotes: `"nginx:alpine` -> `"nginx:alpine"`
fn repair_quote_syntax(val: &str) -> String {
    let mut s = val.to_string();

    // 1. Redundant triple/double outer quotes: `"""v1.2.3"""` -> `"v1.2.3"`
    if s.starts_with("\"\"\"") && s.ends_with("\"\"\"") && s.len() >= 6 {
        s = format!("\"{}\"", &s[3..s.len() - 3]);
    } else if s.starts_with("'''") && s.ends_with("'''") && s.len() >= 6 {
        s = format!("'{}'", &s[3..s.len() - 3]);
    }

    // 2. Mismatched boundary quotes: starts with " and ends with ' (e.g. `"-c'`)
    if s.starts_with('"') && s.ends_with('\'') && !s.contains("\\'") {
        // If string started with " and ended with ', repair ending to "
        s = format!("{}\"", &s[..s.len() - 1]);
    } else if s.starts_with('\'') && s.ends_with('"') && !s.contains("\\\"") {
        // If string started with ' and ended with ", repair ending to '
        s = format!("{}'", &s[..s.len() - 1]);
    }

    // 3. Unescaped nested double quotes: `"echo "text" && run"` -> `"echo 'text' && run"`
    if s.starts_with('"') && s.ends_with('"') && s.len() > 2 {
        let inner = &s[1..s.len() - 1];
        if inner.contains('"') && !inner.contains("\\\"") {
            // Count unescaped double quotes inside
            let inner_quotes = inner.chars().filter(|&c| c == '"').count();
            if inner_quotes % 2 == 0 {
                // Symmetrical nested quotes: convert inner double quotes to single quotes
                let repaired_inner = inner.replace('"', "'");
                s = format!("\"{}\"", repaired_inner);
            }
        }
    }

    // 4. Trap 31: Unquoted Helm expression as mapping scalar value: `{{ .Values.foo }}` -> `"{{ .Values.foo }}"`
    // In YAML, leading `{` opens a flow mapping. An unquoted `{{ ... }}` crashes YAML AST parsers.
    if s.starts_with("{{") && s.ends_with("}}") && !s.starts_with("\"{{") && !s.starts_with("'{{") {
        return format!("\"{}\"", s);
    }

    // 5. Trap 33: Unquoted connection strings / URIs containing colons:
    // e.g. `postgres://user:pass@host:5432/db` -> `"postgres://user:pass@host:5432/db"`
    let known_schemes = [
        "http://", "https://", "ftp://", "ftps://",
        "postgres://", "postgresql://", "mysql://", "mariadb://",
        "mongodb://", "mongodb+srv://", "redis://", "rediss://",
        "grpc://", "grpcs://", "amqp://", "amqps://",
        "kafka://", "jdbc:",
    ];
    if known_schemes.iter().any(|scheme| s.starts_with(scheme)) && !s.starts_with('"') && !s.starts_with('\'') {
        // If it contains inner colons after the scheme delimiter, YAML parsers will fail unless quoted
        return format!("\"{}\"", s);
    }

    // 5b. Trap 59 (SYN-014): Unquoted wildcard host or glob scalar:
    // e.g. `host: *` or `host: *.example.com`
    // In YAML, `*` is the alias indicator. An unquoted `*` or `*.domain` crashes YAML parsers with
    // "did not find expected alias name" or illegal character errors.
    if (s == "*" || s.starts_with("*.")) && !s.starts_with('"') && !s.starts_with('\'') {
        return format!("\"{}\"", s);
    }

    // 6. Hanging unclosed quotes: odd quote count at end of line
    let first = s.chars().next().unwrap();
    if first == '"' || first == '\'' {
        let count = s.chars().filter(|&c| c == first).count();
        if count % 2 != 0 && !s.ends_with(first) {
            s.push(first);
        }
    }

    s
}

/// Normalizes missing whitespace after list dashes (`-item` -> `- item`, `-"val"` -> `- "val"`),
/// document boundaries (`----` -> `---`, `---#` -> `--- #`, `....` -> `...`),
/// and colons (`key:value` -> `key: value`).
pub fn apply_spacing(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation {
        return line.to_string();
    }

    let stripped = line.trim_start();
    let indent_len = line.len() - stripped.len();
    let indent_str = &line[..indent_len];

    // Traps 19, 20, 21: Document boundary and stream delimiter normalization at column 0
    if indent_len == 0 {
        // Trap 19: Multiple dashes `----`, `-----` -> `---`
        if stripped.len() >= 4 && stripped.chars().all(|c| c == '-') {
            return "---".to_string();
        }
        // Trap 20: Comment glued directly to boundary: `---# comment` -> `--- # comment`
        if stripped.starts_with("---#") {
            return format!("--- #{}", &stripped[4..]);
        }
        // Trap 21: Trailing ellipsis `....` -> `...` or `...#` -> `... #`
        if stripped.len() >= 4 && stripped.chars().all(|c| c == '.') {
            return "...".to_string();
        }
        if stripped.starts_with("...#") {
            return format!("... #{}", &stripped[4..]);
        }
    }

    // 1. Dash spacing "-item" -> "- item", and Trap 23: `-"val"` -> `- "val"` / `-'val'` -> `- 'val'`
    // Guards against CLI flags (--flag), JVM options (-XX:, -Xmx:), and negative numbers (-1)
    if stripped.starts_with('-')
        && !stripped.starts_with("--")
        && !stripped.starts_with("---")
        && stripped.len() > 1
    {
        let second_char = stripped.chars().nth(1).unwrap();
        // Trap 23: Bullet glued to quoted string
        if second_char == '"' || second_char == '\'' {
            let mut out = String::with_capacity(indent_len + 2 + stripped.len() - 1);
            out.push_str(indent_str);
            out.push_str("- ");
            out.push_str(&stripped[1..]);
            return out;
        } else if second_char.is_ascii_lowercase() {
            let mut out = String::with_capacity(indent_len + 2 + stripped.len() - 1);
            out.push_str(indent_str);
            out.push_str("- ");
            out.push_str(&stripped[1..]);
            return out;
        }
    }

    // 2. Multi-colon and key spacing normalization ("metadata::" -> "metadata:", "key : value" -> "key: value")
    let cleaned_colons = normalize_key_colons(stripped);
    let stripped = &cleaned_colons;

    // 3. Colon spacing "key:value" -> "key: value"
    if let Some(colon_idx) = find_unquoted_colon(stripped) {
        let before_colon = &stripped[..colon_idx];
        let after_colon = &stripped[colon_idx + 1..];

        // Ensure key doesn't have spaces and after_colon is non-empty and doesn't start with space
        if !before_colon.contains(' ')
            && !after_colon.is_empty()
            && !after_colon.starts_with(' ')
            && !after_colon.starts_with('/')
        // Avoid breaking URLs like http://
        {
            let mut out =
                String::with_capacity(indent_len + before_colon.len() + 2 + after_colon.len());
            out.push_str(indent_str);
            out.push_str(before_colon);
            out.push_str(": ");
            out.push_str(after_colon);
            return out;
        }
    }

    let mut final_out = String::with_capacity(indent_len + stripped.len());
    final_out.push_str(indent_str);
    final_out.push_str(stripped);
    final_out
}

fn normalize_key_colons(text: &str) -> String {
    let (content_part, comment_part) = if let Some(hash_idx) = text.find('#') {
        (&text[..hash_idx], Some(&text[hash_idx..]))
    } else {
        (text, None)
    };

    let trimmed = content_part.trim_end();
    if trimmed.is_empty() {
        return text.to_string();
    }

    // A. Scalar Header Typos: "key: >>" -> "key: >", "key: ||" -> "key: |"
    // Only applies at the scalar position on mapping lines
    let mut normalized_content = if let Some(colon_pos) = trimmed.find(':') {
        let key_part = &trimmed[..colon_pos];
        let val_part = trimmed[colon_pos + 1..].trim();
        if val_part == ">>" || val_part.starts_with(">>") {
            let fixed_val = format!(">{}", &val_part[2..]);
            format!("{}: {}", key_part.trim_end(), fixed_val)
        } else if val_part == "||" || val_part.starts_with("||") {
            let fixed_val = format!("|{}", &val_part[2..]);
            format!("{}: {}", key_part.trim_end(), fixed_val)
        } else {
            trimmed.to_string()
        }
    } else {
        trimmed.to_string()
    };

    // B. Key Semicolon Typo: "metadata;" -> "metadata:"
    // Only if line has no colon and ends with ';' and the key matches a safe schema keyword
    if !normalized_content.contains(':') && normalized_content.ends_with(';') {
        let candidate_key = normalized_content.trim_end_matches(';').trim();
        if !candidate_key.contains(' ') && (SAFE_SEQUENCE_MAPPING_KEYS.contains(&candidate_key) || candidate_key.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-')) {
            normalized_content = format!("{}:", candidate_key);
        }
    }

    // C. Multiple Colons on Keys: "metadata::" -> "metadata:" or "annotations :" -> "annotations:"
    if let Some(first_colon) = normalized_content.find(':') {
        let before = &normalized_content[..first_colon];
        let after = &normalized_content[first_colon..];
        // Strip trailing spaces on key before colon ("key : " -> "key:")
        let clean_key = before.trim_end();
        // Collapse multiple colons at start of after: "::" -> ":"
        let trimmed_colons = after.trim_start_matches(':');
        normalized_content = format!("{}:{}", clean_key, trimmed_colons);
    }

    if let Some(c) = comment_part {
        format!("{} {}", normalized_content.trim_end(), c.trim_start())
    } else {
        normalized_content
    }
}

fn find_unquoted_colon(text: &str) -> Option<usize> {
    let mut quote = None;
    let mut escaped = false;
    let mut chars = text.char_indices().peekable();

    while let Some((index, ch)) = chars.next() {
        if let Some(quote_char) = quote {
            if quote_char == '"' && escaped {
                escaped = false;
            } else if quote_char == '"' && ch == '\\' {
                escaped = true;
            } else if quote_char == '\''
                && ch == '\''
                && chars.peek().map(|(_, next)| *next == '\'').unwrap_or(false)
            {
                chars.next();
            } else if ch == quote_char {
                quote = None;
            }
        } else if ch == '"' || ch == '\'' {
            quote = Some(ch);
        } else if ch == ':' {
            return Some(index);
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_magic_colon_recovers_missing_colon() {
        assert_eq!(apply_magic_colon("image nginx", false), "image: nginx");
        assert_eq!(
            apply_magic_colon("  name web-service", false),
            "  name: web-service"
        );
        assert_eq!(
            apply_magic_colon("- containerPort 80", false),
            "- containerPort: 80"
        );
    }

    #[test]
    fn test_magic_colon_ignores_stopwords() {
        assert_eq!(
            apply_magic_colon("This is a description", false),
            "This is a description"
        );
        assert_eq!(
            apply_magic_colon("Note that pods restart", false),
            "Note that pods restart"
        );
    }

    #[test]
    fn test_magic_colon_protects_command_strings_and_arbitrary_binaries() {
        // Any command in an args or command list must NEVER receive a colon
        assert_eq!(apply_magic_colon("- python main.py", false), "- python main.py");
        assert_eq!(apply_magic_colon("- git clone https://github.com/repo", false), "- git clone https://github.com/repo");
        assert_eq!(apply_magic_colon("- node server.js", false), "- node server.js");
        assert_eq!(apply_magic_colon("- cp -rLf /src /dst", false), "- cp -rLf /src /dst");
        assert_eq!(apply_magic_colon("- rm -rf /tmp/cache", false), "- rm -rf /tmp/cache");
        assert_eq!(apply_magic_colon("- sh -c \"echo hello\"", false), "- sh -c \"echo hello\"");
        assert_eq!(apply_magic_colon("- bash -e run.sh", false), "- bash -e run.sh");
        assert_eq!(apply_magic_colon("- envoy -c /etc/envoy.yaml", false), "- envoy -c /etc/envoy.yaml");
        assert_eq!(apply_magic_colon("- vault agent -config=/vault/config", false), "- vault agent -config=/vault/config");
        assert_eq!(apply_magic_colon("- custom-binary run", false), "- custom-binary run");
    }

    #[test]
    fn test_magic_colon_heals_known_sequence_mapping_properties() {
        assert_eq!(apply_magic_colon("- containerPort 80", false), "- containerPort: 80");
        assert_eq!(apply_magic_colon("- name web", false), "- name: web");
        assert_eq!(apply_magic_colon("- mountPath /data", false), "- mountPath: /data");
        assert_eq!(apply_magic_colon("- image nginx", false), "- image: nginx");
        assert_eq!(apply_magic_colon("- port 443", false), "- port: 443");
    }

    #[test]
    fn test_quote_balancing() {
        assert_eq!(
            apply_quote_balancing("image: \"nginx:latest", false),
            "image: \"nginx:latest\""
        );
        assert_eq!(
            apply_quote_balancing("env: 'production", false),
            "env: 'production'"
        );
    }

    #[test]
    fn test_spacing_repairs() {
        assert_eq!(apply_spacing("-item", false), "- item");
        assert_eq!(apply_spacing("key:value", false), "key: value");
        assert_eq!(
            apply_spacing("url: http://localhost", false),
            "url: http://localhost"
        );
        assert_eq!(
            apply_spacing("  \"quoted:key\": value", false),
            "  \"quoted:key\": value"
        );
        assert_eq!(
            apply_spacing("  'quoted:key': value", false),
            "  'quoted:key': value"
        );
        assert_eq!(apply_spacing("-XX:", false), "-XX:");
        assert_eq!(apply_spacing("-Xmx:", false), "-Xmx:");
        assert_eq!(apply_spacing("--flag", false), "--flag");
        assert_eq!(apply_spacing("-42", false), "-42");
    }

    #[test]
    fn test_scalar_header_and_semicolon_normalization() {
        // Multi-pipe and multi-folded scalars
        assert_eq!(apply_spacing("description: >>", false), "description: >");
        assert_eq!(apply_spacing("script: ||", false), "script: |");

        // Key semicolon
        assert_eq!(apply_spacing("metadata;", false), "metadata:");
        assert_eq!(apply_spacing("  spec;", false), "  spec:");

        // Multi colons and spacing
        assert_eq!(apply_spacing("metadata::", false), "metadata:");
        assert_eq!(apply_spacing("annotations :", false), "annotations:");
    }

    #[test]
    fn test_phase_3_quote_syntax_repairs() {
        // Mismatched boundary quotes
        assert_eq!(
            apply_quote_balancing("- \"-c'", false),
            "- \"-c\""
        );
        assert_eq!(
            apply_quote_balancing("command: '-c\"", false),
            "command: '-c'"
        );

        // Redundant triple quotes
        assert_eq!(
            apply_quote_balancing("tag: \"\"\"v1.2.3\"\"\"", false),
            "tag: \"v1.2.3\""
        );
        assert_eq!(
            apply_quote_balancing("msg: '''hello'''", false),
            "msg: 'hello'"
        );

        // Unescaped nested double quotes in shell one-liners
        assert_eq!(
            apply_quote_balancing("- \"echo \"starting server...\" && exec\"", false),
            "- \"echo 'starting server...' && exec\""
        );
    }

    #[test]
    fn test_document_boundaries_and_glued_quotes() {
        // Trap 19: Multiple dashes
        assert_eq!(apply_spacing("----", false), "---");
        assert_eq!(apply_spacing("-----", false), "---");

        // Trap 20: Glued comment
        assert_eq!(apply_spacing("---# Ingress doc", false), "--- # Ingress doc");

        // Trap 21: Ellipsis
        assert_eq!(apply_spacing("....", false), "...");
        assert_eq!(apply_spacing("...# end", false), "... # end");

        // Trap 23: Sequence dash glued to quote
        assert_eq!(apply_spacing("-\"/bin/sh\"", false), "- \"/bin/sh\"");
        assert_eq!(apply_spacing("-'-c'", false), "- '-c'");
    }

    #[test]
    fn test_unquoted_helm_and_uri_scalars() {
        // Trap 31: Unquoted Helm expression as mapping value
        assert_eq!(
            apply_quote_balancing("app.kubernetes.io/name: {{ .Values.name }}", false),
            "app.kubernetes.io/name: \"{{ .Values.name }}\""
        );
        assert_eq!(
            apply_quote_balancing("- {{ .Values.extraArg }}", false),
            "- \"{{ .Values.extraArg }}\""
        );

        // Trap 33: Unquoted connection URIs with colons
        assert_eq!(
            apply_quote_balancing("value: postgres://user:pass@db:5432/app", false),
            "value: \"postgres://user:pass@db:5432/app\""
        );
        assert_eq!(
            apply_quote_balancing("url: http://service.internal:8080/health", false),
            "url: \"http://service.internal:8080/health\""
        );
        assert_eq!(
            apply_quote_balancing("redis_uri: redis://cache:6379/0", false),
            "redis_uri: \"redis://cache:6379/0\""
        );

        // Trap 59: Unquoted wildcard host in Ingress
        assert_eq!(
            apply_quote_balancing("host: *", false),
            "host: \"*\""
        );
        assert_eq!(
            apply_quote_balancing("host: *.example.com", false),
            "host: \"*.example.com\""
        );
    }
}
