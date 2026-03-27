$ErrorActionPreference = "Continue"
$LogFile = "d:\yamlr\e2e_debug_log.txt"
"Starting Absolute Surface E2E Validation" | Out-File $LogFile

function Run-Test {
    param($Name, $Cmd)
    "Testing: $Name" | Out-File $LogFile -Append
    "$Cmd" | Out-File $LogFile -Append
    $StartTime = Get-Date
    $Result = Invoke-Expression $Cmd 2>&1
    $EndTime = Get-Date
    $Elapsed = ($EndTime - $StartTime).TotalSeconds
    $ExitCode = $LASTEXITCODE
    
    "ExitCode: $ExitCode | Duration: $Elapsed" | Out-File $LogFile -Append
    "Output Snippet: " + ($Result -join "`n" | Select-Object -First 5) | Out-File $LogFile -Append
    "---------------------------------------" | Out-File $LogFile -Append
}

# 1. Global Flags Batch
Run-Test "Help" "dist\yamlr.exe --help"
Run-Test "Version" "dist\yamlr.exe -v"
Run-Test "Kube-Version" "dist\yamlr.exe scan yamlr-demo --kube-version v1.31"
Run-Test "Catalog-Custom" "dist\yamlr.exe scan yamlr-demo --catalog d:\yamlr\catalog"
Run-Test "Max-Depth" "dist\yamlr.exe scan . --max-depth 1"
Run-Test "Concurrency" "dist\yamlr.exe scan yamlr-demo --concurrency 4"
Run-Test "Summary-Only" "dist\yamlr.exe scan yamlr-demo --summary-only"
Run-Test "Verbose" "dist\yamlr.exe scan yamlr-demo --verbose"
Run-Test "Plain" "dist\yamlr.exe scan yamlr-demo --plain"
Run-Test "Quiet" "dist\yamlr.exe scan yamlr-demo --quiet"
Run-Test "Clinical" "dist\yamlr.exe scan yamlr-demo --clinical"
Run-Test "Compact" "dist\yamlr.exe scan yamlr-demo --compact"
Run-Test "Strict" "dist\yamlr.exe check yamlr-demo --strict"
Run-Test "Risk-Threshold" "dist\yamlr.exe scan yamlr-demo --risk-threshold high"
Run-Test "Fail-On" "dist\yamlr.exe scan yamlr-demo --fail-on error"
Run-Test "Stream-To" "dist\yamlr.exe scan yamlr-demo --stream-to out.json"

# 2. Primary Commands & Alias Batch
Run-Test "Audit Alias" "dist\yamlr.exe audit yamlr-demo"
Run-Test "Migrate Alias" "dist\yamlr.exe migrate yamlr-demo --to 1.30 --dry-run"
Run-Test "Diagnose" "dist\yamlr.exe diagnose yamlr-demo"
Run-Test "Upgrade" "dist\yamlr.exe upgrade yamlr-demo --to 1.31 --dry-run"
Run-Test "Secure" "dist\yamlr.exe secure yamlr-demo --dry-run"

# 3. Surgeon Flags
Run-Test "Heal Dry-Run" "dist\yamlr.exe heal yamlr-demo\sample.yaml --dry-run"
Run-Test "Heal No-Backup" "dist\yamlr.exe heal yamlr-demo\sample.yaml --no-backup --dry-run"
Run-Test "Fix-Tags" "dist\yamlr.exe heal yamlr-demo\sample.yaml --fix-tags --dry-run"
Run-Test "Enforce-Namespace" "dist\yamlr.exe heal yamlr-demo\sample.yaml --enforce-namespace --dry-run"
Run-Test "Check-Deprecations" "dist\yamlr.exe heal yamlr-demo\sample.yaml --check-deprecations --dry-run"
Run-Test "Unsafe" "dist\yamlr.exe heal yamlr-demo\sample.yaml --unsafe --dry-run"

# 4. Pro Bridge (Simulated)
$env:Yamlr_LICENSE_KEY='PRO-ECC-SIMULATED-KEY-2026'
Run-Test "Pro Stats" "dist\yamlr.exe stats"
Run-Test "Executive ROI" "dist\yamlr.exe roi"
Run-Test "Semantic DNA" "dist\yamlr.exe dna yamlr-demo\sample.yaml"
Run-Test "Pro Harden" "dist\yamlr.exe heal yamlr-demo\sample.yaml --harden --dry-run"
Run-Test "Fix-Refs" "dist\yamlr.exe heal yamlr-demo --fix-refs --dry-run"
Run-Test "Stub-Refs" "dist\yamlr.exe heal yamlr-demo --stub-refs --dry-run"
Run-Test "Sovereign" "dist\yamlr.exe scan yamlr-demo --sovereign"
Run-Test "Fast-Scan" "dist\yamlr.exe scan yamlr-demo --fast"

# 5. Toolbox
Run-Test "Init Force" "dist\yamlr.exe init --force"
Run-Test "Rules Verbose" "dist\yamlr.exe rules --verbose"
Run-Test "Explain Rule" "dist\yamlr.exe explain rule/no-latest-tag"
Run-Test "Manual" "dist\yamlr.exe manual scan"
Run-Test "Status" "dist\yamlr.exe status"
Run-Test "Welcome" "dist\yamlr.exe welcome"
Run-Test "Demo" "dist\yamlr.exe demo"

"Validation Complete" | Out-File $LogFile -Append
