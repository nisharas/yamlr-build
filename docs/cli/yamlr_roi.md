# yamlr roi

**Executive ROI & Budget Justification**

Displays high-fidelity ROI metrics, cost savings, and financial justification for the Yamlr investment.

## Usage
```bash
yamlr roi [FLAGS]
```

## Description
The `roi` command provides an executive-level view of the value Yamlr brings to your organization. It calculates wealth reclaimed through automation and risk prevention.

## Flags
*   `-h, --help`: Show this help message.
*   `--output=json`: Output statistics as structured JSON.

## Metrics Displayed
*   **Engineering Time Reclaimed**: Total hours saved by automated healing.
*   **Total Wealth Reclaimed**: Estimated financial value of reclaimed time (Default: $100/hr).
*   **Risk Prevention Surface**: Cumulative count of potential outages defused.
*   **Organization-Wide Proof of Value**: Impact aggregated across all workspaces on the machine.

## Philosophy
Yamlr calculates ROI based on surgical complexity weights:
- **Lexer/Syntax**: 2 minutes
- **Semantic/Logic**: 15 minutes
- **Security Hardening**: 30 minutes
- **API Migration**: 60 minutes

## Examples
```bash
# View the Executive ROI Dashboard
yamlr roi

# Export ROI data for budget meetings
yamlr roi --output=json
```

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).

---
*Note: This command uses aggregated local telemetry to prove organizational efficiency without compromising data privacy.*
