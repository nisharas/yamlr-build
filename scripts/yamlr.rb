class Yamlr < Formula
  desc "Deterministic Kubernetes Configuration Safety Engine"
  homepage "https://yamlr.dev"
  version "1.1.0" # This would be updated by CI during release

  if OS.mac? && Hardware::CPU.intel?
    url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-darwin-amd64"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  elsif OS.mac? && Hardware::CPU.arm?
    url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-darwin-arm64"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  elsif OS.linux? && Hardware::CPU.intel?
    url "https://github.com/yamlr/yamlr/releases/download/v#{version}/yamlr-linux-amd64"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  def install
    # Binary name is currently specific to platform in releases, rename to just 'yamlr'
    if OS.mac? && Hardware::CPU.intel?
        bin.install "yamlr-darwin-amd64" => "yamlr"
    elsif OS.mac? && Hardware::CPU.arm?
        bin.install "yamlr-darwin-arm64" => "yamlr"
    elsif OS.linux?
        bin.install "yamlr-linux-amd64" => "yamlr"
    end
  end

  test do
    system "#{bin}/yamlr", "version"
  end
end
