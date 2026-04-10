# Yamlr Bit-for-Bit Parity Verifier
# Goal: Compare current outputs against the Golden Shield Baseline to ensure zero feature loss.

$ErrorActionPreference = "Stop"

$baselineRoot = Join-Path $PSScriptRoot "../.yamlr-baseline"
$outputDir = Join-Path $baselineRoot "outputs"
$tempRoot = Join-Path $PSScriptRoot "../.yamlr-verify"
$tempDir = Join-Path $tempRoot "outputs"
$env:YAMLR_INTERNAL_TEST_MODE = "true"
$env:PYTHONPATH = "src"

Write-Host "🛡️ Verifying Bit-for-Bit Parity..." -ForegroundColor Cyan

# 1. Initialize Temp
if (Test-Path $tempRoot) { Remove-Item $tempRoot -Recurse -Force }
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# 2. Re-Capture current state
$manifestsRoot = Join-Path $PSScriptRoot "../tests"
$targets = @()
$targets += Get-ChildItem -Path $manifestsRoot -Filter "*.yaml"
$targets += Get-ChildItem -Path (Join-Path $manifestsRoot "fixtures") -Filter "*.yaml" -Recurse
$targets += Get-ChildItem -Path (Join-Path $manifestsRoot "simulation/benchmark_1m/batch_0") -Filter "*.yaml" | Select-Object -First 50

foreach ($t in $targets) {
    $rel = Resolve-Path $t.FullName -RelativeBase $manifestsRoot
    $safe = $rel -replace '[\\/]', '_' -replace '\.yaml$', ''
    $out = Join-Path $tempDir "$safe.sarif"
    
    python -m yamlr.cli main scan $t.FullName --output sarif --all --harden --enforce-limits --enforce-namespace > $out 2>&1
}

# 3. Compare with Baseline
$baselineFiles = Get-ChildItem -Path $outputDir -Filter "*.sarif"
$mismatches = 0

foreach ($bf in $baselineFiles) {
    $vf = Join-Path $tempDir $bf.Name
    if (-not (Test-Path $vf)) {
        Write-Host "❌ Missing output for $($bf.Name)" -ForegroundColor Red
        $mismatches++
        continue
    }

    $diff = Compare-Object (Get-Content $bf.FullName) (Get-Content $vf)
    if ($diff) {
        Write-Host "❌ Regression detected in $($bf.Name)" -ForegroundColor Red
        $mismatches++
    }
}

if ($mismatches -eq 0) {
    Write-Host "`n✅ BIT-FOR-BIT PARITY CERTIFIED!" -ForegroundColor Green
    Write-Host "No regressions detected in structural refactor." -ForegroundColor Gray
} else {
    Write-Host "`n❌ FAILED: $mismatches regressions detected!" -ForegroundColor Red
    exit 1
}
