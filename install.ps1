# Yamlr: The Autonomous Resolution Plane for Kubernetes Manifests
# -------------------------------------------------------------
# Release installer for Windows PowerShell.
# Downloads the standalone native Rust binary directly from GitHub Releases.
#
# Usage:
#   $env:YAMLR_VERSION = 'v1.2.3'; irm https://get.yamlr.dev/install.ps1 | iex
# Requires GitHub CLI to verify release provenance.

[CmdletBinding()]
param(
    [switch]$NoVerify,
    [string]$InstallDir = "$env:LOCALAPPDATA\yamlr\bin",
    [string]$Version = $env:YAMLR_VERSION
)

$ErrorActionPreference = "Stop"

$Repo = "yamlr/yamlr"
$BinaryName = "yamlr.exe"

if ($NoVerify -or $env:YAMLR_NO_VERIFY -eq "1") {
    throw "Unverified installation is not supported."
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Set YAMLR_VERSION to an exact release tag such as v1.2.3."
}
if ($Version -notmatch '^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$') {
    throw "Invalid Yamlr release version '$Version'. Use a semantic version tag such as v1.2.3."
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Yamlr • Autonomous Resolution Plane for Kubernetes" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$Arch = if ([IntPtr]::Size -eq 8) { "x86_64" } else { throw "Yamlr release binaries currently support 64-bit Windows only." }
$AssetName = "yamlr-windows-$Arch.zip"
$BaseUrl = "https://github.com/$Repo/releases/download/$Version"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI ('gh') is required to verify the Yamlr release attestation."
}

$DownloadUrl = "$BaseUrl/$AssetName"
$ChecksumUrl = "$BaseUrl/checksums.txt"

Write-Host "[*] Target Environment: windows-$Arch" -ForegroundColor Gray
Write-Host "[*] Downloading Yamlr from: $DownloadUrl" -ForegroundColor Gray
$TempDir = Join-Path $env:TEMP ([System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TempDir | Out-Null
$TempArchive = Join-Path $TempDir $AssetName
$TempChecksum = Join-Path $TempDir "checksums.txt"

try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $TempArchive -UseBasicParsing
    Invoke-WebRequest -Uri $ChecksumUrl -OutFile $TempChecksum -UseBasicParsing
} catch {
    throw "Could not download the pinned Yamlr release and its checksum file: $_"
}

$ChecksumLine = Get-Content -Path $TempChecksum | Where-Object { $_ -match "\s+$([regex]::Escape($AssetName))$" } | Select-Object -First 1
if ($ChecksumLine -notmatch '^([a-fA-F0-9]{64})\s+') {
    throw "No valid SHA-256 entry found for $AssetName."
}
$ExpectedHash = $Matches[1].ToLowerInvariant()
$ActualHash = (Get-FileHash -Path $TempArchive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ExpectedHash -ne $ActualHash) {
    throw "SHA-256 verification failed for $AssetName."
}
Write-Host "[OK] SHA-256 checksum verified: $ActualHash" -ForegroundColor Green

& gh attestation verify $TempArchive --repo "yamlr/yamlr" --signer-workflow "yamlr/yamlr/.github/workflows/release-binaries.yml" --source-ref "refs/tags/$Version"
if ($LASTEXITCODE -ne 0) {
    throw "Release provenance verification failed. Refusing to install Yamlr."
}
Write-Host "[OK] Release provenance verified for $Version." -ForegroundColor Green

Expand-Archive -Path $TempArchive -DestinationPath $TempDir -Force
$TempBin = Join-Path $TempDir $BinaryName
if (-not (Test-Path $TempBin -PathType Leaf)) {
    throw "The verified release archive did not contain $BinaryName."
}

$TargetPath = Join-Path $InstallDir $BinaryName
Move-Item -Path $TempBin -Destination $TargetPath -Force
Remove-Item -Path $TempDir -Recurse -Force

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "[OK] Yamlr successfully installed to: $TargetPath" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green

# Add to user PATH if not present
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
    Write-Host "Added $InstallDir to User PATH environment variable." -ForegroundColor Gray
    Write-Host "Note: Restart your terminal session or run `$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User')` to update PATH." -ForegroundColor Gray
}

try {
    & $TargetPath version
} catch {
    # Non-fatal if binary execution failed due to execution policy
}

Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Cyan
Write-Host "  yamlr scan .          # Read-only clinical audit" -ForegroundColor White
Write-Host "  yamlr heal . --apply  # Safe comment-preserving auto-repair" -ForegroundColor White
Write-Host "  yamlr --help          # Precision command reference" -ForegroundColor White
