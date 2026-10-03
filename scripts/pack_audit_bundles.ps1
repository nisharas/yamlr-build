# ==============================================================================
# Yamlr Audit Bundler (PowerShell)
# Splits and packages the Yamlr repository into 4 logical audit bundles
# using Repomix, fitting within LLM context windows and isolating domains.
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Packing Yamlr Codebase for External Audit (4 Bundles)..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Bundle 1: Core Engine & Architecture (~110k tokens)
Write-Host "`n[1/4] Packing Core Engine & Architecture (including man pages, reports, and pilot guide)..." -ForegroundColor Yellow
repomix `
  --include "src/yamlr/**/*.py,pyproject.toml,ruff.toml,README.md,LICENSE,SECURITY.md,CHANGELOG.md,docs/README.md,docs/PILOT_PROGRAM.md,docs/ARCHITECTURE_MODEL.md,docs/HEALING_ENGINE.md,docs/CORE_CONCEPTS.md,docs/USER_GUIDE.md,docs/CLI_REFERENCE.md,docs/BENCHMARKS.md,docs/BENCHMARK_REPORT.md,docs/GOLDEN_CORPUS_REPORT.md,docs/golden_corpus_results/*.json,docs/cli/*.md,docs/man/man1/*.1" `
  --ignore "**/*.pem,**/*.key" `
  --style markdown `
  -o yamlr-audit-core-engine.md `
  --no-security-check

# Bundle 2: Native Rust Systems Engine (~55k tokens)
Write-Host "`n[2/4] Packing Native Rust Systems Engine..." -ForegroundColor Yellow
repomix `
  --include "native_core/Cargo.toml,native_core/src/**/*.rs,native_core/benches/*.rs,native_core/catalog/forensic_catalog.json,native_core/catalog/k8s_deprecations.json" `
  --ignore "native_core/target/**,native_core/src/schemas/**,**/*.lock" `
  --style markdown `
  -o yamlr-audit-native-rust.md `
  --no-security-check

# Bundle 3: Verification & Test Rigor (~50k tokens)
Write-Host "`n[3/4] Packing Verification Suite & Test Rigor (including Golden Corpus)..." -ForegroundColor Yellow
repomix `
  --include "tests/*.py,tests/fixtures/**/*.yaml,scripts/run_golden_corpus.py,.github/workflows/*.yml,.pre-commit-hooks.yaml" `
  --ignore "tests/scale_10k/**,tests/simulation/**,tests/stress_out/**,tests/samples/**" `
  --style markdown `
  -o yamlr-audit-verification-tests.md `
  --no-security-check

# Bundle 4: Integrations & Infrastructure (~12k tokens)
Write-Host "`n[4/4] Packing Integrations & Edge Infrastructure..." -ForegroundColor Yellow
repomix `
  --include "vscode/src/**/*.ts,vscode/package.json,infra/gateway/src/**/*.ts,infra/gateway/schema.sql,infra/gateway/wrangler.toml,integrations/**/*.yaml,integrations/**/*.yml,integrations/**/*.md,actions/**/*.yml,actions/**/*.sh,actions/**/*.md,.pre-commit-config.example.yaml,docs/PRE_COMMIT_GUIDE.md" `
  --ignore "vscode/bin/**,node_modules/**,**/*.whl,**/*.lock" `
  --style markdown `
  -o yamlr-audit-integrations-infra.md `
  --no-security-check

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Audit Bundles Packed Successfully!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Get-Item yamlr-audit-*.md | Select-Object Name, @{Name="Size (KB)"; Expression={[math]::round($_.Length / 1KB, 1)}} | Format-Table -AutoSize
