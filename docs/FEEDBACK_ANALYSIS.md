# Feedback Analysis & Implementation Strategy

## 1. Critical Issues (Must Fix)

### A. Error Paths & Silent Failures ✅ **RESOLVED**
**Issue:** Pipeline returns `raw_yaml` on error, making it impossible to distinguish "No changes needed" from "Crash/Failure".
**Impact:** High. Callers (CLI/Engine) assume success when it actually failed.
**Resolution:** 
- ✅ Modified `HealingPipeline.heal()` to return a `HealResult` dataclass containing `status` enum (`SUCCESS`, `SKIPPED`, `FAILED`).
- ✅ Exceptions are caught and result in a `FAILED` status with error message.
- **Verified in:** `src/yamlr/core/pipeline.py` (Lines 61, 262, 303, 337, 345, 615)

### B. Brittle Penalty Logic (String Matching) ✅ **RESOLVED**
**Issue:** `cross_resource_penalty` matches strings like "Ghost Service".
**Impact:** Medium. Renaming an analyzer message allows bugs to slip through (penalty drops to 0).
**Resolution:** 
- ✅ Updated `AnalysisResult` to carry a `rule_id` field (e.g., `graph/ghost-service`).
- ✅ Updated penalty calculation to use `rule_id` instead of message strings.
- **Verified in:** `src/yamlr/analyzers/base.py`, `best_practices.py`, `cross_resource.py`

### C. OSS/Pro Split Confusion (Scanner) ⚠️ **PARTIALLY RESOLVED**
**Issue:** "No valid K8s resources found" looks like a parse error when it's actually just Strict Mode filtering.
**Impact:** High (UX). Confuses users.
**Status:**
- ✅ `identity_mode` parameter exists in `pipeline.py` (supports `strict` vs `infer`)
- ❌ CLI flag `--identity-mode` is NOT yet exposed in CLI commands
- ❌ "Skipped" messaging needs improvement
**Remaining Work:** 
- Add `--identity-mode=strict|infer` flag to `scan` and `heal` commands
- Update CLI output to clearly distinguish "Skipped" from "Failed"

## 2. Strategic Improvements (High Value)

### A. Deprecation Reporting
**Issue:** Deprecation info is buried in the result object.
**Value:** High. One of the main value props is "Modernizing Manifests".
**Plan:** 
- Add a dedicated "Deprecations" table/block in the CLI output.
- Group by `kind` (e.g., "3 Deployments using v1beta1").

### B. Structured Pipeline Stats
**Issue:** Logs are unstructured; hard to verify performance/counts programmatically.
**Value:** Medium (DevEx).
**Plan:**
- Return a `PipelineStats` dict/object from `heal()` with:
    - `shards_parsed`: int
    - `lexer_repairs`: int
    - `analyzers_run`: int
    - `timings`: dict

## 3. Items to Defer or Discard

### A. `ensure_dual_identity` Self-Replication
**Feedback:** "Risks surprising ops teams."
**Analysis:** Valid concern for a mature tool. However, for this aggressive "viral" growth phase, this feature is intentional (making `yamlr` and `kubecuro` synonymous).
**Decision:** **Defer**. We will add a check to only do this if specifically requested or in an interactive session, but for now, the viral behavior is a "feature".

### B. Registry Metadata Object
**Feedback:** "Plugin metadata object would simplify validation."
**Analysis:** Good engineering, but `BaseAnalyzer` class attributes (`name`, `analyzer_type`) are sufficient for now.
**Decision:** **Defer**. Over-engineering for the current stage.

### C. Configurable Thresholds
**Feedback:** "Allow usage weighting via config."
**Analysis:** Adds config complexity.
**Decision:** **Defer**. Keep it opinionated for now. "Yamlr knows best."

## Implementation Roadmap

1.  **Refactor Pipeline Return Type**: created `HealResult` dataclass to replace the giant Tuple.
2.  **Fix Scoring Logic**: Switch from string matching to `rule_id`.
3.  **Enhance Scanner/CLI**: Add `--identity-mode` flag and improve "Skipped" messaging.
4.  **CLI Polish**: Add Deprecation Summary block.
