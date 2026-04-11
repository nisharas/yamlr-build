# yamlr rules

**Rule Catalog Dashboard**

Displays a comprehensive table of all active semantic rules, checkers, and healers available in the current version.

## Usage
```bash
yamlr rules [FLAGS]
```

## Flags
*   `-v, --verbose`: Show full rationale for every rule in an extra column.
*   `--output=json`: Export rule database as structured JSON.

## Columns
*   **ID**: The unique Rule ID (e.g., `rules/no-latest-tag`).
*   **Name**: Human-readable name.
*   **Severity**: ERROR, WARNING, or INFO.
*   **Description**: Brief summary of what the rule detects.

### 🛡 Global Performance Flags
Available across all commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.

## Examples
```bash
yamlr rules
# Lists all 50+ active rules
```
