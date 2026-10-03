# yamlr heal
**Manifest Auto-Remediation**

The `yamlr heal` command previews or applies native Rust manifest repairs. It can process a YAML file, a directory of YAML files, stdin, Helm values, or a rendered Kustomize overlay.

---

## Synopsis

```bash
yamlr heal [path] [flags]
```

---

## Safety by Default

By default, `yamlr heal` operates in **preview mode** (safe-by-default). It analyzes files and prints recommended remediations without altering disk state.

*   To preview exact visual AST diffs: run `yamlr heal --diff`.
*   To preview without applying changes: run `yamlr heal --dry-run`.
*   To apply verified changes to disk: run `yamlr heal --apply`.

For regular YAML files, `--apply` creates a temporary sibling `.bak` safety copy, validates the written YAML, then removes the copy after successful validation. If writing or validation fails, Yamlr attempts to restore the original and reports any rollback failure.

---

## Examples

```bash
# Preview proposed repairs for the current directory
yamlr heal .

# Preview side-by-side visual diff of proposed changes
yamlr heal . --diff

# Apply all verified repairs directly to disk
yamlr heal . --apply

# Heal a specific deployment manifest
yamlr heal ./k8s/deploy.yaml --apply

# Audit and heal rendered Helm chart values in-memory
yamlr heal ./charts/my-app --helm --apply

# Audit and heal Kustomize overlays in-memory
yamlr heal ./overlays/production --kustomize --diff

# Ingest an OPA Gatekeeper policy report
yamlr heal . --ingest-opa ./reports/gatekeeper-violations.json --apply

# Ingest a Kyverno PolicyReport
yamlr heal . --ingest-kyverno ./reports/kyverno-report.json --apply

# Force target Kubernetes version schema rules
yamlr heal . --k8s-version 1.31 --apply

# Read YAML from stdin
yamlr heal - < ./deployment.yaml
```

---

## Options & Flags

### Primary Remediation Options

*   **`path`** *(positional, optional)*:
    Path to manifest file, directory, or `-` for stdin. Defaults to `.`.
*   **`--apply, -a`**:
    Apply fixes directly to the input files. Regular YAML files receive a sibling `.bak` backup before writing.
*   **`--diff`**:
    Display an inline diff of the proposed changes.
*   **`--dry-run, -d`**:
    Preview repairs without writing them. This is the default unless `--apply` or `--diff` is specified.

### Targeting & Environment

*   **`--k8s-version, --kube-version, -k <VERSION>`**:
    Select the Kubernetes schema version used by the healer. Defaults to `1.30`.
*   **`--helm`**:
    Process Helm chart values in the target directory.
*   **`--kustomize`**:
    Render and process a Kustomize directory. With `--apply`, writes the healed composite to `kustomize_healed.yaml` in that directory.

### Policy & Tool Ingestion

*   **`--ingest-opa <PATH>`**:
    Ingest an Open Policy Agent (OPA) / Gatekeeper JSON violation report.
*   **`--ingest-kyverno <PATH>`**:
    Ingest a Kyverno `PolicyReport` JSON export.

### CI/CD & Pipeline Integration

*   **`--output, -o text`**:
    Text is the only supported output format. Other formats are rejected.
*   **`--exit-zero`**:
    Return `0` for findings from the completed heal operation. Input, traversal, and write failures still return errors.
*   **`--generate-stubs, --create-stubs`**:
    Generate missing resource stubs; `--apply` writes them to `yamlr_generated_stubs.yaml`.
*   **`--otel, --export-metrics`**:
    Print OpenTelemetry metrics after processing.

Unknown options and more than one target path are rejected. The command does not support `--crd`, `--output-file`, or `--push-telemetry`.

---
