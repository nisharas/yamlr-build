#!/usr/bin/env bash
# Updates the Homebrew formula with real SHA256 hashes from release assets

set -euo pipefail

VERSION=${1:-}
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "Updating Homebrew formula for version $VERSION..."

MAC_ARM_SHA=$(sha256sum yamlr-macos-aarch64.tar.gz 2>/dev/null | awk '{print $1}' || echo "0000000000000000000000000000000000000000000000000000000000000000")
MAC_X64_SHA=$(sha256sum yamlr-macos-x86_64.tar.gz 2>/dev/null | awk '{print $1}' || echo "0000000000000000000000000000000000000000000000000000000000000000")
LINUX_ARM_SHA=$(sha256sum yamlr-linux-aarch64.tar.gz 2>/dev/null | awk '{print $1}' || echo "0000000000000000000000000000000000000000000000000000000000000000")
LINUX_X64_SHA=$(sha256sum yamlr-linux-x86_64.tar.gz 2>/dev/null | awk '{print $1}' || echo "0000000000000000000000000000000000000000000000000000000000000000")

sed -i "s/version \".*\"/version \"$VERSION\"/g" Formula/yamlr.rb
sed -i "/yamlr-macos-aarch64.tar.gz/!b;n;s/sha256 \".*\"/sha256 \"$MAC_ARM_SHA\"/" Formula/yamlr.rb
sed -i "/yamlr-macos-x86_64.tar.gz/!b;n;s/sha256 \".*\"/sha256 \"$MAC_X64_SHA\"/" Formula/yamlr.rb
sed -i "/yamlr-linux-aarch64.tar.gz/!b;n;s/sha256 \".*\"/sha256 \"$LINUX_ARM_SHA\"/" Formula/yamlr.rb
sed -i "/yamlr-linux-x86_64.tar.gz/!b;n;s/sha256 \".*\"/sha256 \"$LINUX_X64_SHA\"/" Formula/yamlr.rb

echo "Formula/yamlr.rb successfully updated to $VERSION."
