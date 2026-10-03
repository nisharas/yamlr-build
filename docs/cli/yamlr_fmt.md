# yamlr fmt
**Canonical Kubernetes Manifest Formatter (k8sfmt / yamlfix)**

The `fmt` command canonicalizes the layout of Kubernetes manifests according to the official Kubernetes OpenAPI schema hierarchy, emulating the authority of `gofmt` for Kubernetes manifests.

## Usage
```bash
yamlr fmt [PATH] [FLAGS]
```

## Description
Formats manifest key ordering and indentation deterministically:
*   **Canonical Ordering**: Reorders root keys to the authoritative Kubernetes hierarchy:
    `apiVersion` -> `kind` -> `metadata` -> `spec` -> `data` -> `status`.
*   **Comment & Blank-Line Preservation**: Preserves all inline and block comments, whitespace, and formatting.
*   **POSIX Pipe Streaming**: Supports stdin/stdout streaming via `-`:
    ```bash
    cat deployment.yaml | yamlr fmt - | kubectl apply -f -
    helm template my-chart | yamlr fmt - | gitops-sync
    ```

## Flags
*   `-w, --write`: Write formatted output back to source files in-place (default prints to stdout).

The target path defaults to `.`. Use `-` to read from stdin. Unknown options and multiple target paths are rejected. Read, traversal, and write failures return a nonzero system-error status.

## Examples
```bash
# Preview formatting of all manifests in the current directory
yamlr fmt .

# Format and rewrite manifests in-place
yamlr fmt -w ./k8s

# Format a single manifest streamed through a Unix pipeline
helm template my-chart | yamlr fmt -
```
