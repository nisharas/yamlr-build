# yamlr baseline
**Snapshot Current Violations to Ignore in Future Scans**

The `baseline` command is a core component of the **GitOps Guard** strategy. It allows teams to adopt Yamlr on legacy codebases by "fingerprinting" all existing violations and saving them to a JSON file. Future scans can then use this file to ignore those specific issues, ensuring that only **new** regressions block your CI/CD pipelines.

## Usage
```bash
yamlr baseline [PATH]... [FLAGS]
```

## Description
Scans your manifests and generates a `.yamlr-baseline.json` file (by default) containing SHA-256 fingerprints of every finding.

### Fingerprint Integrity
Fingerprints are generated based on:
1.  **Rule ID**: The specific check that failed.
2.  **Resource Identity**: The `kind` and `name` of the resource.
3.  **Normalized Path**: The workspace-relative path to the file.
4.  **Message Context**: The specific error message.

> [!NOTE]
> **Line numbers are excluded** from the fingerprint. This ensures that the baseline remains valid even if you add or remove lines elsewhere in the file.

## Options
*   `--output <PATH>`: Custom path for the baseline file (Default: `.yamlr-baseline.json`).
*   `--ext <EXTENSIONS>`: Extensions to process (Default: `.yaml,.yml`).
*   `--max-depth <N>`: Limit directory recursion.

## How to use in CI/CD (GitOps Guard)

1.  **Establish Baseline**: Run once on your main branch.
    ```bash
    yamlr baseline . --output .yamlr-baseline.json
    git add .yamlr-baseline.json && git commit -m "docs: establish yamlr baseline"
    ```

2.  **Enforce in PRs**: Use the `--baseline` flag in your PR checks.
    ```bash
    yamlr scan . --baseline .yamlr-baseline.json --fail-on any
    ```
    Yamlr will return **exit code 0** (PASS) if all findings are in the baseline, and **exit code 1** (FAIL) only if a new violation is introduced.

### Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).

## See Also
- [yamlr scan](yamlr_scan.md) - Deep audit with baseline filtering support.
- [yamlr dna](yamlr_dna.md) - Mathematical proof of semantic integrity.
