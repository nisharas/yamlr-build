# Download Yamlr

## ⬇ Download Binaries

Standalone binaries are available for Windows, Linux, and macOS. These are the **only** supported way to run Yamlr Pro and ensure 100% compatibility with our security engine.

### Package Managers (Official)
We are currently rolling out to official repositories:
*   **macOS/Linux:** `brew install yamlr/tap/yamlr`
*   **Windows:** `choco install yamlr`

### Manual Download
Select an exact release tag when installing. Installers verify the archive checksum and GitHub release attestation before installing; GitHub CLI (`gh`) is required for provenance verification. No Python is required.

| Platform | Arch | Link |
| :--- | :--- | :--- |
| **Windows** | `x86_64` | `yamlr-windows-x86_64.zip` |
| **Linux** | `x86_64` / `aarch64` | `yamlr-linux-x86_64.tar.gz` / `yamlr-linux-aarch64.tar.gz` |
| **macOS** | `x86_64` / `aarch64` | `yamlr-macos-x86_64.tar.gz` / `yamlr-macos-aarch64.tar.gz` |

Download the matching archive and `checksums.txt` from the same exact [Yamlr release](https://github.com/yamlr/yamlr/releases). Verify the archive with GitHub CLI before manual extraction, using the workflow that published it:

```sh
gh attestation verify yamlr-linux-x86_64.tar.gz --repo yamlr/yamlr --signer-workflow yamlr/yamlr/.github/workflows/release-binaries.yml --source-ref refs/tags/v1.2.3
```

The standalone-binaries workflow is the publisher for these installer archive names. The broader native release uses `yamlr-native-` prefixed archives and `native-checksums.txt`. For scripted installation, download the installer from the exact release tag, verify its attestation, and set `YAMLR_VERSION` to that tag before running it.

### Quick Start (Windows)
1.  Download `yamlr.exe`.
2.  Move it to a folder (e.g., `C:\Program Files\Yamlr`).
3.  **Add that folder to your PATH environment variable.**
4.  Open a new terminal and type:
    ```powershell
    yamlr scan .
    ```

```bash
docker pull yamlr/yamlr:latest
```
