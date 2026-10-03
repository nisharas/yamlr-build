# yamlr restore

Accidents happen. `yamlr restore` is your safety net.

Every time `yamlr heal`, `upgrade`, or `secure` modifies a file, it creates a timestamped backup in the `.yamlr/backups` directory.

## Usage

### List Backups
View all available recovery points.
```bash
yamlr restore
```
*Output:*
```text
Found 3 backups:
1. demo.yaml (2023-10-27 10:00:01)
2. deployment.yaml (2023-10-27 09:55:00)
...
```

### Restore Everything
Revert to the state immediately before the last operation.
```bash
yamlr restore .
```

### Restore Specific File
```bash
yamlr restore ./manifests/deployment.yaml
```

## How It Works
*   **Location**: Backups are stored in `<project_root>/.yamlr/backups/`.
*   **Rotation**: Yamlr automatically rotates backups to prevent disk bloat (keeps last 5 by default).
*   **Security**: Backup files are created with restricted permissions (`0o600`).

> **Warning**: If you used `--unsafe=Secret` during healing, your backups may contain sensitive data. Ensure `.yamlr/` is in your `.gitignore`.

### Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).
