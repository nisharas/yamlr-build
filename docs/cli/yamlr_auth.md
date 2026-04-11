# yamlr auth

**Enterprise Authentication**

Manages authentication for Yamlr Enterprise features (Pro).

## Usage
```bash
yamlr auth [COMMAND]
```

## Commands
*   `login`: Initiates a Device Flow login to Yamlr Cloud. Unlocks Pro features like OPA integration and Remote Bundles on this machine.
*   `logout`: Clears local credentials.
*   `status` / `whoami`: Checks current authentication state.

## Examples
```bash
yamlr auth login
# Follow the prompts to authenticate via browser
```

### 🛡 Global Performance Flags
Available across all commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
