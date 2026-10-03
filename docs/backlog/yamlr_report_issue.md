# `yamlr report-issue`

**Upload redacted local forensic logs for analysis.**

The `report-issue` command allows you to share diagnostic data with the Yamlr support team while ensuring your sensitive information remains private.

## Usage

```bash
yamlr report-issue [options]
```

## Description

This command performs a multi-stage redaction of your local logs and environment data before uploading a forensic bundle to our secure support endpoint.

**Automatic Redaction includes:**
- Absolute system paths (HOME, TMP, CWD)
- Sensitive environment variables (Secrets, Tokens)
- Kubernetes manifest content (unless explicitly authorized)

## Options

| Flag | Description |
|:--|:--|
| `--bundle PATH` | Path to a pre-generated diagnostic bundle (from `yamlr diagnose --bundle`) |
| `--comment TEXT` | Add a human description to the report |
| `--no-upload` | Redact and package the bundle locally without uploading |

## Strategic Value

1. **Enterprise Supportability**: Enables rapid resolution of complex environmental issues without compromising security.
2. **Zero-PII Compliance**: Built-in redaction engine ensures that your forensic data complies with SOC2 and GDPR requirements.

---

* Use `yamlr diagnose --bundle` first to generate a diagnostic package.*
