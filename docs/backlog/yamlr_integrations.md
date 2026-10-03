# yamlr integrations
**CI/CD Template Marketplace**

The `yamlr integrations` command provides production-ready CI/CD templates to bridge the gap between local manifest auditing and automated pipeline enforcement.

## Usage

```bash
# Export GitLab CI template
yamlr integrations gitlab

# Export Jenkins Pipeline snippet
yamlr integrations jenkins
```

## Description

To ensure "Zero-Touch" adoption in large organizations, Yamlr provides opinionated integration templates. These templates are optimized for:
- **Performance**: Uses deterministic caching and shallow cloning where applicable.
- **Observability**: Standardized SARIF output for GitHub/GitLab security dashboards.
- **Safety**: Enabling strict GitOps gates that block deployments on critical safety regressions.

## Supported Platforms

### 1. GitLab CI (`gitlab`)
Generates a `.gitlab-ci.yml` job definition that can be included in your main pipeline.
- **Features**: Merge Request security reports, code quality artifacts, and pipeline badges.

### 2. Jenkins (`jenkins`)
Generates a `Jenkinsfile` stage snippet compatible with modern Pipeline-as-Code.
- **Features**: Specialized pipeline steps for `yamlr scan` and `yamlr heal --dry-run` to provide feedback to developers.

## Examples

### GitLab CI Integration
```bash
yamlr integrations gitlab > .yamlr-ci.yml
```
Then include it in your `.gitlab-ci.yml`:
```yaml
include:
  - local: '.yamlr-ci.yml'
```

---

> [!NOTE]
> This command is part of the **Yamlr Ecosystem** and is available in the Free version to encourage best-practice GitOps adoption.
