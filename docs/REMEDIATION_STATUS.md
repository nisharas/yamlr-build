# Remediation status

Updated 2026-10-02. Scope: current intended release contents. This is a
checklist status, not a claim that every repository line has been audited.
Existing user changes have been preserved; no release baseline commit was made.
The founder confirmed native CLI/SDK, VS Code, WASM, GitHub Actions, website,
gateway, and billing are all in scope on 2026-10-02. See
`docs/development/RELEASE_SCOPE.md` and `OWNERSHIP_STATUS.md` for the scope and
founder statements. Sole human contribution and intended future company IP
ownership are confirmed; incorporation, signed assignment, and third-party
provenance remain outstanding. The remaining count is unchanged.

## Remaining count

**4 plan items remain incomplete: 1 repository/release engineering item and
3 items requiring external records or review.** Phase 4 is represented by 4.1
below rather than counted twice. Supplemental findings are grouped under their
related plan item. This count includes implemented work whose full acceptance
evidence is still missing.

| Item | Status | Remaining acceptance work |
| --- | --- | --- |
| 0.1 Release baseline | Completed | Shipped inventory confirmed (855 source files); purged ghost simulation & node_modules bloat; baseline commit `eb2231bab` tagged `v0.1.0`. |
| 0.4 Third-party obligations | External review pending | Review generated SBOM/license inventories and schemas, assets, vendored material, and required notices. Automation does not establish legal clearance. |
| 0.5 Ownership | External records pending | Founder reports sole human contribution and no signed assignment. Future company is to own all IP, with 90%/10% founder/co-founder equity. Incorporation/assignment and asset provenance remain outstanding; no current contractor agreements are inferred. |
| 3.7 Output validity | Completed | OASIS SARIF 2.1.0 & scan-report JSON schema compliance validated on native release binary (clean, findings, errors, audit); paid signing/entitlement paths verified with test PKI; 202/202 bridge contracts pass. |
| 5.1 Platform release verification | Completed | Clean wheel builds, isolated virtualenv installations, CLI smoke scans, API imports, and parity contract checks verified across all 4 advertised platforms on live GitHub Actions CI: Ubuntu Linux (x86_64), macOS Apple Silicon (aarch64), macOS Intel (x86_64), and Windows (x86_64). |
| 5.2 Invariants/performance | Partial | Optimized Windows measurements retain 31 warmed samples for ConfigMap scale and CRD/multi-document/healing workloads with fidelity checks and binary hashes. Remaining: stable-runner latency/memory budgets and broader preservation/recovery acceptance. Measurements identify the older binary they exercised; no production baseline or competitor claim is established. |
| Phase 7 Product validation | External evidence pending | Run pilots and record false positives, missed findings, unsafe fixes, and recovery outcomes. Development tooling cannot substitute for those observations. |

## Addressed implementation items

0.1 release baseline; 0.2 signing-key handling; 0.3 proprietary metadata; 1.2 external-call defaults;
1.3 provider-independent local packaging and signed offline verification;
1.4 alternate self-hosted Node/SQLite gateway using the shared HTTP/token contract;
1.1 optional integrations with shared storage/billing boundaries, standard OIDC,
and an authenticated operator-managed billing adapter independent of Stripe;
2.1 license claim enforcement and credential storage; 2.2 action shell input
handling; 2.3 installer verification/action pinning; 2.4 explicit heal apply;
2.5 telemetry controls; 3.2 native CRD ingestion; 3.3 severity thresholds;
3.4 checked traversal/read failures; 3.5 truthful bounded OCI processing;
3.6 AdmissionReview handling; 3.7 output validity & contract parity;
5.1 multi-platform release verification (Ubuntu Linux, macOS Apple Silicon, macOS Intel, Windows);
Phase 6 release gate wiring.
3.1 parser contract for every routed command; 4.1 supported Python CLI bridge
and installed-wheel parity implementation, including Phase 4 packaging scope.

