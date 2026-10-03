# typed: false
# frozen_string_literal: true

# Homebrew Formula for Yamlr
# Install via: brew install yamlr/tap/yamlr
class Yamlr < Formula
  desc "Autonomous Resolution Plane and Lossless Healing Engine for Kubernetes"
  homepage "https://yamlr.dev"
  version "0.1.0"
  # Yamlr is proprietary software; see the repository LICENSE for terms.
  license :cannot_represent

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-macos-aarch64.tar.gz"
      sha256 "0000000000000000000000000000000000000000000000000000000000000000" # Updated on tag release
    else
      url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-macos-x86_64.tar.gz"
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    end
  end

  on_linux do
    if Hardware::CPU.arm? && Hardware::CPU.is_64_bit?
      url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-linux-aarch64.tar.gz"
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    else
      url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-linux-x86_64.tar.gz"
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    end
  end

  def install
    bin.install "yamlr"
  end

  test do
    assert_match "Autonomous Resolution Plane", shell_output("#{bin}/yamlr --help")
  end
end
