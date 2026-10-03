# Yamlr Strategic Golden Shield: Optimized Baseline Capture
# Goal: Establish 100% functional bit-for-bit parity baseline using a representative test set.

$ErrorActionPreference = "Stop"

$baselineRoot = Join-Path $PSScriptRoot "../.yamlr-baseline"
$outputDir = Join-Path $baselineRoot "outputs"
$manifestsRoot = Join-Path $PSScriptRoot "../tests"
$env:YAMLR_INTERNAL_TEST_MODE = "true"
$env:PYTHONPATH = "src"

Write-Host " Establishing Optimized Golden Shield Baseline..." -ForegroundColor Cyan

# 1. Initialize
if (Test-Path $baselineRoot) { Remove-Item $baselineRoot -Recurse -Force }
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

# 2. Select Representative Targets
$targets = @()
$targets += Get-ChildItem -Path $manifestsRoot -Filter "*.yaml" # Root tests
$targets += Get-ChildItem -Path (Join-Path $manifestsRoot "fixtures") -Filter "*.yaml" -Recurse # Fixtures
$targets += Get-ChildItem -Path (Join-Path $manifestsRoot "simulation/benchmark_1m/batch_0") -Filter "*.yaml" | Select-Object -First 50 # Performance sample

Write-Host "🔍 Selected $($targets.Count) representative baseline manifests." -ForegroundColor Cyan

# 3. Capture bit-for-bit SARIF artifacts
foreach ($t in $targets) {
    # Create safe filename based on path
    $rel = Resolve-Path $t.FullName -RelativeBase $manifestsRoot
    $safe = $rel -replace '[\\/]', '_' -replace '\.yaml$', ''
    $out = Join-Path $outputDir "$safe.sarif"
    
    Write-Host " Baseline Capturing: $rel" -ForegroundColor Gray
    python -m yamlr.cli main scan $t.FullName --output sarif --all --harden --enforce-limits --enforce-namespace > $out 2>&1
}

Write-Host "`n✅ Strategic Golden Shield Baseline Established!" -ForegroundColor Green
Write-Host " Location: $baselineRoot" -ForegroundColor Gray
