#!/usr/bin/env sh
# Yamlr — Universal Installer for Linux, macOS, and Windows
# Zero-dependency, cloud-agnostic, and vendor-neutral installation script.
# Usage:
#   YAMLR_VERSION=v1.2.3 sh scripts/install.sh
# GitHub CLI is required to verify the release attestation.

set -e

REPO="yamlr/yamlr"
INSTALL_DIR="${YAMLR_INSTALL_DIR:-/usr/local/bin}"
USER_INSTALL_DIR="${HOME}/.local/bin"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Yamlr • Autonomous Resolution Plane for Kubernetes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Detect Operating System
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows";;
    *)
        echo "[ERROR] Unsupported operating system: ${OS}"
        exit 1
        ;;
esac

# 2. Detect CPU Architecture
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)   ARCH="x86_64";;
    aarch64|arm64)  ARCH="aarch64";;
    *)
        echo "[ERROR] Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

# 3. Determine Asset Name and Suffix
EXT="tar.gz"
if [ "${PLATFORM}" = "windows" ]; then
    BINARY_NAME="yamlr.exe"
    EXT="zip"
else
    BINARY_NAME="yamlr"
fi

TARGET="${PLATFORM}-${ARCH}"
ASSET_NAME="yamlr-${TARGET}.${EXT}"
VERSION="${YAMLR_VERSION:-}"
if [ -z "${VERSION}" ]; then
    echo "[ERROR] A pinned release is required. Set YAMLR_VERSION to a version tag such as v1.2.3."
    exit 1
fi

if ! printf '%s\n' "${VERSION}" | awk '
    /^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$/ { valid = 1 }
    END { exit !valid }
'; then
    echo "[ERROR] Invalid Yamlr release version '${VERSION}'. Use a semantic version tag such as v1.2.3."
    exit 1
fi

BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
DOWNLOAD_URL="${BASE_URL}/${ASSET_NAME}"
CHECKSUM_URL="${BASE_URL}/checksums.txt"

echo "[*] Target Environment: ${PLATFORM} (${ARCH})"
echo "[*] Downloading Yamlr from: ${DOWNLOAD_URL}..."

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'yamlr')"
trap 'rm -rf "${TMP_DIR}"' EXIT

ARCHIVE_PATH="${TMP_DIR}/yamlr.${EXT}"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${DOWNLOAD_URL}" -o "${ARCHIVE_PATH}"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "${ARCHIVE_PATH}" "${DOWNLOAD_URL}"
else
    echo "[ERROR] Neither 'curl' nor 'wget' was found on your system."
    exit 1
fi

CHECKSUM_PATH="${TMP_DIR}/checksums.txt"
if command -v curl >/dev/null 2>&1; then
    if ! curl -fsSL "${CHECKSUM_URL}" -o "${CHECKSUM_PATH}"; then
        echo "[ERROR] Could not download the release checksum file. Refusing to install an unverified binary."
        exit 1
    fi
elif ! wget -qO "${CHECKSUM_PATH}" "${CHECKSUM_URL}"; then
    echo "[ERROR] Could not download the release checksum file. Refusing to install an unverified binary."
    exit 1
fi

EXPECTED_HASH="$(awk -v asset="${ASSET_NAME}" '$2 == asset { print $1; exit }' "${CHECKSUM_PATH}")"
case "${EXPECTED_HASH}" in
    ''|*[!0123456789abcdefABCDEF]*)
        echo "[ERROR] No valid SHA-256 entry found for ${ASSET_NAME}. Refusing to install an unverified binary."
        exit 1
        ;;
esac
if [ "${#EXPECTED_HASH}" -ne 64 ]; then
    echo "[ERROR] Invalid SHA-256 entry for ${ASSET_NAME}. Refusing to install an unverified binary."
    exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_HASH="$(sha256sum "${ARCHIVE_PATH}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
    ACTUAL_HASH="$(shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}')"
else
    echo "[ERROR] Neither sha256sum nor shasum is available. Refusing to install an unverified binary."
    exit 1
fi

if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
    echo "[ERROR] Checksum mismatch for ${ASSET_NAME}!"
    echo "  Expected: ${EXPECTED_HASH}"
    echo "  Actual:   ${ACTUAL_HASH}"
    exit 1
fi
echo "[OK] Checksum verified: ${ACTUAL_HASH}"

if [ "${YAMLR_VERIFY_ATTESTATION:-true}" != "true" ]; then
    echo "[ERROR] Release attestation verification cannot be disabled."
    exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
    echo "[ERROR] GitHub CLI ('gh') is required to verify the signed Yamlr release attestation."
    exit 1
fi
if ! gh attestation verify "${ARCHIVE_PATH}" \
    --repo "yamlr/yamlr" \
    --signer-workflow "yamlr/yamlr/.github/workflows/release-binaries.yml" \
    --source-ref "refs/tags/${VERSION}"; then
    echo "[ERROR] Release provenance verification failed. Refusing to install Yamlr."
    exit 1
fi
echo "[OK] Release provenance verified for ${VERSION}."

echo "[*] Extracting release archive..."
if [ "${EXT}" = "zip" ]; then
    unzip -q "${ARCHIVE_PATH}" -d "${TMP_DIR}"
else
    tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"
fi

SOURCE_BIN="${TMP_DIR}/${BINARY_NAME}"
if [ ! -f "${SOURCE_BIN}" ]; then
    # Try locating extracted binary in subdirectories if packaged inside folder
    FOUND_BIN="$(find "${TMP_DIR}" -type f -name "${BINARY_NAME}" | head -n 1)"
    if [ -n "${FOUND_BIN}" ]; then
        SOURCE_BIN="${FOUND_BIN}"
    else
        echo "[ERROR] Could not locate '${BINARY_NAME}' in downloaded archive."
        exit 1
    fi
fi

chmod +x "${SOURCE_BIN}"

# 4. Target Directory Selection (with graceful non-root fallback)
DEST_PATH="${INSTALL_DIR}/${BINARY_NAME}"
if [ -w "${INSTALL_DIR}" ]; then
    mv "${SOURCE_BIN}" "${DEST_PATH}"
elif [ "$(id -u)" -eq 0 ]; then
    mv "${SOURCE_BIN}" "${DEST_PATH}"
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo mv "${SOURCE_BIN}" "${DEST_PATH}"
else
    echo "[!] Cannot write to ${INSTALL_DIR} without sudo. Installing to ${USER_INSTALL_DIR}..."
    mkdir -p "${USER_INSTALL_DIR}"
    DEST_PATH="${USER_INSTALL_DIR}/${BINARY_NAME}"
    mv "${SOURCE_BIN}" "${DEST_PATH}"
    
    # Path warning if ~/.local/bin is not in PATH
    case ":${PATH}:" in
        *:"${USER_INSTALL_DIR}":*) ;;
        *)
            echo "[NOTE] Add ${USER_INSTALL_DIR} to your PATH to run 'yamlr' directly:"
            echo "       export PATH=\"\${HOME}/.local/bin:\${PATH}\""
            ;;
    esac
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [OK] Yamlr successfully installed to: ${DEST_PATH}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"${DEST_PATH}" version || true
echo ""
echo "Quick Start:"
echo "  yamlr scan .          # Read-only clinical audit"
echo "  yamlr heal . --apply  # Safe comment-preserving auto-repair"
echo "  yamlr --help          # Precision command reference"
