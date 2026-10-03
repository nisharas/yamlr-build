# Yamlr Configuration Guide
This document serves as the single source of truth for the `.yamlr.yaml` configuration file.

## File Structure
The configuration file is a standard YAML file found at the root of your project.

### 1. Rules Configuration
Customize global thresholds and specific rule ignores.

```yaml
rules:
  # The minimum health score (0-100) required to pass a scan.
  # If the score drops below this, 'yamlr scan' returns exit code 1.
  threshold: 70

  # List of Rule IDs to completely ignore during scanning.
  # Use 'yamlr rules' to see all available IDs.
  ignore:
    - "rules/no-latest-tag"
    - "rules/resource-limits"
```

### 2. File Ignoring
Exclude specific files or directories from processing.
```yaml
ignore:
  files:
    - "vendor/**"       # Ignore third-party charts
    - "tests/*.yaml"    # Ignore test fixtures
    - "**/*.bak"        # Ignore backup files
```

### 3. Output Settings [ROADMAP]
Control the default output format for CLI commands.
> **Note:** This section is currently a **ROADMAP** feature. CLI flags (e.g., `--output json`) must be used for now as config settings are ignored.

```yaml
output:
  # Options: text, json, sarif
  format: text
```

### 4. Analyzers (Advanced)
Fine-tune specific analyzer behavior. You can explicitly enable or disable analyzers.

> **Note:** Initial support for enabling/disabling analyzers is live via the `analyzers.enabled` key. Use `rules.ignore` for fine-grained rule suppression.

```yaml
analyzers:
  enabled:
    - "*"                     # Enable all by default
    - "-ghost_service"        # Disable Ghost Service detector (Planned)
  
  # Specific Analyzer Settings
  ghost_service:
    fuzzy_match_threshold: 70 # (0-100) Similarity score to suggest fixes (Default: 70)
```

### 5. Security (Pro)
Configure security hardening and trusted paths.
```yaml
security:
  # trusted_registries: Enforce image registry allow-lists
  trusted_registries:
    - "docker.io"
    - "quay.io"
    - "my-company.jfrog.io"

  # allowed_host_paths: Whitelist paths for HostPath volumes
  allowed_host_paths:
    - "/var/log"
```

### 6. Kubernetes Versioning
Force a specific Kubernetes version for validation.

**Version Priority (Highest to Lowest):**
1. **CLI Flag:** `--kube-version`
2. **Environment:** `Yamlr_KUBE_VERSION`
3. **Auto-Detect:** Pro Cluster/Kubectl detection
4. Config File: `kubernetes.version`
5. Auto-Resolution: `YamlrManager` falls back to bundled `distilled` catalog if no match found.
6. Default: `v1.31` (Supports range 1.9 -> 1.35+)

> **Note:** The config file setting below provides the default project-level baseline.
> **Developer Note:** To update the ultimate global fallback version for the engine itself, modify `default_version` in `src/yamlr/core/context.py` (inside `HealContext._get_default_cluster_version()`).

```yaml
kubernetes:
  version: "v1.28"  # Enforce 1.28 validation rules
```

### 7. Healing Configuration
Control automated fixing behavior globally. CLI flags always take precedence.

```yaml
healing:
  # Auto-inject context-aware CPU/Memory requests/limits.
  enforce_limits: true

  # Enforce industrial security hardening (dropping capabilities, read-only FS).
  harden: true

  # [NEW] Exit 1 if any finding exceeds this risk level (high, medium, low).
  risk_threshold: high

  # Auto-inject Liveness and Readiness probes.
  enforce_probes: false

  # Auto-pin image tags to :stable.
  fix_tags: true

  # Explicitly audit for and record deprecated Kubernetes APIs.
  # When enabled, findings will appear in reports and affect health scores.
  check_deprecations: false

  # Automatically orchestrate all fixes without prompting (Automated Healing Mode)
  # yamlr heal . --no-input

  # Scan from stdin (Standard Pipe Integration)
  # kubectl get deployment -o yaml | yamlr scan -

  # Automatically inject a default namespace for resources missing 'metadata.namespace'.
  enforce_namespace: true

  # [PRO] Cross-Resource Auto-Fix: selector/port mismatch and stub generation.
  # Leverages the ResourceGraph (17 edge types) for impact analysis.
  fix_refs: true

### 8. Safety Engine (Heuristics)
The Safety Engine uses heuristic scoring to classify risks into 15 categories.

```yaml
safety:
  # Minimum score (0-100) to consider a manifest 'Healthy'.
  # Below this, RiskClassifier triggers a HIGH/MEDIUM finding.
  health_threshold: 70
```
```

### 8. Logging [ROADMAP]
Control the verbosity and destination of Yamlr's internal logs.
> **Note:** Currently controlled via `--verbose` flag. Config file support is on the **ROADMAP**.

