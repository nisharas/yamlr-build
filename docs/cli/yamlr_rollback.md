# yamlr rollback

Perform an atomic reversal of the most recent remediation session.

`yamlr rollback` (and its alias `yamlr restore`) provides an instant, zero-friction safety net. Whenever `yamlr heal`, `yamlr fmt -w`, or automated policy fixes modify files on disk, Yamlr captures an immutable checkpoint before applying any mutations.

## Usage

### Rollback Last Session
Reverts all files modified in the latest healing run back to their exact pre-run byte state:
```bash
yamlr rollback
```

### Rollback Within Specific Target Path
```bash
yamlr rollback ./manifests
```

## How It Works
1. **Atomic Checkpoints**: Before any in-place mutation, the `BackupManager` stages pre-mutation copies inside `<workspace>/.yamlr/backups/`.
2. **Reverse Patching**: Executing `rollback` restores original files with bit-for-bit fidelity, preserving original timestamps and permissions.
3. **Session Removal**: Once rolled back, the session checkpoint is safely retired to prevent double-restoration conflicts.

## See Also
* [`yamlr restore`](yamlr_restore.md) — Canonical restore command.
* [`yamlr heal`](yamlr_heal.md) — Autonomous remediation engine.
