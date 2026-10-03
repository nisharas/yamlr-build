# yamlr founder

**Strategic Command Center**

The `founder` command is a privileged operational dashboard designed for the Yamlr project founder to monitor ecosystem health and strategic metrics.

## Usage
```bash
yamlr founder [ACTION]
```

## Description
Aggregates global telemetry (anonymized) to provide a macro-view of product performance, rule efficacy, and user friction points.

## Actions
*   **`dashboard`**: (Default) Show high-level strategic KPI dashboard.
*   **`errors`**: View the latest anonymized fatal exception reports from the community.

## Output
Displays real-time metrics including:
*   Global ROI (Wealth Reclaimed)
*   Rule Heatmap (Most frequently triggered rules)
*   Top 10 failing K8s clusters (by version)
*   Infrastructure health of the license server

## Examples
```bash
yamlr founder dashboard
```

## Privacy & Security
This command only displays data that has been explicitly anonymized and uploaded via the telemetry layer. No raw YAML data or PII is ever visible in the founder dashboard.
