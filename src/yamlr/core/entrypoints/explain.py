import os
import pkgutil
import sys
import inspect

import yaml
from rich.markdown import Markdown
from rich.panel import Panel

SEVERITY_DISPLAY = {
    "critical": "Blocker",
    "error": "Blocker",
    "high": "Risky",
    "warning": "Warning",
    "mixed": "Warning",
    "info": "Note",
}


def display_severity(raw: str) -> str:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return SEVERITY_DISPLAY.get(raw.lower(), raw)


def load_rules():
    """Loads rules from the data directory using robust discovery."""
    from yamlr.core.utils import resolve_bundled_asset
    
    # Try the most common locations for the rules database
    rules_path = resolve_bundled_asset("core/data/rules.yaml") or resolve_bundled_asset("rules.yaml")
    
    if rules_path and rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except Exception:
                return {}

    # Try pkgutil as a last-resort fallback
    try:
        data = pkgutil.get_data("yamlr.core.data", "rules.yaml") or pkgutil.get_data("yamlr.core.entrypoints", "rules.yaml")
        if data:
            return yaml.safe_load(data) or {}
    except:
        pass

    return {}

    return {}

    return {}


RULEDB = load_rules()
RULE_DB = RULEDB


def handle_explain_command(args, console):
    """
    Explains a specific rule or lists available rules.
    """
    rule_id = args.rule_id

    if not rule_id:
        console.print("[bold cyan]Available Rules:[/bold cyan]")
        for rid, data in RULEDB.items():
            console.print(f" - [bold]{rid}[/bold]: {data.get('name', 'Unknown')}")
        console.print("\n[dim]Usage: yamlr explain <rule_id>[/dim]")
        return 0

    # Special Case: Config Documentation
    if rule_id.startswith("config"):
        return _explain_config(rule_id, console)

    # 🛡 Robust Resolution: Check for prefix-less match across all known namespaces
    data = RULEDB.get(rule_id)
    if not data:
        # Search for any rule that ends with the requested slug
        # e.g. 'validation-error' -> 'schema/validation-error'
        # e.g. 'required-labels' -> 'policy.rego/required-labels'
        candidates = [rid for rid in RULEDB.keys() if rid.endswith(f"/{rule_id}") or rid == rule_id]
        
        if len(candidates) == 1:
            rule_id = candidates[0]
            data = RULEDB.get(rule_id)
        elif len(candidates) > 1:
            # Ambiguity: prefer 'rule/' prefix if available as it's the most common
            preferred = next((c for c in candidates if c.startswith("rule/")), candidates[0])
            rule_id = preferred
            data = RULEDB.get(rule_id)

    if not data:
        console.print(f"[red]❌ Unknown rule or config ID: {rule_id}[/red]")
        console.print(
            "[dim]Try 'yamlr explain config' or see 'yamlr rules' for valid IDs.[/dim]"
        )
        return 1

    raw_severity = data.get("severity", "")
    shown_severity = display_severity(raw_severity)

    description = (data.get("description", "") or "").strip()
    rationale = (data.get("rationale", "") or "").strip()
    remediation = (data.get("remediation", "") or "").strip()
    example = data.get("example")

    content_parts = []

    content_parts.append(f"**Severity:** {shown_severity}\n")

    if description:
        content_parts.append("### Description")
        content_parts.append(description)
        content_parts.append("")

    if rationale:
        content_parts.append("### Rationale")
        content_parts.append(rationale)
        content_parts.append("")

    if remediation:
        content_parts.append("### Remediation")
        content_parts.append(remediation)
        content_parts.append("")

    if example:
        content_parts.append("### Example")
        # Wrap as fenced code block so Rich preserves formatting
        content_parts.append("```yaml")
        content_parts.append(example.rstrip())
        content_parts.append("```")
        content_parts.append("")

    content = "\n".join(content_parts).rstrip() + "\n"

    console.print(
        Panel(
            Markdown(content),
            title=f"[bold magenta]📜 Rule: {data.get('name', 'Unknown')} ({rule_id})[/bold magenta]",
            border_style="magenta",
        )
    )

    return 0


