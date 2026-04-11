# yamlr audit
**Deep Compliance Audit (Alias for [scan](yamlr_scan.md))**

Compliance-focused alias for `yamlr scan`.

## Usage
```bash
yamlr audit [PATH]... [FLAGS]
```

## 🔬 Scientific Mode (Benchmarking)
Benchmarking the healing engine against a known-good corpus.

```bash
# Run a full benchmark
yamlr audit ./tests/corpus --bench

# View HAS (Healing Accuracy Score)
yamlr audit ./tests/corpus --bench --stats
```

### Metrics Produced:
*   **HAS (Healing Accuracy Score)**: Percentage of manifests successfully healed.
*   **Detect Rate**: Percentage of issues identified.
*   **Reconstruction Depth**: Light, Medium, or Heavy repairs.

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--output FORMAT`**: Report format (text, json, sarif).
*   **`--bench`**: Run in 'Scientific Mode' against a labeled corpus.
*   **`--stats`**: Show summary stats only for the benchmark.
*   **`--verify <RECEIPT>`**: Verify a .yamlr-receipt.json against its target manifest.
*   **`--risk-threshold <high|medium|low>`**: Exit with code 1 if any finding meets or exceeds risk level.
*   **`--fail-on <CHOICE>`**: CI/CD Gate: Exit 1 if specified severity found.
*   **`--baseline <FILE>`**: Path to violation baseline (SHA-256 fingerprints to ignore).
*   **`--fast`** [PRO]: Enable lightning-fast scanning via native Rust extension.
*   **`--kube-version <V>`**: Force specific K8s version (e.g., 1.31).
*   **`--max-depth <N>`**: Limit recursion depth (Default: 10).
*   **`--strict`**: Treat warnings as hard errors.
*   **`--compact`**: Minify output (2-space indent).
*   **`--health-threshold <0-100>`**: Min score to pass (Default: 70).
*   **`--check-deprecations`**: Audit for and record deprecated APIs.
*   **`--summary-only`**: Aggregate stats only.
*   **`--plain`**: ASCII-only output mode.
*   **`--verbose`**: Full audit logs and engine stages.
*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`-q`, `--quiet`**: Minimal output mode (exit codes only).
*   **`--diff`** / **`--dry-run`**: Show proposed fixes as a preview.
