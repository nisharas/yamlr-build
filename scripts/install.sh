#!/bin/bash
# Yamlr: The Kubernetes Configuration Safety Engine
# -----------------------------------------------
# Zero-friction installation script for Linux and macOS.
#
# Usage: curl -sSfL https://get.yamlr.dev | sh

set -e

# Configuration
REPO="yamlr/yamlr"
INSTALL_DIR="${HOME}/.yamlr/bin"
BINARY_NAME="yamlr"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️ Yamlr: The Kubernetes Configuration Safety Engine${NC}"
echo -e "Starting installation..."

# Detect OS and Arch
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
esac

case "$OS" in
    linux) PLATFORM="linux" ;;
    darwin) PLATFORM="darwin" ;;
    *) echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
esac

# For now, we point to the GitHub releases naming convention
# yamlr-linux-amd64 / yamlr-darwin-arm64 etc.
DOWNLOAD_NAME="yamlr-${PLATFORM}-${ARCH}"
# If it's a Pro build, the user might have a different URL, but we default to Community.
# To support Pro, we'd check for a LICENSE_KEY env var here.

# Get latest version from GitHub API
echo -e "Detecting latest version..."
LATEST_TAG=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_TAG" ]; then
    echo -e "${RED}Failed to detect latest version. Falling back to 'latest' suffix.${NC}"
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${DOWNLOAD_NAME}"
else
    echo -e "Found version: ${GREEN}${LATEST_TAG}${NC}"
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${LATEST_TAG}/${DOWNLOAD_NAME}"
fi

# Create install directory
mkdir -p "$INSTALL_DIR"

# Download binary
echo -e "Downloading ${DOWNLOAD_NAME}..."
curl -L -o "${INSTALL_DIR}/${BINARY_NAME}" "$DOWNLOAD_URL"
chmod +x "${INSTALL_DIR}/${BINARY_NAME}"

echo -e "${GREEN}✅ Yamlr installed successfully to ${INSTALL_DIR}/${BINARY_NAME}${NC}"

# Path suggestion
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "\n${BLUE}Final Step: Add Yamlr to your PATH${NC}"
    case "$SHELL" in
        */zsh)
            echo -e "Run: ${GREEN}echo 'export PATH=\"\$HOME/.yamlr/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc${NC}"
            ;;
        */bash)
            echo -e "Run: ${GREEN}echo 'export PATH=\"\$HOME/.yamlr/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${NC}"
            ;;
        *)
            echo -e "Add ${INSTALL_DIR} to your environment PATH."
            ;;
    esac
fi

echo -e "\nTry it out: ${GREEN}yamlr welcome${NC}"