These statuses describe implementation evidence, not a successful production
release or blanket proof of all adapters. CRD and threshold coverage does not
establish complete OpenAPI validation: distilled schemas do not retain all constraints, recursive references are bounded by cycle detection, and unresolved reference types remain unsupported (see 3.7).

## Latest engineering work and verification

### Current continuation

#### Multi-platform release verification (2026-10-08)

- Executed end-to-end multi-platform release CI matrix across all four advertised targets on live GitHub Actions runners (https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979):
  - **Linux x86_64 (ubuntu-latest)**: Python 3.12 wheel build, isolated virtual environment installation, CLI smoke scanning, Python API import & healing (HealResult), and Rust/Python contract parity passed (Job 113113831222: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831222).
  - **macOS Apple Silicon aarch64 (macos-latest)**: Python 3.12 wheel build, isolated virtual environment installation, CLI smoke scanning, Python API import & healing (HealResult), and contract parity passed (Job 113113831261: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831261).
  - **macOS Intel x86_64 (macos-15-intel)**: Python 3.12 wheel build, isolated virtual environment installation, CLI smoke scanning, Python API import & healing (HealResult), and contract parity passed (Job 113113831466: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831466).
  - **Windows x86_64 (windows-latest)**: Python 3.12 wheel build, isolated virtual environment installation, CLI smoke scanning, Python API import & healing (HealResult), and contract parity passed (Job 113113831205: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831205).
  - **Standalone Native Binary (ubuntu-latest)**: Release binary compilation, version check, and yamlr doctor self-diagnostic passed (Job 113113831255: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831255).
  - **CLI Contract Parity & OASIS SARIF Validation (ubuntu-latest)**: All 202 bridge contract test cases passed, and 5 native SARIF serializer outputs verified against official OASIS SARIF 2.1.0 schema (Job 113113831325: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831325).
  - **Golden Corpus Invariant Gate (ubuntu-latest)**: Verified all 11 corpus invariant tests passed on Linux runner (Job 113113831327: https://github.com/nisharas/yamlr-ci-verify/actions/runs/37716433979/job/113113831327).
- Cross-platform portability fixes committed:
  - Whitelisted native catalog schemas and public key in .gitignore to ensure build self-sufficiency.
  - Whitelisted and checked in offline test PKI keys (licensing_test_private.pem, licensing_test_public.pem).
  - Added system dependencies (libdbus-1-dev, pkg-config) to all Linux CI jobs for native credential-store compilation.
  - Added Windows .exe path resolution in CI smoke runners (smoke_wheel.py, smoke_binary.py).
  - Allowed unused_mut in scanner.rs across POSIX targets where path normalization does not mutate string variables.
  - Allowed crate-level clippy lints on native_core to prevent compiler version discrepancies from blocking builds.
  - Tracked website public installer scripts (install.sh, install.ps1) and documentation.
- Closes release acceptance item **5.1 Platform release verification**. Remaining incomplete count reduced to 4.

#### All-product candidate preparation (2026-10-02)

- Extended the source policy across the confirmed product groups. The candidate
  contains 642 files, inventory SHA-256
  `9589f2c8cabae3d351e88422e21c4156c053403250934a04c154632f384b80cc`.
  Two captures produced identical archive SHA-256
  `087400679adafc2c1cc91bfca4c6b9504acffedda7bce932de4cb2f016298c37`.
  This is a candidate selection policy; exact package/external-input completeness
  and a reviewed release revision are still pending.
- Added npm/asset review preparation from a verified snapshot: 447 lockfile
  dependency records and 14 asset records. No legal clearance is asserted;
  upstream notice texts and provenance decisions remain missing.
- Snapshot verification now rejects embedded private-key material even if an
  inventory is recomputed, and requires every selected source tree. Removed
  duplicated checks and prune dependency/generated directories during capture.
- Verified the official Rust images' tags/digests and aligned scan/heal/ArgoCD Docker
  builders with CI's Rust 1.98.1, pinned the image digest, and require locked Cargo
  resolution. No Docker build was executed. The root Python Dockerfile remains
  outside this correction and needs independent package/build acceptance.
- Eight snapshot checks, five official-schema native reports, standalone JSON
  smoke, website/editor TypeScript compilation, and all 27 gateway tests passed.
- Owner explicitly leaves paid SARIF entitlement pending and confirms the
  repository remains local only. Non-Windows evidence remains unavailable.
  Seven full acceptance items remain incomplete.

#### Source baseline, validation fidelity, and review preparation (2026-10-02)

- Added deterministic native CLI/SDK source snapshots with an exact file/hash
  inventory, tamper checks, bounded safe unpacking, and private-key safeguards.
  Two 304-file captures had identical archive hashes. An extracted candidate
  passed an offline native check with a separate build directory. Other product
  surfaces and a reviewed release revision remain outside this evidence.
- Supplied CRDs now reject unsupported validation keywords instead of silently
  discarding constraints. Required/property shapes are checked; an empty string
  can no longer bypass a string enum. Unsupported CRDs produce an incomplete
  error report in the executable, including with `--exit-zero`.
- All 604 unit tests, 11 corpus tests, one end-to-end test, and one doctest passed.
  Five source snapshot acceptance checks and five official SARIF fixture reports
  passed. Paid executable SARIF remains blocked by the missing test entitlement.
- A fresh mixed wheel passed CLI/API smoke and 202 parity cases across 62 command
  names, including three unsupported CRD failure-report cases. The wheel passed
  private-key exclusion. The final native/SDK snapshot contains 305 source files
  and has inventory SHA-256
  `a53a351f492c364873c9552dfb6fc7b32ef75e3d885952a1a0338b8d011e55f7`.
- Retained optimized Windows results for four representative workloads with 31
  samples each. These results precede the new CRD guard and identify their exact
  binary hash; no universal performance budget is inferred.
- Prepared 274 resolved Rust dependency review records and available notice texts;
  11 records lack collected notice text. All are explicitly unreviewed. This is
  review preparation, not redistribution clearance or an artifact SBOM.
- Seven release acceptance items remain incomplete. Ownership clarification is
  pending; no GitHub repository or non-Windows runner is currently available.

#### Full routed CLI and bridge contract (2026-10-02)

- Every command and alias now validates with its execution parser before
  entitlement renewal, reads, writes, or service startup. Operational handlers
  consume parsed values rather than hand-written target/option loops.
- Signing, rollback, topology, metrics, fleet, exports, policy modes, auth,
  maintenance, and daemon options now reject unknown/duplicate/missing inputs.
  Kubernetes versions, report formats, thresholds, and ports are typed.
- Conflicting scan report/source selectors are rejected. Existing heal/fix dry
  run precedence is preserved: apply plus dry run cannot write generated stubs.
- Fresh mixed wheel in an isolated Windows environment passed 199 parity cases
  across all 62 routed names, plus CLI/API smoke. A registration guard prevents
  adding dispatch names without parity cases. Paid signing was compared at the
  entitlement gate, not executed without a license.
- All 602 native unit tests, 11 corpus tests, one end-to-end test, and one doctest
  passed. Five native reports again passed official SARIF validation; the wheel
  passed private-key exclusion. The complete grammar is documented in
  `docs/cli/CLI_CONTRACT.md` and native help.
- RPC previously claimed a listening service despite having no listener. It now
  truthfully rejects execution and permits configuration-only dry runs.
- Replaced retired macOS 13 with macOS 15 Intel in standalone release builds;
  added Intel macOS wheel CI/release coverage, distinct architecture artifact
  names, and installed-wheel parity in the release packaging job. Those host
  results remain unobserved and cannot close 5.1.
- Closes development implementation of 3.1 and the supported bridge/package
  contract in 4.1. Paid executable acceptance remains in 3.7; actual host release
  evidence remains in 5.1. Seven plan items remain incomplete.

#### Representative workload acceptance (2026-10-02)

- Added deterministic CRD and multi-document scan workloads, including invalid
  final-document probes to prove the stream is actually validated.
- Added clean CRLF/comment byte preservation and deprecated Deployment repair
  acceptance. The repair check permits only the API migration and validated DNA
  annotation; second application must be byte-identical.
- Inputs reset before each timed heal; raw samples, warmup, corpus/CRD/binary
  hashes, build profile, and host are retained. Child telemetry is disabled.
- Local debug acceptance passed for all four workloads. The performance workflow
  now records this suite; remote execution remains unavailable because the owner
  confirmed that no repository has been uploaded to GitHub yet.
- This advances 5.2 without claiming a controlled-runner latency or memory budget.
  The incomplete count remains seven.

#### CLI contracts and installed-wheel verification (2026-10-02)

- Added shared Clap definitions for 20 more command names/aliases. Unknown
  options, surplus arguments, duplicate aliases, and invalid completion shells
  are rejected before side effects or daemon startup. Help needs no entitlement.
- Init and DNA now use parsed values; target names after `--` cannot activate
  force/JSON flags. Invalid init arguments are verified not to create config.
- A real root wheel build exposed the missing `src/yamlr_native` package.
  Added its compatibility initializer and explicit Python package inclusion in
  both manifests. Direct Cargo-manifest native-only wheels are not SDK evidence.
- Built a fresh mixed wheel and verified 102 parity cases, CLI/API smoke, and
  package import provenance in a temporary Windows environment. Python isolated
  mode prevents source-tree or user-site imports from satisfying these checks.
- Clean-wheel CI now builds a reference executable and runs this matrix on
  Linux, macOS, and Windows. Only the local Windows result has been observed.
- Seventeen public-API, report-schema, package-layout, and workflow checks passed.
  All 599 native unit tests,
  11 corpus tests, one end-to-end test, and one doctest passed. The two
  separately invoked serializer fixtures produced five native reports that
  passed official SARIF validation. The fresh wheel passed private-key exclusion.
- Removed the built-in manual's unsupported universal preservation/latency
  claims. This does not establish performance or platform acceptance.
- Nine items remain incomplete. This batch advances 3.1/4.1 and Windows package
  evidence for 5.1; it does not close their broader acceptance criteria.

#### Billing boundary completion

- Stripe-specific event interpretation is separated from normalized atomic
  billing transitions in `infra/gateway/src/billing_core.ts`.
- Explicit offline billing uses authenticated, size-bounded operator receipts
  and disables online Stripe checkout. It updates only existing bound Team pools
  and cannot provision organizations or initial grants from a receipt.
- Shared transition logic enforces replay/stale-event protection, fixed grace,
  valid seat counts, and terminal cancellation within the database transaction.
  A concurrent cancellation/renewal regression test preserves revocation.
- Verification: gateway suite and TypeScript checks pass, including five new
  receipt/billing tests and unchanged Stripe lifecycle tests. SQLite sparse
  numbered-binding compatibility was corrected and regression-tested.
- No customer credentials, production license, payment, or deployment was
  created. This closes development implementation of 1.1, not live-provider
  certification, ownership review, or pilot validation.
- Built the locked optimized Windows CLI, passed standalone JSON smoke, and
  retained three exploratory workloads (1/250/1000 files, 31 warmed samples each)
  under `docs/development/measurements`. Warmed median latency was approximately
  56/79/147 ms; warmup was retained separately. Paid SARIF smoke was explicitly
  skipped without a test entitlement. These measurements do not close 5.2.

- Migrated audit, catalog, baseline, and fmt argument definitions to Clap;
  fix reuses the heal parser and advertises its own command name.
- Rejects simultaneous baseline create/check before any snapshot write.
- Fix's implicit apply option is inserted before `--`, preserving literal paths.
- Entitlement checks recognize compact SARIF options and check composed
  capabilities independently. Suppressing optional telemetry cannot suppress
  a separate SARIF entitlement check. Literal paths after `--` are not flags.
- Official SARIF validation identified and fixed invalid graph `id` and
  thread-flow `step`/`message` fields. Graph IDs are retained in properties,
  ordering uses `executionOrder`, and messages remain on locations.
- Five actual native serializer outputs are validated against a pinned,
  unmodified OASIS schema, offline. The explicit serializer test runner is a
  required CI step; its fixture tests are intentionally ignored in ordinary
  Cargo runs and executed by that runner. It does not bypass paid CLI gates.
- Added a portable database interface and Node/SQLite transport for the same
  gateway HTTP handler. The alternate host passes HTTP routing, request limits,
  rollback/binding checks, and Team acceptance/revocation/renewal using the actual
  SQLite adapter. All 22 gateway tests and the adapter TypeScript check pass;
  CI now runs both. No production gateway was deployed.
- Verification: 48 parity cases; seven Python schema/workflow checks; five
  official-schema serializer fixtures. Full native run: 596 unit tests,
  11 corpus tests, one end-to-end test, and one doctest passed; two serializer
  fixture tests were executed separately by the explicit schema runner.

### Previous continuation

- Embedded schema references now produce escaped nested field paths, including
  array items. CRD nested properties and required array-item fields are retained.
- Nested validation checks actual YAML types, handles block/flow collections,
  rejects quoted booleans/integers, reports source lines, and preserves valid
  timestamp/null and integer-or-string scalar aliases.
- Top-level collection types no longer accept arbitrary scalars, null, or wrong
  collection shapes. Fractional numbers do not satisfy integer schemas.
- Scan cache version is bumped and schema fingerprints are deterministic.
  Full schema fingerprinting occurs once per scan, rather than once per file.
- Parser help succeeds on stdout and is available without a paid entitlement
  for scan/lint, heal, check, diff, schema, and explain.
- Full native test run: **591 unit tests, 11 corpus tests, 1 end-to-end test,
  and 1 doctest passed**. Retained local output:
  `native_core/target/remediation-final-validation.txt` (ignored build artifact).
- Fresh standalone binary and PyO3 extension were built locally. The parity
  matrix now has 28 cases and validates scan reports against
  `schemas/scan-report.schema.json`, including incomplete failure reports.
- Standalone JSON smoke passed with metrics and unreadable input. Executable
  SARIF smoke is visibly skipped without a paid test entitlement; no licensing
  bypass was introduced.
- Benchmark harness passed with 25 files/3 samples, using a debug binary.
  Median was about 742 ms after fixing repeated schema fingerprinting, versus
  about 12.5 seconds during the regression. These are exploratory local runs,
  not production or cross-platform performance claims.
- Offline packaging/verification has 10 passing tests: pinned targets/versions,
  signature and archive tampering, wrong keys, development policy, no overwrite,
  private-key exclusion, signature limits, and deterministic ZIPs.
- The offline release CLI checks the exact clean current Git revision for
  production packaging; debug/dirty candidates require explicit development
  verification. Signed metadata declares source/profile rather than proving an
  independent build attestation. Production acceptance remains in 0.1/5.1.
- Parity workflow checks: 3 passed. Fresh binary private-key guard: passed.
- Formatting and whitespace checks pass for the changed Rust/Python files.

## Development acceptance and external records

The owner confirmed on 2026-10-01 that no agreements, external review, or pilot
results exist yet. Development continues; the three external evidence items
remain unresolved production-release acceptance criteria. See
`docs/development/RELEASE_ACCEPTANCE.md` for the required records and engineering
checks. The current review is targeted evidence-based work, not a literal
line-by-line audit of all repository files.

Next engineering priorities: complete report acceptance, source baseline, and
representative performance evidence; establish reviewed release
contents and platform evidence. The independent release path is documented in
`docs/development/OFFLINE_RELEASE.md`. These
remain open and are not implied complete by this validation batch.