def _explain_config(topic_id: str, console) -> int:
    """
    Renders configuration documentation for the user.
    IDs: config, config/rules, config/ignore, config/security, etc.
    """
    from rich.markdown import Markdown
    from rich.panel import Panel

    # Map sub-topics to content
    CONFIG_DOCS = {
        "config": """
# ⚙️ Yamlr Configuration (.yamlr.yaml)
The configuration file allows you to customize rules, security, and ignores.

## Quick Start
Run `yamlr init` to generate a starter file.

## Sections
- `config/rules`: Adjust thresholds and ignore specific rules.
- `config/ignore`: Exclude files from scanning.
- `config/output`: Configure reporting formats.
- `config/analyzers`: Fine-tune specific analyzers.
- `config/security`: Trusted registries and allowed paths.
- `config/kubernetes`: Force specific K8s versions.
- `config/logging`: Debug settings.
- `config/plugins`: Experimental plugin paths.
- `config/cicd`: CI/CD gates and exit code enforcement.
- `config/scale`: Ultra-scale streaming and performance.
- `config/healing`: Auto-injection and deprecation auditing.
- `config/discovery`: How to find rules, docs, and hidden features.
- `config/faq`: Frequently Asked Questions.
        """,
        "config/cicd": """
# 🚀 CI/CD Gates (.yamlr.yaml)
Yamlr can act as a hard gate in your pipelines.

## Fail-On Severity
Exit with code 1 if specific issues are found.
CLI: `--fail-on <error|warning|any>`

## Default Behavior
`yamlr check` is optimized for PRs:
- Defaults to `--strict`
- Defaults to `--summary-only`
        """,
        "config/scale": """
# ♾️ Ultra-Scale Performance
Yamlr is verified for repositories with 70,000+ files.

## Memory Safety (Streaming)
Use `--stream-to results.ndjson` to prevent RAM saturation.
This enables O(1) memory growth regardless of repository size.

## Concurrency
Yamlr uses all available CPU cores by default.
Limit via `--concurrency N` for shared CI environment.
        """,
        "config/healing": """
# 🩹 Healing & Upgrades
Customize how Yamlr repairs your manifests.

```yaml
healing:
  check_deprecations: true  # Audit for stale APIs
  fix_tags: true           # Auto-pin :stable tags
  enforce_limits: true      # Inject CPU/Mem requests
```
        """,
        "config/rules": """
# 📏 Rules Configuration
Control how strict the scanner should be.

```yaml
rules:
  threshold: 70         # Fail if score < 70
  ignore:               # Ignore specific Rule IDs
    - "rules/no-latest-tag"
```
        """,
        "config/faq": """
# ❓ Configuration FAQ

**Q: Missing Config?**
A: Yamlr uses safe defaults (K8s v1.31). Run `yamlr init` to create one.

**Q: Reset to Default?**
A: Run `yamlr init --force`.

**Q: CI/CD?**
A: `yamlr scan . --output sarif` (Exit code 1 on failure).

**Q: Inline Ignores?**
A: Not yet. Use `rules.ignore` in config.

**Q: Pro vs Free Version?**
A: Basic scanning is free. Security hardening is Pro.
        """,
        "config/ignore": """
# 🙈 File Ignoring
Exclude files from processing using glob patterns.

```yaml
ignore:
  files:
    - "vendor/**"
    - "tests/*.yaml"
```
        """,
        "config/output": """
# 📊 Output Settings
Customize how Yamlr reports its findings.

```yaml
output:
  format: text      # text, json, sarif
  compact: false    # Minimal whitespace for CI
  verbose: false    # Show full audit traces
```
        """,
        "config/security": """
# 🔐 Security Settings (Pro)
Hardening features for enterprise environments.

```yaml
security:
  allowed_host_paths:
    - "/var/log"
  trusted_registries:
    - "docker.io"
```
        """,
        "config/analyzers": """
# 🧠 Analyzer Settings
Configure complex scanners like the Ghost Service detector.

```yaml
analyzers:
  ghost_service:
    enabled: true
    fuzzy_match: true # Suggest close matches for selectors
```
        """,
        "config/kubernetes": """
# ☸️ Kubernetes Settings
Force validation for a specific version.

**Version Priority (Highest to Lowest):**
1. ` --kube-version` flag
2. `Yamlr_KUBE_VERSION` env var
3. Pro Auto-Detection
4. Default (`v1.31`)

> **Note:** This can be overridden by the `--kube-version` flag or `Yamlr_KUBE_VERSION` environment variable.

```yaml
kubernetes:
  version: "v1.28"
```
        """,
        "config/logging": """
# 📝 Logging
Debug Yamlr internally.

> **Note:** Currently requires `--verbose` flag.

```yaml
logging:
  level: "DEBUG"
  file: ".yamlr/debug.log"
```
        """,
        "config/plugins": """
# 🔌 Plugins (Experimental)
Load custom rules from local paths.

> **Status:** Roadmap Feature.

```yaml
plugins:
  paths:
    - "./my-rules"
```
        """,
        "config/discovery": """
# 🔎 Value Discovery
Yamlr is built to be self-documenting. Use these commands to find what you need.

## 1. Rule Directory
See every protection Yamlr enforces:
`yamlr rules`
`yamlr rules --verbose` (Shows the 'Rationale' behind every rule)

## 2. Dynamic Explanation
Learn about any rule or config key:
`yamlr explain rule/no-latest-tag`
`yamlr explain config/security`

## 3. The Offline Manual
Read the complete implementation guide without leaving the terminal:
`yamlr manual`

## 4. Live Health Dashboard
See your project's compliance status:
`yamlr status`
        """,
    }

    content = CONFIG_DOCS.get(topic_id)
    if not content:
        console.print(f"[red]❌ Unknown config topic: {topic_id}[/red]")
        console.print("[dim]Available: config, config/rules, config/ignore, config/security, config/analyzers[/dim]")
        return 1
    
    console.print(
        Panel(
            Markdown(inspect.cleandoc(content)),
            title=f"[bold cyan]Documentation: {topic_id}[/bold cyan]",
            border_style="cyan",
        )
    )
    return 0
