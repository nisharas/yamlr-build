# Yamlr: The Kubernetes Configuration Safety Engine
# -----------------------------------------------
# Zero-friction installation script for Windows.
#
# Usage: iwr https://get.yamlr.dev/install.ps1 -useb | iex

$ErrorActionPreference = "Stop"

$Repo = "yamlr/yamlr"
$InstallDir = Join-Path $HOME ".yamlr\bin"
$BinaryName = "yamlr.exe"

Write-Host "🛡️ Yamlr: The Kubernetes Configuration Safety Engine" -ForegroundColor Cyan
Write-Host "Starting installation..."

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

# Detect Arch
$Arch = "amd64" # Default for Windows

# Get latest version from GitHub API
Write-Host "Detecting latest version..."
try {
    $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    $Tag = $Release.tag_name
    Write-Host "Found version: $Tag" -ForegroundColor Green
    $DownloadUrl = "https://github.com/$Repo/releases/download/$Tag/yamlr-windows-amd64.exe"
} catch {
    Write-Host "Failed to detect latest version via API. Falling back to latest redirect." -ForegroundColor Yellow
    $DownloadUrl = "https://github.com/$Repo/releases/latest/download/yamlr-windows-amd64.exe"
}

$DestPath = Join-Path $InstallDir $BinaryName

Write-Host "Downloading Yamlr..."
Invoke-WebRequest -Uri $DownloadUrl -OutFile $DestPath

Write-Host "✅ Yamlr installed successfully to $DestPath" -ForegroundColor Green

# Update PATH for current session
if ($env:Path -notlike "*$InstallDir*") {
    $env:Path += ";$InstallDir"
    
    # Persistent update
    Write-Host "Updating PATH environment variable..." -ForegroundColor Gray
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$InstallDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
        Write-Host "PATH updated permanently." -ForegroundColor Gray
    }
}

Write-Host "`nTry it out: yamlr welcome" -ForegroundColor Green