```yaml
logging:
  level: "INFO"     # DEBUG, INFO, WARNING, ERROR
```

### 9. Plugins [COMING SOON] 🧱
Register custom Python plugins for extended analysis.
> **Status:** Roadmap Feature. Not yet available in this version.

```yaml
plugins:
  paths:
    - "./custom_rules"
```

## Frequently Asked Questions

**Q: Can I use absolute paths in `ignore`?**
A: No, Yamlr `ignore` patterns are strictly **relative** to the workspace root for portability.

**Q: Why are there two `ignore` sections?**
A: They serve different purposes:
*   `rules.ignore`: Disables specific **Rule IDs** (e.g., "rules/no-latest-tag").
*   `ignore.files`: Excludes actual **Files** from being scanned (e.g., "node_modules/**").

**Q: How do I change the log location or output format?**
A: Currently, these are controlled via CLI flags (e.g. `--verbose`, `--output json`), not the config file.

**Q: Can I disable specific analyzers?**
A: Yes. You can explicitly enable or disable analyzers using the `analyzers.enabled` key in your `.yamlr.yaml` file. You can also ignore specific findings using `rules.ignore`.

**Q: What happens if I don't have a `.yamlr.yaml` file?**
A: Yamlr uses sensible defaults (e.g., Standard K8s v1.31 validation, all rules enabled). Run `yamlr init` to create one.

**Q: How do I reset my configuration to defaults?**
A: Run `yamlr init --force` to overwrite your existing `.yamlr.yaml` with the default template.

**Q: Can I ignore a rule for just one specific line or block?**
A: Currently, Yamlr supports **file-level** or **project-level** ignores. Inline comment-based ignores (e.g., `# yamlr:ignore`) are **(Coming Soon)**.

**Q: Does Yamlr support ignoring specific YAML documents in a multi-doc file?**
A: No, file ignores apply to the physical file. Use `rules.ignore` to suppress findings if needed.

**Q: How do I use Yamlr in CI/CD pipelines?**
A: Use `yamlr scan . --output sarif > report.sarif` for integration with GitHub Advanced Security, or use the exit code (1 for failure) to block builds.

**Q: Do I need a Pro license for basic scanning?**
A: No, basic semantic scanning (Yamlr Guard) is 100% free and unlimited. Automated healing (Yamlr Surgeon) is also free for up to 5 files per day. Enterprise features (Industrial Hardeneding, OPA, Compliance) require a Pro license.

**Q: Why is my `kubernetes.version` setting ignored?**
A: The CLI flag `--kube-version` or environment variable `Yamlr_KUBE_VERSION` always override the config file to ensure consistent behavior across environments.
## 🌍 Environment Variables Reference
Yamlr can be configured via environment variables for easy CI/CD integration.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `Yamlr_KUBE_VERSION` | Override target Kubernetes version (e.g. `1.30`) | `v1.31` |
| `Yamlr_LICENSE_KEY` | [Pro] Enterprise license key | N/A |
| `Yamlr_PRO`         | [Pro] Force enable Enterprise mode features | `false` |
| `Yamlr_LOG_LEVEL` | Engine verbosity (`DEBUG`, `INFO`, `ERROR`) | `INFO` |
| `Yamlr_OFFLINE`   | [Pro] Enable network kill switch (offline mode) | `false` |
| `Yamlr_CATALOG_PATH` | Path to custom schema catalog storage | `XDG_CONFIG_HOME/yamlr/catalogs` (POSIX) or `%APPDATA%/Yamlr/catalogs` (Windows) |
| `Yamlr_CATALOG_URL` | Upstream URL for catalog updates | GitHub |
| `Yamlr_PROVIDER` | Cluster provider hint (`eks`, `gke`, `minikube`) | `auto` |
| `Yamlr_KUBECTL_PATH` | Path to `kubectl` binary for oracle validation | `kubectl` |
| `Yamlr_TERMINAL_WIDTH`| Force TUI width | Auto |
| `Yamlr_QUIET` | Minimal output for CI/CD | `false` |
| `Yamlr_PLAIN` | ASCII-only output mode | `false` |
| `Yamlr_DOCS_PATH` | Path to User Guide markdown for `manual` command | `docs/` |
| `NO_COLOR` | Disable ANSI colors in output (Standard) | N/A |
| `FORCE_COLOR` | Force ANSI colors even on non-TTY (Standard) | N/A |
| `YAMLR_CLASSIC` | Force kubectl-style help (classic mode) | `false` |
| `ARGOCD_APP_NAME` | GitOps Integration: Detects Argo CD environment | N/A |
| `FLUX_KUSTOMIZATION_NAME` | GitOps Integration: Detects Flux environment | N/A |
| `FLUX_HELM_RELEASE_NAME` | GitOps Integration: Detects Flux environment | N/A |
| `PYTHONUTF8` | Ensure UTF-8 handling on Windows | `1` |
