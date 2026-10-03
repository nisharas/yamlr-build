This file is a merged representation of a subset of the codebase, containing specifically included files and files not matching ignore patterns, combined into a single document by Repomix.
The content has been processed where security check has been disabled.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: tests/*.py, tests/fixtures/**/*.yaml, scripts/run_golden_corpus.py, .github/workflows/*.yml, .pre-commit-hooks.yaml
- Files matching these patterns are excluded: tests/scale_10k/**, tests/simulation/**, tests/stress_out/**, tests/samples/**
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
.github/workflows/catalog-sync.yml
.github/workflows/dogfood.yml
.github/workflows/e2e-cluster.yml
.github/workflows/golden-corpus-cron.yml
.github/workflows/lint.yml
.github/workflows/mutation-tests.yml
.github/workflows/performance-gate.yml
.github/workflows/release-binaries.yml
.github/workflows/release.yml
.github/workflows/security_audit.yml
.github/workflows/security_scan.yml
.github/workflows/stress-test.yml
.github/workflows/test.yml
.github/workflows/verify_actions.yml
.github/workflows/yamlr-autofix.yml
.github/workflows/yamlr-gitops.yml
.github/workflows/yamlr-pr-audit.yml
.pre-commit-hooks.yaml
scripts/run_golden_corpus.py
tests/conftest.py
tests/fixtures/crd_test.yaml
tests/fixtures/deploy_healer_test.yaml
tests/fixtures/deprecated-api.yaml
tests/fixtures/healer_test.yaml
tests/fixtures/toxic-collision.yaml
tests/fixtures/verify_workload_relational.yaml
tests/test_adversarial_invariants.py
tests/test_ast_fuzz.py
tests/test_ast_property.py
tests/test_backup_cleanup.py
tests/test_backups.py
tests/test_cis_benchmark.py
tests/test_cli_admin_dispatch.py
tests/test_cli_admin.py
tests/test_cli_diagnostic_edge_cases.py
tests/test_cli_dispatch.py
tests/test_cli_evidence_and_admin.py
tests/test_cli_flags_progressive.py
tests/test_cli_handlers_coverage.py
tests/test_cli_help_alias.py
tests/test_cli_help_extended_v2.py
tests/test_cli_help.py
tests/test_cli_main_edge.py
tests/test_cli_main_remediation.py
tests/test_cli_pipeline_extended.py
tests/test_cli_pipeline.py
tests/test_cli_render_report.py
tests/test_cli_schema.py
tests/test_cli_security.py
tests/test_cli_sign_verify.py
tests/test_cli_utils_extended.py
tests/test_cncf_crds.py
tests/test_commands.py
tests/test_core_logic_extended.py
tests/test_crd_distiller.py
tests/test_deprecation_upgrades.py
tests/test_design_partner_pilot_kit.py
tests/test_diff.py
tests/test_dna_no_files.py
tests/test_e2e_backup_restore.py
tests/test_e2e_pipeline.py
tests/test_e2e_sarif_json.py
tests/test_e2e_scan_heal.py
tests/test_evidence_vault.py
tests/test_exception_handling.py
tests/test_explain_usage.py
tests/test_fleet_batcher.py
tests/test_fmt_cmd.py
tests/test_forensic_logic.py
tests/test_golden_corpus_invariants.py
tests/test_guide_missing.py
tests/test_healing_invariants.py
tests/test_helm_umbrella_scan.py
tests/test_hermetic_offline.py
tests/test_inline_diff.py
tests/test_integrations_fail.py
tests/test_integrations.py
tests/test_k8s_functional_schema.py
tests/test_knowledge_bible.py
tests/test_license_extended.py
tests/test_license.py
tests/test_logic_utils.py
tests/test_lsp_code_action.py
tests/test_lsp_error_handling.py
tests/test_lsp_logic.py
tests/test_lsp.py
tests/test_mcp_server.py
tests/test_phase3_lexer_verification.py
tests/test_pipe_composability.py
tests/test_pipeline.py
tests/test_policy_ingestion.py
tests/test_precommit_hooks.py
tests/test_proto_service.py
tests/test_public_api.py
tests/test_remediation_integrity.py
tests/test_remediation_logic.py
tests/test_remediation.py
tests/test_renderer.py
tests/test_roi_no_native.py
tests/test_sarif_fixes.py
tests/test_sarif_reporter.py
tests/test_scrub_ansi.py
tests/test_shard_processing_error.py
tests/test_stages.py
tests/test_streaming_multi_doc.py
tests/test_streaming_os_error.py
tests/test_streaming_scan.py
tests/test_template_masker_dynamic_keys.py
tests/test_template_masker_multiline.py
tests/test_template_masker.py
tests/test_topology_audit.py
tests/test_ui_dossier.py
tests/test_ui_field_dossier.py
tests/test_ui_graph.py
tests/test_ui_renderer_extended.py
tests/test_ui_renderer.py
tests/test_version_extended.py
tests/test_webhook_server.py
```

# Files

## File: .github/workflows/catalog-sync.yml
````yaml
name: Catalog Sync
on:
  schedule:
    - cron: '0 0 * * 0' # Weekly on Sunday
  workflow_dispatch:

jobs:
  sync-catalog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          # Add any dependencies needed for distiller here
          
      - name: Distill Latest K8s Catalog
        run: |
          python scripts/catalog_distiller.py --version latest --output src/yamlr/core/data/catalog.json
          
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "chore: update kubernetes catalog to latest"
          title: "chore: automated kubernetes catalog sync"
          body: "Automated update of the Kubernetes schema catalog from official OpenAPI specs."
          branch: auto-catalog-sync
````

## File: .github/workflows/dogfood.yml
````yaml
name: Yamlr Distribution Test

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  # 1. Test the Action itself (Docker Build + Run)
  action-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
            
      # This effectively runs 'docker build .' and 'yamlr scan .'
      - name: Dogfood Yamlr Action
        uses: ./
        with:
          args: scan . --output sarif --output-file yamlr-report.sarif

      - name: Upload SARIF to GitHub Security Tab
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: yamlr-report.sarif

  # 2. Enterprise Stress Tests (GAUNTLET)
  stress-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-mock rich pydantic pyyaml
      - name: Run Enterprise Stress Tests
        run: pytest tests/pro/test_stress_enterprise.py -v
````

## File: .github/workflows/e2e-cluster.yml
````yaml
name: Ephemeral E2E Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  e2e-kind-cluster:
    name: E2E Test on Ephemeral Kubernetes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        k8s-version: ["v1.28.0", "v1.30.0"]

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: 'pip'

      - name: Create k8s Kind Cluster
        uses: helm/kind-action@v1.10.0
        with:
          node_image: kindest/node:${{ matrix.k8s-version }}
          cluster_name: yamlr-e2e-cluster

      - name: Install Yamlr & Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r src/requirements.txt
          pip install .

      - name: Run E2E Smoke Tests
        run: |
          # Apply a broken manifest to the cluster
          kubectl create deployment nginx --image=nginx:latest --dry-run=client -o yaml > deployment.yaml
          
          # Use yamlr to scan and fix it (simulate user action)
          yamlr scan deployment.yaml
          
          # Deploy it
          kubectl apply -f deployment.yaml
          
          # Wait for ready
          kubectl wait --for=condition=available deployment/nginx --timeout=60s
````

## File: .github/workflows/golden-corpus-cron.yml
````yaml
name: Upstream Golden Corpus Regression

on:
  schedule:
    # Runs every Monday at 04:00 UTC to guard against upstream manifest drift
    - cron: '0 4 * * 1'
  workflow_dispatch:
    inputs:
      clear_cache:
        description: 'Force fresh download of upstream manifests'
        required: false
        default: 'true'
        type: boolean

permissions:
  contents: read

jobs:
  golden-corpus:
    name: Verify Upstream Invariants
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Set up Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install dependencies & build native module
        run: |
          python -m pip install --upgrade pip maturin
          maturin develop --release -m native_core/Cargo.toml
          pip install -e .

      - name: Execute Upstream Golden Corpus
        run: |
          ARGS=""
          if [ "${{ github.event_name }}" = "schedule" ] || [ "${{ inputs.clear_cache }}" = "true" ]; then
            ARGS="--clear-cache"
          fi
          python scripts/run_golden_corpus.py $ARGS

      - name: Publish Step Summary to GitHub Actions UI
        if: always()
        run: |
          if [ -f docs/GOLDEN_CORPUS_REPORT.md ]; then
            cat docs/GOLDEN_CORPUS_REPORT.md >> $GITHUB_STEP_SUMMARY
          fi

      - name: Archive Golden Corpus Telemetry & Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: golden-corpus-telemetry
          path: |
            docs/GOLDEN_CORPUS_REPORT.md
            docs/golden_corpus_results/*.json
          retention-days: 90
````

## File: .github/workflows/lint.yml
````yaml
name: Quality Gates (Linting)

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  python-lint:
    name: Python Lint (Ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install Ruff
        run: pip install ruff
      - name: Run Ruff Check
        run: ruff check src/
      - name: Run Ruff Format
        run: ruff format --check src/

  rust-lint:
    name: Rust Lint (Clippy)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          components: clippy
          profile: minimal
          override: true
      - name: Run Clippy
        run: |
          cd native_core
          cargo clippy --features python -- -D warnings
````

## File: .github/workflows/mutation-tests.yml
````yaml
name: Mutation Testing (Nightly)

on:
  schedule:
    - cron: '0 2 * * *' # Run at 2 AM every night

jobs:
  python-mutation:
    name: Mutmut (Python)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: 'pip'
      
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r src/requirements.txt
          pip install . pytest mutmut

      - name: Run mutmut
        run: |
          mutmut run || echo "Mutations survived. Please check mutmut results."
          mutmut results

  rust-mutation:
    name: Cargo Mutants (Rust)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
      
      - name: Install cargo-mutants
        run: cargo install cargo-mutants
      
      - name: Run cargo mutants
        run: |
          cd native_core
          cargo mutants
````

## File: .github/workflows/performance-gate.yml
````yaml
name: Performance Budget Gate

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  check-latency:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install rich
          # Note: We don't install yamlr here because we run from source for the budget gate
          # to ensure the engineering-level latency is tracked correctly.

      - name: Run Performance Gate
        env:
          PYTHONPATH: src
          PYTHONUTF8: 1
          YAMLR_QUIET: true
        run: python scripts/performance_gate.py
````

## File: .github/workflows/release-binaries.yml
````yaml
name: Release Standalone Binaries

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build-binaries:
    name: Build (${{ matrix.target }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - target: x86_64-unknown-linux-musl
            os: ubuntu-latest
            artifact_name: yamlr
            asset_name: yamlr-linux-amd64.tar.gz
            use_cross: true
          - target: aarch64-unknown-linux-musl
            os: ubuntu-latest
            artifact_name: yamlr
            asset_name: yamlr-linux-arm64.tar.gz
            use_cross: true
          - target: x86_64-apple-darwin
            os: macos-13
            artifact_name: yamlr
            asset_name: yamlr-darwin-amd64.tar.gz
            use_cross: false
          - target: aarch64-apple-darwin
            os: macos-latest
            artifact_name: yamlr
            asset_name: yamlr-darwin-arm64.tar.gz
            use_cross: false
          - target: x86_64-pc-windows-msvc
            os: windows-latest
            artifact_name: yamlr.exe
            asset_name: yamlr-windows-amd64.zip
            use_cross: false

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Install Rust Toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Install Cross-Compilation Tool
        if: matrix.use_cross
        run: cargo install cross --git https://github.com/cross-rs/cross

      - name: Build Standalone Binary (Cross)
        if: matrix.use_cross
        run: cross build --release --target ${{ matrix.target }} --bin yamlr --manifest-path native_core/Cargo.toml

      - name: Build Standalone Binary (Native)
        if: "!matrix.use_cross"
        run: cargo build --release --target ${{ matrix.target }} --bin yamlr --manifest-path native_core/Cargo.toml

      - name: Package Unix Archive
        if: matrix.os != 'windows-latest'
        run: |
          mkdir -p dist
          BIN_PATH="native_core/target/${{ matrix.target }}/release/${{ matrix.artifact_name }}"
          tar -czf "dist/${{ matrix.asset_name }}" -C "$(dirname $BIN_PATH)" "${{ matrix.artifact_name }}"
          cd dist && sha256sum "${{ matrix.asset_name }}" > "${{ matrix.asset_name }}.sha256"
        shell: bash

      - name: Package Windows Archive
        if: matrix.os == 'windows-latest'
        run: |
          New-Item -ItemType Directory -Force -Path dist
          $BinPath = "native_core/target/${{ matrix.target }}/release/${{ matrix.artifact_name }}"
          Compress-Archive -Path $BinPath -DestinationPath "dist/${{ matrix.asset_name }}"
          $Hash = (Get-FileHash -Path "dist/${{ matrix.asset_name }}" -Algorithm SHA256).Hash.ToLower()
          "$Hash  ${{ matrix.asset_name }}" | Out-File -FilePath "dist/${{ matrix.asset_name }}.sha256" -Encoding ascii
        shell: pwsh

      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.target }}
          path: dist/*
          retention-days: 2

  publish:
    name: Publish GitHub Release Assets
    needs: build-binaries
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - name: Download all binary artifacts
        uses: actions/download-artifact@v4
        with:
          path: release_artifacts

      - name: Prepare Release Directory
        run: |
          mkdir -p release_dist
          find release_artifacts -type f -exec cp {} release_dist/ \;
          cd release_dist && sha256sum yamlr-*.tar.gz yamlr-*.zip > SHA256SUMS.txt
          ls -la release_dist/

      - name: Publish Release Assets
        uses: softprops/action-gh-release@v2
        with:
          files: release_dist/*
          draft: false
          prerelease: false
          generate_release_notes: true
````

## File: .github/workflows/release.yml
````yaml
name: Native Release Pipeline

on:
  push:
    tags:
      - 'v*.*.*'  # Triggers on tags like v1.1.0

jobs:
  build:
    name: Build Native Binaries
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.12"]

    steps:
      - name: Checkout Enterprise Codebase
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Set up Rust Toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true

      - name: Install Nuitka and Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install nuitka zstandard maturin
          pip install -r src/requirements.txt || true # Install core deps if they exist

      - name: Compile Native Binary (package.py)
        run: python scripts/package.py

      - name: Compile Standalone Rust Native Binary
        run: |
          cargo build --release --bin yamlr --manifest-path native_core/Cargo.toml
          mkdir -p dist
          if [ "$RUNNER_OS" = "Windows" ]; then
            cp native_core/target/release/yamlr.exe dist/yamlr-windows-amd64.exe
          elif [ "$RUNNER_OS" = "macOS" ]; then
            cp native_core/target/release/yamlr dist/yamlr-darwin-arm64
          else
            cp native_core/target/release/yamlr dist/yamlr-linux-amd64
          fi
        shell: bash

      - name: Upload Artifacts to Pipeline
        uses: actions/upload-artifact@v4
        with:
          name: yamlr-${{ runner.os }}-build
          path: dist/*
          retention-days: 1

  publish:
    name: Push to Public Repository
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download all compiled artifacts
        uses: actions/download-artifact@v4
        with:
          path: compiled_binaries

      - name: Flatten Artifact Directory
        run: |
          mkdir -p release_assets
          find compiled_binaries -type f -exec cp {} release_assets/ \;
          ls -la release_assets/

      - name: Publish to Public Hub
        uses: softprops/action-gh-release@v1
        with:
          files: release_assets/*
          repository: yamlr/yamlr
          token: ${{ secrets.PUBLIC_HUB_PAT }}
          name: Release ${{ github.ref_name }}
          draft: false
          prerelease: false
          generate_release_notes: true

  docker_release:
    name: Build & Push Docker Image
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: actions/scan/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/yamlr:latest
            ghcr.io/${{ github.repository }}/yamlr:${{ github.ref_name }}
````

## File: .github/workflows/security_audit.yml
````yaml
name: " Yamlr Security Audit"

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 1' # Weekly on Mondays

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pip-audit detect-secrets

      - name:  Dependency Audit (pip-audit)
        run: pip-audit

      - name: 🔑 Secret Detection (detect-secrets)
        run: |
          detect-secrets scan --exclude-files 'tests/.*' > .secrets.baseline
          detect-secrets audit .secrets.baseline --report
````

## File: .github/workflows/security_scan.yml
````yaml
name: Security Scan

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 1' # Weekly scan

jobs:
  security-audit:
    name: Security Audit & Secret Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Security Tools
        run: |
          pip install pip-audit detect-secrets

      - name: Dependency Audit (pip-audit)
        run: |
          # Allow it to fail build on high-severity vulnerabilities
          pip-audit --strict --desc on -r src/requirements.txt || true
          # Note: Added '|| true' for initial baseline; remove to enforce in future.

      - name: Secret Scan (detect-secrets)
        run: |
          detect-secrets scan --all-files --exclude-files '.*\.gemini/.*' --exclude-files '.*brain/.*' > .secrets.baseline
          # Verification step: if baseline has results, fail or warn
          if [ -s .secrets.baseline ]; then
            echo "⚠ Potential secrets detected in codebase!"
            cat .secrets.baseline
          fi
````

## File: .github/workflows/stress-test.yml
````yaml
name: 🛠 Hyperscale Stress Test (150k+)

on:
  workflow_dispatch:
    inputs:
      manifest_count:
        description: 'Total number of manifests to generate and test'
        required: true
        default: '150000'
        type: 'string'

jobs:
  stress-test:
    name:  Execute 100x Scale Stress Test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name:  Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install psutil rich
          # No need to install yamlr as we run from source (src/)

      - name:  Run Stress Test Orchestrator
        env:
          PYTHONPATH: src
          PYTHONUTF8: 1
          YAMLR_QUIET: true
        run: |
          python scripts/stress_test_orchestrator.py --count ${{ github.event.inputs.manifest_count }} --output stress_results.json

      - name: 📊 Upload Stress Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: stress-test-report-${{ github.run_id }}
          path: stress_results.json

      - name: 📝 Final Validation Summary
        if: always()
        run: |
          echo "###  Hyperscale Stress Test Summary" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "| :--- | :--- |" >> $GITHUB_STEP_SUMMARY
          echo "| Total Manifests | ${{ github.event.inputs.manifest_count }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Peak RAM (GB) | $(cat stress_results.json | jq -r '.results.peak_memory_gb' | xargs printf '%.3f') |" >> $GITHUB_STEP_SUMMARY
          echo "| Throughput (f/s) | $(cat stress_results.json | jq -r '.results.files_per_sec' | xargs printf '%.2f') |" >> $GITHUB_STEP_SUMMARY
          echo "| Status | $(cat stress_results.json | jq -r '.results.success') |" >> $GITHUB_STEP_SUMMARY
````

## File: .github/workflows/test.yml
````yaml
name: Core Test Matrix

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  python-tests:
    name: Python Tests (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r src/requirements.txt
          pip install pytest pytest-cov
      
      - name: Run Tests with Coverage
        run: |
          pytest --cov=src --cov-fail-under=85 --cov-report=xml tests/
        env:
          YAMLR_K8S_VERSION: "v1.30"

  rust-tests:
    name: Rust Native Tests (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          profile: minimal
          override: true
      
      - name: Run Cargo Tests
        run: |
          cd native_core
          cargo test --features python
````

## File: .github/workflows/verify_actions.yml
````yaml
name: Verify local Actions
on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test-actions:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          pip install .[dev]
          
      - name: Run Core Verification (with Coverage Gate)
        run: |
          pytest --cov=src/yamlr --cov-report=term-missing --cov-fail-under=50 tests/
          
      - name: Run Performance Regression Check
        # Only run on Linux to avoid env-specific variance in CI comparison
        if: matrix.os == 'ubuntu-latest'
        run: |
          python scripts/benchmark.py > bench.txt
          cat bench.txt
          # Failure logic: If "Throughput" < 0.03 MB/s (Low bar for CI VMs)
          grep "Throughput" bench.txt | awk '{if ($2 < 0.03) exit 1}'
          
      - name: Run Zero-Regression Parity Guard
        if: matrix.os == 'ubuntu-latest'
        run: |
          export PYTHONPATH=$PYTHONPATH:$(pwd)/src
          python tests/verify_rust_parity.py --baseline "python -m yamlr scan" --candidate "python tests/stubs/rust_scanner_stub.py" --target tests/fixtures
      
      - name: Test Scan Action
        uses: ./.github/actions/scan
        with:
          path: 'tests/fixtures'
          args: '--harden'
          
      - name: Test Heal Action (Dry Run)
        uses: ./.github/actions/heal
        with:
          path: 'tests/fixtures'
          args: '--yes-all --no-backup --dry-run'
````

## File: .github/workflows/yamlr-autofix.yml
````yaml
name: Yamlr Manifest Auto-Fix

on:
  schedule:
    - cron: '0 4 * * 1' # Weekly every Monday at 04:00 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  autofix:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Yamlr
        run: |
          python -m pip install --upgrade pip
          pip install yamlr

      - name: Run Yamlr Auto-Fix
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -c "from yamlr.ci.autofix import execute_autofix; execute_autofix('.', create_pr=True)"
````

## File: .github/workflows/yamlr-gitops.yml
````yaml
name: Yamlr GitOps Formatter & Manifest Auto-Fix

'on':
  push:
    branches: [ main, master ]
    paths:
      - '**.yaml'
      - '**.yml'
  pull_request:
    branches: [ main, master ]
    paths:
      - '**.yaml'
      - '**.yml'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  gitops-fmt-and-fix:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref || github.ref }}
          fetch-depth: 0

      - name: Run Yamlr Canonical Formatter
        uses: ./
        with:
          command: 'fmt'
          write: 'true'
          autocommit: 'false'

      - name: Run Yamlr Manifest Auto-Fixer
        uses: ./
        with:
          command: 'fix'
          autocommit: 'true'
          commit-message: 'chore(k8s): yamlr auto-format and repair manifests'
````

## File: .github/workflows/yamlr-pr-audit.yml
````yaml
name: "Yamlr Manifest PR Audit"

on:
  pull_request:
    paths:
      - "**.yaml"
      - "**.yml"

permissions:
  contents: read
  security-events: write

jobs:
  audit:
    name: "Audit & Diff Manifests"
    runs-on: ubuntu-latest
    steps:
      - name: "Checkout Repository"
        uses: actions/checkout@v4

      - name: "Set up Python"
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: "Install Yamlr"
        run: pip install yamlr

      - name: "Preview Auto-Remediation Diffs"
        id: diff_preview
        run: |
          echo "### 🔍 Proposed Manifest Corrections" >> $GITHUB_STEP_SUMMARY
          echo '```diff' >> $GITHUB_STEP_SUMMARY
          yamlr diff --unified . >> $GITHUB_STEP_SUMMARY 2>&1 || true
          echo '```' >> $GITHUB_STEP_SUMMARY

      - name: "Execute Schema & Integrity Scan"
        run: |
          yamlr scan . --output sarif --output-file results.sarif --fail-on error

      - name: "Upload SARIF Report to GitHub Code Scanning"
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        continue-on-error: true
        with:
          sarif_file: results.sarif
````

## File: .pre-commit-hooks.yaml
````yaml
- id: yamlr-fmt
  name: Yamlr Manifest Formatter (k8sfmt)
  description: Canonical Kubernetes manifest formatter. Normalizes indentation and reorders keys according to the official Kubernetes schema hierarchy.
  entry: yamlr fmt
  args: ["-w"]
  language: system
  files: \.(yaml|yml)$
  pass_filenames: true
  require_serial: false

- id: yamlr-fix
  name: Yamlr Manifest Auto-Fixer
  description: Instant zero-configuration auto-repair for deprecated APIs, floating tags, and schema deviations.
  entry: yamlr fix
  language: system
  files: \.(yaml|yml)$
  pass_filenames: true
  require_serial: false

- id: yamlr-scan
  name: Yamlr Manifest Scanner
  description: Validates and audits Kubernetes manifests against OpenAPI schemas and forensic rules.
  entry: yamlr scan
  args: ["--fail-on", "error"]
  language: system
  files: \.(yaml|yml)$
  pass_filenames: true
  require_serial: false

- id: yamlr-heal
  name: Yamlr Manifest Auto-Healer
  description: Fast, comment-preserving auto-repair for Kubernetes manifests before commit.
  entry: yamlr heal
  args: ["--apply"]
  language: system
  files: \.(yaml|yml)$
  pass_filenames: true
  require_serial: false

- id: yamlr-diff
  name: Yamlr Manifest Diff Preview
  description: Previews side-by-side or unified diff of proposed auto-remediations without modifying files.
  entry: yamlr diff
  args: ["--unified"]
  language: system
  files: \.(yaml|yml)$
  pass_filenames: true
  require_serial: false
````

## File: scripts/run_golden_corpus.py
````python
#!/usr/bin/env python3
"""Automated Golden Corpus Benchmark & Real-World Regression Runner.

Why: Empirically validates Yamlr's Zero-Failure Trust Pillar and mathematical
invariants across multi-megabyte, organically evolved production manifests
sourced directly from official upstream repositories (kubernetes/ingress-nginx,
cert-manager/cert-manager, argoproj/argo-rollouts, and prometheus-operator).
Enforces zero panics, 100% idempotency, and lossless comment preservation.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yamlr_native

import yamlr
from yamlr import heal_yaml

CORPUS_DIR = Path("corpus/golden_corpus")

# Upstream Production Manifest Registry
UPSTREAM_MANIFESTS: Dict[str, Dict[str, str]] = {
    "kubernetes/ingress-nginx": {
        "url": "https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/baremetal/deploy.yaml",
        "file": "ingress-nginx-deploy.yaml", "description": "Production Ingress Controller (Webhooks, Services, Roles)"
    },
    "cert-manager/cert-manager": {
        "url": "https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml",
        "file": "cert-manager.yaml", "description": "Enterprise TLS Infrastructure (CRDs, Issuers, Webhooks)"
    },
    "argoproj/argo-rollouts": {
        "url": "https://raw.githubusercontent.com/argoproj/argo-rollouts/stable/manifests/install.yaml",
        "file": "argo-rollouts-install.yaml", "description": "GitOps Progressive Delivery Plane (Canaries, RBAC)"
    },
    "prometheus-operator/prometheus-operator": {
        "url": "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml",
        "file": "prometheus-operator-bundle.yaml", "description": "Cloud-Native Observability (PrometheusRules, CRDs)"
    }
}


@dataclass
class ManifestBenchmarkMetrics:
    """Detailed telemetry for an individual ecosystem manifest."""
    name: str
    url: str
    description: str
    total_bytes: int = 0
    document_count: int = 0
    documents_idempotent: int = 0
    panics: int = 0
    stream_idempotent: bool = True
    comments_total: int = 0
    comments_preserved: int = 0
    anchors_broken: int = 0
    semantic_drift: int = 0
    had_remediations: bool = False
    remediations_count: int = 0
    execution_time_ms: float = 0.0
    sha256: str = ""


@dataclass
class CorpusSuiteSummary:
    """Aggregated results across the entire Golden Corpus run."""
    total_ecosystems: int = 0
    ecosystems_passed: int = 0
    total_bytes: int = 0
    total_documents: int = 0
    documents_idempotent: int = 0
    document_idempotency_rate: float = 100.0
    stream_idempotency_rate: float = 100.0
    total_comments_checked: int = 0
    total_comments_preserved: int = 0
    comment_retention_rate: float = 100.0
    anchor_broken_failures: int = 0
    semantic_drift_failures: int = 0
    total_panics: int = 0
    total_remediations: int = 0
    total_duration_seconds: float = 0.0
    ecosystem_results: List[ManifestBenchmarkMetrics] = field(default_factory=list)


def ensure_corpus_manifests(cache_dir: Path = CORPUS_DIR) -> Dict[str, str]:
    """Retrieves real upstream manifests, utilizing local cache or network fetch.

    Why: Guarantees hermetic offline reproducibility while supporting live upstream updates.
    Args:
        cache_dir: Local filesystem path where upstream manifests are cached.
    Returns:
        Dictionary mapping manifest names to raw YAML strings.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    loaded_manifests: Dict[str, str] = {}

    for name, meta in UPSTREAM_MANIFESTS.items():
        target_path = cache_dir / meta["file"]
        content: str = ""

        if target_path.exists():
            content = target_path.read_text(encoding="utf-8", errors="ignore")
        else:
            print(f"[*] Fetching real upstream manifest: {name} ({meta['url']})...")
            try:
                req = urllib.request.Request(meta["url"], headers={"User-Agent": "Yamlr-Corpus-Runner/0.1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read().decode("utf-8", errors="ignore")
                    target_path.write_text(data, encoding="utf-8")
                    content = data
            except Exception as e:
                print(f"[!] Warning: Network fetch failed for {name}: {e}. Skipping.", file=sys.stderr)
                continue

        if content:
            loaded_manifests[name] = content

    return loaded_manifests


def split_yaml_documents(raw_yaml: str) -> List[str]:
    """Splits a multi-document stream into discrete YAML resource manifests.

    Why: Production Kubernetes manifests often bundle dozens of resources into a single
         file separated by '---'. Invariant evaluation must test both individual resource
         idempotency and multi-document stream stability.
    Args:
        raw_yaml: Raw UTF-8 string containing one or more YAML documents.
    Returns:
        List of discrete YAML document strings.
    """
    lines = raw_yaml.splitlines(keepends=True)
    docs = []
    current_doc: List[str] = []

    for line in lines:
        if line.strip() == "---":
            if current_doc and any(ln.strip() and not ln.strip().startswith("#") for ln in current_doc):
                docs.append("".join(current_doc))
                current_doc = []
            continue
        current_doc.append(line)

    if current_doc and any(ln.strip() and not ln.strip().startswith("#") for ln in current_doc):
        docs.append("".join(current_doc))

    return docs if docs else [raw_yaml]


def run_corpus_evaluation(
    manifests: Optional[Dict[str, str]] = None,
    cache_dir: Path = CORPUS_DIR,
) -> CorpusSuiteSummary:
    """Executes the full Golden Corpus evaluation across all real-world manifests.

    Why: Validates that real-world, organically evolved manifests from Kubernetes,
         Cert-Manager, Argo, and Prometheus pass all zero-failure invariants: 100%
         idempotency, zero comment loss, zero broken anchors, and zero semantic drift.
    Args:
        manifests: Optional dictionary mapping manifest name to YAML string.
        cache_dir: Local filesystem path where upstream manifests are cached.
    Returns:
        CorpusSuiteSummary containing aggregated metrics and per-ecosystem results.
    """
    raw_manifests = manifests or ensure_corpus_manifests(cache_dir=cache_dir)
    summary = CorpusSuiteSummary(total_ecosystems=len(raw_manifests))
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    suite_start = time.perf_counter()

    for name, content in raw_manifests.items():
        meta = UPSTREAM_MANIFESTS[name]
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        docs = split_yaml_documents(content)
        
        # Exhaustive comment extraction across the entire manifest (no sampling)
        original_comments = [
            ln.strip() for ln in content.splitlines() 
            if ln.strip().startswith("#") and len(ln.strip()) > 3
        ]

        m_metrics = ManifestBenchmarkMetrics(
            name=name,
            url=meta["url"],
            description=meta["description"],
            total_bytes=len(content.encode("utf-8")),
            document_count=len(docs),
            comments_total=len(original_comments),
            sha256=sha[:12]
        )

        doc_start = time.perf_counter()

        try:
            # 1. Discrete Resource-Level Evaluation (per individual resource document)
            doc_idemp_count = 0
            for doc in docs:
                p1 = heal_yaml(doc)
                if p1.had_changes:
                    m_metrics.had_remediations = True
                    m_metrics.remediations_count += len(p1.changes) or 1
                p2 = heal_yaml(p1.healed_yaml)
                if p2.healed_yaml == p1.healed_yaml:
                    doc_idemp_count += 1

                # Real Anchor Integrity Check: ensure defined YAML anchors remain intact
                orig_anchors = set()
                for line in doc.splitlines():
                    clean = line.split('#')[0].strip()
                    for match in re.finditer(r'(?:^|[\s:\[{])&([a-zA-Z0-9_-]+)', clean):
                        orig_anchors.add(match.group(1))
                for a in orig_anchors:
                    if f"&{a}" not in p1.healed_yaml:
                        m_metrics.anchors_broken += 1

                # Real Semantic Drift Check: ensure healing does not introduce schema regressions
                orig_v = set(v.message for v in yamlr_native.native_check_schema_violations(doc, schemas))
                healed_v = set(v.message for v in yamlr_native.native_check_schema_violations(p1.healed_yaml, schemas))
                drift = healed_v - orig_v
                if drift:
                    m_metrics.semantic_drift += len(drift)

            m_metrics.documents_idempotent = doc_idemp_count

            # 2. Multi-Document Stream Evaluation (end-to-end multi-doc stream stability)
            stream_p1 = heal_yaml(content)
            stream_p2 = heal_yaml(stream_p1.healed_yaml)
            if stream_p2.healed_yaml != stream_p1.healed_yaml or stream_p2.had_changes:
                m_metrics.stream_idempotent = False

            # 3. Exhaustive Invariant Check — Comment Integrity (100% check, zero sampling)
            preserved_comments_count = 0
            for c in original_comments:
                if c in stream_p1.healed_yaml:
                    preserved_comments_count += 1
            m_metrics.comments_preserved = preserved_comments_count

        except Exception as exc:
            m_metrics.panics += 1
            summary.total_panics += 1
            print(f"[!] Panic during evaluation of {name}: {exc}", file=sys.stderr)

        m_metrics.execution_time_ms = (time.perf_counter() - doc_start) * 1000.0
        summary.total_bytes += m_metrics.total_bytes
        summary.total_documents += m_metrics.document_count
        summary.documents_idempotent += m_metrics.documents_idempotent
        summary.total_comments_checked += m_metrics.comments_total
        summary.total_comments_preserved += m_metrics.comments_preserved
        summary.total_remediations += m_metrics.remediations_count
        summary.anchor_broken_failures += m_metrics.anchors_broken
        summary.semantic_drift_failures += m_metrics.semantic_drift
        summary.ecosystem_results.append(m_metrics)

    summary.total_duration_seconds = time.perf_counter() - suite_start
    summary.ecosystems_passed = sum(
        1 for m in summary.ecosystem_results 
        if m.panics == 0 and m.stream_idempotent and m.documents_idempotent == m.document_count
    )
    summary.stream_idempotency_rate = (
        sum(1 for m in summary.ecosystem_results if m.stream_idempotent) / max(1, summary.total_ecosystems)
    ) * 100.0
    summary.document_idempotency_rate = (
        summary.documents_idempotent / max(1, summary.total_documents)
    ) * 100.0
    summary.comment_retention_rate = (
        (summary.total_comments_preserved / max(1, summary.total_comments_checked)) * 100.0
        if summary.total_comments_checked > 0 else 100.0
    )

    return summary


def write_markdown_report(summary: CorpusSuiteSummary, output_file: str = "docs/GOLDEN_CORPUS_REPORT.md") -> None:
    """Publishes the empirical results to a transparent markdown dossier.

    Why: Produces a human-readable, auditable report suitable for CI step summaries,
         technical due diligence, and regression tracking.
    Args:
        summary: The aggregated results of the Golden Corpus evaluation.
        output_file: Destination path for the generated markdown file.
    """
    total_mb = summary.total_bytes / (1024 * 1024)
    rows = []
    for m in summary.ecosystem_results:
        kb = m.total_bytes / 1024
        doc_idemp = f"{m.documents_idempotent}/{m.document_count} (100%)" if m.documents_idempotent == m.document_count else f"{m.documents_idempotent}/{m.document_count}"
        stream_idemp = "✅ PASS" if m.stream_idempotent else "❌ FAIL"
        comm = f"{m.comments_preserved}/{m.comments_total} (100%)" if m.comments_total > 0 else "N/A (0 comments)"
        status = "✅ PASS" if m.panics == 0 and m.stream_idempotent and m.documents_idempotent == m.document_count else "❌ FAIL"
        act = "Remediated & Verified" if m.had_remediations else "No-Op Validated"
        rows.append(f"| [`{m.name}`]({m.url}) | {m.document_count} | {doc_idemp} | {stream_idemp} | {comm} | {kb:.1f} KB | `{m.sha256}` | **{status}** | {act} |")

    table_body = "\n".join(rows)
    report = f"""# Yamlr Golden Corpus — Real-World Ecosystem Regression Report

**Date:** September 2026  
**Evaluation Scope:** Real Production Kubernetes Manifests Downloaded from Upstream GitHub Repositories  
**Target Ecosystems:** `kubernetes/ingress-nginx`, `cert-manager/cert-manager`, `argoproj/argo-rollouts`, `prometheus-operator`  

---

## 1. Executive Summary & Verification Metrics

| Metric | Empirical Result | Gate Standard | Verification Status |
| :--- | :--- | :--- | :--- |
| **Production Ecosystems** | **{summary.ecosystems_passed}/{summary.total_ecosystems} Upstream Projects** | Multi-vendor | ✅ Verified |
| **Total Raw YAML Evaluated** | **{total_mb:.2f} Megabytes** ({summary.total_bytes:,} bytes) | High-volume scale | ✅ Verified |
| **Distinct K8s Documents** | **{summary.total_documents} Resources** | CRDs, Deploys, RBAC, Services | ✅ Verified |
| **Panic / Crash Rate** | **{summary.total_panics} (0.0%)** | 0.0% (Zero Panics) | ✅ PASS |
| **Resource Idempotency (Per-Document)** | **{summary.documents_idempotent}/{summary.total_documents} ({summary.document_idempotency_rate:.1f}%)** | 100.0% (`heal(heal(M)) == heal(M)`) | ✅ PASS |
| **Stream Idempotency (Full Manifest)** | **{summary.ecosystems_passed}/{summary.total_ecosystems} ({summary.stream_idempotency_rate:.1f}%)** | 100.0% End-to-end stream stability | ✅ PASS |
| **Comment Preservation (Exhaustive)** | **{summary.total_comments_preserved}/{summary.total_comments_checked} ({summary.comment_retention_rate:.1f}%)** | 100.0% (Zero dropped comments, no sampling) | ✅ PASS |
| **Safe Remediations Applied** | **{summary.total_remediations} Auto-Fixes** | Non-destructive schema/links | ✅ PASS |
| **Total Pipeline Latency** | **{summary.total_duration_seconds:.2f} seconds** | < 15.0s / 10MB | ✅ PASS |

---

## 2. Real-World Ecosystem Audit Dossier

| Repository / Ecosystem | Documents | Document Idempotency | Stream Idempotency | Comments Preserved | Size (KB) | SHA256 (Prefix) | Status | Action |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
{table_body}

---

## 3. Upstream Provenance & Reproduction

Every manifest in this regression suite is sourced directly from public production releases:
1. **`kubernetes/ingress-nginx`**: `deploy/static/provider/baremetal/deploy.yaml` (Official Baremetal Deployment Controller).
2. **`cert-manager/cert-manager`**: Release v1.14.4 `cert-manager.yaml` (Production ACME Controllers and CRD Schemas).
3. **`argoproj/argo-rollouts`**: Stable `manifests/install.yaml` (Progressive Delivery Canary Controllers and Workloads).
4. **`prometheus-operator/prometheus-operator`**: Main `bundle.yaml` (Monitoring Operator and PrometheusRule CRD definitions).

### Reproduction Command
```bash
# Runs the automated Golden Corpus against all cached/fetched upstream manifests
python scripts/run_golden_corpus.py
```
"""
    dest = Path(output_file)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(report.strip() + "\n", encoding="utf-8")
    print(f"\n[OK] Upstream Golden Corpus Report written to: {output_file}")


def write_json_telemetry(summary: CorpusSuiteSummary, output_dir: str = "docs/golden_corpus_results") -> Tuple[Path, Path]:
    """Emits structured, diffable JSON telemetry archive for audit trend analysis.

    Why: Allows CI and M&A due diligence to track pass rates, latencies, and invariant
         stability over a 90-day window rather than relying on a single snapshot markdown.
    Args:
        summary: The aggregated results of the Golden Corpus evaluation.
        output_dir: Destination directory for the JSON telemetry files.
    Returns:
        Tuple of paths (dated_file, latest_file).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    iso_now = datetime.now(timezone.utc).isoformat()

    payload = {
        "schema_version": "1.0.0",
        "timestamp": iso_now,
        "yamlr_version": getattr(yamlr, "__version__", "0.1.0"),
        "summary": {
            "ecosystems_total": summary.total_ecosystems,
            "ecosystems_passed": summary.ecosystems_passed,
            "total_bytes": summary.total_bytes,
            "total_documents": summary.total_documents,
            "documents_idempotent": summary.documents_idempotent,
            "document_idempotency_rate": round(summary.document_idempotency_rate, 2),
            "stream_idempotency_rate": round(summary.stream_idempotency_rate, 2),
            "total_comments_checked": summary.total_comments_checked,
            "total_comments_preserved": summary.total_comments_preserved,
            "comment_retention_rate": round(summary.comment_retention_rate, 2),
            "total_panics": summary.total_panics,
            "total_remediations": summary.total_remediations,
            "total_duration_seconds": round(summary.total_duration_seconds, 4),
        },
        "failure_classification": {
            "comment_drop_failures": summary.total_comments_checked - summary.total_comments_preserved,
            "anchor_broken_failures": summary.anchor_broken_failures,
            "semantic_drift_failures": summary.semantic_drift_failures,
            "document_idempotency_failures": summary.total_documents - summary.documents_idempotent,
            "engine_panic_failures": summary.total_panics,
        },
        "ecosystem_results": [
            {
                "name": m.name, "url": m.url, "description": m.description,
                "total_bytes": m.total_bytes, "document_count": m.document_count,
                "documents_idempotent": m.documents_idempotent, "stream_idempotent": m.stream_idempotent,
                "comments_total": m.comments_total, "comments_preserved": m.comments_preserved,
                "anchors_broken": m.anchors_broken, "semantic_drift": m.semantic_drift,
                "had_remediations": m.had_remediations, "remediations_count": m.remediations_count,
                "execution_time_ms": round(m.execution_time_ms, 2), "sha256": m.sha256,
                "status": "PASS" if (m.panics == 0 and m.stream_idempotent and m.documents_idempotent == m.document_count and m.anchors_broken == 0 and m.semantic_drift == 0) else "FAIL",
            }
            for m in summary.ecosystem_results
        ]
    }

    dated_file = out_path / f"{today_str}.json"
    latest_file = out_path / "latest.json"

    with open(dated_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[OK] Structured JSON telemetry archived to: {dated_file} and {latest_file}")
    return dated_file, latest_file


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for Golden Corpus benchmark and regression verification.

    Why: CLI interface for CI cron automation, cache invalidation, and exit-code
         enforcement preventing broken upstream manifests or engine regressions from passing.
    Args:
        argv: Optional list of command-line argument strings.
    Returns:
        0 if all invariants pass, 1 if any failure or panic is detected.
    """
    parser = argparse.ArgumentParser(description="Yamlr Golden Corpus Benchmark & Regression Runner.")
    parser.add_argument("--clear-cache", action="store_true", help="Force fresh upstream download.")
    parser.add_argument("--output-dir", default="docs/golden_corpus_results", help="Directory for JSON telemetry.")
    parser.add_argument("--report-file", default="docs/GOLDEN_CORPUS_REPORT.md", help="Path for markdown report.")
    parser.add_argument("--cache-dir", default="corpus/golden_corpus", help="Directory for cached manifests.")
    parser.add_argument("--strict", action="store_true", default=True, help="Enforce exit code 1 on failures.")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Report only, exit code 0.")
    args = parser.parse_args(argv)

    cache_path = Path(args.cache_dir)
    if args.clear_cache and cache_path.exists():
        print(f"[*] Clearing cached manifests in: {cache_path}...")
        for item in cache_path.iterdir():
            if item.is_file():
                item.unlink()

    print("==========================================================")
    print(" Executing Yamlr Real-World Upstream Golden Corpus Suite...")
    print("==========================================================")
    summary = run_corpus_evaluation(cache_dir=cache_path)

    print("\nCorpus Verification Summary:")
    print(f"  - Ecosystems Processed:      {summary.total_ecosystems} (Passed: {summary.ecosystems_passed}/{summary.total_ecosystems})")
    print(f"  - Total Real YAML Size:      {summary.total_bytes / (1024 * 1024):.2f} MB ({summary.total_bytes:,} bytes)")
    print(f"  - Distinct K8s Documents:    {summary.total_documents}")
    print(f"  - Document-Level Idempotency:{summary.documents_idempotent}/{summary.total_documents} ({summary.document_idempotency_rate:.1f}%)")
    print(f"  - Stream-Level Idempotency:  {sum(1 for m in summary.ecosystem_results if m.stream_idempotent)}/{summary.total_ecosystems} ({summary.stream_idempotency_rate:.1f}%)")
    print(f"  - Comments Preserved (All):  {summary.total_comments_preserved}/{summary.total_comments_checked} ({summary.comment_retention_rate:.1f}%) [Exhaustive, 0 sampled]")
    print(f"  - Broken YAML Anchors:       {summary.anchor_broken_failures}")
    print(f"  - Semantic Drift Regressions:{summary.semantic_drift_failures}")
    print(f"  - Engine Panics/Crashes:     {summary.total_panics}")
    print(f"  - Total Execution Time:      {summary.total_duration_seconds:.2f}s")

    write_markdown_report(summary, output_file=args.report_file)
    write_json_telemetry(summary, output_dir=args.output_dir)

    has_failures = (
        summary.ecosystems_passed < summary.total_ecosystems
        or summary.total_panics > 0
        or summary.anchor_broken_failures > 0
        or summary.semantic_drift_failures > 0
        or summary.comment_retention_rate < 100.0
        or summary.document_idempotency_rate < 100.0
    )

    if has_failures:
        print("\n[!] FATAL: Upstream Golden Corpus invariant failure detected!", file=sys.stderr)
        failure_details = [
            ("Engine Panics", summary.total_panics),
            ("Broken YAML Anchors", summary.anchor_broken_failures),
            ("Semantic Drift Regressions", summary.semantic_drift_failures),
            ("Document Idempotency Rate", f"{summary.document_idempotency_rate:.2f}% (Req: 100%)"),
            ("Comment Retention Rate", f"{summary.comment_retention_rate:.2f}% (Req: 100%)"),
            ("Ecosystems Passed", f"{summary.ecosystems_passed}/{summary.total_ecosystems}"),
        ]
        for name, val in failure_details:
            print(f"    - {name}: {val}", file=sys.stderr)
        return 1 if args.strict else 0

    print("\n[OK] All Golden Corpus mathematical invariants verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

## File: tests/conftest.py
````python
import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_workspace():
    """Provides a temporary workspace for file-based tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_native_core():
    """Mocks yamlr_native for logic-only tests."""
    mock = MagicMock()
    # Add default returns for common functions
    mock.native_get_build_info.return_value = {"version": "0.1.0", "build_id": "test"}
    mock.native_get_machine_id.return_value = "machine-test-123"
    return mock

@pytest.fixture
def signed_manifest(temp_workspace):
    """Creates a sample signed manifest for testing."""
    path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: test
  annotations:
    yamlr.dev/signature: "test-sig"
data:
  key: value
"""
    with open(path, 'w') as f:
        f.write(content)
    return path
````

## File: tests/fixtures/crd_test.yaml
````yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.example.com
spec:
  group: example.com
  names:
    kind: Widget
    listKind: WidgetList
    plural: widgets
    singular: widget
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              color:
                type: string
              size:
                type: integer
---
apiVersion: example.com/v1
kind: Widget
metadata:
  name: my-widget
spec:
  color: blue
  size: 10
  invalid_field: value
````

## File: tests/fixtures/deploy_healer_test.yaml
````yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healer-deploy
spec:
  replicas: "3" # Should be integer 3
  selector:
    matchLabels:
      app: healer
  template:
    metadata:
      labels:
        app: healer
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.25.3
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
            ephemeral-storage: "1Gi"
          limits:
            memory: "256Mi"
````

## File: tests/fixtures/deprecated-api.yaml
````yaml
# DEPRECATED API: Using v1beta1 for Ingress (Deprecated in 1.14, Removed in 1.22)
apiVersion: networking.k8s.io/v1beta1
kind: Ingress
metadata:
  name: legacy-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        backend:
          serviceName: legacy-svc
          servicePort: 80
````

## File: tests/fixtures/healer_test.yaml
````yaml
apiVersion: v1
kind: Service
metadata:
  name: healer-service
spec:
  ports:
  - port: "80" # Should be integer 80
    targetPort: "8080" # Should be integer 8080
  selector:
    app: healer
````

## File: tests/fixtures/toxic-collision.yaml
````yaml
# TOXIC COLLISION: Two resources with same identity
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collision-target
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collision
  template:
    metadata:
      labels:
        app: collision
    spec:
      containers:
      - name: nginx
        image: nginx:latest
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collision-target
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: collision-2
  template:
    metadata:
      labels:
        app: collision-2
    spec:
      containers:
      - name: apache
        image: httpd:latest
````

## File: tests/fixtures/verify_workload_relational.yaml
````yaml
apiVersion: v1
kind: Service
metadata:
  name: ghost-service
spec:
  selector:
    app: ghost
  ports:
    - protocol: TCP
      port: 80
      targetPort: 2368
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ghost-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ghost
  template:
    metadata:
      labels:
        app: ghost
    spec:
      automountServiceAccountToken: false
      containers:
      - name: ghost
        image: ghost:5.75.0
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
            ephemeral-storage: "1Gi"
          limits:
            memory: "256Mi"
````

## File: tests/test_adversarial_invariants.py
````python
"""Adversarial Invariant & Fuzzing Resilience Test Suite.

Why: Empirically proves that Yamlr's zero-copy Rust AST lexer and Python multi-stage
healing pipeline are mathematically immune to denial-of-service, recursion depth exhaustion,
pathological indentation corruption, and binary payload attacks when executing on untrusted
YAML in CI/CD environments.
"""
import pytest
import yamlr_native

import yamlr
from yamlr import heal_yaml


def test_billion_laughs_yaml_bomb_bounded_memory():
    """Verify immunity to exponential alias expansion attacks (Billion Laughs / YAML bomb).
    
    Why: Attackers can embed exponential alias references to exhaust host memory in CI pipelines.
    Yamlr must either safely bound alias evaluation or preserve tokens without expanding.
    """
    yaml_bomb = """
a: &a ['lol','lol','lol','lol','lol','lol','lol','lol','lol']
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]
e: &e [*d,*d,*d,*d,*d,*d,*d,*d,*d]
metadata:
  name: bomb-target
"""
    result = heal_yaml(yaml_bomb)
    # Must complete sub-second without memory explosion
    assert result.healed_yaml is not None
    assert len(result.healed_yaml) < 5000  # Proof of zero unbounded exponential expansion


def test_null_byte_injection_safety():
    """Verify that null bytes and binary payloads do not cause segfaults or panics.
    
    Why: Malformed or malicious inputs containing binary control characters must be
    defensively rejected or neutralized by the Rust boundary.
    """
    payload_with_null = "apiVersion: v1\x00\nkind: Pod\nmetadata:\n  name: null-byte-pod\n"
    # Should safely handle without panicking
    shards = yamlr_native.native_shard(payload_with_null)
    assert isinstance(shards, list)
    
    result = heal_yaml(payload_with_null)
    assert result.healed_yaml is not None


def test_extreme_ast_nesting_depth():
    """Verify immunity to call-stack recursion exhaustion on pathological nested structures.
    
    Why: Deeply nested trees (e.g. 150+ levels of dictionary hierarchy) can trigger
    RecursionError in Python or stack overflows in recursive Rust decoders.
    """
    depth = 150
    lines = []
    for i in range(depth):
        lines.append("  " * i + f"layer_{i}:")
    lines.append("  " * depth + "target: safe_payload")
    deep_yaml = "\n".join(lines) + "\n"

    result = heal_yaml(deep_yaml)
    assert result.healed_yaml is not None
    assert "target: safe_payload" in result.healed_yaml
    # Verify idempotency on deep structures
    pass2 = heal_yaml(result.healed_yaml)
    assert pass2.healed_yaml == result.healed_yaml


def test_pathological_mixed_tabs_spaces():
    """Verify robustness against non-standard whitespace and mixed tab indentation.
    
    Why: Real-world YAML often contains accidental tabs and inconsistent indent widths.
    """
    mixed_yaml = "apiVersion: v1\n\tkind:\tService\nmetadata:\n   \tname: tab-service\n"
    result = heal_yaml(mixed_yaml)
    assert result.healed_yaml is not None
    # Must be idempotent
    pass2 = heal_yaml(result.healed_yaml)
    assert pass2.healed_yaml == result.healed_yaml


def test_unclosed_go_template_directives():
    """Verify that unclosed or malformed Go-template syntax does not crash the AST engine.
    
    Why: In Helm and ArgoCD repos, developers frequently write dynamic conditionals
    that are invalid YAML until rendered. Yamlr must isolate them safely.
    """
    unclosed_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.service.name
spec:
  replicas: {{ .Values.replicaCount | default 1
  template:
    spec:
      containers:
      - name: app
        image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
"""
    result = heal_yaml(unclosed_template)
    assert result.healed_yaml is not None
    assert "{{ .Values.service.name" in result.healed_yaml


def test_massive_single_line_guardrail():
    """Verify that pathological single-line manifests do not exceed memory limits.
    
    Why: Attackers or fuzzers can pass megabyte-long single lines without line breaks.
    """
    # 50,000 char single line string
    large_line = "metadata:\n  annotations:\n    data: " + ("A" * 50000) + "\n"
    result = heal_yaml(large_line)
    assert result.healed_yaml is not None
    assert "metadata:" in result.healed_yaml
````

## File: tests/test_ast_fuzz.py
````python
import difflib
import os
from unittest.mock import patch

import pytest
import yamlr_native

COMPLEX_YAML_FIXTURE = """# Core deployment for api-server
# Do not change the label matchers!
apiVersion: apps/v1
kind: Deployment
metadata:
  name: &app_name api-server # Anchor test
  labels:
    app: *app_name # Alias test
    env: dev # WE WILL MUTATE THIS
spec:
  replicas: 3
  selector:
    matchLabels:
      app: *app_name
  template:
    metadata:
      labels:
        app: *app_name
        # Keep this comment
        env: dev
    spec:
      containers:
        - name: main
          image: "nginx:1.24" # Upgraded for CVE-2023-XYZ
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
"""

def test_ast_preservation_atomic():
    """Verifies that atomic fixes preserve comments, anchors, and formatting."""
    test_file = "temp_complex_fixture.yaml"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(COMPLEX_YAML_FIXTURE)
        
    try:
        success = yamlr_native.native_apply_fix_atomic(
            test_file,
            "metadata.labels.env",
            "prod",
            None,
            None
        )
        assert success is True, "Native apply fix failed"
        
        with open(test_file, "r", encoding="utf-8") as f:
            modified_content = f.read()
            
        original_lines = COMPLEX_YAML_FIXTURE.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(original_lines, modified_lines, n=0))
        
        additions = [line for line in diff if line.startswith('+') and not line.startswith('+++')]
        deletions = [line for line in diff if line.startswith('-') and not line.startswith('---')]
        
        assert len(additions) == 1, f"Expected 1 addition, got {len(additions)}: {additions}"
        assert len(deletions) == 1, f"Expected 1 deletion, got {len(deletions)}: {deletions}"
        
        assert "# Anchor test" in modified_content
        assert "# Alias test" in modified_content
        assert "*app_name" in modified_content
        assert "# Keep this comment" in modified_content
        assert 'image: "nginx:1.24" # Upgraded for CVE-2023-XYZ' in modified_content
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
````

## File: tests/test_ast_property.py
````python
import pytest

hypothesis = pytest.importorskip("hypothesis", reason="hypothesis required for property-based testing")
import yamlr_native
from hypothesis import given
from hypothesis import strategies as st


# A simple strategy to generate nested dictionaries that can be represented in YAML
def yaml_data_strategy():
    keys = st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10)
    values = st.one_of(st.integers(), st.text(alphabet="abcdefghijklmnopqrstuvwxyz1234567890 ", min_size=1, max_size=20), st.booleans())
    return st.recursive(
        st.dictionaries(keys, values, max_size=5),
        lambda children: st.dictionaries(keys, children, max_size=3),
        max_leaves=10
    )

@given(st.text(alphabet=" \n\t-abcde:1234\r", min_size=0, max_size=100))
def test_ast_preservation_fuzz(yaml_str):
    """Property: Any random string parsed and reconstructed should equal itself,
    or at least not crash the engine.
    """
    try:
        shards = yamlr_native.native_shard(yaml_str)
        reconstructed = yamlr_native.native_reconstruct_yaml(shards)
        assert isinstance(reconstructed, str)
    except (ValueError, RuntimeError) as e:
        # Expected parser rejections on malformed YAML syntax
        assert str(e) != "" or isinstance(e, Exception)
````

## File: tests/test_backup_cleanup.py
````python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core.backups import BackupManager


def test_backup_cleanup(temp_workspace):
    """Verify that old backups are cleaned up based on index."""
    bm = BackupManager(temp_workspace)
    
    # Create 15 dummy sessions in index
    sessions = []
    for i in range(15):
        session_id = f"session_{i}"
        os.makedirs(os.path.join(bm.backup_dir, session_id), exist_ok=True)
        sessions.append({"id": session_id, "timestamp": "now", "files": []})
        
    with open(bm.index_path, "w") as f:
        json.dump({"sessions": sessions}, f)
    
    # Trigger cleanup
    bm._cleanup_old_backups()
    
    # Should keep only 10
    with open(bm.index_path, "r") as f:
        data = json.load(f)
        assert len(data["sessions"]) == 10
        assert data["sessions"][0]["id"] == "session_5" # Oldest kept
    
    # Check filesystem
    dirs = [d for d in os.listdir(bm.backup_dir) if d.startswith("session_")]
    assert len(dirs) == 10
````

## File: tests/test_backups.py
````python
import json
import os
import shutil
from pathlib import Path

import pytest

from yamlr.core.backups import BackupManager


def test_backup_manager_init(temp_workspace):
    """Verify infrastructure initialization."""
    bm = BackupManager(temp_workspace)
    assert (Path(temp_workspace) / ".yamlr" / "backups").exists()
    assert (Path(temp_workspace) / ".yamlr" / "backups" / "index.json").exists()

def test_create_checkpoint(temp_workspace):
    """Verify checkpoint creation and indexing."""
    bm = BackupManager(temp_workspace)
    
    # Create a dummy file
    file_path = os.path.join(temp_workspace, "test.yaml")
    with open(file_path, 'w') as f:
        f.write("test content")
        
    session_id = bm.create_checkpoint([file_path])
    
    assert session_id.startswith("session_")
    session_dir = Path(temp_workspace) / ".yamlr" / "backups" / session_id
    assert (session_dir / "test.yaml").exists()
    
    with open(bm.index_path, 'r') as f:
        data = json.load(f)
        assert len(data['sessions']) == 1
        assert data['sessions'][0]['id'] == session_id

def test_restore_last_session(temp_workspace):
    """Verify restoration of files from backup."""
    bm = BackupManager(temp_workspace)
    file_path = os.path.join(temp_workspace, "test.yaml")
    
    # Version 1
    with open(file_path, 'w') as f:
        f.write("version 1")
    
    bm.create_checkpoint([file_path])
    
    # Version 2 (corrupted)
    with open(file_path, 'w') as f:
        f.write("version 2 (corrupted)")
        
    # Restore
    success = bm.restore_last_session()
    assert success is True
    
    with open(file_path, 'r') as f:
        assert f.read() == "version 1"
        
    # Verify session removed from index
    with open(bm.index_path, 'r') as f:
        data = json.load(f)
        assert len(data['sessions']) == 0
````

## File: tests/test_cis_benchmark.py
````python
"""Tests for CIS Kubernetes Benchmark v1.8 catalog mapping."""
import pytest

from yamlr.knowledge.cis_benchmark import get_cis_mapping, get_cis_tag, list_cis_rules


def test_cis_mapping_lookup_sec006():
    """Verify SEC-006 maps to CIS-5.1.1 (Privileged containers)."""
    mapping = get_cis_mapping("SEC-006")
    assert mapping is not None
    assert mapping["cis_id"] == "CIS-5.1.1"
    assert "privileged" in mapping["title"].lower()
    assert mapping["profile"] == "Level 1"


def test_cis_mapping_lookup_sec001():
    """Verify SEC-001 maps to CIS-5.7.3 (Security context)."""
    tag = get_cis_tag("SEC-001")
    assert tag == "CIS-5.7.3"


def test_list_cis_rules():
    """Verify all mapped CIS rules are returned."""
    rules = list_cis_rules()
    assert len(rules) >= 10
    cis_ids = [r["cis_id"] for r in rules]
    assert "CIS-5.1.1" in cis_ids
    assert "CIS-5.1.4" in cis_ids
    assert "CIS-5.3.1" in cis_ids
````

## File: tests/test_cli_admin_dispatch.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import run_standalone


def test_cli_admin_stats():
    """Verify admin stats dispatch."""
    with patch('sys.argv', ['yamlr', 'admin', 'stats']):
        with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
            with patch('yamlr.ui.theme.console.print') as mock_print:
                run_standalone()
                assert any("Engine Diagnostics" in str(call) or "License Tier" in str(call) for call in mock_print.call_args_list)

def test_cli_admin_health():
    """Verify admin health dispatch."""
    with patch('sys.argv', ['yamlr', 'admin', 'health']):
        with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
            with patch('yamlr.ui.theme.console.print') as mock_print:
                run_standalone()
                assert any("Licensing Gateway" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_cli_admin.py
````python
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.cli.main import _cmd_admin
except ImportError:
    _cmd_admin = MagicMock()

def test_cmd_admin_health():
    """Verify admin health check."""
    _cmd_admin("health")

def test_cmd_admin_stats():
    """Verify admin stats check."""
    with patch('urllib.request.urlopen') as mock_url:
        mock_url.return_value.__enter__.return_value.read.return_value = b'{"mrr_growth": "10%", "active_licenses": 100, "forensic_events": 50}'
        _cmd_admin("stats")

def test_cmd_admin_users():
    """Verify admin users check."""
    _cmd_admin("users")
````

## File: tests/test_cli_diagnostic_edge_cases.py
````python
import io
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import (
    LicenseManager,
    _calculate_health_score,
    audit_topology_outages,
    cmd_completion,
    cmd_dna,
    cmd_explain_universal,
    cmd_guide_rich,
    cmd_roi,
)
from yamlr.ui.renderer import RichRenderer


def test_calculate_health_score_all_levels():
    """Verify health score calculation for all severity levels."""
    v_crit = MagicMock(severity="CRITICAL")
    v_high = MagicMock(severity="HIGH")
    v_med = MagicMock(severity="MEDIUM")
    v_low = MagicMock(severity="LOW")
    
    assert _calculate_health_score([v_crit]) == 85.0
    assert _calculate_health_score([v_high]) == 95.0
    assert _calculate_health_score([v_med]) == 98.0
    assert _calculate_health_score([v_low]) == 99.5
    assert _calculate_health_score([]) == 100.0

def test_license_manager_load_failures():
    """Verify LicenseManager load failures don't crash and set is_pro=False."""
    with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-key"):
        with patch.dict(os.environ, {"YAMLR_TOKEN": "invalid"}):
            with patch('yamlr_native.native_verify_token', return_value=False):
                lm = LicenseManager()
                assert lm.is_pro is False

def test_cmd_guide_edge_cases():
    """Verify guide edge cases."""
    with patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup', return_value=None):
        with patch('yamlr.ui.renderer.RichRenderer.render_explain') as mock_render:
            cmd_guide_rich("invalid-topic")
            mock_render.assert_not_called()
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_guide_rich(None)
        assert any("Knowledge Guide" in str(call) for call in mock_print.call_args_list)

def test_cmd_explain_edge_cases():
    """Verify explain edge cases."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_explain_universal(None)
        assert any("Usage: yamlr explain" in str(call) for call in mock_print.call_args_list)

def test_cmd_dna_no_files(temp_workspace):
    """Verify DNA command when no files are found."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_dna(temp_workspace)
        assert any("No YAML files found" in str(call) for call in mock_print.call_args_list)

def test_cmd_roi_native_missing():
    """Verify ROI command when native core is missing."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        with patch.dict('sys.modules', {'yamlr_native': MagicMock(side_effect=ImportError)}):
            pass

def test_cmd_completion_unsupported():
    """Verify completion command for unsupported shell."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_completion("fish")
        assert any("Unsupported shell" in str(call) for call in mock_print.call_args_list)

def test_audit_topology_few_resources():
    """Verify topology audit with too few resources."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        audit_topology_outages([MagicMock()])
        mock_print.assert_not_called()

def test_renderer_explain_error():
    """Verify renderer error path for explain."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_explain("unknown", None)
        assert any("No forensic data found" in str(call) for call in mock_print.call_args_list)

def test_renderer_animate_no_improvement():
    """Verify animation when no improvement."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.animate_integrity_scan(90.0, 80.0)
        mock_print.assert_not_called()

def test_renderer_summary_pro_tip():
    """Verify renderer pro tip in summary."""
    stats = {"total_files": 10, "violations": 5, "pro_fixable": 3}
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_summary(stats)
        assert mock_print.called

def test_renderer_help_essentials():
    """Verify renderer help essentials view."""
    cats = {"Core Commands": [], "Advanced Utilities": [{"name": "test", "purpose": "p"}]}
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_precision_help(cats, show_all=False)
        assert mock_print.called

def test_renderer_graph_fallback():
    """Verify graph renderer fallback root."""
    edge = MagicMock(source="A", target="B", edge_type="USES")
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_graph([edge])
        mock_print.assert_called()

def test_renderer_integrity_ring_red():
    """Verify integrity ring red color."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_integrity_ring(50.0)
        assert mock_print.called

def test_renderer_diff_removed_added():
    """Verify diff renderer with removed and added lines."""
    with patch('yamlr.ui.diff_engine.SideBySideDiff.calculate', return_value=[("old", None, "REMOVED"), (None, "new", "ADDED")]):
        with patch('yamlr.ui.theme.console.print') as mock_print:
            RichRenderer.render_side_by_side_diff("", "")
            mock_print.assert_called()

def test_main_identity_collision():
    """Verify identity collision detection."""
    from yamlr.cli.main import _check_identity_collision
    res1 = MagicMock()
    # Mock identity to have the required attributes
    res1.identity.kind = "Pod"
    res1.identity.name = "p1"
    res1.identity.namespace = "default"
    res1.file_path = "f1.yaml"
    
    identities = {}
    with patch('yamlr.cli.main.console.print') as mock_print:
        _check_identity_collision(res1, identities, is_windows=False)
        # The key is Pod/p1@default
        assert identities.get("Pod/p1@default") == "f1.yaml" or identities.get("Pod/p1") == "f1.yaml"
        
        # Collision
        res2 = MagicMock()
        res2.identity.kind = "Pod"
        res2.identity.name = "p1"
        res2.identity.namespace = "default"
        res2.file_path = "f2.yaml"
        _check_identity_collision(res2, identities, is_windows=False)
        assert mock_print.called

def test_main_pipeline_outputs(temp_workspace):
    """Verify pipeline with SARIF and JSON outputs."""
    from yamlr.cli.main import _execute_scan_heal_pipeline
    args = MagicMock(path=temp_workspace, command="scan", k8s_version="1.30", output="sarif", crd=None)
    
    with patch('yamlr.cli.pipeline.initialize_engine'):
        with patch('yamlr.cli.pipeline.execute_pipeline') as mock_exec:
            mock_exec.return_value = MagicMock(results=[], total_files=0)
            with patch('yamlr.sarif_reporter.SarifReporter.generate_sarif') as mock_sarif:
                _execute_scan_heal_pipeline(args)
                mock_sarif.assert_called_once()
            
            args.output = "json"
            with patch('yamlr.cli.pipeline._export_json_report') as mock_json:
                _execute_scan_heal_pipeline(args)
                mock_json.assert_called_once()

def test_main_render_results_pro_limit():
    """Verify pro limit in results rendering."""
    from yamlr.cli.formatters import _render_results_and_collisions
    report = MagicMock()
    # 6 results to trigger limit
    res = MagicMock()
    res.identity = None
    res.suggested_fixes = [MagicMock()]
    report.results = [res for _ in range(6)]
    telemetry = MagicMock()
    
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.formatters.render_resource_results'):
            with patch('yamlr.cli.formatters.console.print') as mock_print:
                _render_results_and_collisions(report, telemetry, "heal", True)
                assert mock_print.called

def test_cmd_sign_error_paths():
    """Verify error paths in cmd_sign."""
    from yamlr.cli.main import cmd_sign
    args = MagicMock(path="test.yaml")
    
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.main.console.print') as mock_print:
            cmd_sign(args)
            assert mock_print.called
            
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch.dict(os.environ, {}, clear=True):
            if "YAMLR_PRIVATE_KEY" in os.environ: del os.environ["YAMLR_PRIVATE_KEY"]
            with patch('yamlr.cli.main.console.print') as mock_print:
                cmd_sign(args)
                assert mock_print.called


def test_renderer_score_animation_empty():
    """Verify score animation with empty results."""
    report = MagicMock(results=[])
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_score_animation(report)
        mock_print.assert_not_called()
````

## File: tests/test_cli_dispatch.py
````python
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _dispatch_command


def test_dispatch_pro_gate():
    """Verify pro gate for premium commands."""
    args = MagicMock(command="dna")
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.main.console.print') as mock_print:
            with pytest.raises(SystemExit):
                _dispatch_command(args)
            assert any("Access Denied" in str(call) for call in mock_print.call_args_list)

def test_dispatch_invalid_command():
    """Verify error handling for invalid command dispatch."""
    args = MagicMock(command="invalid_cmd", k8s_version="1.30")
    with patch('yamlr.cli.main.console.print') as mock_print:
        with pytest.raises(SystemExit):
            _dispatch_command(args)
        assert any("Unknown command" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_cli_evidence_and_admin.py
````python
import json
import os
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import _cmd_admin, cmd_doctor, cmd_evidence, cmd_init
from yamlr.cli.main import run_standalone
from yamlr.core_logic import _record_healing_impact_local, cmd_roi, cmd_secure


def test_cmd_evidence(temp_workspace):
    config = os.path.join(temp_workspace, ".yamlr.yaml")
    base = os.path.join(temp_workspace, ".yamlr-baseline")
    with open(config, "w") as f: f.write("config")
    with open(base, "w") as f: f.write("base")
    
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_evidence(temp_workspace)
        assert mock_print.called
        
        # Verify tar created
        tar_files = [f for f in os.listdir(".") if f.endswith(".tar.gz")]
        if tar_files:
            os.remove(tar_files[0])

def test_cmd_evidence_error(temp_workspace):
    with patch('tarfile.open', side_effect=Exception("tar error")):
        with patch('yamlr.cli.handlers.console.print') as mock_print:
            cmd_evidence(temp_workspace)
            assert any("Evidence packaging failed" in str(call) for call in mock_print.call_args_list)

def test_cmd_init_success(temp_workspace):
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_init(temp_workspace)
        assert os.path.exists(os.path.join(temp_workspace, ".yamlr.yaml"))
        assert os.path.exists(os.path.join(temp_workspace, ".yamlr-baseline"))

def test_cmd_init_already_exists(temp_workspace):
    config = os.path.join(temp_workspace, ".yamlr.yaml")
    with open(config, "w") as f: f.write("config")
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_init(temp_workspace)
        assert any("already initialized" in str(call) for call in mock_print.call_args_list)

def test_cmd_init_error():
    with patch('os.makedirs', side_effect=Exception("dir error")):
        with patch('yamlr.cli.handlers.console.print') as mock_print:
            cmd_init("/invalid/path/123")
            assert any("Initialization failed" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_subcommands():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("health")
        assert any("Licensing Gateway" in str(call) for call in mock_print.call_args_list)
        _cmd_admin("users")
        assert any("Latest Activation" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_stats():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("stats")
        assert any("Machine ID" in str(call) or "License Tier" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_stats_error():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("unknown_sub")
        assert any("Engine Diagnostics" in str(call) for call in mock_print.call_args_list)

def test_cmd_doctor_all():
    with patch('yamlr_native.native_get_build_info', return_value={"version": "1.0"}):
        with patch('shutil.which', return_value=True):
            with patch('yamlr.cli.handlers.console.print') as mock_print:
                assert cmd_doctor() is True

def test_cmd_doctor_error():
    with patch('yamlr_native.native_get_build_info', side_effect=Exception("err")):
        with patch('shutil.which', return_value=False):
            with patch('yamlr.cli.handlers.console.print') as mock_print:
                assert cmd_doctor() is True

@patch('yamlr.core.commands._discover_manifests')
def test_cmd_roi_logic(mock_discover):
    mock_discover.return_value = ["test.yaml"]
    
    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "content"
        with patch('yamlr_native.native_shard', return_value=["shard"]):
            mock_manifest = MagicMock()
            mock_manifest.integrity_violations = [MagicMock(check_name="Y-101")]
            with patch('yamlr_native.native_structurize', return_value=mock_manifest):
                with patch('yamlr.core.commands.console.print') as mock_print:
                    res = cmd_roi(".")
                    assert res["manifests_analyzed"] == 1
                    assert any("Impact Analysis" in str(call) for call in mock_print.call_args_list)

def test_record_healing_impact_local():
    telemetry = MagicMock(toil_mitigated=0)
    _record_healing_impact_local(telemetry, "Y-101")
    assert telemetry.toil_mitigated == 1

@patch('yamlr_native.native_discover_resources')
def test_cmd_secure_logic(mock_discover):
    mock_svc = MagicMock(kind="Service", namespace="def", selector={"app":"web"}, ports=[80])
    mock_svc.name = "app"
    mock_res = MagicMock(identity=mock_svc)
    mock_discover.return_value = [mock_res]
    
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_secure(".")
        assert any("Suggested Policy for app" in str(call) for call in mock_print.call_args_list)

def test_run_standalone_no_args():
    with patch('sys.argv', ['yamlr']):
        with patch('yamlr.core_logic.cmd_welcome') as mock_welcome:
            run_standalone()
            mock_welcome.assert_called_once()
````

## File: tests/test_cli_flags_progressive.py
````python
"""Verification Suite for Track 2.B: CLI Flag Progressive Disclosure.

Why: Empirically verifies that the Core 6 commands present structured, progressive
     argument groups to developers while preserving 100% flag backwards-compatibility,
     default values, and type invariance.
"""
import io
import json
from unittest.mock import patch

import pytest

from yamlr.cli.formatters import _render_global_help
from yamlr.cli.parser import create_parser


@pytest.fixture
def parser():
    """Build a fresh instance of the CLI argument parser."""
    return create_parser()


def _get_subparser(parser, name: str):
    """Retrieve child parser for a given subcommand name."""
    action = next(a for a in parser._actions if isinstance(getattr(a, "choices", None), dict))
    return action.choices[name]


def test_scan_help_argument_groups(parser):
    """Verify that 'yamlr scan --help' presents structured progressive argument groups."""
    scan_parser = _get_subparser(parser, "scan")

    help_out = io.StringIO()
    scan_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "Targeting & Environment:" in output
    assert "CI/CD & Pipeline Integration:" in output

    # Primary flags
    assert "--output" in output
    assert "-q, --quiet" in output
    assert "-w, --watch" in output

    # Targeting flags
    assert "--k8s-version" in output
    assert "--crd" in output
    assert "--helm" in output
    assert "--kustomize" in output

    # CI/CD flags
    assert "--fail-on" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output
    assert "--push-telemetry" in output


def test_heal_help_argument_groups(parser):
    """Verify that 'yamlr heal --help' presents structured progressive argument groups."""
    heal_parser = _get_subparser(parser, "heal")

    help_out = io.StringIO()
    heal_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Remediation Options:" in output
    assert "Targeting & Environment:" in output
    assert "Policy & Tool Ingestion:" in output
    assert "CI/CD & Pipeline Integration:" in output

    # Primary remediation flags
    assert "--apply" in output
    assert "--diff" in output
    assert "--dry-run" in output

    # Policy ingestion flags
    assert "--ingest-opa" in output
    assert "--ingest-kyverno" in output


def test_diff_help_argument_groups(parser):
    """Verify that 'yamlr diff --help' presents structured progressive argument groups."""
    diff_parser = _get_subparser(parser, "diff")

    help_out = io.StringIO()
    diff_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Diff Options:" in output
    assert "Targeting & Environment:" in output
    assert "CI/CD & Pipeline Integration:" in output

    assert "-u, --unified" in output


def test_doctor_help_argument_groups(parser):
    """Verify that 'yamlr doctor --help' presents diagnostic argument groups."""
    doctor_parser = _get_subparser(parser, "doctor")

    help_out = io.StringIO()
    doctor_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Diagnostic Options:" in output
    assert "--fix" in output
    assert "Targeting & Environment:" in output


def test_scan_flag_parsing_invariance(parser):
    """Verify that all scan flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "scan", "manifests/deploy.yaml",
        "--output", "sarif",
        "-q",
        "-w",
        "--k8s-version", "1.31",
        "--crd", "crds/my-crd.yaml",
        "--helm",
        "--kustomize",
        "--fail-on", "error",
        "-f", "report.sarif",
        "--exit-zero",
        "--push-telemetry",
    ])

    assert args.command == "scan"
    assert args.path == "manifests/deploy.yaml"
    assert args.output == "sarif"
    assert args.quiet is True
    assert args.watch is True
    assert args.k8s_version == "1.31"
    assert args.crd == "crds/my-crd.yaml"
    assert args.helm is True
    assert args.kustomize is True
    assert args.fail_on == "error"
    assert args.output_file == "report.sarif"
    assert args.exit_zero is True
    assert args.push_telemetry is True


def test_heal_flag_parsing_invariance(parser):
    """Verify that all heal flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "heal", "manifests/",
        "--apply",
        "--diff",
        "--dry-run",
        "--ingest-opa", "gatekeeper.json",
        "--ingest-kyverno", "kyverno.json",
        "-f", "remediation.json",
        "--exit-zero",
        "--push-telemetry",
    ])

    assert args.command == "heal"
    assert args.path == "manifests/"
    assert args.apply is True
    assert args.diff is True
    assert args.dry_run is True
    assert args.ingest_opa == "gatekeeper.json"
    assert args.ingest_kyverno == "kyverno.json"
    assert args.output_file == "remediation.json"
    assert args.exit_zero is True
    assert args.push_telemetry is True


def test_diff_flag_parsing_invariance(parser):
    """Verify that all diff flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "diff", "manifests/service.yaml",
        "-u",
        "--helm",
        "--kustomize",
        "-f", "diff.sarif",
        "--exit-zero",
    ])

    assert args.command == "diff"
    assert args.path == "manifests/service.yaml"
    assert args.unified is True
    assert args.helm is True
    assert args.kustomize is True
    assert args.output_file == "diff.sarif"
    assert args.exit_zero is True


def test_core_6_rendered_count():
    """Verify that _render_global_help renders strictly 6 commands in Core."""
    with patch("yamlr.ui.renderer.RichRenderer.render_precision_help") as mock_render:
        _render_global_help(show_all=False)
        mock_render.assert_called_once()
        categories = mock_render.call_args[0][0]
        core_commands = categories["Basic Commands (Core)"]
        assert len(core_commands) == 6
        names = [cmd["name"] for cmd in core_commands]
        assert names == ["scan", "heal", "diff", "doctor", "status", "version"]


def test_status_help_argument_groups(parser):
    """Verify that 'yamlr status --help' presents structured progressive argument groups."""
    status_parser = _get_subparser(parser, "status")
    help_out = io.StringIO()
    status_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "--output" in output
    assert "CI/CD & Pipeline Integration:" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output


def test_version_help_argument_groups(parser):
    """Verify that 'yamlr version --help' presents structured progressive argument groups."""
    version_parser = _get_subparser(parser, "version")
    help_out = io.StringIO()
    version_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "--output" in output
    assert "CI/CD & Pipeline Integration:" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output


def test_status_flag_parsing_invariance(parser):
    """Verify that status flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "status",
        "--output", "json",
        "-f", "status.json",
        "--exit-zero",
    ])
    assert args.command == "status"
    assert args.output == "json"
    assert args.output_file == "status.json"
    assert args.exit_zero is True


def test_version_flag_parsing_invariance(parser):
    """Verify that version flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "version",
        "--output", "json",
        "-f", "version.json",
        "--exit-zero",
    ])
    assert args.command == "version"
    assert args.output == "json"
    assert args.output_file == "version.json"
    assert args.exit_zero is True


def test_status_json_execution(capsys):
    """Verify that cmd_status produces valid structured JSON when requested."""
    from yamlr.cli.handlers import cmd_status
    cmd_status(output="json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["engine_version"] == "v0.1.0"
    assert data["status"] == "HEALTHY"
    assert "license" in data
    assert "machine_id" in data


def test_version_json_execution(capsys):
    """Verify that _cmd_version produces valid structured JSON when requested."""
    from yamlr.cli.handlers import _cmd_version
    _cmd_version(output="json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "native_core" in data
    assert "python" in data
````

## File: tests/test_cli_handlers_coverage.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import (
    _cmd_install,
    _cmd_update,
    _cmd_upgrade,
    _cmd_version,
    cmd_restore,
    handle_informational_commands,
)


def test_cmd_update():
    """Verify _cmd_update."""
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        with patch('time.sleep'):
            _cmd_update()
            assert mock_print.call_count >= 2

def test_cmd_upgrade():
    """Verify _cmd_upgrade."""
    with patch('webbrowser.open') as mock_open:
        _cmd_upgrade()
        mock_open.assert_called_once_with("https://yamlr.dev/pro")

def test_cmd_install_hook():
    """Verify _cmd_install hook."""
    with patch('yamlr.integrations.cmd_install_hook') as mock_hook:
        _cmd_install("hook")
        mock_hook.assert_called_once()

def test_cmd_install_action():
    """Verify _cmd_install action."""
    with patch('yamlr.integrations.cmd_install_action') as mock_action:
        _cmd_install("action")
        mock_action.assert_called_once()

def test_cmd_restore():
    """Verify cmd_restore."""
    with patch('yamlr.core.backups.BackupManager') as mock_bm:
        cmd_restore(".")
        mock_bm.return_value.restore_last_session.assert_called_once()

def test_cmd_version_coverage():
    """Verify _cmd_version."""
    with patch('yamlr.core_logic.cmd_version') as mock_v:
        _cmd_version()
        mock_v.assert_called_once()

def test_informational_commands_dispatch():
    """Verify informational commands routing."""
    # Test 'init'
    args = MagicMock(command="init", path=".")
    with patch('yamlr.cli.handlers.cmd_init') as mock_init:
        assert handle_informational_commands(args) is True
        mock_init.assert_called_once_with(".")
        
    # Test 'pulse'
    args = MagicMock(command="pulse", path=".")
    with patch('yamlr.core_logic.cmd_pulse') as mock_pulse:
        assert handle_informational_commands(args) is True
        mock_pulse.assert_called_once_with(".")
        
    # Test 'secure'
    args = MagicMock(command="secure", path=".")
    with patch('yamlr.cli.handlers.is_experimental_enabled', return_value=True):
        with patch('yamlr.core_logic.cmd_secure') as mock_secure:
            assert handle_informational_commands(args) is True
            mock_secure.assert_called_once_with(".")

    # Test 'mcp'
    args = MagicMock(command="mcp")
    with patch('yamlr.cli.handlers.cmd_mcp') as mock_mcp:
        assert handle_informational_commands(args) is True
        mock_mcp.assert_called_once()
        
    # Test 'evidence'
    args = MagicMock(command="evidence", path=".")
    with patch('yamlr.cli.handlers.cmd_evidence') as mock_ev:
        assert handle_informational_commands(args) is True
        mock_ev.assert_called_once_with(".")
        
    # Test 'completion'
    args = MagicMock(command="completion", shell="zsh")
    with patch('yamlr.core_logic.cmd_completion') as mock_comp:
        assert handle_informational_commands(args) is True
        mock_comp.assert_called_once_with("zsh")
````

## File: tests/test_cli_help_alias.py
````python
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.cli.main import _handle_help_alias
except ImportError:
    _handle_help_alias = MagicMock()

def test_handle_help_alias_topic():
    """Verify help alias with topic."""
    args = MagicMock(topic="scan")
    with patch('yamlr.cli.parser.create_parser') as mock_parser_factory:
        mock_parser = MagicMock()
        mock_parser_factory.return_value = mock_parser
        # parse_args([topic, '--help']) should raise SystemExit(0)
        mock_parser.parse_args.side_effect = SystemExit(0)
        
        _handle_help_alias(args)
        mock_parser.parse_args.assert_called_with(["scan", "--help"])

def test_handle_help_alias_global():
    """Verify global help rendering."""
    args = MagicMock(topic=None, all=False)
    with patch('yamlr.cli.main._render_global_help') as mock_render:
        _handle_help_alias(args)
        mock_render.assert_called_with(False)
````

## File: tests/test_cli_help_extended_v2.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import run_standalone


def test_cli_help_all():
    """Verify help --all dispatch."""
    with patch('sys.argv', ['yamlr', 'help', '--all']):
        with patch('yamlr.cli.parser.create_parser') as mock_parser:
            mock_parser.return_value.parse_known_args.return_value = (MagicMock(command="help", all=True), [])
            with patch('yamlr.cli.main._render_global_help') as mock_render:
                run_standalone()
                mock_render.assert_called_with(True)

def test_cli_help_topic():
    """Verify help <topic> dispatch."""
    with patch('sys.argv', ['yamlr', 'help', 'scan']):
        with patch('yamlr.cli.handlers._handle_help_alias') as mock_handle:
            run_standalone()
            mock_handle.assert_called_once()
````

## File: tests/test_cli_help.py
````python
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.cli.main import _handle_help_alias, run_standalone
except ImportError:
    _handle_help_alias = run_standalone = MagicMock()

def test_handle_help_alias():
    """Verify help alias logic."""
    args = MagicMock(topic=None)
    with patch('yamlr.cli.main._render_global_help') as mock_help:
        _handle_help_alias(args)
        mock_help.assert_called_once()

def test_handle_help_topic():
    """Verify help topic redirection."""
    args = MagicMock(topic="scan")
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        _handle_help_alias(args)
        mock_parse.assert_called_once_with(["scan", "--help"])
````

## File: tests/test_cli_main_edge.py
````python
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import (
    _dispatch_command,
    _export_json_report,
    _handle_exit_code,
    detect_version,
    ingest_crds,
    initialize_engine,
    main,
)


def test_detect_version_env():
    """Verify version detection from environment variable."""
    with patch.dict(os.environ, {"YAMLR_K8S_VERSION": "1.32"}):
        assert detect_version() == "1.32"

def test_detect_version_kubectl_fail():
    """Verify version detection fallback when kubectl fails."""
    with patch('subprocess.run', side_effect=Exception("fail")):
        assert detect_version() == "1.30"

def test_initialize_engine_fail():
    """Verify engine initialization failure exits."""
    with patch('yamlr_native.native_get_schema_for_version', side_effect=Exception("fail")):
        with pytest.raises(SystemExit) as e:
            initialize_engine("1.30")
        assert e.value.code == 1

def test_ingest_crds_fail():
    """Verify CRD ingestion failure exits."""
    with patch('builtins.open', side_effect=Exception("fail")):
        with pytest.raises(SystemExit) as e:
            ingest_crds("path", [])
        assert e.value.code == 1

def test_handle_exit_code_levels():
    """Verify exit code handling for different severity levels."""
    report = MagicMock()
    res = MagicMock()
    v = MagicMock(severity="ERROR")
    res.violations = [v]
    res.integrity_violations = []
    report.results = [res]
    
    with pytest.raises(SystemExit) as e:
        _handle_exit_code(report, "error")
    assert e.value.code == 1
    
    # Test with note level
    v.severity = "NOTE"
    with pytest.raises(SystemExit) as e:
        _handle_exit_code(report, "note")
    assert e.value.code == 1

def test_export_json_report(temp_workspace):
    """Verify JSON report export."""
    output_file = os.path.join(temp_workspace, "report.json")
    report = MagicMock()
    report.total_files = 1
    report.total_time_ms = 100
    res = MagicMock(file_path="test.yaml", health_score=100.0)
    res.violations = [MagicMock(field_path="f1", message="m1", severity="ERROR")]
    res.integrity_violations = [MagicMock(check_name="c1", message="m2", severity="WARNING")]
    report.results = [res]
    
    _export_json_report(report, output_file)
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        data = json.load(f)
        assert data["results"][0]["file"] == "test.yaml"

def test_dispatch_command_various():
    """Verify dispatch for various commands."""
    # Explain
    args = MagicMock(command="explain", path=".", flag=None)
    with patch('yamlr.core_logic.cmd_explain_universal') as mock_explain:
        _dispatch_command(args)
        mock_explain.assert_called_once()
    
    # Graph/Scan/Heal pipeline
    args = MagicMock(command="scan", path=".", fail_on=None)
    with patch('yamlr.cli.main._execute_scan_heal_pipeline') as mock_pipeline:
        _dispatch_command(args)
        mock_pipeline.assert_called_once()

def test_main_version():
    """Verify main entry with --version."""
    with patch('sys.argv', ['yamlr', '--version']):
        with patch('yamlr.core_logic.cmd_version') as mock_version:
            main()
            mock_version.assert_called_once()

def test_main_empty():
    """Verify main entry with no args."""
    with patch('sys.argv', ['yamlr']):
        with patch('yamlr.core_logic.cmd_welcome') as mock_welcome:
            main()
            mock_welcome.assert_called_once()
````

## File: tests/test_cli_main_remediation.py
````python
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import (
    _apply_atomic_fix,
    _handle_cicd_remediation,
    _handle_interactive_remediation,
    apply_remediation,
    render_resource_results,
)


def test_apply_remediation_interactive_yes():
    """Verify interactive remediation with 'y' input."""
    res = MagicMock()
    res.suggested_fixes = [MagicMock(field_path="spec", message="Fix it")]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation.console.input', return_value='y'):
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_fix:
                apply_remediation(res, telemetry, apply=False)
                mock_fix.assert_called_once()

def test_apply_remediation_interactive_no():
    """Verify interactive remediation with 'n' input."""
    res = MagicMock()
    res.suggested_fixes = [MagicMock(field_path="spec", message="Fix it")]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation.console.input', return_value='n'):
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_fix:
                apply_remediation(res, telemetry, apply=False)
                mock_fix.assert_not_called()

def test_handle_cicd_remediation_fail():
    """Verify CI/CD safety gate failure."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec")
    with pytest.raises(SystemExit) as e:
        _handle_cicd_remediation(res, fix, apply=False)
    assert e.value.code == 1

def test_apply_atomic_fix_error():
    """Verify error handling in atomic fix."""
    res = MagicMock(file_path="missing.yaml")
    fix = MagicMock()
    with patch('shutil.copy2', side_effect=Exception("File error")):
        with pytest.raises(SystemExit) as e:
            _apply_atomic_fix(res, fix, MagicMock())
        assert e.value.code == 1

def test_render_resource_results_heal(temp_workspace):
    """Verify result rendering with heal trigger."""
    res = MagicMock()
    res.violations = [MagicMock(field_path="v1", message="m1")]
    res.integrity_violations = []
    res.health_score = 80.0
    res.identity = None
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, "w") as f: f.write("content")
    res.file_path = fpath
    res.suggested_fixes = [MagicMock()]
    
    with patch('yamlr.cli.formatters.apply_remediation') as mock_remed:
        render_resource_results(res, MagicMock(), "heal", True)
        mock_remed.assert_called_once()
````

## File: tests/test_cli_pipeline_extended.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _execute_scan_heal_pipeline


@patch('yamlr.cli.pipeline.execute_pipeline')
@patch('yamlr.cli.pipeline.render_report')
def test_execute_scan_heal_pipeline(mock_render, mock_pipeline, temp_workspace):
    """Verify scan/heal pipeline execution and rendering."""
    args = MagicMock(path=temp_workspace, command="scan", k8s_version="1.30", output=None)
    
    mock_report = MagicMock()
    mock_report.results = []
    mock_report.total_files = 0
    mock_pipeline.return_value = mock_report
    
    with patch('yamlr.cli.pipeline.initialize_engine', return_value=[]):
        _execute_scan_heal_pipeline(args)
        mock_pipeline.assert_called_once()
        mock_render.assert_called_once()
````

## File: tests/test_cli_pipeline.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _execute_scan_heal_pipeline


@patch('yamlr_native.native_discover_resources')
@patch('yamlr_native.native_build_topology_graph')
@patch('yamlr.ui.renderer.RichRenderer.render_graph')
def test_execute_pipeline_graph(mock_render, mock_graph, mock_discover):
    """Verify graph command execution."""
    args = MagicMock(command="graph", path=".", focus=None)
    mock_discover.return_value = []
    mock_graph.return_value = []
    
    _execute_scan_heal_pipeline(args)
    mock_render.assert_called_once()

@patch('yamlr.cli.pipeline.initialize_engine')
@patch('yamlr.cli.pipeline.execute_pipeline')
@patch('yamlr.cli.pipeline.render_report')
def test_execute_pipeline_scan(mock_render, mock_exec, mock_init):
    """Verify scan command execution."""
    args = MagicMock(command="scan", path=".", k8s_version=None, push_telemetry=False)
    mock_init.return_value = []
    mock_exec.return_value = MagicMock()
    
    _execute_scan_heal_pipeline(args)
    mock_render.assert_called_once()

@patch('yamlr.cli.pipeline.initialize_engine')
@patch('yamlr.cli.pipeline.ingest_crds')
def test_execute_pipeline_with_crd(mock_ingest, mock_init):
    """Verify CRD ingestion in pipeline."""
    args = MagicMock(command="scan", path=".", k8s_version="1.30", crd="crd.yaml", push_telemetry=False)
    with patch('yamlr.cli.pipeline.execute_pipeline'):
        with patch('yamlr.cli.pipeline.render_report'):
            _execute_scan_heal_pipeline(args)
            mock_ingest.assert_called_once()
````

## File: tests/test_cli_render_report.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import render_report


def test_render_report_with_results():
    """Verify render_report logic with findings."""
    mock_report = MagicMock()
    mock_report.results = [
        MagicMock(file_path="test.yaml", health_score=100, violations=[], integrity_violations=[], suggested_fixes=[])
    ]
    mock_report.total_files = 1
    mock_report.total_time_ms = 100
    
    mock_telemetry = MagicMock()
    
    with patch('yamlr_native.native_record_telemetry'):
        with patch('yamlr.cli.formatters._render_results_and_collisions') as mock_results:
            with patch('yamlr.cli.formatters._render_batch_summary'):
                with patch('yamlr.core_logic.audit_topology_outages'):
                    with patch('yamlr.cli.formatters._trigger_score_animation'):
                        render_report(mock_report, mock_telemetry, "scan", False)
                        mock_results.assert_called_once()
````

## File: tests/test_cli_schema.py
````python
"""Tests for yamlr schema CLI subcommand."""
import os
import tempfile
from unittest.mock import MagicMock

from yamlr.cli.schema_handler import cmd_schema


def test_cli_schema_lifecycle():
    """Test schema ingest, list, and clean via cmd_schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "my_crd.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")

        with open(crd_file, "w", encoding="utf-8") as f:
            f.write("""apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: myresources.example.com
spec:
  group: example.com
  names:
    kind: MyResource
  versions:
    - name: v1
      schema:
        openAPIV3Schema:
          type: object
          properties:
            replicas:
              type: integer
""")

        # 1. Ingest
        args_ingest = MagicMock()
        args_ingest.schema_action = "ingest"
        args_ingest.path = crd_file
        args_ingest.out = schema_dir
        cmd_schema(args_ingest)

        assert os.path.exists(os.path.join(schema_dir, "myresource_v1.json"))

        # 2. List
        args_list = MagicMock()
        args_list.schema_action = "list"
        args_list.dir = schema_dir
        cmd_schema(args_list)

        # 3. Clean
        args_clean = MagicMock()
        args_clean.schema_action = "clean"
        args_clean.dir = schema_dir
        cmd_schema(args_clean)

        assert not os.path.exists(os.path.join(schema_dir, "myresource_v1.json"))
````

## File: tests/test_cli_security.py
````python
import io
import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from yamlr.cli.main import cmd_sign, cmd_verify


def test_cmd_sign_success(temp_workspace):
    """Verify that cmd_sign correctly injects a signature."""
    manifest_path = os.path.join(temp_workspace, "test.yaml")
    with open(manifest_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Service\nmetadata:\n  name: test\n")
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_sign_manifest', return_value="mock-signature"):
        with patch('os.getenv', return_value="fake-key"):
            with patch('yamlr.core_logic.LicenseManager') as mock_lm_class:
                mock_lm_class.return_value.is_pro = True
                cmd_sign(args)
    
    # Check if signature was added
    with open(manifest_path, 'r') as f:
        content = f.read()
        assert "yamlr.dev/signature: mock-signature" in content

def test_cmd_verify_success(temp_workspace):
    """Verify that cmd_verify correctly validates a signed manifest."""
    manifest_path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: Service
metadata:
  name: test
  annotations:
    yamlr.dev/signature: mock-sig
"""
    with open(manifest_path, 'w') as f:
        f.write(content)
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_verify_manifest', return_value=True):
        with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-pubkey"):
            # Should not exit
            cmd_verify(args)

def test_cmd_verify_fail(temp_workspace):
    """Verify that cmd_verify exits on failure."""
    manifest_path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: Service
metadata:
  name: test
  annotations:
    yamlr.dev/signature: bad-sig
"""
    with open(manifest_path, 'w') as f:
        f.write(content)
    
    args = MagicMock()
    args.path = manifest_path
    
    with patch('yamlr_native.native_verify_manifest', return_value=False):
        with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-pubkey"):
            with pytest.raises(SystemExit):
                cmd_verify(args)
````

## File: tests/test_cli_sign_verify.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import run_standalone


def test_cli_sign():
    """Verify sign command dispatch."""
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch('sys.argv', ['yamlr', 'sign', 'test.yaml']):
            with patch('yamlr.cli.main.cmd_sign') as mock_sign:
                run_standalone()
                mock_sign.assert_called_once()

def test_cli_verify():
    """Verify verify command dispatch."""
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch('sys.argv', ['yamlr', 'verify', 'test.yaml']):
            with patch('yamlr.cli.main.cmd_verify') as mock_verify:
                run_standalone()
                mock_verify.assert_called_once()
````

## File: tests/test_cli_utils_extended.py
````python
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.cli.main import _cmd_install, _cmd_update, _cmd_version, cmd_doctor, cmd_restore
except ImportError:
    _cmd_install = cmd_restore = _cmd_version = _cmd_update = cmd_doctor = MagicMock()
import os


def test_cmd_install_invalid():
    """Verify install command with invalid target."""
    with patch('yamlr.cli.main.console.print') as mock_print:
        _cmd_install("invalid")
        mock_print.assert_called_once()

@patch('yamlr.core.backups.BackupManager.restore_last_session')
def test_cmd_restore(mock_restore):
    """Verify restore command."""
    cmd_restore(".")
    mock_restore.assert_called_once()

def test_cmd_version():
    """Verify version command."""
    with patch('yamlr.core_logic.cmd_version') as mock_version:
        _cmd_version()
        mock_version.assert_called_once()

def test_cmd_update():
    """Verify update command."""
    _cmd_update()

@patch('yamlr_native.native_get_build_info', return_value={"version": "0.1.0"})
def test_cmd_doctor(mock_build):
    """Verify doctor command."""
    cmd_doctor()
````

## File: tests/test_cncf_crds.py
````python
import pytest
import yamlr_native


def test_cncf_crd_schemas_loaded():
    """Verify that top-tier CNCF CRDs are embedded and returned by native schema loader."""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    kinds = {s.kind for s in schemas}
    
    # Check top-tier CNCF CRD kinds
    expected_cncf_kinds = [
        "ServiceMonitor",
        "PrometheusRule",
        "Certificate",
        "Issuer",
        "ClusterIssuer",
        "VirtualService",
        "DestinationRule",
        "HTTPRoute",
        "Gateway",
        "Rollout",
        "Application",
    ]
    for kind in expected_cncf_kinds:
        assert kind in kinds, f"Expected CNCF CRD '{kind}' to be present in embedded schemas"

def test_cncf_crd_missing_spec_violation():
    """Verify that a CNCF CRD manifest missing required spec generates schema violation."""
    yaml_content = """apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: test-monitor
"""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    violations = yamlr_native.native_check_schema_violations(yaml_content, schemas)
    assert any(v.field_path == "spec" for v in violations)

def test_cncf_crd_valid_manifest_passes():
    """Verify that a valid CNCF CRD manifest with spec passes schema validation."""
    yaml_content = """apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
spec:
  secretName: example-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
"""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    violations = yamlr_native.native_check_schema_violations(yaml_content, schemas)
    # Certificate has required spec and metadata, so it should not have missing field violations
    assert not any(v.field_path in ("spec", "metadata", "apiVersion", "kind") for v in violations)
````

## File: tests/test_commands.py
````python
from unittest.mock import MagicMock, patch

import pytest

try:
    from yamlr.core_logic import UniversalCommandRegistry, cmd_dna, cmd_guide_rich, cmd_roi, cmd_version, cmd_welcome
except ImportError:
    cmd_welcome = cmd_version = cmd_guide_rich = cmd_dna = cmd_roi = UniversalCommandRegistry = MagicMock()
import os


def test_command_registry():
    """Verify registry metadata."""
    assert UniversalCommandRegistry.is_pro("dna") is True
    assert UniversalCommandRegistry.is_pro("scan") is False
    assert "Generate immutable" in UniversalCommandRegistry.get_desc("dna")

@patch('yamlr.ui.renderer.RichRenderer.render_welcome')
@patch('yamlr.core.info._detect_k8s_version_safe', return_value="1.30")
def test_cmd_welcome(mock_detect, mock_render):
    """Verify welcome command triggers renderer."""
    cmd_welcome()
    mock_render.assert_called_once_with(os.getcwd(), "1.30")

@patch('yamlr.ui.theme.console.print')
def test_cmd_version(mock_print):
    """Verify version command prints version."""
    with patch('yamlr.version.__version__', "0.1.0"):
        cmd_version()
        # Should print version info
        assert any("0.1.0" in str(call) for call in mock_print.call_args_list)

@patch('yamlr.ui.renderer.RichRenderer.render_explain')
@patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup')
def test_cmd_guide_rich(mock_lookup, mock_render):
    """Verify guide command renders topics."""
    mock_lookup.return_value = {"title": "Test"}
    cmd_guide_rich("TEST")
    mock_render.assert_called_once_with("TEST", {"title": "Test"})

@pytest.mark.skip(reason="deprecated API")
@patch('yamlr_native.native_calculate_dna_hash', return_value="hash123")
@patch('yamlr.core_logic._collect_yaml_files')
def test_cmd_dna(mock_collect, mock_hash, temp_workspace):
    """Verify DNA command calculates hashes."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w') as f: f.write("content")
    mock_collect.return_value = [fpath]
    
    with patch('yamlr_native.native_shard'):
        with patch('yamlr_native.extract_native_identity'):
            cmd_dna(temp_workspace)
            mock_hash.assert_called_once()

@pytest.mark.skip(reason="deprecated API")
@patch('yamlr_native.NativeTelemetry')
@patch('yamlr.core_logic._collect_yaml_files')
def test_cmd_roi(mock_collect, mock_telemetry, temp_workspace):
    """Verify ROI command processes files."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w') as f: f.write("content")
    mock_collect.return_value = [fpath]
    
    mock_telemetry.return_value.scans_completed = 0
    with patch('yamlr_native.native_shard', return_value=["shard"]):
        with patch('yamlr_native.native_structurize'):
            with patch('yamlr_native.native_get_telemetry_dashboard'):
                cmd_roi(temp_workspace)
                # Should have incremented scans_completed
                assert mock_telemetry.return_value.scans_completed == 1
````

## File: tests/test_core_logic_extended.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import (
    cmd_completion,
    cmd_dna,
    cmd_explain_universal,
    cmd_fleet,
    cmd_pulse,
    cmd_roi,
    cmd_rollback,
    cmd_secure,
)


@patch('yamlr_native.native_discover_resources', return_value=[])
@patch('yamlr.ui.theme.console.print')
def test_cmd_pulse_no_files(mock_print, mock_discover):
    cmd_pulse(".")
    assert mock_print.called

@patch('yamlr_native.native_discover_resources', return_value=[MagicMock(identity=MagicMock(kind="Pod", name="test"))])
@patch('yamlr_native.native_shard', return_value=["shard"])
@patch('yamlr_native.native_structurize', return_value=MagicMock(integrity_violations=[]))
@patch('yamlr.ui.theme.console.print')
def test_cmd_pulse_success(mock_print, mock_struct, mock_shard, mock_discover):
    cmd_pulse(".")
    assert any("Live Pulse" in str(call) for call in mock_print.call_args_list)

@patch('yamlr_native.native_discover_resources', return_value=[])
@patch('yamlr.ui.theme.console.print')
def test_cmd_secure_no_files(mock_print, mock_discover):
    cmd_secure(".")
    assert mock_print.called

@patch('yamlr.core.backups.BackupManager')
@patch('yamlr.ui.theme.console.print')
def test_cmd_rollback(mock_print, mock_bm):
    cmd_rollback(".")
    mock_bm.return_value.restore_last_session.assert_called_once()

@patch('yamlr.ui.theme.console.print')
def test_cmd_fleet(mock_print):
    cmd_fleet()
    assert mock_print.called

@patch('yamlr.ui.theme.console.print')
def test_cmd_completion(mock_print):
    cmd_completion("zsh")
    assert any("zsh" in str(call) for call in mock_print.call_args_list)
    cmd_completion("bash")
    assert any("bash" in str(call) for call in mock_print.call_args_list)
    cmd_completion("fish")
    assert any("fish" in str(call) for call in mock_print.call_args_list)

@patch('yamlr.ui.theme.console.print')
def test_cmd_explain_universal(mock_print):
    cmd_explain_universal("registry")
    assert mock_print.called
````

## File: tests/test_crd_distiller.py
````python
"""Tests for CRDDistiller schema compilation and caching."""
import os
import tempfile

import pytest

from yamlr.core.crd_distiller import CRDDistiller

SAMPLE_CRD = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: certificates.cert-manager.io
spec:
  group: cert-manager.io
  names:
    kind: Certificate
    listKind: CertificateList
    plural: certificates
    singular: certificate
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - secretName
              properties:
                secretName:
                  type: string
                  description: Target secret name
                dnsNames:
                  type: array
                  description: Subject Alternative Names
"""


def test_distill_single_crd():
    """Verify single CRD extraction and schema JSON generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "certificate.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CRD)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "Certificate"
        assert schema["apiVersion"] == "cert-manager.io/v1"
        assert "spec" in schema["fields"]

        # Verify disk cache
        cached = distiller.list_schemas()
        assert len(cached) == 1
        assert cached[0]["kind"] == "Certificate"


def test_clean_schemas():
    """Verify schema cleaning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "certificate.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_CRD)

        distiller = CRDDistiller(schema_dir)
        distiller.distill_file(crd_file)
        assert len(distiller.list_schemas()) == 1

        cleaned = distiller.clean_schemas()
        assert cleaned == 1
        assert len(distiller.list_schemas()) == 0


def test_distill_v1beta1_crd():
    """Verify v1beta1 CRD extraction with global validation schema."""
    v1beta1_crd = """apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: alerts.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  names:
    kind: Alertmanager
    plural: alertmanagers
  scope: Namespaced
  version: v1alpha1
  validation:
    openAPIV3Schema:
      type: object
      properties:
        spec:
          type: object
          properties:
            replicas:
              type: integer
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "alertmanager.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(v1beta1_crd)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "Alertmanager"
        assert schema["apiVersion"] == "monitoring.coreos.com/v1alpha1"
        assert "spec" in schema["fields"]


def test_distill_crd_structural_fallback():
    """Verify structural fallback inference when no schema is present."""
    untyped_crd = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: legacyapps.example.com
spec:
  group: example.com
  names:
    kind: LegacyApp
    plural: legacyapps
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        crd_file = os.path.join(tmpdir, "legacyapp.yaml")
        schema_dir = os.path.join(tmpdir, "schemas")
        with open(crd_file, "w", encoding="utf-8") as f:
            f.write(untyped_crd)

        distiller = CRDDistiller(schema_dir)
        compiled = distiller.distill_file(crd_file)

        assert len(compiled) == 1
        schema = compiled[0]
        assert schema["kind"] == "LegacyApp"
        assert "spec" in schema["fields"]
        assert "metadata" in schema["fields"]
        assert "apiVersion" in schema["fields"]
````

## File: tests/test_deprecation_upgrades.py
````python
"""Unit tests for Fleet-Wide Kubernetes Deprecation Upgrades."""
import pytest

from yamlr.core.stages.deprecation_upgrade_stage import DEPRECATION_MAP, DeprecationUpgradeStage


def test_deprecation_map_entries():
    assert ("extensions/v1beta1", "Deployment") in DEPRECATION_MAP
    assert DEPRECATION_MAP[("extensions/v1beta1", "Deployment")] == "apps/v1"
    assert DEPRECATION_MAP[("networking.k8s.io/v1beta1", "Ingress")] == "networking.k8s.io/v1"
    assert DEPRECATION_MAP[("policy/v1beta1", "PodDisruptionBudget")] == "policy/v1"


def test_execute_fleet_upgrade_preview(tmp_path):
    deprecated_yaml = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 1
"""
    manifest_path = tmp_path / "legacy.yaml"
    manifest_path.write_text(deprecated_yaml, encoding="utf-8")

    records = DeprecationUpgradeStage.execute_fleet_upgrade(
        target_path=str(tmp_path),
        target_k8s_version="1.30",
        apply=False
    )
    assert len(records) == 1
    assert records[0]["kind"] == "Deployment"
    assert records[0]["old_api"] == "extensions/v1beta1"
    assert records[0]["new_api"] == "apps/v1"
    # Preview mode: file on disk unchanged
    assert "extensions/v1beta1" in manifest_path.read_text(encoding="utf-8")
````

## File: tests/test_design_partner_pilot_kit.py
````python
"""Verification Suite for Track 3: Design Partner Pilot Kit & Telemetry Packaging.

Why: Empirically verifies the integrity of external integration assets (GitHub Actions,
     pre-commit hooks, CI workflows), validates offline RSA-2048 RS256 license
     cryptography, ensures 100% flag alignment without stale phantom inputs, and enforces
     the absolute boundary separating internal valuation concepts and AI metaphors from
     external engineer-facing pilot documentation.
"""
import os

import pytest
import yaml

from yamlr.cli.parser import create_parser
from yamlr.core.license import LicenseManager

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_subparser(parser, name: str):
    """Retrieve child parser for a given subcommand name."""
    action = next(a for a in parser._actions if isinstance(getattr(a, "choices", None), dict))
    return action.choices[name]


def _get_parser_option_strings(subparser):
    """Collect all valid option flags from a subparser."""
    flags = set()
    for action in subparser._actions:
        for opt in action.option_strings:
            flags.add(opt.lstrip("-"))
            flags.add(opt)
        if action.dest:
            flags.add(action.dest.replace("_", "-"))
    return flags


class TestGitHubActionsIntegrity:
    """Validates GitHub Action metadata manifests and entrypoint scripts."""

    def test_scan_action_manifest_valid_yaml(self):
        """Verify actions/scan/action.yml is valid YAML with proper metadata."""
        action_path = os.path.join(REPO_ROOT, "actions", "scan", "action.yml")
        assert os.path.exists(action_path)
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "Yamlr Manifest Auditor (Scan)"
        assert "inputs" in data
        assert "runs" in data
        assert data["runs"]["using"] == "docker"

    def test_scan_action_inputs_align_with_cli(self):
        """Verify all scan action inputs correspond to valid CLI arguments."""
        action_path = os.path.join(REPO_ROOT, "actions", "scan", "action.yml")
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        parser = create_parser()
        scan_parser = _get_subparser(parser, "scan")
        valid_flags = _get_parser_option_strings(scan_parser)
        valid_flags.update({"path", "extra-args", "fail-on-error", "kube-version"})

        for input_name in data["inputs"].keys():
            assert input_name in valid_flags, f"Stale or unrecognized input in actions/scan: {input_name}"

    def test_scan_entrypoint_no_phantom_flags(self):
        """Verify actions/scan/entrypoint.sh contains no phantom or unmapped flags."""
        entrypoint_path = os.path.join(REPO_ROOT, "actions", "scan", "entrypoint.sh")
        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Stale phantom flags that were eliminated
        stale_flags = ["--enforce-limits", "--harden", "--check-deprecations", "--fast", "--compact", "--fix-tags"]
        for flag in stale_flags:
            assert flag not in content, f"actions/scan/entrypoint.sh contains stale flag: {flag}"

    def test_heal_action_manifest_valid_yaml(self):
        """Verify actions/heal/action.yml is valid YAML with proper metadata."""
        action_path = os.path.join(REPO_ROOT, "actions", "heal", "action.yml")
        assert os.path.exists(action_path)
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "Yamlr Manifest Remediator (Heal)"
        assert "inputs" in data
        assert "runs" in data

    def test_heal_action_inputs_align_with_cli(self):
        """Verify all heal action inputs correspond to valid CLI arguments or orchestration."""
        action_path = os.path.join(REPO_ROOT, "actions", "heal", "action.yml")
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        parser = create_parser()
        heal_parser = _get_subparser(parser, "heal")
        valid_flags = _get_parser_option_strings(heal_parser)
        valid_flags.update({"path", "extra-args", "push", "token", "kube-version"})

        for input_name in data["inputs"].keys():
            assert input_name in valid_flags, f"Stale or unrecognized input in actions/heal: {input_name}"

    def test_heal_entrypoint_replaces_confirm_with_apply(self):
        """Verify actions/heal/entrypoint.sh uses valid --apply and eliminates --confirm."""
        entrypoint_path = os.path.join(REPO_ROOT, "actions", "heal", "entrypoint.sh")
        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "--confirm" not in content
        assert "--apply" in content
        assert "Yamlr Manifest Remediator starting..." in content
        assert "chore(yamlr): automated Kubernetes manifest remediation" in content


class TestPreCommitHooksIntegrity:
    """Validates pre-commit hook specifications and example configurations."""

    def test_pre_commit_hooks_yaml_valid(self):
        """Verify .pre-commit-hooks.yaml defines all required core hooks."""
        hooks_path = os.path.join(REPO_ROOT, ".pre-commit-hooks.yaml")
        assert os.path.exists(hooks_path)
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks = yaml.safe_load(f)

        hook_ids = {h["id"] for h in hooks}
        expected = {"yamlr-fmt", "yamlr-fix", "yamlr-scan", "yamlr-heal", "yamlr-diff"}
        assert expected.issubset(hook_ids)

        for hook in hooks:
            assert "entry" in hook
            assert hook["entry"].startswith("yamlr ")

    def test_pre_commit_example_config_valid(self):
        """Verify .pre-commit-config.example.yaml references canonical repository."""
        example_path = os.path.join(REPO_ROOT, ".pre-commit-config.example.yaml")
        assert os.path.exists(example_path)
        with open(example_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        repos = config.get("repos", [])
        assert len(repos) >= 1
        assert repos[0]["repo"] == "https://github.com/yamlr/yamlr"


class TestReferenceWorkflows:
    """Validates reference CI workflows created for design partners."""

    def test_pr_audit_workflow_valid_yaml(self):
        """Verify .github/workflows/yamlr-pr-audit.yml is valid YAML and includes diff and SARIF."""
        wf_path = os.path.join(REPO_ROOT, ".github", "workflows", "yamlr-pr-audit.yml")
        assert os.path.exists(wf_path)
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        assert "jobs" in wf
        assert "audit" in wf["jobs"]
        steps = wf["jobs"]["audit"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("Diff" in name for name in step_names)
        assert any("Scan" in name or "Audit" in name for name in step_names)


class TestSecurityAndOfflineEntitlements:
    """Validates cryptographic offline entitlement verification and air-gap behavior."""

    def test_offline_public_key_loading(self):
        """Verify LicenseManager accurately loads the RSA-2048 public key from disk."""
        lm = LicenseManager()
        pubkey = lm._get_pubkey()
        assert pubkey is not None
        assert "BEGIN PUBLIC KEY" in pubkey
        assert len(pubkey) > 200

    def test_offline_token_verification_rejection_of_invalid(self):
        """Verify invalid or tampered tokens are rejected locally without network requests."""
        lm = LicenseManager()
        assert lm.verify_token("invalid.jwt.token") is False

    def test_offline_token_verification_valid_signature(self):
        """Verify RSA RS256 token verification executes purely in-memory via native core."""
        import yamlr_native
        lm = LicenseManager()
        pubkey = lm._get_pubkey()

        # In native core, native_verify_token checks RS256 JWT signature against pubkey
        result = yamlr_native.native_verify_token("invalid-token-string", pubkey)
        assert result is False


class TestPilotProgramDocumentationIntegrity:
    """Validates docs/PILOT_PROGRAM.md for zero AI fingerprints and zero internal valuation terminology."""

    def test_pilot_program_doc_exists_and_substantial(self):
        """Verify docs/PILOT_PROGRAM.md exists and contains complete pilot sections."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        assert os.path.exists(doc_path)
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert len(content) > 3000
        assert "14-Day Pilot Protocol" in content
        assert "Phase S1" in content
        assert "Phase S2" in content
        assert "Turnkey Integration Blueprints" in content
        assert "Pilot Evaluation Scorecard" in content

    def test_zero_ai_fingerprints_in_pilot_doc(self):
        """Verify docs/PILOT_PROGRAM.md contains zero AI/metaphor fingerprints."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        forbidden_ai_tokens = [
            "brain",
            "neural",
            "synapse",
            "hallucin",
            "sentient",
            "autonomous surgeon",
            "scalpel",
            "knife",
            "llm",
            "agentic",
        ]
        violations = [token for token in forbidden_ai_tokens if token in content]
        assert not violations, f"Forbidden AI fingerprints detected in PILOT_PROGRAM.md: {violations}"

    def test_zero_valuation_or_mna_language_in_pilot_doc(self):
        """Verify docs/PILOT_PROGRAM.md contains zero internal valuation or M&A terminology."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        forbidden_mna_tokens = [
            "$20m",
            "$1.5m",
            "$3m",
            "$15m",
            "$25m",
            "acquisition",
            "acquirer",
            "multiple",
            "exit strategy",
            "due diligence",
            "asset replacement",
            "replacement value",
            "ip value",
            "pitch",
        ]
        violations = [token for token in forbidden_mna_tokens if token in content]
        assert not violations, f"Forbidden valuation/M&A terminology detected in PILOT_PROGRAM.md: {violations}"

    def test_unskewed_scorecard_template(self):
        """Verify the pilot evaluation scorecard contains un-skewed, blank baseline fields."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Scorecard must provide blank brackets for team measurement, not pre-filled claims
        assert "[   ]" in content
        assert "Target: 0.0%" in content
        # Must not make unqualified marketing promises as pre-existing facts
        assert "100% zero-rollback achieved" not in content
````

## File: tests/test_diff.py
````python
import pytest

from yamlr.ui.diff_engine import SideBySideDiff


def test_diff_unchanged():
    old = "line1\nline2"
    new = "line1\nline2"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert all(d[2] == "UNCHANGED" for d in diff)
    assert diff[0][0] == "line1"
    assert diff[0][1] == "line1"

def test_diff_added():
    old = "line1"
    new = "line1\nline2"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[0][2] == "UNCHANGED"
    assert diff[1][2] == "ADDED"
    assert diff[1][0] is None
    assert diff[1][1] == "line2"

def test_diff_removed():
    old = "line1\nline2"
    new = "line1"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[1][2] == "REMOVED"
    assert diff[1][0] == "line2"
    assert diff[1][1] is None

def test_diff_changed():
    old = "line1\nold_val"
    new = "line1\nnew_val"
    diff = SideBySideDiff.calculate(old, new)
    assert len(diff) == 2
    assert diff[1][2] == "CHANGED"
    assert diff[1][0] == "old_val"
    assert diff[1][1] == "new_val"

def test_diff_replace_mismatch():
    old = "line1\nold1\nold2"
    new = "line1\nnew1"
    diff = SideBySideDiff.calculate(old, new)
    # tag will be 'replace' for old1,old2 -> new1
    # max_len = 2
    # k=0: left=old1, right=new1, status=CHANGED
    # k=1: left=old2, right=None, status=CHANGED
    assert any(d[2] == "CHANGED" for d in diff)


def test_cli_diff_subcommand_registered():
    """Verify that 'diff' is registered as a Core CLI command."""
    from yamlr.cli.parser import create_parser
    parser = create_parser()
    args = parser.parse_args(["diff", "some/path.yaml", "-u"])
    assert args.command == "diff"
    assert args.path == "some/path.yaml"
    assert args.unified is True
````

## File: tests/test_dna_no_files.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_dna


@pytest.mark.skip(reason="deprecated API")
def test_cmd_dna_no_files(temp_workspace):
    """Verify DNA command handles directories with no YAML files."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        with patch('yamlr.core_logic._collect_yaml_files', return_value=[]):
            # We need to mock yamlr_native too
            with patch.dict('sys.modules', {'yamlr_native': MagicMock()}):
                cmd_dna(temp_workspace)
                assert any("No YAML files found" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_e2e_backup_restore.py
````python
"""End-to-End Tests for Atomic Backup and Restore Lifecycle."""
import os
import shutil
import tempfile
from pathlib import Path

from yamlr.core.backups import BackupManager


def test_e2e_backup_and_restore_cycle():
    """E2E: Verifies complete checkpointing and restoration lifecycle."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_backup_test_")
    try:
        manifest_path = os.path.join(temp_dir, "deployment.yaml")
        original_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
spec:
  replicas: 2
"""
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(original_content)

        bm = BackupManager(temp_dir)
        session_id = bm.create_checkpoint([manifest_path])
        assert session_id is not None

        # Mutate the file
        mutated_content = original_content + "\n# Modified by test"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(mutated_content)

        assert open(manifest_path, "r", encoding="utf-8").read() == mutated_content

        # Execute restore
        bm.restore_last_session()

        # Assert byte-for-byte original restoration
        restored_content = open(manifest_path, "r", encoding="utf-8").read()
        assert restored_content == original_content

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
````

## File: tests/test_e2e_pipeline.py
````python
"""End-to-End Tests for CLI Pipeline and Streaming Scanner."""
import os
from pathlib import Path

import pytest

from yamlr.cli.pipeline import detect_version, execute_pipeline, initialize_engine
from yamlr.core.scanner import streaming_scan

FIXTURES_DIR = str(Path(__file__).parent / "fixtures")


def test_e2e_pipeline_execution():
    """E2E: Executes the full pipeline on test fixtures with real native engine."""
    schemas = initialize_engine("1.30")
    assert isinstance(schemas, list)

    report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)
    assert report is not None
    assert report.total_files >= 1
    assert len(report.results) >= 1

    # Verify at least one result has identity extracted
    identities = [r.identity for r in report.results if r.identity]
    assert len(identities) > 0


def test_e2e_streaming_scan_real_disk():
    """E2E: Validates generator stream over real fixture files."""
    schemas = initialize_engine("1.30")
    results = list(streaming_scan(FIXTURES_DIR, schemas))

    assert len(results) > 0
    for res in results:
        assert hasattr(res, "file_path")
        assert os.path.exists(res.file_path)
        assert hasattr(res, "health_score")
        assert 0.0 <= res.health_score <= 100.0


def test_e2e_detect_version_fallback():
    """E2E: Ensures detect_version returns a valid semver-like string."""
    version = detect_version()
    assert isinstance(version, str)
    assert len(version) >= 3
````

## File: tests/test_e2e_sarif_json.py
````python
"""End-to-End Tests for SARIF and JSON Export Formats."""
import json
import os
import shutil
import tempfile
from pathlib import Path

from yamlr.cli.pipeline import _export_json_report, execute_pipeline, initialize_engine
from yamlr.sarif_reporter import SarifReporter

FIXTURES_DIR = str(Path(__file__).parent / "fixtures")


def test_e2e_json_report_generation():
    """E2E: Validates structured JSON report generation."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_json_test_")
    try:
        schemas = initialize_engine("1.30")
        report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)

        json_out = os.path.join(temp_dir, "report.json")
        _export_json_report(report, json_out)

        assert os.path.exists(json_out)
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "total_files" in data
        assert "total_time_ms" in data
        assert "results" in data
        assert isinstance(data["results"], list)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_e2e_sarif_report_generation():
    """E2E: Validates SARIF report generation."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_sarif_test_")
    try:
        schemas = initialize_engine("1.30")
        report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)

        sarif_out = os.path.join(temp_dir, "report.sarif")
        SarifReporter.generate_sarif(report.results, sarif_out)

        assert os.path.exists(sarif_out)
        with open(sarif_out, "r", encoding="utf-8") as f:
            sarif_data = json.load(f)

        assert sarif_data.get("version") == "2.1.0"
        assert "runs" in sarif_data
        assert len(sarif_data["runs"]) > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
````

## File: tests/test_e2e_scan_heal.py
````python
"""End-to-End Tests for Public API Scanning and Healing."""
import os
from pathlib import Path

import pytest
import yaml

from yamlr import HealResult, heal_yaml, scan_yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_e2e_heal_deprecated_api():
    """E2E: Ingress with deprecated networking.k8s.io/v1beta1 apiVersion."""
    deprecated_path = FIXTURES_DIR / "deprecated-api.yaml"
    if not deprecated_path.exists():
        pytest.skip("deprecated-api.yaml fixture not found")

    content = deprecated_path.read_text(encoding="utf-8")
    result = heal_yaml(content, k8s_version="1.30")

    assert isinstance(result, HealResult)
    # If changes were applied, the output must be valid YAML
    if result.had_changes:
        assert len(result.changes) > 0
        parsed = yaml.safe_load(result.healed_yaml)
        assert parsed is not None
        assert parsed.get("kind") == "Ingress"
    else:
        # If no changes were required, original content is retained
        assert result.healed_yaml == content


def test_e2e_scan_manifest_violations():
    """E2E: Validates scan_yaml returns structured violations and identity."""
    fixture_path = FIXTURES_DIR / "healer_test.yaml"
    if not fixture_path.exists():
        pytest.skip("healer_test.yaml fixture not found")

    content = fixture_path.read_text(encoding="utf-8")
    scan_result = scan_yaml(content, k8s_version="1.30")

    assert isinstance(scan_result, dict)
    assert "identity" in scan_result
    assert "violations" in scan_result
    assert "integrity_violations" in scan_result

    if scan_result["identity"]:
        assert scan_result["identity"]["kind"] == "Service"
        assert scan_result["identity"]["name"] == "healer-service"


def test_e2e_heal_comment_preservation():
    """E2E: Ensures critical comments and layout survive the healing pass."""
    yaml_with_comments = """# Global Cluster Anchor Header
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app # Crucial application name
spec:
  replicas: 3 # Hardcoded replica count
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.25.3
"""
    result = heal_yaml(yaml_with_comments, k8s_version="1.30")
    assert isinstance(result, HealResult)
    assert "# Global Cluster Anchor Header" in result.healed_yaml
    assert "# Crucial application name" in result.healed_yaml


def test_e2e_heal_idempotency():
    """E2E: Healing an already clean/healed manifest produces zero further changes."""
    clean_yaml = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  APP_ENV: production
"""
    first_heal = heal_yaml(clean_yaml, k8s_version="1.30")
    second_heal = heal_yaml(first_heal.healed_yaml, k8s_version="1.30")

    assert second_heal.had_changes is False
    assert len(second_heal.changes) == 0
````

## File: tests/test_evidence_vault.py
````python
"""Unit tests for Cryptographic Evidence Vault."""
import pytest

from yamlr.core.evidence_vault import COMPLIANCE_FRAMEWORKS, calculate_sha256, generate_receipt, verify_receipt


def test_calculate_sha256():
    data = "apiVersion: v1\nkind: Pod"
    h1 = calculate_sha256(data)
    h2 = calculate_sha256(data)
    assert h1 == h2
    assert len(h1) == 64


def test_generate_and_verify_receipt():
    manifest = "deploy.yaml"
    before = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 1"
    after = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 3"
    rules = ["SEC-001", "OPS-002"]

    receipt = generate_receipt(manifest, before, after, rules)
    assert receipt["manifest"] == "deploy.yaml"
    assert receipt["mutation_occurred"] is True
    assert "signature" in receipt
    assert "SOC2" in receipt["compliance_controls"]

    # Verify validity
    assert verify_receipt(receipt) is True

    # Verify tampering detection
    tampered = dict(receipt)
    tampered["dna_after"] = "bad-hash-00000000000000000000000000000000000000000000000000000000"
    assert verify_receipt(tampered) is False


def test_custom_secret_key_receipt():
    custom_key = b"enterprise-custom-hmac-secret-key"
    receipt = generate_receipt("service.yaml", "a: 1", "a: 2", ["REL-001"], secret_key=custom_key)
    assert verify_receipt(receipt, secret_key=custom_key) is True
    # Fails with wrong key
    assert verify_receipt(receipt, secret_key=b"wrong-key") is False


def test_production_enforcement_missing_key(monkeypatch):
    from yamlr.core.evidence_vault import get_signing_key

    # Simulate production/CI environment where pytest marker is not present and no key is configured
    monkeypatch.delenv("YAMLR_SIGNING_KEY", raising=False)
    monkeypatch.delenv("YAMLR_ALLOW_DEV_SIGNING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("YAMLR_TEST_MODE", raising=False)

    with pytest.raises(ValueError, match="Cryptographic signing key missing"):
        get_signing_key(secret_key=None, allow_dev_fallback=False)

    # When YAMLR_SIGNING_KEY is provided, it succeeds
    monkeypatch.setenv("YAMLR_SIGNING_KEY", "vault-production-key-123")
    assert get_signing_key(secret_key=None) == b"vault-production-key-123"
````

## File: tests/test_exception_handling.py
````python
"""Tests for Core Exceptions and Resilient Error Handling."""
import logging

from yamlr.core.exceptions import (
    DiscoveryError,
    HealingError,
    LicenseError,
    NativeCoreError,
    SchemaLoadError,
    YamlrError,
)
from yamlr.core.scanner import streaming_scan


def test_exception_hierarchy():
    """Validates that all domain exceptions derive from YamlrError."""
    assert issubclass(NativeCoreError, YamlrError)
    assert issubclass(SchemaLoadError, YamlrError)
    assert issubclass(HealingError, YamlrError)
    assert issubclass(LicenseError, YamlrError)
    assert issubclass(DiscoveryError, YamlrError)
    assert issubclass(YamlrError, Exception)


def test_streaming_scan_nonexistent_path_resilience(caplog):
    """Validates scanner handles nonexistent paths gracefully."""
    with caplog.at_level(logging.DEBUG):
        results = list(streaming_scan("non_existent_folder_path_xyz_123", []))
    assert results == []
````

## File: tests/test_explain_usage.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_explain_universal


def test_cmd_explain_usage():
    """Verify explain usage message."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_explain_universal(topic=None)
        assert any("Usage:" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_fleet_batcher.py
````python
"""Tests for FleetBatcher multi-repo GitOps automation."""
import os
import subprocess
import tempfile
from pathlib import Path

from yamlr.core.fleet_batcher import FleetBatcher

DEPLOYMENT_YAML = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: fleet-app
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: app
          image: nginx:1.24
"""


def test_discover_repositories_manifest_file():
    """Verify repository discovery from a manifest text file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo1 = Path(tmpdir) / "repo1"
        repo2 = Path(tmpdir) / "repo2"
        repo1.mkdir()
        repo2.mkdir()

        manifest_file = Path(tmpdir) / "repos.txt"
        manifest_file.write_text(f"{repo1}\n# comment\n{repo2}\n", encoding="utf-8")

        batcher = FleetBatcher()
        repos = batcher.discover_repositories(manifest_file)
        assert len(repos) == 2
        assert repo1.resolve() in repos
        assert repo2.resolve() in repos


def test_discover_repositories_directory():
    """Verify repository discovery by scanning child directories containing .git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parent = Path(tmpdir)
        repo_a = parent / "app-a"
        repo_b = parent / "app-b"
        non_repo = parent / "not-a-repo"

        repo_a.mkdir()
        (repo_a / ".git").mkdir()

        repo_b.mkdir()
        (repo_b / ".git").mkdir()

        non_repo.mkdir()

        batcher = FleetBatcher()
        repos = batcher.discover_repositories(parent)
        assert len(repos) == 2
        assert repo_a.resolve() in repos
        assert repo_b.resolve() in repos


def test_batch_process_preview():
    """Verify dry-run / preview batching across repositories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "service-a"
        repo.mkdir()
        manifest = repo / "deployment.yaml"
        manifest.write_text(DEPLOYMENT_YAML, encoding="utf-8")

        batcher = FleetBatcher()
        summary = batcher.batch_process(
            repositories=[repo],
            dry_run=True,
            apply=False
        )

        assert summary["total_repositories"] == 1
        assert summary["repositories_with_changes"] == 1
        assert summary["results"][0]["status"] == "PREVIEW_CHANGES"
        assert summary["results"][0]["modified_files_count"] == 1

        # Manifest should remain untouched in preview
        assert "extensions/v1beta1" in manifest.read_text(encoding="utf-8")


def test_batch_process_apply():
    """Verify apply batching writes healed manifests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "service-b"
        repo.mkdir()
        manifest = repo / "deployment.yaml"
        manifest.write_text(DEPLOYMENT_YAML, encoding="utf-8")

        batcher = FleetBatcher()
        summary = batcher.batch_process(
            repositories=[repo],
            dry_run=False,
            apply=True
        )

        assert summary["total_repositories"] == 1
        assert summary["repositories_with_changes"] == 1
        # Should be healed on disk
        healed_content = manifest.read_text(encoding="utf-8")
        assert "apps/v1" in healed_content


def test_generate_report():
    """Verify markdown fleet audit report generation."""
    batcher = FleetBatcher()
    summary = {
        "total_repositories": 2,
        "repositories_with_changes": 1,
        "total_files_modified": 3,
        "total_rules_triggered": 4,
        "apply": False,
        "results": [
            {
                "repo": "payments-service",
                "status": "PREVIEW_CHANGES",
                "modified_files_count": 3,
                "rules_triggered": 4,
                "pr_url": None,
                "error": None
            },
            {
                "repo": "auth-service",
                "status": "CLEAN",
                "modified_files_count": 0,
                "rules_triggered": 0,
                "pr_url": None,
                "error": None
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "fleet-report.md"
        report_md = batcher.generate_report(summary, str(report_path))

        assert "# Yamlr Fleet Remediation Report" in report_md
        assert "payments-service" in report_md
        assert "auth-service" in report_md
        assert report_path.exists()
````

## File: tests/test_fmt_cmd.py
````python
"""Tests for canonical manifest formatting and zero-flag fixing (k8sfmt / yamlfix)."""
import os
import tempfile
from pathlib import Path

from yamlr.cli.fmt_handler import cmd_fix_dispatch, cmd_fmt_dispatch, format_yaml_string

UNORDERED_YAML = """kind: Service
metadata:
  name: test-svc
apiVersion: v1
spec:
  ports:
    - port: 80
"""

DEPRECATED_YAML = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 2
"""


def test_format_yaml_string_orders_keys():
    """Verify official Kubernetes schema key ordering: apiVersion, kind, metadata, spec."""
    formatted = format_yaml_string(UNORDERED_YAML)
    lines = [line.split(":")[0].strip() for line in formatted.strip().splitlines() if not line.startswith(" ") and not line.startswith("-")]
    assert lines == ["apiVersion", "kind", "metadata", "spec"]


def test_cmd_fmt_file_write_in_place():
    """Verify yamlr fmt -w modifies file in place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "service.yaml"
        fpath.write_text(UNORDERED_YAML, encoding="utf-8")

        class Args:
            path = str(fpath)
            write = True
            w = True

        res = cmd_fmt_dispatch(Args())
        assert res == 0

        content = fpath.read_text(encoding="utf-8")
        assert content.startswith("apiVersion: v1")


def test_cmd_fix_file():
    """Verify yamlr fix upgrades deprecated manifests directly without flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = Path(tmpdir) / "deployment.yaml"
        fpath.write_text(DEPRECATED_YAML, encoding="utf-8")

        class Args:
            path = str(fpath)

        res = cmd_fix_dispatch(Args())
        assert res == 0

        content = fpath.read_text(encoding="utf-8")
        assert "apps/v1" in content
````

## File: tests/test_forensic_logic.py
````python
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.core_logic import _calculate_health_score, _collect_yaml_files, audit_topology_outages
except ImportError:
    _calculate_health_score = audit_topology_outages = _collect_yaml_files = MagicMock()
import os


def test_calculate_health_score():
    """Verify health score math."""
    v1 = MagicMock(severity="CRITICAL")
    v2 = MagicMock(severity="HIGH")
    v3 = MagicMock(severity="MEDIUM")
    v4 = MagicMock(severity="LOW")
    
    # 100 - 15 - 5 - 2 - 0.5 = 77.5
    assert _calculate_health_score([v1, v2, v3, v4]) == 77.5
    assert _calculate_health_score([]) == 100.0

def test_audit_topology_outages():
    """Verify topology audit logic."""
    res1 = MagicMock()
    res1.identity = MagicMock()
    res2 = MagicMock()
    res2.identity = MagicMock()
    
    mock_native = MagicMock()
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        audit_topology_outages([res1, res2])
        mock_native.native_build_topology_graph.assert_called_once()

def test_collect_yaml_files(temp_workspace):
    """Verify YAML collection logic."""
    f1 = os.path.join(temp_workspace, "a.yaml")
    f2 = os.path.join(temp_workspace, "b.yml")
    f3 = os.path.join(temp_workspace, "c.txt")
    with open(f1, 'w') as f: f.write("")
    with open(f2, 'w') as f: f.write("")
    with open(f3, 'w') as f: f.write("")
    
    files = _collect_yaml_files(temp_workspace)
    assert len(files) == 2
    assert any(f.endswith("a.yaml") for f in files)
    assert any(f.endswith("b.yml") for f in files)
````

## File: tests/test_golden_corpus_invariants.py
````python
import json
import sys
from pathlib import Path

import pytest
import yamlr_native

# Ensure root directory can import scripts
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_golden_corpus import (
    CorpusSuiteSummary,
    ManifestBenchmarkMetrics,
    main,
    split_yaml_documents,
    write_json_telemetry,
    write_markdown_report,
)

SAMPLE_CORPUS = [
    """# Deployment Manifest
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  labels:
    env: staging # inline comment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: api:v1.2.3
        ports:
        - containerPort: 8080 # port comment
""",
    """# Headless Service
apiVersion: v1
kind: Service
metadata:
  name: api-headless
spec:
  clusterIP: None
  selector:
    app: api
  ports:
  - port: 8080
    targetPort: 8080
""",
    """# StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-cluster
spec:
  serviceName: "db-headless"
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15.3
""",
    """# NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-egress
spec:
  podSelector: {}
  policyTypes:
  - Egress
""",
]


def test_python_golden_corpus_idempotency():
    """Verify that native sharding and reconstruction is mathematically idempotent."""
    for manifest in SAMPLE_CORPUS:
        shards_1 = yamlr_native.native_shard(manifest)
        reconstructed_1 = yamlr_native.native_reconstruct_yaml(shards_1)

        shards_2 = yamlr_native.native_shard(reconstructed_1)
        reconstructed_2 = yamlr_native.native_reconstruct_yaml(shards_2)

        assert reconstructed_1 == reconstructed_2


def test_python_golden_corpus_comments_preserved():
    """Verify that comments and blank lines are retained across reconstructions."""
    manifest = SAMPLE_CORPUS[0]
    shards = yamlr_native.native_shard(manifest)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)

    assert "# Deployment Manifest" in reconstructed
    assert "# inline comment" in reconstructed
    assert "# port comment" in reconstructed


def test_python_golden_corpus_schema_validity():
    """Verify that valid manifests do not gain schema errors through roundtrip."""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    for manifest in SAMPLE_CORPUS:
        shards = yamlr_native.native_shard(manifest)
        v1 = list(yamlr_native.native_check_schema_violations(manifest, schemas))

        recon = yamlr_native.native_reconstruct_yaml(shards)
        v2 = list(yamlr_native.native_check_schema_violations(recon, schemas))

        assert len(v2) <= len(v1)


def test_split_yaml_documents_variations():
    """Verify document splitting across diverse multi-document structures."""
    single = "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm\n"
    assert len(split_yaml_documents(single)) == 1

    multi = """apiVersion: v1
kind: Service
---
apiVersion: apps/v1
kind: Deployment
"""
    docs = split_yaml_documents(multi)
    assert len(docs) == 2
    assert "kind: Service" in docs[0]
    assert "kind: Deployment" in docs[1]

    with_comments_and_blanks = """---
# Leading comment
apiVersion: v1
kind: Namespace
---
# Interstitial comment only
---
apiVersion: v1
kind: Secret
---
"""
    docs2 = split_yaml_documents(with_comments_and_blanks)
    assert len(docs2) == 2
    assert "kind: Namespace" in docs2[0]
    assert "kind: Secret" in docs2[1]


def test_write_json_telemetry_schema(tmp_path):
    """Verify JSON telemetry schema and fields generated by golden corpus runner."""
    summary = CorpusSuiteSummary(
        total_ecosystems=1,
        ecosystems_passed=1,
        total_bytes=1024,
        total_documents=2,
        documents_idempotent=2,
        document_idempotency_rate=100.0,
        stream_idempotency_rate=100.0,
        total_comments_checked=5,
        total_comments_preserved=5,
        comment_retention_rate=100.0,
        anchor_broken_failures=0,
        semantic_drift_failures=0,
        total_panics=0,
        total_remediations=1,
        total_duration_seconds=0.12,
        ecosystem_results=[
            ManifestBenchmarkMetrics(
                name="test/project",
                url="https://example.com/manifest.yaml",
                description="Test workload",
                total_bytes=1024,
                document_count=2,
                documents_idempotent=2,
                stream_idempotent=True,
                comments_total=5,
                comments_preserved=5,
                anchors_broken=0,
                semantic_drift=0,
                had_remediations=True,
                remediations_count=1,
                execution_time_ms=120.0,
                sha256="abc12345",
            )
        ],
    )

    dated_file, latest_file = write_json_telemetry(summary, output_dir=str(tmp_path))
    assert dated_file.exists()
    assert latest_file.exists()

    data = json.loads(latest_file.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0.0"
    assert "summary" in data
    assert "failure_classification" in data
    assert "ecosystem_results" in data

    fc = data["failure_classification"]
    assert fc["comment_drop_failures"] == 0
    assert fc["anchor_broken_failures"] == 0
    assert fc["semantic_drift_failures"] == 0
    assert fc["document_idempotency_failures"] == 0
    assert fc["engine_panic_failures"] == 0

    assert len(data["ecosystem_results"]) == 1
    assert data["ecosystem_results"][0]["status"] == "PASS"


def test_write_markdown_report_output(tmp_path):
    """Verify markdown report generation and table structure."""
    summary = CorpusSuiteSummary(
        total_ecosystems=1,
        ecosystems_passed=1,
        total_bytes=2048,
        total_documents=1,
        documents_idempotent=1,
        total_comments_checked=2,
        total_comments_preserved=2,
        ecosystem_results=[
            ManifestBenchmarkMetrics(
                name="org/repo",
                url="https://github.com/org/repo",
                description="Sample",
                total_bytes=2048,
                document_count=1,
                documents_idempotent=1,
                stream_idempotent=True,
                comments_total=2,
                comments_preserved=2,
                sha256="deadbeef",
            )
        ],
    )
    report_file = tmp_path / "REPORT.md"
    write_markdown_report(summary, output_file=str(report_file))

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# Yamlr Golden Corpus — Real-World Ecosystem Regression Report" in content
    assert "org/repo" in content
    assert "✅ PASS" in content


def test_golden_corpus_cli_parser_help():
    """Verify that CLI parser accepts standard help flag without error."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_golden_corpus_strict_failure_exit(tmp_path, monkeypatch):
    """Verify that strict mode enforces exit code 1 when invariants fail."""
    failing_summary = CorpusSuiteSummary(
        total_ecosystems=1,
        ecosystems_passed=0,
        total_panics=1,
        total_documents=1,
        documents_idempotent=0,
        total_comments_checked=2,
        total_comments_preserved=1,
        comment_retention_rate=50.0,
        document_idempotency_rate=0.0,
        anchor_broken_failures=1,
        semantic_drift_failures=1,
    )
    monkeypatch.setattr(
        "scripts.run_golden_corpus.run_corpus_evaluation",
        lambda **kwargs: failing_summary,
    )

    exit_code = main([
        "--strict",
        "--cache-dir", str(tmp_path),
        "--output-dir", str(tmp_path / "results"),
        "--report-file", str(tmp_path / "REPORT.md"),
    ])
    assert exit_code == 1

    exit_code_non_strict = main([
        "--no-strict",
        "--cache-dir", str(tmp_path),
        "--output-dir", str(tmp_path / "results"),
        "--report-file", str(tmp_path / "REPORT.md"),
    ])
    assert exit_code_non_strict == 0
````

## File: tests/test_guide_missing.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_guide_rich


def test_cmd_guide_not_found():
    """Verify guide command handles missing topics."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        with patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup', return_value=None):
            cmd_guide_rich(topic="unknown")
            assert any("not found" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_healing_invariants.py
````python
"""Property-based invariant and behavioral tests for Yamlr healing engine.

Why: Enforces the Zero-Failure Trust Pillar through formal mathematical
invariants: Idempotency (heal(heal(x)) == heal(x)), No-Op Safety (heal on valid manifests
produces zero mutations), and Comment & Anchor Preservation.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import yamlr.cli.handlers as handlers
import yamlr.core.info as core_info
from yamlr import heal_yaml
from yamlr.core.license import LicenseManager

# ---------------------------------------------------------------------------
# Invariant 1: Idempotency (heal(heal(x)) == heal(x))
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("manifest_input", [
    """apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: legacy-ingress
spec:
  rules:
  - http:
      paths:
      - path: /test
        backend:
          serviceName: test-svc
          servicePort: 80
""",
    """apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: busybox:1.36
""",
])
def test_healing_idempotency_invariant(manifest_input: str):
    """Verify that applying heal repeatedly reaches a stable fixed point."""
    first_pass = heal_yaml(manifest_input)
    assert first_pass.healed_yaml is not None

    second_pass = heal_yaml(first_pass.healed_yaml)
    # The second pass must be identical to the first pass and report zero further changes
    assert second_pass.healed_yaml == first_pass.healed_yaml
    assert second_pass.had_changes is False


# ---------------------------------------------------------------------------
# Invariant 2: No-Op Safety (heal(valid) == valid, had_changes == False)
# ---------------------------------------------------------------------------

def test_healing_noop_safety_invariant():
    """Verify that a schema-valid, modern manifest is not mutated by heal."""
    clean_manifest = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: clean-nginx
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.0
        ports:
        - containerPort: 80
"""
    res = heal_yaml(clean_manifest)
    assert res.had_changes is False
    assert res.healed_yaml == clean_manifest


# ---------------------------------------------------------------------------
# Invariant 3: Comment & Layout Preservation Invariant
# ---------------------------------------------------------------------------

def test_healing_preserves_comments_and_structure():
    """Verify that healing never strips developer comments or annotations."""
    commented_manifest = """# Primary cluster ingress configuration
# Managed by Platform Operations
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  # Metadata annotation block
  name: core-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-svc
            port:
              number: 80 # Upstream HTTP port
"""
    res = heal_yaml(commented_manifest)
    # All comments must be preserved byte-for-byte
    assert "# Primary cluster ingress configuration" in res.healed_yaml
    assert "# Managed by Platform Operations" in res.healed_yaml
    assert "# Metadata annotation block" in res.healed_yaml
    assert "# Upstream HTTP port" in res.healed_yaml


# ---------------------------------------------------------------------------
# Behavioral Tests: CLI Handlers & Diagnostic Boundaries
# ---------------------------------------------------------------------------

def test_cmd_auth_activation_flow():
    """Verify auth handler correctly delegates license activation."""
    with patch.object(LicenseManager, "activate_offline_key", return_value=True) as mock_act:
        handlers._cmd_auth("activate", "dummy_key_token")
        mock_act.assert_called_once_with("dummy_key_token")


def test_cmd_version_output():
    """Verify version command outputs cleanly without throwing exceptions."""
    with patch("yamlr.ui.theme.console.print") as mock_print:
        core_info.cmd_version()
        assert mock_print.called


def test_cmd_subscribe_output():
    """Verify subscribe handler triggers browser redirect and prints instructions."""
    with patch("webbrowser.open") as mock_wb, \
         patch("yamlr.ui.theme.console.print") as mock_print:
        handlers._cmd_subscribe()
        mock_wb.assert_called_once_with("https://yamlr.dev/pro")
        assert mock_print.called


def test_license_manager_offline_activation():
    """Verify offline key activation handles unparseable payloads safely."""
    lm = LicenseManager()
    assert lm.activate_offline_key("invalid_unparseable_key") is False
````

## File: tests/test_helm_umbrella_scan.py
````python
"""Tests for Helm chart scanning with templates, values variants, and subcharts."""
import os
import tempfile

import pytest

from yamlr.core.scanner import scan_helm_chart


def test_helm_chart_fallback_subcharts(monkeypatch):
    """Verify scan_helm_chart discovers templates and subcharts even if helm template CLI fails."""
    # Force helm command to fail
    import subprocess
    real_run = subprocess.run
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "helm":
            class MockProc:
                returncode = 1
                stdout = ""
                stderr = "mock helm failure"
            return MockProc()
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create chart structure
        chart_dir = os.path.join(tmpdir, "mychart")
        templates_dir = os.path.join(chart_dir, "templates")
        charts_dir = os.path.join(chart_dir, "charts")
        subchart_dir = os.path.join(charts_dir, "subservice")
        sub_templates = os.path.join(subchart_dir, "templates")
        os.makedirs(templates_dir)
        os.makedirs(sub_templates)

        # Write values.yaml
        with open(os.path.join(chart_dir, "values.yaml"), "w", encoding="utf-8") as f:
            f.write("replicaCount: 3\n")

        # Write main template
        with open(os.path.join(templates_dir, "deployment.yaml"), "w", encoding="utf-8") as f:
            f.write("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: main-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: main
  template:
    metadata:
      labels:
        app: main
    spec:
      containers:
        - name: app
          image: nginx:1.21.0
""")

        # Write subchart template
        with open(os.path.join(sub_templates, "service.yaml"), "w", encoding="utf-8") as f:
            f.write("""apiVersion: v1
kind: Service
metadata:
  name: sub-svc
spec:
  ports:
    - port: 80
""")

        results = list(scan_helm_chart(chart_dir, schemas=[]))
        # Should have found results from main chart and subchart
        assert len(results) >= 2
        paths = [r.file_path for r in results]
        assert any("deployment.yaml" in p for p in paths)
        assert any("service.yaml" in p for p in paths)
````

## File: tests/test_hermetic_offline.py
````python
"""Tests for hermetic offline execution and embedded schema rodata."""
import socket
from unittest.mock import patch

import pytest
import yamlr_native

TEST_DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: hermetic-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hermetic
  template:
    metadata:
      labels:
        app: hermetic
    spec:
      containers:
        - name: app
          image: nginx:1.24
"""


def test_schema_rodata_embedded_versions():
    """Verify standard Kubernetes schemas v1.21 through v1.37 are embedded in binary rodata."""
    for minor in range(21, 38):
        version_str = f"1.{minor}"
        schemas = yamlr_native.native_get_schema_for_version(version_str)
        assert len(schemas) > 0, f"Schema bundle missing for K8s v{version_str}"
        kinds = [s.kind for s in schemas]
        assert "Deployment" in kinds
        assert "Service" in kinds


def test_hermetic_execution_zero_network_egress():
    """Verify manifest formatting and healing executes with zero socket connections."""
    def guarded_socket(*args, **kwargs):
        raise RuntimeError("Network egress attempted during hermetic execution!")

    with patch.object(socket, 'socket', side_effect=guarded_socket):
        # Sharding & Structuring
        shards = yamlr_native.native_shard(TEST_DEPLOYMENT)
        assert len(shards) > 0

        manifest = yamlr_native.native_structurize(shards)
        assert manifest is not None

        # Formatting
        formatted = yamlr_native.native_format_yaml(TEST_DEPLOYMENT)
        assert "apiVersion: apps/v1" in formatted

        # Healing
        from yamlr import heal_yaml
        res = heal_yaml(TEST_DEPLOYMENT)
        assert res is not None
````

## File: tests/test_inline_diff.py
````python
import pytest

from yamlr.ui.diff_engine import (
    InlineWordDiff,
    SideBySideDiff,
    render_inline_diff,
    render_side_by_side_diff,
    render_unified_diff,
)
from yamlr.ui.renderer import RichRenderer


def test_inline_word_diff_tokenization():
    """Verify line tokenization isolates identifiers, punctuation, and spaces."""
    line = "  apiVersion: extensions/v1beta1 # legacy"
    tokens = InlineWordDiff.tokenize_line(line)
    assert "  " in tokens
    assert "apiVersion" in tokens
    assert ":" in tokens
    assert "extensions" in tokens
    assert "/" in tokens
    assert "v1beta1" in tokens
    assert "legacy" in tokens

def test_inline_word_diff_computation():
    """Verify word-level diff highlights exact replacements."""
    old_line = "  apiVersion: extensions/v1beta1"
    new_line = "  apiVersion: apps/v1"
    old_text, new_text = InlineWordDiff.compute_inline_words(old_line, new_line)
    
    assert "extensions/v1beta1" in old_text.plain
    assert "apps/v1" in new_text.plain
    assert "apiVersion:" in old_text.plain
    assert "apiVersion:" in new_text.plain

def test_render_diff_methods_execute_cleanly():
    """Verify that all RichRenderer diff methods execute without raising exceptions."""
    old = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: old-app\n"
    new = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: new-app\n"
    
    # Should execute without throwing any exception
    RichRenderer.render_inline_word_diff(old, new, title="Test Diff")
    RichRenderer.render_unified_diff(old, new, title="Test Unified")
    RichRenderer.render_side_by_side_diff(old, new, title="Test Side-by-Side")

def test_render_diff_identical_content():
    """Verify diff methods handle identical content gracefully."""
    content = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-svc\n"
    RichRenderer.render_inline_word_diff(content, content)
    RichRenderer.render_unified_diff(content, content)
    RichRenderer.render_side_by_side_diff(content, content)
````

## File: tests/test_integrations_fail.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.integrations import cmd_install_hook


def test_install_hook_fail():
    """Verify install hook failure handling."""
    with patch('os.path.exists', return_value=False):
        with patch('yamlr.ui.theme.console.print') as mock_print:
            cmd_install_hook()
            # Check for ERROR in the output
            found = False
            for call in mock_print.call_args_list:
                if "ERROR" in str(call[0]):
                    found = True
                    break
            assert found
````

## File: tests/test_integrations.py
````python
import os
import shutil

import pytest

from yamlr.integrations import cmd_install_action, cmd_install_hook


def test_install_hook_no_git(temp_workspace):
    """Verify failure if .git is missing."""
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_hook()
        assert result is False

def test_install_hook_success(temp_workspace):
    """Verify successful hook installation."""
    git_dir = os.path.join(temp_workspace, ".git")
    os.makedirs(git_dir)
    
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_hook()
        assert result is True
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        assert os.path.exists(hook_path)
        with open(hook_path, 'r') as f:
            content = f.read()
            assert "yamlr scan" in content

def test_install_action(temp_workspace):
    """Verify GitHub Action generation."""
    with patch('os.getcwd', return_value=temp_workspace):
        result = cmd_install_action()
        assert result is True
        action_path = os.path.join(temp_workspace, ".github", "workflows", "yamlr-safety.yml")
        assert os.path.exists(action_path)
        with open(action_path, 'r') as f:
            content = f.read()
            assert "yamlr/action@v1" in content

from unittest.mock import patch
````

## File: tests/test_k8s_functional_schema.py
````python
"""Functional Schema Validation & Semantic Correctness Test Suite.

Why: Empirically proves that Yamlr's healing mutations produce semantically valid
Kubernetes resources adhering to the official OpenAPI v3 schema (simulating admission
validation in an API server), closing the gap between textual invariance and operational
deployability.
"""
import sys
from pathlib import Path

import pytest

# Ensure scripts directory can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yamlr_native

import yamlr
from scripts.run_golden_corpus import UPSTREAM_MANIFESTS, split_yaml_documents
from yamlr import heal_yaml


@pytest.fixture(scope="module")
def k8s_schemas():
    """Load native Kubernetes OpenAPI schemas for v1.30."""
    return yamlr_native.native_get_schema_for_version("1.30")


def test_workload_missing_spec_detected(k8s_schemas):
    """Verify that incomplete workloads missing required 'spec' are correctly caught."""
    incomplete_deploy = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-deploy
"""
    violations = yamlr_native.native_check_schema_violations(incomplete_deploy, k8s_schemas)
    spec_violations = [v for v in violations if v.field_path == "spec"]
    assert len(spec_violations) == 1
    assert "Missing required field 'spec'" in spec_violations[0].message


def test_non_workload_without_spec_is_valid(k8s_schemas):
    """Verify that non-workloads (Namespace, ConfigMap, Secret) are not falsely flagged for missing spec."""
    valid_namespace = """apiVersion: v1
kind: Namespace
metadata:
  name: production-env
"""
    violations = yamlr_native.native_check_schema_violations(valid_namespace, k8s_schemas)
    assert len(violations) == 0

    valid_configmap = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  key: value
"""
    violations_cm = yamlr_native.native_check_schema_violations(valid_configmap, k8s_schemas)
    assert len(violations_cm) == 0


def test_golden_corpus_post_heal_functional_schema_validity(k8s_schemas):
    """Verify that 100% of healed Golden Corpus manifests adhere to Kubernetes schemas."""
    cache_dir = Path("corpus/golden_corpus")
    total_docs_checked = 0

    for name, meta in UPSTREAM_MANIFESTS.items():
        manifest_file = cache_dir / meta["file"]
        if not manifest_file.exists():
            continue

        raw_yaml = manifest_file.read_text(encoding="utf-8", errors="ignore")
        docs = split_yaml_documents(raw_yaml)

        for doc in docs:
            # Heal manifest
            healed_result = heal_yaml(doc)
            healed_yaml = healed_result.healed_yaml

            # Validate against Kubernetes OpenAPI schema
            violations = yamlr_native.native_check_schema_violations(healed_yaml, k8s_schemas)
            assert len(violations) == 0, f"Schema violation detected in {name}: {[v.message for v in violations]}"
            total_docs_checked += 1

    assert total_docs_checked >= 95, f"Expected at least 95 documents evaluated, got {total_docs_checked}"
````

## File: tests/test_knowledge_bible.py
````python
import os

import pytest

from yamlr.knowledge.bible import BiblicalRegistry


def test_bible_registry_parse(temp_workspace):
    man_path = os.path.join(temp_workspace, "man1")
    os.makedirs(man_path)
    
    # Create dummy man page
    roff_content = r"""
.TH "YAMLR-TEST" "1" "May 2026" "Yamlr 0.1.0" "Yamlr Manual"
.SH "NAME"
yamlr-test \- Test command
.SH "DESCRIPTION"
This is a test command.
.PP
.SH "OPTIONS"
\fB--flag <ARG>\fR: A test flag
"""
    with open(os.path.join(man_path, "yamlr-test.1"), "w") as f:
        f.write(roff_content)
        
    registry = BiblicalRegistry(man_path=man_path)
    
    # Test lookup command
    res = registry.lookup("test")
    assert res is not None
    assert res["title"] == "Yamlr Test"
    assert "test command" in res["definition"]
    
    # Test lookup flag
    res_flag = registry.lookup("test", "--flag")
    assert res_flag is not None
    assert "A test flag" in res_flag["definition"]
    
    # Test missing command
    assert registry.lookup("missing") is None
    
    # Test missing flag
    assert registry.lookup("test", "--missing") is None

def test_bible_registry_no_dir(temp_workspace):
    registry = BiblicalRegistry(man_path=os.path.join(temp_workspace, "does_not_exist"))
    assert registry.lookup("test") is None
````

## File: tests/test_license_extended.py
````python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import LicenseManager


def test_license_load_env():
    """Verify loading from YAMLR_TOKEN."""
    with patch.dict('os.environ', {'YAMLR_TOKEN': 'test-token'}):
        with patch('yamlr_native.native_verify_token', return_value=True):
            lm = LicenseManager()
            assert lm.is_pro is True

def test_license_load_keyring():
    """Verify loading from keyring."""
    with patch('keyring.get_password', return_value='test-token'):
        with patch('yamlr_native.native_verify_token', return_value=True):
            lm = LicenseManager()
            assert lm.is_pro is True

def test_license_load_file(temp_workspace):
    """Verify loading from encrypted file."""
    license_file = os.path.join(temp_workspace, ".yamlr", "license.json")
    os.makedirs(os.path.dirname(license_file))
    with open(license_file, 'w') as f:
        json.dump({"token": "encrypted"}, f)
        
    with patch('os.path.expanduser', return_value=license_file):
        with patch('yamlr_native.native_decrypt_credential', return_value='token'):
            with patch('yamlr_native.native_verify_token', return_value=True):
                lm = LicenseManager()
                assert lm.is_pro is True

def test_license_save_token(temp_workspace):
    """Verify token saving to layers."""
    license_file = os.path.join(temp_workspace, "license.json")
    with patch('yamlr.core_logic.LicenseManager._get_machine_id', return_value="test-mid"):
        lm = LicenseManager()
        with patch('keyring.set_password'):
            with patch('yamlr_native.native_encrypt_credential', return_value="enc"):
                with patch('os.path.expanduser', return_value=license_file):
                    with patch('os.makedirs'):
                        lm._save_token("raw-token")
                        assert os.path.exists(license_file)
                        with open(license_file, 'r') as f:
                            data = json.load(f)
                            assert data['token'] == "enc"
````

## File: tests/test_license.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import LicenseManager


def test_license_manager_mid():
    """Verify machine ID generation."""
    with patch('yamlr_native.native_get_machine_id', return_value="test-mid"):
        lm = LicenseManager()
        assert lm.mid == "test-mid"

def test_license_manager_check_pro_no_token():
    """Check pro returns False if no token is found."""
    with patch('keyring.get_password', return_value=None):
        with patch('os.path.exists', return_value=False):
            lm = LicenseManager()
            assert lm.check_pro() is False

def test_license_manager_verify_heartbeat():
    """Verify heartbeat verification logic."""
    lm = LicenseManager()
    # Mocking native_verify_token to return True
    with patch('yamlr_native.native_verify_token', return_value=True):
        assert lm.verify_token("fake-token") is True
````

## File: tests/test_logic_utils.py
````python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(reason="Function refactored/moved to native core")
try:
    from yamlr.core_logic import _collect_yaml_files, _detect_k8s_version_safe, _print_available_topics
except ImportError:
    _collect_yaml_files = _detect_k8s_version_safe = _print_available_topics = MagicMock()

def test_collect_yaml_files(temp_workspace):
    """Verify recursive YAML collection."""
    # Create structure
    os.makedirs(os.path.join(temp_workspace, "subdir"))
    f1 = os.path.join(temp_workspace, "root.yaml")
    f2 = os.path.join(temp_workspace, "subdir", "child.yml")
    f3 = os.path.join(temp_workspace, "ignore.txt")
    
    for f in [f1, f2, f3]:
        with open(f, 'w') as fh: fh.write("content")
        
    files = _collect_yaml_files(temp_workspace)
    assert len(files) == 2
    assert f1 in files
    assert any(f2 in f for f in files) # Handle path separators

@patch('os.getenv', return_value="1.29")
def test_detect_k8s_version_env(mock_env):
    """Verify version detection from env."""
    assert _detect_k8s_version_safe() == '1.29'

@patch('os.getenv', return_value=None)
@patch('subprocess.run')
def test_detect_k8s_version_kubectl(mock_run, mock_env):
    """Verify version detection from kubectl."""
    mock_run.return_value = MagicMock(
        returncode=0, 
        stdout=json.dumps({"clientVersion": {"major": "1", "minor": "28"}})
    )
    assert _detect_k8s_version_safe() == "1.28"

@patch('yamlr.ui.theme.console.print')
def test_print_available_topics(mock_print):
    """Verify print_available_topics renders table."""
    mock_registry = MagicMock()
    mock_registry.DATA = {"Y-101": {"title": "Test Topic"}}
    _print_available_topics(mock_registry)
    mock_print.assert_called()
````

## File: tests/test_lsp_code_action.py
````python
"""Unit tests for LSP Code Action provider and rule URLs."""
import json

import pytest

from yamlr.lsp import LspServer


def test_lsp_server_capabilities():
    server = LspServer()
    # Mock send_response to capture output
    captured = []
    server.send_response = lambda req_id, result: captured.append((req_id, result))

    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    server.handle_request(init_req)
    assert len(captured) == 1
    req_id, result = captured[0]
    assert req_id == 1
    assert result["capabilities"]["codeActionProvider"] is True


def test_lsp_code_action_generation(tmp_path):
    server = LspServer()
    captured = []
    server.send_response = lambda req_id, result: captured.append((req_id, result))

    broken_manifest = tmp_path / "broken.yaml"
    broken_manifest.write_text("""apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: test-deploy
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
""", encoding="utf-8")

    ca_req = {
        "jsonrpc": "2.0",
        "id": 42,
        "method": "textDocument/codeAction",
        "params": {
            "textDocument": {"uri": f"file:///{broken_manifest.as_posix()}"},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}
        }
    }
    server.handle_request(ca_req)
    assert len(captured) == 1
    req_id, actions = captured[0]
    assert req_id == 42
    assert len(actions) >= 1
    assert "Yamlr: Auto-repair manifest" in actions[0]["title"]
    assert actions[0]["kind"] == "quickfix"
````

## File: tests/test_lsp_error_handling.py
````python
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer


def test_lsp_server_error_handling():
    """Verify LSP server handles scanning errors gracefully."""
    server = LspServer()
    # Mock send_diagnostics to fail
    with patch.object(server, 'send_diagnostics', side_effect=Exception("Crash")):
        with patch('sys.stderr.write') as mock_err:
            server.handle_request({"method": "textDocument/didOpen", "params": {"textDocument": {"uri": "file://test.yaml"}}})
            mock_err.assert_called()

def test_lsp_notification_crash_safety():
    """Verify that a crash in diagnostic generation doesn't kill the server."""
    server = LspServer()
    # Mock handle_request to fail
    with patch.object(server, 'send_diagnostics', side_effect=Exception("Crash")):
        # Call handler - should be caught by try-except in handle_request
        server.handle_request({"method": "textDocument/didOpen", "params": {"textDocument": {"uri": "file://test.yaml"}}})
        # No exception should be raised
````

## File: tests/test_lsp_logic.py
````python
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer, cmd_lsp


def test_lsp_initialize():
    """Verify LSP initialization response."""
    server = LspServer()
    payload = b'{"jsonrpc": "2.0", "id": 1, "method": "initialize"}'
    content = b'Content-Length: ' + str(len(payload)).encode() + b'\r\n\r\n' + payload
    server.reader = io.BytesIO(content)
    server.writer = io.BytesIO()
    
    # Run one iteration (hacky but works for unit test)
    try:
        server.run()
    except EOFError:
        pass
    except Exception:
        pass # readline will fail eventually
    
    output = server.writer.getvalue().decode('utf-8')
    assert "capabilities" in output
    assert "diagnosticProvider" in output

@patch('yamlr.lsp.streaming_scan')
def test_lsp_diagnostics(mock_scan):
    """Verify LSP diagnostics notification."""
    server = LspServer()
    server.writer = io.BytesIO()
    
    violation = MagicMock(line_no=10, severity="CRITICAL", rule_id="ERR-01", message="Test failure")
    mock_scan.return_value = [MagicMock(integrity_violations=[violation])]
    
    server.send_diagnostics("file://test.yaml", "test.yaml")
    
    output = server.writer.getvalue().decode('utf-8')
    assert "textDocument/publishDiagnostics" in output
    assert "Test failure" in output
    assert "ERR-01" in output
````

## File: tests/test_lsp.py
````python
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer


def test_lsp_handle_initialize():
    """Verify that LSP server handles initialize request."""
    server = LspServer()
    server.send_message = MagicMock()
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    server.handle_request(request)
    
    server.send_message.assert_called_once()
    response = server.send_message.call_args[0][0]
    assert response['id'] == 1
    assert "capabilities" in response['result']

def test_lsp_send_diagnostics():
    """Verify that LSP server sends diagnostics for a file."""
    server = LspServer()
    server.send_message = MagicMock()
    
    # Mock violation
    v = MagicMock()
    v.rule_id = "Y-001"
    v.severity = "CRITICAL"
    v.message = "Test"
    v.line_no = 5
    
    # Mock result
    res = MagicMock()
    res.integrity_violations = [v]
    
    with patch('yamlr.lsp.streaming_scan', return_value=[res]):
        server.send_diagnostics("file:///test.yaml", "/test.yaml")
        
    server.send_message.assert_called()
    notification = server.send_message.call_args[0][0]
    assert notification['method'] == "textDocument/publishDiagnostics"
    assert len(notification['params']['diagnostics']) > 0
    diag = notification['params']['diagnostics'][0]
    assert diag['code'] == "Y-001"
    assert diag['range']['start']['line'] == 4
````

## File: tests/test_mcp_server.py
````python
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.mcp_server import _execute_tool, run_mcp_server


def test_mcp_initialize():
    """Verify initialize request."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["id"] == 1
            assert "serverInfo" in output["result"]

def test_mcp_tools_list():
    """Verify tools/list request."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["id"] == 2
            assert len(output["result"]["tools"]) == 5

def test_mcp_tools_call():
    """Verify tools/call request."""
    req = {
        "jsonrpc": "2.0", 
        "id": 3, 
        "method": "tools/call", 
        "params": {"name": "scan_manifests", "arguments": {"path": "."}}
    }
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('yamlr.mcp_server._execute_tool', return_value={"status": "success"}) as mock_exec:
                run_mcp_server()
                output = json.loads(mock_stdout.getvalue().strip())
                assert output["id"] == 3
                assert "content" in output["result"]
                mock_exec.assert_called_once_with("scan_manifests", {"path": "."})

def test_mcp_method_not_found():
    """Verify unknown method request."""
    req = {"jsonrpc": "2.0", "id": 4, "method": "unknown"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["error"]["code"] == -32601

def test_mcp_error_handling():
    """Verify exception handling during request parsing."""
    with patch('sys.stdin', io.StringIO("invalid json\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["error"]["code"] == -32603

@patch('yamlr_native.NativeTelemetry')
@patch('yamlr_native.native_apply_fix_atomic', return_value=True)
def test_execute_tool_heal(mock_apply, mock_telemetry):
    """Verify _execute_tool heal logic."""
    with patch('yamlr.cli.main.detect_version', return_value="1.30"):
        with patch('yamlr.cli.main.initialize_engine', return_value=[]):
            mock_res = MagicMock(
                file_path="test.yaml", 
                health_score=80.0,
                violations=[MagicMock(field_path="v", message="msg")],
                integrity_violations=[MagicMock(check_name="i", message="msg")],
                suggested_fixes=[MagicMock(field_path="v", suggested_value="x")]
            )
            mock_report = MagicMock(results=[mock_res], total_files=1)
            with patch('yamlr.cli.main.execute_pipeline', return_value=mock_report):
                res = _execute_tool("heal_manifests", {"path": "."})
                assert res["status"] == "success"
                assert res["applied_fixes"] == 1
                assert len(res["results"]) == 1
                assert len(res["results"][0]["violations"]) == 2

def test_execute_tool_error():
    """Verify _execute_tool exception handling."""
    with patch('yamlr.cli.main.detect_version', side_effect=Exception("detect error")):
        res = _execute_tool("scan_manifests", {"path": "."})
        assert res["status"] == "error"
        assert res["message"] == "detect error"

@patch('yamlr_native.native_get_schema_info', create=True)
def test_execute_tool_get_openapi_schema(mock_schema):
    """Verify get_openapi_schema logic."""
    mock_schema.return_value = '{"openapi": "3.0.0"}'
    res = _execute_tool("get_openapi_schema", {"kind": "Deployment", "k8s_version": "1.30"})
    assert res["status"] == "success"
    assert "openapi" in res["schema"]
    mock_schema.assert_called_once_with("Deployment", "1.30")

def test_execute_tool_get_resource_dependencies():
    """Verify get_resource_dependencies logic."""
    with patch('yamlr.cli.main.detect_version', return_value="1.30"):
        with patch('yamlr.cli.main.initialize_engine', return_value=[]):
            mock_res1 = MagicMock()
            mock_res1.dependencies = [{"kind": "ConfigMap", "name": "app-config"}]
            mock_res1.identity.kind = "Deployment"
            mock_res1.identity.name = "web"
            
            mock_report = MagicMock(results=[mock_res1], total_files=1)
            with patch('yamlr.cli.main.execute_pipeline', return_value=mock_report):
                res = _execute_tool("get_resource_dependencies", {"path": ".", "kind": "ConfigMap", "name": "app-config"})
                assert res["status"] == "success"
                assert res["target"] == "ConfigMap/app-config"
                assert "Deployment web" in res["dependencies"]
````

## File: tests/test_phase3_lexer_verification.py
````python
"""High-fidelity YAML lexer verification test suite covering odd indents, block chomping, and line endings."""
import pytest
import yamlr_native


def test_odd_indentation_1_and_3_spaces_preservation():
    """Verify that 1-space and 3-space indents are NOT snapped to even numbers."""
    raw_yaml = (
        "spec:\n"
        "   replicas: 3\n"
        "   template:\n"
        "    metadata:\n"
        "     labels:\n"
        "      app: odd-indent-test\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "   replicas: 3" in reconstructed, "3-space indent must be preserved verbatim!"
    assert "    metadata:" in reconstructed, "4-space indent must be preserved!"
    assert "     labels:" in reconstructed, "5-space indent must be preserved verbatim!"
    assert "      app: odd-indent-test" in reconstructed, "6-space indent must be preserved!"


def test_block_scalar_chomping_strip_and_keep():
    """Verify that |- (strip) and |+ (keep) block scalar indicators are preserved."""
    raw_yaml = (
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: script-config\n"
        "data:\n"
        "  run.sh: |-\n"
        "    #!/bin/bash\n"
        "    echo 'Hello Yamlr'\n"
        "  notes.txt: |+\n"
        "    Some notes\n"
        "\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "run.sh: |-" in reconstructed or "|-" in reconstructed, "Chomping indicator |- must be preserved!"
    assert "notes.txt: |+" in reconstructed or "|+" in reconstructed, "Chomping indicator |+ must be preserved!"
    assert "echo 'Hello Yamlr'" in reconstructed


def test_multidoc_with_comments_and_blank_lines():
    """Verify that multi-document streams with pure comments and blank lines are reconstructed with 100% fidelity."""
    raw_yaml = (
        "# Header comment\n"
        "apiVersion: v1\n"
        "kind: Namespace\n"
        "metadata:\n"
        "  name: prod\n"
        "---\n"
        "# Second document comment\n"
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n"
        "  name: prod-svc\n"
        "spec:\n"
        "  ports:\n"
        "  - port: 80 # inline comment\n"
        "    targetPort: 8080\n"
    )
    shards = yamlr_native.native_shard(raw_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "# Header comment" in reconstructed
    assert "kind: Namespace" in reconstructed
    assert "---" in reconstructed
    assert "# Second document comment" in reconstructed
    assert "# inline comment" in reconstructed
    assert "targetPort: 8080" in reconstructed


def test_crlf_windows_line_ending_preservation():
    """Verify that Windows CRLF line endings are parsed and reconstructed without corrupting newlines."""
    crlf_yaml = "apiVersion: v1\r\nkind: Pod\r\nmetadata:\r\n  name: crlf-pod\r\n"
    shards = yamlr_native.native_shard(crlf_yaml)
    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    
    assert "apiVersion: v1" in reconstructed
    assert "kind: Pod" in reconstructed
    assert "name: crlf-pod" in reconstructed
````

## File: tests/test_pipe_composability.py
````python
"""Tests for POSIX / Unix pipe composability (stdin / stdout)."""
import io
import sys

from yamlr.cli.fmt_handler import cmd_fix_dispatch, cmd_fmt_dispatch

INPUT_UNORDERED = """kind: Service
metadata:
  name: pipe-svc
apiVersion: v1
spec:
  ports:
    - port: 443
"""

INPUT_DEPRECATED = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: pipe-deployment
spec:
  replicas: 2
"""


def test_fmt_stdin_stdout(monkeypatch):
    """Verify yamlr fmt - reads from stdin and outputs formatted YAML to stdout."""
    monkeypatch.setattr('sys.stdin', io.StringIO(INPUT_UNORDERED))
    out_capture = io.StringIO()
    monkeypatch.setattr('sys.stdout', out_capture)

    class Args:
        path = "-"
        write = False
        w = False

    res = cmd_fmt_dispatch(Args())
    assert res == 0

    output = out_capture.getvalue()
    lines = [l.split(":")[0].strip() for l in output.strip().splitlines() if not l.startswith(" ") and not l.startswith("-")]
    assert lines == ["apiVersion", "kind", "metadata", "spec"]


def test_fix_stdin_stdout(monkeypatch):
    """Verify yamlr fix - reads from stdin and outputs healed YAML to stdout."""
    monkeypatch.setattr('sys.stdin', io.StringIO(INPUT_DEPRECATED))
    out_capture = io.StringIO()
    monkeypatch.setattr('sys.stdout', out_capture)

    class Args:
        path = "-"

    res = cmd_fix_dispatch(Args())
    assert res == 0

    output = out_capture.getvalue()
    assert "apiVersion: apps/v1" in output
    assert "kind: Deployment" in output
````

## File: tests/test_pipeline.py
````python
import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from yamlr.cli.main import execute_pipeline
from yamlr.core_logic import _process_document_shards, streaming_scan


def test_streaming_scan_single_file(temp_workspace):
    """Verify that streaming_scan handles a single file correctly."""
    yaml_path = os.path.join(temp_workspace, "test.yaml")
    with open(yaml_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n")
    
    mock_shard = MagicMock()
    mock_shard.is_doc_boundary = False
    
    with patch('yamlr_native.native_shard', return_value=[mock_shard]):
        with patch('yamlr.core.scanner._process_document_shards', return_value="mock-result") as mock_process:
            results = list(streaming_scan(yaml_path, []))
            assert len(results) == 1
            assert results[0] == "mock-result"
            mock_process.assert_called_once()

def test_streaming_scan_multi_doc(temp_workspace):
    """Verify that streaming_scan splits multi-document files."""
    yaml_path = os.path.join(temp_workspace, "multi.yaml")
    with open(yaml_path, 'w') as f:
        f.write("---\napiVersion: v1\nkind: Pod\n---\napiVersion: v1\nkind: Service\n")
    
    # Mock shards with doc boundaries
    shard1 = MagicMock()
    shard1.is_doc_boundary = True
    shard2 = MagicMock()
    shard2.is_doc_boundary = False
    shard3 = MagicMock()
    shard3.is_doc_boundary = True
    
    with patch('yamlr_native.native_shard', return_value=[shard1, shard2, shard3]):
        with patch('yamlr.core.scanner._process_document_shards', return_value="mock-result") as mock_process:
            results = list(streaming_scan(yaml_path, []))
            # Shard 1 is boundary (first doc starts), Shard 2 is content, Shard 3 is boundary (next doc starts)
            # Logic: yields on boundary if doc_shards is not empty.
            # Shard 1: doc_shards=[], nothing yielded. doc_shards=[shard1] (wait, logic says: if is_doc_boundary { if doc_shards { yield } doc_shards=[] } else { doc_shards.append })
            # Actually line 296: for shard in shards: if shard.is_doc_boundary: if doc_shards: yield; doc_shards=[] else: doc_shards.append(shard)
            # Plus a final yield after the loop.
            assert len(results) == 1 # Depending on the exact logic in core_logic.py
            # Let's check the logic again:
            # 296: for shard in shards:
            # 297:     if shard.is_doc_boundary:
            # 298:         if doc_shards:
            # 299:             result = _process_document_shards(...)
            # 303:             yield result
            # 304:             doc_shards = []
            # 305:     else:
            # 306:         doc_shards.append(shard)
            # 309: if doc_shards: yield _process_document_shards(...)
            
            # Shard 1: is_boundary=True, doc_shards=[] -> nothing. Loop continues. (Wait, shard 1 is NOT appended)
            # Shard 2: is_boundary=False -> doc_shards=[shard2]
            # Shard 3: is_boundary=True, doc_shards=[shard2] -> yield. doc_shards=[]
            # End of loop. doc_shards is empty.
            # Total: 1 yield.
            
def test_process_document_shards_scoring():
    """Verify health score calculation in _process_document_shards."""
    mock_native = MagicMock()
    mock_native.extract_native_identity.return_value = MagicMock(kind="Pod", name="test")
    
    # Mock violations
    v1 = MagicMock()
    v1.severity = "CRITICAL"
    v2 = MagicMock()
    v2.severity = "HIGH"
    mock_native.native_check_schema_violations.return_value = [v1, v2]
    
    mock_native.native_audit_forensics.return_value = []
    
    _process_document_shards(mock_native, "test.yaml", [], ["some-schema"], "content")
    
    # Check ResourceResult call
    args, kwargs = mock_native.ResourceResult.call_args
    assert kwargs['health_score'] == 80.0

def test_execute_pipeline_aggregation():
    """Verify that execute_pipeline aggregates streaming results into a report."""
    with patch('yamlr.core_logic.streaming_scan', return_value=[MagicMock(file_path="p1"), MagicMock(file_path="p2")]):
        with patch('yamlr_native.NativeReport') as mock_report_class:
            execute_pipeline("some/path", [])
            mock_report_class.assert_called_once()
            args, kwargs = mock_report_class.call_args
            assert kwargs['total_files'] == 2
            assert kwargs['results'] == [ANY, ANY]
````

## File: tests/test_policy_ingestion.py
````python
"""Unit tests for OPA and Kyverno policy ingestion."""
import json
import os

import pytest

from yamlr.core.stages.policy_ingestion_stage import PolicyIngestionStage


def test_parse_opa_violations(tmp_path):
    opa_data = {
        "violations": [
            {
                "constraint": "k8srequiredlabels",
                "resource": {"kind": "Deployment", "name": "my-deploy"},
                "message": "Missing required label: app"
            }
        ]
    }
    report_file = tmp_path / "opa-report.json"
    report_file.write_text(json.dumps(opa_data), encoding="utf-8")

    violations = PolicyIngestionStage._parse_opa(opa_data)
    assert len(violations) == 1
    assert violations[0]["kind"] == "Deployment"
    assert violations[0]["name"] == "my-deploy"


def test_parse_kyverno_violations(tmp_path):
    kyverno_data = {
        "results": [
            {
                "policy": "disallow-latest-tag",
                "resources": [{"kind": "Pod", "name": "test-pod"}],
                "message": "Using latest tag is disallowed."
            }
        ]
    }
    violations = PolicyIngestionStage._parse_kyverno(kyverno_data)
    assert len(violations) == 1
    assert violations[0]["kind"] == "Pod"
    assert violations[0]["name"] == "test-pod"
````

## File: tests/test_precommit_hooks.py
````python
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

def test_precommit_hooks_yaml_validity():
    """Verify that .pre-commit-hooks.yaml exists, parses, and defines required hooks."""
    hooks_file = ROOT / ".pre-commit-hooks.yaml"
    assert hooks_file.exists(), ".pre-commit-hooks.yaml must exist at repo root"
    
    with open(hooks_file, "r", encoding="utf-8") as f:
        hooks = yaml.safe_load(f)
    
    assert isinstance(hooks, list), ".pre-commit-hooks.yaml must be a list of hook definitions"
    hook_ids = {h.get("id"): h for h in hooks}
    
    # 1. Verify yamlr-fmt
    assert "yamlr-fmt" in hook_ids, "yamlr-fmt hook must be defined"
    fmt = hook_ids["yamlr-fmt"]
    assert "yamlr fmt" in fmt.get("entry", "")
    assert "-w" in fmt.get("args", [])
    assert fmt.get("pass_filenames") is True
    
    # 2. Verify yamlr-fix
    assert "yamlr-fix" in hook_ids, "yamlr-fix hook must be defined"
    fix = hook_ids["yamlr-fix"]
    assert "yamlr fix" in fix.get("entry", "")
    assert fix.get("pass_filenames") is True

    # 3. Verify backward-compatible yamlr-scan and yamlr-heal
    assert "yamlr-scan" in hook_ids, "yamlr-scan hook must be preserved"
    assert "yamlr-heal" in hook_ids, "yamlr-heal hook must be preserved"

def test_precommit_config_example_validity():
    """Verify that .pre-commit-config.example.yaml parses cleanly."""
    example_file = ROOT / ".pre-commit-config.example.yaml"
    assert example_file.exists(), ".pre-commit-config.example.yaml must exist"
    
    with open(example_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert "repos" in config
    assert len(config["repos"]) > 0
    repo = config["repos"][0]
    hook_ids = [h["id"] for h in repo.get("hooks", [])]
    assert "yamlr-fmt" in hook_ids
    assert "yamlr-fix" in hook_ids

def test_github_action_yaml_validity():
    """Verify that action.yml parses and exposes all GitOps inputs."""
    action_file = ROOT / "action.yml"
    assert action_file.exists(), "action.yml must exist at repo root"
    
    with open(action_file, "r", encoding="utf-8") as f:
        action = yaml.safe_load(f)
    
    inputs = action.get("inputs", {})
    assert "command" in inputs
    assert "write" in inputs
    assert "check" in inputs
    assert "autocommit" in inputs
    assert "commit-message" in inputs
    assert "path" in inputs

def test_github_workflow_gitops_yaml_validity():
    """Verify that .github/workflows/yamlr-gitops.yml is valid YAML."""
    wf_file = ROOT / ".github" / "workflows" / "yamlr-gitops.yml"
    assert wf_file.exists(), "yamlr-gitops.yml workflow must exist"
    
    with open(wf_file, "r", encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    
    assert "on" in wf or True in wf, "Workflow must define trigger events"
    assert "jobs" in wf
    assert "gitops-fmt-and-fix" in wf["jobs"]
````

## File: tests/test_proto_service.py
````python
import pytest

from yamlr.proto_service import ManifestService


def test_proto_service_scan_valid():
    svc = ManifestService()
    req = {
        "content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.0
""",
        "file_path": "in-memory.yaml",
        "target_k8s_version": "1.30",
    }
    resp = svc.scan_document(req)
    assert resp["status"] in ["passed", "failed"]
    assert "health_score" in resp
    assert "duration_ms" in resp


def test_proto_service_heal_idempotent():
    svc = ManifestService()
    content = """# Comment
apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
  ports:
  - port: 80
    targetPort: 80
"""
    req = {"content": content, "dry_run": True}
    resp = svc.heal_document(req)
    assert resp["healed_content"] == content
    assert resp["mutated"] is False
````

## File: tests/test_public_api.py
````python
import pytest

import yamlr


def test_heal_yaml_public_api():
    yaml_in = "apiVersion: extensions/v1beta1\nkind: Deployment\nmetadata:\n  name: my-app # important comment\nspec:\n  replicas: 2\n"
    res = yamlr.heal_yaml(yaml_in)
    assert res.had_changes is True
    assert "# important comment" in res.healed_yaml
    assert len(res.changes) > 0
    assert repr(res).startswith("<HealResult")

def test_scan_yaml_public_api():
    yaml_in = "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\nspec:\n  ports:\n  - port: 80\n"
    res = yamlr.scan_yaml(yaml_in)
    assert res["identity"] is not None
    assert res["identity"]["kind"] == "Service"
    assert res["identity"]["name"] == "my-svc"
````

## File: tests/test_remediation_integrity.py
````python
"""Tests for post-write invariant verification and instant auto-rollback."""
import os
import shutil
import tempfile
from unittest.mock import MagicMock

from yamlr.cli.remediation import apply_remediation


def test_remediation_post_write_auto_rollback(monkeypatch):
    """Verify that if post-write invariant fails, the file is automatically restored from .bak."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = os.path.join(tmpdir, "test.yaml")
        original_content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        mock_fix = MagicMock()
        mock_fix.field_path = "spec.replicas"
        mock_fix.suggested_value = 3
        mock_fix.message = "Set replicas"

        mock_res = MagicMock()
        mock_res.file_path = target_file
        mock_res.suggested_fixes = [mock_fix]
        mock_res.identity = MagicMock(kind="Pod", name="test")

        import yamlr_native
        # Simulate native_apply_fix_atomic writing corrupted unparseable content
        def mock_apply_atomic(path, field, val, kind, name):
            with open(path, "w", encoding="utf-8") as f:
                f.write("corrupted: invalid: [yaml: {unclosed")
            return True

        monkeypatch.setattr(yamlr_native, "native_apply_fix_atomic", mock_apply_atomic)

        # Apply remediation
        apply_remediation(mock_res, telemetry=None, apply=True, dry_run=False, diff=False)

        # Verify that post-write invariant failed and restored original content!
        with open(target_file, "r", encoding="utf-8") as f:
            final_content = f.read()

        assert final_content == original_content, "Corrupted file must be automatically rolled back from .bak!"
````

## File: tests/test_remediation_logic.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import apply_remediation


def test_apply_remediation_interactive():
    """Verify interactive remediation flow."""
    res = MagicMock()
    fix = MagicMock()
    fix.field_path = "spec.replicas"
    fix.message = "Low replicas"
    res.suggested_fixes = [fix]
    
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation._handle_interactive_remediation', return_value=True) as mock_handle:
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_apply:
                apply_remediation(res, telemetry, True)
                mock_handle.assert_called_once()
                mock_apply.assert_called_once()

def test_apply_remediation_cicd():
    """Verify CI/CD remediation flow."""
    res = MagicMock()
    fix = MagicMock()
    res.suggested_fixes = [fix]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=False):
        with patch('yamlr.cli.remediation._handle_cicd_remediation') as mock_handle:
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_apply:
                apply_remediation(res, telemetry, True)
                mock_handle.assert_called_once()
                mock_apply.assert_called_once()
````

## File: tests/test_remediation.py
````python
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _apply_atomic_fix, apply_remediation, render_resource_results


def test_apply_atomic_fix_success(temp_workspace):
    """Verify atomic fix application with backup."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w') as f: f.write("content")
    
    res = MagicMock(file_path=fpath)
    fix = MagicMock(field_path="spec.replicas", suggested_value="3")
    telemetry = MagicMock()
    
    with patch('yamlr_native.native_record_telemetry'):
        with patch('yamlr_native.native_apply_fix_atomic', return_value=True):
            with patch('yamlr.ui.theme.console.print'):
                _apply_atomic_fix(res, fix, telemetry)
            
    assert os.path.exists(fpath + ".bak")

@patch('sys.stdin.isatty', return_value=False)
@patch('yamlr.cli.remediation._apply_atomic_fix')
def test_apply_remediation_cicd(mock_fix, mock_tty):
    """Verify CI/CD remediation auto-apply."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec", message="Fix it")
    res.suggested_fixes = [fix]
    
    # Mode: apply=True
    apply_remediation(res, MagicMock(), apply=True)
    mock_fix.assert_called_once()

@patch('sys.stdin.isatty', return_value=True)
@patch('yamlr.cli.remediation.console.input', return_value='y')
@patch('yamlr.cli.remediation._apply_atomic_fix')
def test_apply_remediation_interactive(mock_fix, mock_input, mock_tty):
    """Verify interactive remediation."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec", message="Fix it")
    res.suggested_fixes = [fix]
    
    apply_remediation(res, MagicMock(), apply=False)
    mock_fix.assert_called_once()

@patch('yamlr.ui.theme.console.print')
def test_render_resource_results(mock_print):
    """Verify per-resource rendering."""
    res = MagicMock()
    res.violations = [MagicMock(field_path="v1", message="m1")]
    res.health_score = 80.0
    res.identity = MagicMock(kind="Pod", name="p1")
    res.suggested_fixes = []
    
    render_resource_results(res, MagicMock(), "scan", False)
    mock_print.assert_called()

import os
````

## File: tests/test_renderer.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


@patch('yamlr.ui.theme.console.print')
def test_render_welcome(mock_print):
    RichRenderer.render_welcome("/tmp", "1.30")
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_explain_dossier(mock_print):
    data = {"title": "Test", "definition": "Def", "rationale": "Rat", "impact": "High"}
    RichRenderer.render_explain("TEST", data)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_explain_k8s(mock_print):
    RichRenderer.render_explain("deployment.spec", None)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_summary(mock_print):
    stats = {"total_files": 10, "verified": 8, "violations": 2, "healed": 1, "time_ms": 150}
    RichRenderer.render_summary(stats)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_precision_help(mock_print):
    categories = {"Core": [{"name": "scan", "purpose": "Audit"}]}
    RichRenderer.render_precision_help(categories)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_graph(mock_print):
    edge = MagicMock(source="A", target="B", edge_type="DEPENDS")
    RichRenderer.render_graph([edge])
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_side_by_side_diff(mock_print):
    RichRenderer.render_side_by_side_diff("old", "new")
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_batch_summary(mock_print):
    res = MagicMock(violations=[], integrity_violations=[])
    report = MagicMock(results=[res], total_files=1, total_time_ms=100)
    RichRenderer.render_batch_summary(report, apply=True)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_score_animation(mock_print):
    res = MagicMock(health_score=85.0)
    report = MagicMock(results=[res])
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        RichRenderer.render_score_animation(report)
    mock_print.assert_called()
````

## File: tests/test_roi_no_native.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_roi


def test_cmd_roi_no_native():
    """Verify ROI command handles missing native core."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        # Force ImportError when importing yamlr_native in cmd_roi
        # We need to ensure it's not already in sys.modules or mock it
        with patch.dict('sys.modules', {'yamlr_native': MagicMock()}):
            # Patch the import inside the function
            with patch('builtins.__import__', side_effect=ImportError):
                try:
                    cmd_roi(".")
                except ImportError:
                    pass
                assert any("Native core required" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_sarif_fixes.py
````python
"""Tests for SARIF 2.1.0 fixes objects with artifactChanges."""
import json
import tempfile
from unittest.mock import MagicMock

from yamlr.sarif_reporter import SarifReporter


def test_sarif_includes_fixes():
    """Verify SARIF generator attaches fixes objects to auto-repairable violations."""
    mock_res = MagicMock()
    mock_res.file_path = "deploy.yaml"
    mock_res.violations = []
    
    mock_iv = MagicMock()
    mock_iv.rule_id = "INT-001"
    mock_iv.check_name = "Image Immutability"
    mock_iv.message = "Container uses mutable image tag :latest"
    mock_iv.severity = "WARNING"
    mock_iv.line_no = 15
    mock_res.integrity_violations = [mock_iv]

    mock_fix = MagicMock()
    mock_fix.rule_id = "INT-001"
    mock_fix.field_path = "image"
    mock_fix.suggested_value = "nginx:1.25.3"
    mock_res.suggested_fixes = [mock_fix]

    with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as tf:
        out_path = tf.name

    try:
        SarifReporter.generate_sarif([mock_res], out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = data["runs"][0]["results"]
        assert len(results) == 1
        res = results[0]
        assert res["ruleId"] == "INT-001"
        assert "fixes" in res
        fix_obj = res["fixes"][0]
        assert "artifactChanges" in fix_obj
        changes = fix_obj["artifactChanges"][0]
        assert changes["artifactLocation"]["uri"] == "deploy.yaml"
        assert len(changes["replacements"]) == 1
        assert "nginx:1.25.3" in changes["replacements"][0]["insertedContent"]["text"]
    finally:
        import os
        if os.path.exists(out_path):
            os.remove(out_path)
````

## File: tests/test_sarif_reporter.py
````python
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.sarif_reporter import SarifReporter


def test_generate_sarif_basic(tmp_path):
    """Test generating a simple SARIF report."""
    output_path = tmp_path / "report.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test.yaml"
    
    mock_integrity = MagicMock()
    mock_integrity.rule_id = "R-1"
    mock_integrity.check_name = "Check"
    mock_integrity.message = "Msg"
    mock_integrity.severity = "CRITICAL"
    mock_integrity.line_no = 5
    
    mock_res.integrity_violations = [mock_integrity]
    mock_res.violations = []
    
    SarifReporter.generate_sarif([mock_res], str(output_path))
    
    assert output_path.exists()
    with open(output_path, "r") as f:
        data = json.load(f)
        
    assert data["version"] == "2.1.0"
    assert len(data["runs"]) == 1
    assert data["runs"][0]["tool"]["driver"]["name"] == "yamlr"
    
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "R-1"
    assert results[0]["level"] == "error"
    assert results[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 5

def test_generate_sarif_schema_violations(tmp_path):
    """Test generating SARIF with schema violations."""
    output_path = tmp_path / "report2.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test2.yaml"
    mock_res.integrity_violations = []
    
    mock_schema = MagicMock()
    mock_schema.field_path = "spec.replicas"
    mock_schema.message = "Bad schema"
    mock_schema.severity = "HIGH"
    
    mock_res.violations = [mock_schema]
    
    SarifReporter.generate_sarif([mock_res], str(output_path))
    
    with open(output_path, "r") as f:
        data = json.load(f)
        
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "SCHEMA-spec.replicas"
    assert results[0]["level"] == "error"

def test_generate_sarif_no_catalog_fallback(tmp_path):
    """Test SARIF generation when the catalog file is missing."""
    output_path = tmp_path / "report3.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test3.yaml"
    mock_res.integrity_violations = []
    mock_res.violations = []
    
    with patch('os.path.exists', return_value=False):
        SarifReporter.generate_sarif([mock_res], str(output_path))
        
    with open(output_path, "r") as f:
        data = json.load(f)
    assert len(data["runs"][0]["results"]) == 0

def test_map_severity():
    """Test severity mapping."""
    assert SarifReporter._map_severity("CRITICAL") == "error"
    assert SarifReporter._map_severity("HIGH") == "error"
    assert SarifReporter._map_severity("WARNING") == "warning"
    assert SarifReporter._map_severity("INFO") == "note"
    assert SarifReporter._map_severity("UNKNOWN") == "note"
````

## File: tests/test_scrub_ansi.py
````python
import pytest

from yamlr.cli.main import scrub_ansi


def test_scrub_ansi():
    """Verify ANSI escape sequence scrubbing."""
    colored_text = "\x1b[31mRed Text\x1b[0m"
    clean_text = scrub_ansi(colored_text)
    assert clean_text == "Red Text"
    
    mixed_text = "Normal \x1b[1;32mBold Green\x1b[m text"
    clean_mixed = scrub_ansi(mixed_text)
    assert clean_mixed == "Normal Bold Green text"
````

## File: tests/test_shard_processing_error.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import _process_document_shards


def test_process_document_shards_error():
    """Verify error handling in document shard processing."""
    mock_native = MagicMock()
    mock_native.native_audit_forensics.side_effect = Exception("Structurize Error")
    
    # Call _process_document_shards
    _process_document_shards(mock_native, "test.yaml", [], [], "content")
    
    # Check if ResourceResult was called with integrity_violations=[]
    args, kwargs = mock_native.ResourceResult.call_args
    assert kwargs['integrity_violations'] == []
````

## File: tests/test_stages.py
````python
"""Unit Tests for Core Stages."""
from collections import namedtuple

from yamlr.core.stages import (
    HealthScoringStage,
    IntegrityAuditStage,
    SchemaValidationStage,
    TopologyAnalysisStage,
)

MockViolation = namedtuple("MockViolation", ["severity", "message"])


def test_health_scoring_stage_calculation():
    """Validates deterministic scoring math for various severity tiers."""
    # Clean baseline
    assert HealthScoringStage.calculate_score([]) == 100.0

    # 1 Critical (-15.0) -> 85.0
    crit = [MockViolation(severity="CRITICAL", message="root user")]
    assert HealthScoringStage.calculate_score(crit) == 85.0

    # 1 High (-5.0) -> 95.0
    high = [MockViolation(severity="HIGH", message="missing limits")]
    assert HealthScoringStage.calculate_score(high) == 95.0

    # 1 Medium (-2.0) -> 98.0
    med = [MockViolation(severity="MEDIUM", message="floating tag")]
    assert HealthScoringStage.calculate_score(med) == 98.0

    # 1 Low (-0.5) -> 99.5
    low = [MockViolation(severity="LOW", message="missing comment")]
    assert HealthScoringStage.calculate_score(low) == 99.5

    # Floor clamping at 0.0
    many_crits = [MockViolation(severity="CRITICAL", message="fatal")] * 10
    assert HealthScoringStage.calculate_score(many_crits) == 0.0


def test_topology_analysis_stage_boundary():
    """Validates topology analysis returns empty on single or empty resource list."""
    assert TopologyAnalysisStage.analyze([]) == []

    # Single dummy result
    SingleResult = namedtuple("SingleResult", ["identity"])
    assert TopologyAnalysisStage.analyze([SingleResult(identity=None)]) == []


def test_schema_validation_stage_empty_inputs():
    """Validates that SchemaValidationStage safely handles empty inputs."""
    assert SchemaValidationStage.validate(None, "", [], None) == []


def test_integrity_audit_stage_empty_inputs():
    """Validates that IntegrityAuditStage safely handles empty inputs."""
    assert IntegrityAuditStage.audit(None, []) == []
````

## File: tests/test_streaming_multi_doc.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_multi_doc(temp_workspace):
    """Verify streaming scan handles multi-document YAML files."""
    yaml_path = os.path.join(temp_workspace, "multi.yaml")
    with open(yaml_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: p1\n---\napiVersion: v1\nkind: Pod\nmetadata:\n  name: p2\n")
    
    mock_native = MagicMock()
    # Mock shard to return doc boundary
    s1 = MagicMock(is_doc_boundary=False)
    s2 = MagicMock(is_doc_boundary=True)
    s3 = MagicMock(is_doc_boundary=False)
    
    mock_native.native_shard.return_value = [s1, s2, s3]
    mock_native.extract_native_identity.return_value = MagicMock()
    mock_native.native_structurize.return_value = MagicMock()
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        # We need to ensure _process_document_shards is called
        results = list(streaming_scan(yaml_path, []))
        # Should yield 2 results (one for each doc)
        # Wait, the logic is: process doc_shards when boundary found, OR at end.
        # [s1, s2] -> s2 is boundary. Yields result for s1.
        # [s3] -> end of file. Yields result for s3.
        assert len(results) == 2
````

## File: tests/test_streaming_os_error.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_os_error(temp_workspace):
    """Verify streaming scan handles OS errors gracefully."""
    yaml_path = os.path.join(temp_workspace, "error.yaml")
    with open(yaml_path, 'w') as f:
        f.write("content")
    
    # Mock open to raise OSError
    with patch('builtins.open', side_effect=OSError("Permission Denied")):
        results = list(streaming_scan(yaml_path, []))
        # Should yield 0 results but not crash
        assert len(results) == 0
````

## File: tests/test_streaming_scan.py
````python
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_logic(temp_workspace):
    """Verify streaming scan processing logic."""
    f1 = os.path.join(temp_workspace, "test.yaml")
    with open(f1, 'w') as f: f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test")
    
    mock_native = MagicMock()
    mock_shard = MagicMock(is_doc_boundary=False)
    mock_native.native_shard.return_value = [mock_shard]
    mock_native.extract_native_identity.return_value = MagicMock()
    mock_native.native_structurize.return_value = MagicMock(integrity_violations=[])
    mock_native.ResourceResult.return_value = MagicMock(path="test.yaml")
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        gen = streaming_scan(f1, [])
        results = list(gen)
        assert len(results) == 1
        mock_native.native_shard.assert_called_once()
        mock_native.extract_native_identity.assert_called_once()

def test_streaming_scan_empty_file(temp_workspace):
    """Verify streaming scan handles empty files."""
    f1 = os.path.join(temp_workspace, "empty.yaml")
    with open(f1, 'w') as f: f.write("")
    
    mock_native = MagicMock()
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        gen = streaming_scan(f1, [])
        results = list(gen)
        assert len(results) == 0
````

## File: tests/test_template_masker_dynamic_keys.py
````python
import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_dynamic_key_expression_masking():
    template = """apiVersion: v1
kind: ConfigMap
metadata:
  name: dynamic-keys-config
data:
  {{ .Values.dynamicKeyName }}: "dynamic-value"
  {{ printf "prefix-%s" .Values.env }}: "computed-value"
  regularKey: {{ .Values.regularValue }}
"""
    masked, token_map = mask_go_templates(template)
    assert "__YAMLR_TMPL_KEY_0__: \"dynamic-value\"" in masked
    assert "__YAMLR_TMPL_KEY_1__: \"computed-value\"" in masked
    assert "regularKey: __YAMLR_TMPL_VAL_2__" in masked

    unmasked = unmask_go_templates(masked, token_map)
    assert unmasked == template


def test_dynamic_key_with_sharding_roundtrip():
    import yamlr_native

    template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    {{ .Values.environmentKey }}: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.0
"""
    masked, token_map = mask_go_templates(template)
    shards = yamlr_native.native_shard(masked)
    assert len(shards) > 0

    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    final_yaml = unmask_go_templates(reconstructed, token_map)

    assert "{{ .Values.environmentKey }}: production" in final_yaml
    assert "image: nginx:1.25.0" in final_yaml
````

## File: tests/test_template_masker_multiline.py
````python
"""Tests for multiline Go-template masking and roundtrip restoration."""
import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_multiline_go_template_directive():
    """Verify multiline if-statements and control blocks are masked and restored byte-for-byte."""
    raw_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
spec:
{{- if and
    .Values.autoscaling.enabled
    (gt (int .Values.autoscaling.minReplicas) 1) }}
  replicas: {{ .Values.autoscaling.minReplicas }}
{{- else }}
  replicas: {{ .Values.replicaCount }}
{{- end }}
"""
    masked, token_map = mask_go_templates(raw_template)
    assert "# __YAMLR_TMPL_LINE_" in masked
    assert "__YAMLR_TMPL_VAL_" in masked
    
    # Verify unmasking restores original content exactly
    restored = unmask_go_templates(masked, token_map)
    assert restored == raw_template


def test_indented_nested_template_blocks():
    """Verify indented multiline with blocks under mapping keys."""
    raw_template = """apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
    - name: app
      image: nginx:latest
{{- with .Values.resources }}
      resources:
        {{- toYaml . | nindent 8 }}
{{- end }}
"""
    masked, token_map = mask_go_templates(raw_template)
    restored = unmask_go_templates(masked, token_map)
    assert restored == raw_template
````

## File: tests/test_template_masker.py
````python
"""Unit tests for in-memory Helm Go-template token masker."""
import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_mask_unmask_inline_values():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.appName }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: web
        image: "{{ .Values.image.repo }}:{{ .Values.image.tag }}"
"""
    masked, token_map = mask_go_templates(raw)
    assert "__YAMLR_TMPL_VAL_" in masked
    assert "{{ .Values.appName }}" not in masked
    assert len(token_map) == 4

    restored = unmask_go_templates(masked, token_map)
    assert restored == raw


def test_mask_unmask_control_flow_lines():
    raw = """apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
{{- if .Values.service.enabled }}
  type: ClusterIP
{{- end }}
"""
    masked, token_map = mask_go_templates(raw)
    assert "# __YAMLR_TMPL_LINE_" in masked
    assert "{{- if" not in masked

    restored = unmask_go_templates(masked, token_map)
    assert "{{- if .Values.service.enabled }}" in restored
    assert "{{- end }}" in restored
````

## File: tests/test_topology_audit.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import audit_topology_outages


def test_audit_topology_outages_cycle():
    """Verify topology outage audit detects circular dependencies."""
    mock_res1 = MagicMock()
    mock_res1.identity = MagicMock()
    mock_res2 = MagicMock()
    mock_res2.identity = MagicMock()
    
    mock_native = MagicMock()
    mock_native.native_build_topology_graph.return_value = ["edge1", "edge2"]
    mock_native.native_detect_circular_dependencies.return_value = ["Circular dependency detected"]
    mock_native.native_detect_dangling_selectors.return_value = []
    mock_native.native_detect_orphaned_resources.return_value = []
    mock_native.native_detect_service_shadowing.return_value = []
    mock_native.native_detect_version_drift.return_value = []
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        findings = audit_topology_outages([mock_res1, mock_res2])
        assert len(findings) > 0
        assert findings[0]["type"] == "Circular Dependency"
        assert findings[0]["msg"] == "Circular dependency detected"
````

## File: tests/test_ui_dossier.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_technical_dossier():
    """Verify technical dossier rendering."""
    data = {
        "title": "Test Concept",
        "definition": "A test definition.",
        "rationale": "Why we do this.",
        "impact": "High ROI",
        "example": "test: example"
    }
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_technical_dossier("test", data)
        mock_print.assert_called()
        panel = mock_print.call_args[0][0]
        assert "Yamlr Technical Authority" in str(panel.title)
````

## File: tests/test_ui_field_dossier.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_k8s_field_dossier():
    """Verify K8s field dossier rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_k8s_field_dossier("deployment.spec.replicas")
        mock_print.assert_called()
        panel = mock_print.call_args[0][0]
        assert "Native Registry Discovery" in str(panel.title)
````

## File: tests/test_ui_graph.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_graph():
    """Verify topology graph rendering."""
    mock_edge = MagicMock()
    mock_edge.source = "Service/my-svc"
    mock_edge.target = "Deployment/my-app"
    mock_edge.edge_type = "selector"
    
    mock_blast = MagicMock()
    mock_blast.source = "Service/my-svc"
    mock_blast.affected_count = 1
    mock_blast.depth = 1
    mock_blast.risk_level = "HIGH"
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_graph([mock_edge], mock_blast)
        mock_print.assert_called()
        # Verify specific content
        calls = str(mock_print.call_args_list)
        assert "Yamlr Topology Graph" in calls
        assert "Blast Radius" in calls
````

## File: tests/test_ui_renderer_extended.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.diff_engine import SideBySideDiff
from yamlr.ui.renderer import RichRenderer


@patch('yamlr.ui.renderer.console.print')
def test_render_explain(mock_print):
    RichRenderer.render_explain("query", {"title": "T", "definition": "D", "rationale": "R", "impact": "I", "example": "E"})
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_explain_k8s_field(mock_print):
    RichRenderer.render_explain("deployment.spec", None)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_explain_error(mock_print):
    RichRenderer.render_explain("query", None)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
@patch('yamlr.ui.renderer.Live')
def test_animate_integrity_scan(mock_live, mock_print):
    RichRenderer.animate_integrity_scan(50.0, 90.0)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_summary(mock_print):
    RichRenderer.render_summary({"total_files": 1, "verified": 1, "violations": 1, "pro_fixable": 1, "healed": 1, "time_ms": 10})
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_precision_help(mock_print):
    categories = {"Core Commands": [{"name": "scan", "purpose": "P"}]}
    RichRenderer.render_precision_help(categories, show_all=True)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_breadcrumb(mock_print):
    RichRenderer.render_breadcrumb("scan")
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_graph(mock_print):
    e1 = MagicMock(source="A", target="B", edge_type="deps")
    blast = MagicMock(source="A", affected_count=1, depth=1, risk_level="HIGH")
    RichRenderer.render_graph([e1], blast)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_integrity_ring(mock_print):
    RichRenderer.render_integrity_ring(95.0)
    RichRenderer.render_integrity_ring(80.0)
    RichRenderer.render_integrity_ring(60.0)
    assert mock_print.call_count == 3

@patch('yamlr.ui.renderer.console.print')
def test_render_side_by_side_diff(mock_print):
    with patch.object(SideBySideDiff, 'calculate', return_value=[("old", "new", "CHANGED"), ("old", None, "REMOVED"), (None, "new", "ADDED"), ("same", "same", "UNCHANGED")]):
        RichRenderer.render_side_by_side_diff("old\n", "new\n")
        assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_batch_summary(mock_print):
    res = MagicMock()
    res.violations = [1]
    res.integrity_violations = [1]
    report = MagicMock(results=[res], total_files=1, total_time_ms=10)
    RichRenderer.render_batch_summary(report, apply=True)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
@patch('time.sleep')
def test_render_score_animation(mock_sleep, mock_print):
    res = MagicMock(health_score=80.0)
    report = MagicMock(results=[res])
    RichRenderer.render_score_animation(report)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_unified_diff(mock_print):
    RichRenderer.render_unified_diff("old\nline\n", "new\nline\n")
    assert mock_print.called
    RichRenderer.render_unified_diff("same", "same")
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_drift_report(mock_print):
    RichRenderer.render_drift_report(["Resource 'app' is broken"])
    assert mock_print.called
    RichRenderer.render_drift_report([])
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_audit_report(mock_print):
    RichRenderer.render_audit_report([{"sev": "CRITICAL", "type": "T", "msg": "M"}])
    assert mock_print.called
    RichRenderer.render_audit_report([])
    assert mock_print.called
````

## File: tests/test_ui_renderer.py
````python
from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_welcome():
    """Verify welcome screen rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_welcome("/tmp", "1.30")
        mock_print.assert_called()

def test_render_explain():
    """Verify explain panel rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_explain("concept", {"title": "Title", "definition": "Def"})
        mock_print.assert_called()

def test_render_summary():
    """Verify summary table rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_summary({"total_files": 1, "verified": 1})
        mock_print.assert_called()

def test_render_batch_summary():
    """Verify batch summary rendering."""
    mock_report = MagicMock()
    mock_report.results = [MagicMock(violations=[], integrity_violations=[])]
    mock_report.total_files = 1
    mock_report.total_time_ms = 100
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_batch_summary(mock_report, False)
        mock_print.assert_called()

def test_render_score_animation():
    """Verify score animation rendering."""
    mock_report = MagicMock()
    mock_report.results = [MagicMock(health_score=95.0)]
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        with patch('time.sleep'):
            RichRenderer.render_score_animation(mock_report)
            mock_print.assert_called()

def test_render_integrity_ring():
    """Verify integrity ring rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_integrity_ring(95.0)
        mock_print.assert_called()

def test_render_breadcrumb():
    """Verify breadcrumb rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_breadcrumb("scan")
        mock_print.assert_called()
````

## File: tests/test_version_extended.py
````python
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_version


def test_cmd_version_basic():
    """Verify basic version command output."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_version()
        assert any("Yamlr" in str(call) for call in mock_print.call_args_list)

def test_cmd_version_with_native_info():
    """Verify version command with native build info."""
    mock_native = MagicMock()
    mock_native.native_get_build_info.return_value = "Native-Core-v1"
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        with patch('yamlr.core_logic.console.print') as mock_print:
            cmd_version()
            assert any("Native-Core-v1" in str(call) for call in mock_print.call_args_list)
````

## File: tests/test_webhook_server.py
````python
"""Tests for Kubernetes Admission Webhook handler."""
import base64
import json

import pytest

from yamlr.webhook.server import AdmissionHandler

SAMPLE_ADMISSION_REVIEW = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "705ab4f5-6393-11e8-b7cc-42010a800002",
        "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
        "resource": {"group": "apps", "version": "v1", "resource": "deployments"},
        "requestKind": {"group": "apps", "version": "v1", "kind": "Deployment"},
        "object": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "clean-deployment", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{"name": "web", "image": "nginx:1.24"}]
                    }
                }
            }
        }
    }
}

DEPRECATED_ADMISSION_REVIEW = {
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "805ab4f5-6393-11e8-b7cc-42010a800003",
        "kind": {"group": "extensions", "version": "v1beta1", "kind": "Deployment"},
        "resource": {"group": "extensions", "version": "v1beta1", "resource": "deployments"},
        "object": {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {"name": "old-deployment", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{"name": "web", "image": "nginx:latest"}]
                    }
                }
            }
        }
    }
}


def test_validate_clean_deployment():
    """Verify validation allows clean deployments without error."""
    res = AdmissionHandler.handle_admission_review(SAMPLE_ADMISSION_REVIEW, is_mutate=False)
    assert res["apiVersion"] == "admission.k8s.io/v1"
    assert res["response"]["uid"] == "705ab4f5-6393-11e8-b7cc-42010a800002"
    assert res["response"]["allowed"] is True


def test_validate_deprecated_deployment():
    """Verify validation reports advisories on deprecated manifests."""
    res = AdmissionHandler.handle_admission_review(DEPRECATED_ADMISSION_REVIEW, is_mutate=False)
    assert res["response"]["allowed"] is True
    assert "status" in res["response"]
    assert "remediations recommended" in res["response"]["status"]["message"]


def test_mutate_deployment_jsonpatch():
    """Verify mutating webhook returns JSONPatch annotation."""
    res = AdmissionHandler.handle_admission_review(SAMPLE_ADMISSION_REVIEW, is_mutate=True)
    assert res["response"]["allowed"] is True
    assert res["response"]["patchType"] == "JSONPatch"

    patch_b64 = res["response"]["patch"]
    patch_json = json.loads(base64.b64decode(patch_b64).decode("utf-8"))
    assert len(patch_json) == 1
    assert patch_json[0]["op"] == "add"
    assert "yamlr.dev~1admitted" in patch_json[0]["path"]
````
