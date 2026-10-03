# yamlr check

Run a read-only schema and integrity check against a manifest or directory. The command does not heal or rewrite files.

## Usage

```text
yamlr check [PATH] [OPTIONS]
```

With no path, the command checks the current directory. Directories are traversed recursively for `.yaml` and `.yml` files. The path and options may appear in any order. Only one target path and one instance of each value option are accepted; unsupported options return a usage error.

## Options

- `-k`, `--k8s-version`, `--kube-version <VERSION>`: Kubernetes schema version (default `1.30`).
- `--fail-on <error|warning|note|any|info|none>`: Minimum finding severity that makes the command fail (default `error`).
- `-q`, `--quiet`: Suppress normal output while preserving the exit status.

Examples:

```bash
yamlr check ./manifests
yamlr check --k8s-version 1.30 ./manifests --fail-on warning
yamlr check ./deployment.yaml --quiet
```

## Exit status

- `0`: No findings met the selected severity threshold.
- `1`: One or more findings met the threshold.
- `2`: The target path does not exist or the requested threshold is invalid.
- `3`: An unsupported or malformed option was supplied.
- `4`: A manifest could not be read or directory traversal failed.
