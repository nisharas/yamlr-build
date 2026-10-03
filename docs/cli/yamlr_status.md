# yamlr status

**Engine Health & Licensing Dashboard**

Displays an operational dashboard of the current Yamlr engine, native core linkage, active Kubernetes schema catalogue, and licensing tier.

## Usage
```bash
yamlr status [OPTIONS]
```

## Argument Groups

### Primary Options
*   `--output {text,json}`: Output format (human-readable panel or structured JSON). Default: `text`.

### CI/CD & Pipeline Integration
*   `-f, --output-file <FILE>`: Path to write structured report (JSON).
*   `--exit-zero`: Always exit with code 0.

## Output Fields
*   **Engine Version**: Active Yamlr CLI release.
*   **Build ID**: Native core PyO3 build identifier.
*   **Machine ID**: Deterministic host identifier for license binding.
*   **Registry**: Status of the 16 offline Kubernetes schema versions (1.21-1.36).
*   **Acceleration**: Status of native AVX2/NEON SIMD acceleration.
*   **License**: Community Edition or Enterprise Pro entitlement.

## Examples
```bash
# Terminal status panel
yamlr status

# Machine-readable JSON output for automation
yamlr status --output json
```
