# yamlr catalog

Yamlr validates your manifests against official Kubernetes JSON schemas. These schemas are distilled for performance and cached locally in `~/.Yamlr/catalogs`.

The `yamlr catalog` command allows you to manage this local cache.

## Usage

```bash
# Check status of local catalog
yamlr catalog
```

### Update Catalog
Download the latest schemas from the upstream repository.
```bash
yamlr catalog update
```

### List Versions
See which Kubernetes versions are currently available in your local cache.
```bash
yamlr catalog list
```

## Options
*   **`--kube-version V`**: Target version for catalog operations (alias: **`--k8s-version`**).

### 🛡 Universal Expert Flags
Available across primary commands:

*   **`--timing`**: [PERFORMANCE] Output surgical execution timing breakdown.
*   **`--timing-file <FILE>`**: [PERFORMANCE] Save performance profiling data to a JSON file.
*   **`--verbose`**: Full audit logs and engine stages.
*   `-q`, `--quiet`: Minimal output mode (exit codes only).
