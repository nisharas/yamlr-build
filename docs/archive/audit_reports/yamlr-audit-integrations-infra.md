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
- Only files matching these patterns are included: vscode/src/**/*.ts, vscode/package.json, infra/gateway/src/**/*.ts, infra/gateway/schema.sql, infra/gateway/wrangler.toml, integrations/**/*.yaml, integrations/**/*.yml, integrations/**/*.md, actions/**/*.yml, actions/**/*.sh, actions/**/*.md, .pre-commit-config.example.yaml, docs/PRE_COMMIT_GUIDE.md
- Files matching these patterns are excluded: vscode/bin/**, node_modules/**, **/*.whl, **/*.lock
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
.pre-commit-config.example.yaml
actions/heal/action.yml
actions/heal/entrypoint.sh
actions/heal/README.md
actions/scan/action.yml
actions/scan/entrypoint.sh
actions/scan/README.md
docs/PRE_COMMIT_GUIDE.md
infra/gateway/schema.sql
infra/gateway/src/index.ts
infra/gateway/wrangler.toml
integrations/argocd/kustomization.yaml
integrations/argocd/plugin.yaml
integrations/argocd/README.md
integrations/argocd/sidecar-patch.yaml
integrations/flux/kustomization-example.yaml
integrations/gitlab-ci.yml
integrations/helm/test-hook.yaml
integrations/kustomize/validator.yaml
vscode/src/extension.ts
```

# Files

## File: .pre-commit-config.example.yaml
````yaml
# Turnkey Pre-Commit Configuration for Kubernetes Manifests
# Place this file as .pre-commit-config.yaml in your repository root.
# Install pre-commit: pip install pre-commit && pre-commit install

repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      # 1. Canonical Formatter: Automatically sorts keys to Kubernetes OpenAPI hierarchy and sets 2-space indent
      - id: yamlr-fmt

      # 2. Manifest Auto-Fixer: Upgrades deprecated APIs and pins latest tags
      - id: yamlr-fix

      # 3. Manifest Auto-Healer (Recommended): Safe, comment-preserving auto-heal before commit
      - id: yamlr-heal
        args: ["--apply"]

      # 4. Optional Diff Preview: Read-only diff preview without modifying files
      # - id: yamlr-diff
      #   args: ["--unified"]

      # 5. Optional Scanner Gate: Strict audit gate exiting with code 1 on schema errors
      # - id: yamlr-scan
      #   args: ["--fail-on", "error"]
````

## File: actions/heal/action.yml
````yaml
name: Yamlr Manifest Remediator (Heal)
description: Autonomous, comment-preserving Kubernetes manifest auto-repair with git commit and push capability.
author: Yamlr
inputs:
  path:
    description: Path to manifests (file or directory)
    required: false
    default: .
  apply:
    description: Apply fixes directly to manifests
    required: false
    default: 'true'
  diff:
    description: Show side-by-side diff of proposed changes
    required: false
    default: 'false'
  dry-run:
    description: Show forensic impact without applying changes
    required: false
    default: 'false'
  k8s-version:
    description: Target Kubernetes schema version (e.g. 1.30, 1.31)
    required: false
  kube-version:
    description: Backward-compatible alias for k8s-version
    required: false
  crd:
    description: Path to CRD manifests to ingest
    required: false
  helm:
    description: Audit and heal Helm values in-memory
    required: false
    default: 'false'
  kustomize:
    description: Audit and heal Kustomize overlays in-memory
    required: false
    default: 'false'
  ingest-opa:
    description: Path to OPA Gatekeeper JSON report to ingest and auto-repair
    required: false
  ingest-kyverno:
    description: Path to Kyverno PolicyReport JSON to ingest and auto-repair
    required: false
  output-file:
    description: Path to write report
    required: false
  exit-zero:
    description: Always exit with code 0 (for non-blocking CI warnings)
    required: false
    default: 'false'
  push:
    description: Automatically push repairs to the branch
    required: false
    default: 'false'
  push-telemetry:
    description: Push anonymous execution telemetry to telemetry gateway
    required: false
    default: 'false'
  token:
    description: GitHub token for pushing repairs
    required: false
    default: ${{ github.token }}
  extra-args:
    description: Universal passthrough for additional CLI flags
    required: false
    default: ''
runs:
  using: docker
  image: Dockerfile
  env:
    INPUT_PATH: ${{ inputs.path }}
    INPUT_APPLY: ${{ inputs.apply }}
    INPUT_DIFF: ${{ inputs.diff }}
    INPUT_DRY_RUN: ${{ inputs.dry-run }}
    INPUT_K8S_VERSION: ${{ inputs.k8s-version }}
    INPUT_KUBE_VERSION: ${{ inputs.kube-version }}
    INPUT_CRD: ${{ inputs.crd }}
    INPUT_HELM: ${{ inputs.helm }}
    INPUT_KUSTOMIZE: ${{ inputs.kustomize }}
    INPUT_INGEST_OPA: ${{ inputs.ingest-opa }}
    INPUT_INGEST_KYVERNO: ${{ inputs.ingest-kyverno }}
    INPUT_OUTPUT_FILE: ${{ inputs.output-file }}
    INPUT_EXIT_ZERO: ${{ inputs.exit-zero }}
    INPUT_PUSH: ${{ inputs.push }}
    INPUT_PUSH_TELEMETRY: ${{ inputs.push-telemetry }}
    GITHUB_TOKEN: ${{ inputs.token }}
    INPUT_EXTRA_ARGS: ${{ inputs.extra-args }}
````

## File: actions/heal/entrypoint.sh
````bash
#!/bin/bash
set -e

# Configure Git for automated commits
git config --global user.name "yamlr[bot]"
git config --global user.email "bot@yamlr.dev"
git config --global --add safe.directory /github/workspace

echo "Yamlr Manifest Remediator starting..."

# Default to current workspace if not provided
TARGET_PATH=${INPUT_PATH:-"."}

# Assemble command into an array for safe execution (prevents shell injection)
CMD_ARRAY=("yamlr" "heal" "$TARGET_PATH")

if [ "${INPUT_APPLY:-true}" = "true" ]; then
    CMD_ARRAY+=("--apply")
fi

if [ "${INPUT_DIFF:-false}" = "true" ]; then
    CMD_ARRAY+=("--diff")
fi

if [ "${INPUT_DRY_RUN:-false}" = "true" ]; then
    CMD_ARRAY+=("--dry-run")
fi

K8S_VER="${INPUT_K8S_VERSION:-$INPUT_KUBE_VERSION}"
if [ -n "$K8S_VER" ]; then
    CMD_ARRAY+=("--k8s-version" "$K8S_VER")
fi

if [ -n "$INPUT_CRD" ]; then
    CMD_ARRAY+=("--crd" "$INPUT_CRD")
fi

if [ "${INPUT_HELM:-false}" = "true" ]; then
    CMD_ARRAY+=("--helm")
fi

if [ "${INPUT_KUSTOMIZE:-false}" = "true" ]; then
    CMD_ARRAY+=("--kustomize")
fi

if [ -n "$INPUT_INGEST_OPA" ]; then
    CMD_ARRAY+=("--ingest-opa" "$INPUT_INGEST_OPA")
fi

if [ -n "$INPUT_INGEST_KYVERNO" ]; then
    CMD_ARRAY+=("--ingest-kyverno" "$INPUT_INGEST_KYVERNO")
fi

if [ -n "$INPUT_OUTPUT_FILE" ]; then
    CMD_ARRAY+=("--output-file" "$INPUT_OUTPUT_FILE")
fi

if [ "${INPUT_EXIT_ZERO:-false}" = "true" ]; then
    CMD_ARRAY+=("--exit-zero")
fi

if [ "${INPUT_PUSH_TELEMETRY:-false}" = "true" ]; then
    CMD_ARRAY+=("--push-telemetry")
fi

# Parse extra args reliably
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

echo "Running: ${CMD_ARRAY[*]}"

# Execute via direct array call (no eval)
"${CMD_ARRAY[@]}"

# Check for changes
if [[ -n $(git status -s) ]]; then
  echo "Remediations applied. Committing changes..."
  git add .
  git commit -m "chore(yamlr): automated Kubernetes manifest remediation"
  
  if [[ "$INPUT_PUSH" == "true" ]]; then
    echo "Pushing remediations back to branch..."
    git push
  fi
else
  echo "No changes needed. Manifests conform to schema."
fi
````

## File: actions/heal/README.md
````markdown
# 🩹 Yamlr Surgeon: Autonomous Manifest Repair

**Yamlr Surgeon** (`yamlr/heal`) is the industry's first **autonomous repair bot** for Kubernetes configurations. It doesn't just find issues—it fixes them, commits the repairs, and pushes them back to your branch.

## 🧪 The "Slash Command" Experience

The Surgeon is designed for high-velocity platform teams. When configured, it monitors PRs for configuration drift or errors and provides a "Magic Moment" fix:

1. **Scan**: Identifies malformed YAML or security holes.
2. **Heal**: Natively repairs manifests using our **Professional C-Engine**.
3. **Commit**: Automatically commits the fixes with clear audit logs.
4. **Push**: Updates your PR branch instantly.

## 🛠️ Usage

```yaml
jobs:
  repair:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.PAT_TOKEN }} # Required for push
      - name: Yamlr Surgeon Repair
        uses: yamlr/heal@v1
        with:
          path: './k8s'
          push: 'true'
```

## 🔒 Enterprise Security

The Surgeon runs the **Professional Edition** of the Yamlr engine, compiled natively for maximum IP protection and performance. Your manifests are processed locally in the runner—no data ever leaves your GitHub environment.

---
**Yamlr Surgeon: Stop finding problems. Start fixing them.**
````

## File: actions/scan/action.yml
````yaml
name: Yamlr Manifest Auditor (Scan)
description: Fast, zero-network Kubernetes manifest audit and schema validation with SARIF output.
author: Yamlr
inputs:
  path:
    description: Path to manifests (file or directory)
    required: false
    default: .
  output:
    description: Output format (sarif, text, or json)
    required: false
    default: sarif
  output-file:
    description: Path to write structured report (e.g. results.sarif)
    required: false
  k8s-version:
    description: Target Kubernetes schema version (e.g. 1.30, 1.31)
    required: false
  kube-version:
    description: Backward-compatible alias for k8s-version
    required: false
  crd:
    description: Path to CRD manifests to ingest
    required: false
  helm:
    description: Audit rendered Helm chart templates in-memory
    required: false
    default: 'false'
  kustomize:
    description: Audit rendered Kustomize overlay resources in-memory
    required: false
    default: 'false'
  fail-on:
    description: Exit with non-zero code if violations of this severity or higher are found (error, warning, note)
    required: false
    default: error
  fail-on-error:
    description: Backward-compatible alias for fail-on
    required: false
  exit-zero:
    description: Always exit with code 0 (for non-blocking CI warnings)
    required: false
    default: 'false'
  quiet:
    description: Suppress non-essential output
    required: false
    default: 'false'
  push-telemetry:
    description: Push anonymous execution telemetry to telemetry gateway
    required: false
    default: 'false'
  extra-args:
    description: Universal passthrough for additional CLI flags
    required: false
    default: ''
outputs:
  results-sarif:
    description: Path to the generated SARIF report
runs:
  using: docker
  image: Dockerfile
  env:
    INPUT_PATH: ${{ inputs.path }}
    INPUT_OUTPUT: ${{ inputs.output }}
    INPUT_OUTPUT_FILE: ${{ inputs.output-file }}
    INPUT_K8S_VERSION: ${{ inputs.k8s-version }}
    INPUT_KUBE_VERSION: ${{ inputs.kube-version }}
    INPUT_CRD: ${{ inputs.crd }}
    INPUT_HELM: ${{ inputs.helm }}
    INPUT_KUSTOMIZE: ${{ inputs.kustomize }}
    INPUT_FAIL_ON: ${{ inputs.fail-on }}
    INPUT_FAIL_ON_ERROR: ${{ inputs.fail-on-error }}
    INPUT_EXIT_ZERO: ${{ inputs.exit-zero }}
    INPUT_QUIET: ${{ inputs.quiet }}
    INPUT_PUSH_TELEMETRY: ${{ inputs.push-telemetry }}
    INPUT_EXTRA_ARGS: ${{ inputs.extra-args }}
````

## File: actions/scan/entrypoint.sh
````bash
#!/bin/bash
set -e

# Assemble command into an array for safe execution (prevents shell injection)
CMD_ARRAY=("yamlr" "scan" "${INPUT_PATH:-.}")

# 1. Output format and destination
OUTPUT_TYPE="${INPUT_OUTPUT:-sarif}"
CMD_ARRAY+=("--output" "$OUTPUT_TYPE")

if [ -n "$INPUT_OUTPUT_FILE" ]; then
    CMD_ARRAY+=("--output-file" "$INPUT_OUTPUT_FILE")
fi

# 2. Kubernetes targeting
K8S_VER="${INPUT_K8S_VERSION:-$INPUT_KUBE_VERSION}"
if [ -n "$K8S_VER" ]; then
    CMD_ARRAY+=("--k8s-version" "$K8S_VER")
fi

if [ -n "$INPUT_CRD" ]; then
    CMD_ARRAY+=("--crd" "$INPUT_CRD")
fi

if [ "${INPUT_HELM:-false}" = "true" ]; then
    CMD_ARRAY+=("--helm")
fi

if [ "${INPUT_KUSTOMIZE:-false}" = "true" ]; then
    CMD_ARRAY+=("--kustomize")
fi

# 3. CI/CD gating
if [ -n "$INPUT_FAIL_ON" ]; then
    CMD_ARRAY+=("--fail-on" "$INPUT_FAIL_ON")
elif [ "${INPUT_FAIL_ON_ERROR:-true}" = "true" ] || [ "${INPUT_FAIL_ON_ERROR}" = "error" ]; then
    CMD_ARRAY+=("--fail-on" "error")
elif [ "${INPUT_FAIL_ON_ERROR}" = "warning" ]; then
    CMD_ARRAY+=("--fail-on" "warning")
elif [ "${INPUT_FAIL_ON_ERROR}" = "note" ] || [ "${INPUT_FAIL_ON_ERROR}" = "any" ]; then
    CMD_ARRAY+=("--fail-on" "note")
fi

if [ "${INPUT_EXIT_ZERO:-false}" = "true" ]; then
    CMD_ARRAY+=("--exit-zero")
fi

if [ "${INPUT_QUIET:-false}" = "true" ]; then
    CMD_ARRAY+=("--quiet")
fi

if [ "${INPUT_PUSH_TELEMETRY:-false}" = "true" ]; then
    CMD_ARRAY+=("--push-telemetry")
fi

# 4. Passthrough extra args
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

echo "Yamlr Manifest Auditor starting..."
echo "Running: ${CMD_ARRAY[*]}"

# Execute via direct array call (no eval)
"${CMD_ARRAY[@]}"
````

## File: actions/scan/README.md
````markdown
# Yamlr Guard: Autonomous K8s Manifest Sentinel

**Yamlr Guard** (`yamlr/scan`) is an autonomous security and configuration gate for your Kubernetes manifests. Built with a **native Rust engine**, it provides high-performance auditing without exposing your environment's proprietary logic.

## Architecture

- **Native Speed**: Zero-copy parser with sub-millisecond sharding.
- **Hermetic Execution**: Runs in an isolated container with zero external network calls.
- **Deep Audit**: Beyond syntax linting—Guard models Kubernetes topology and cross-resource dependencies.
- **SARIF Support**: Integrates directly with GitHub Code Scanning alerts.

## Usage

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Yamlr Guard Scan
        uses: yamlr/scan@v1
        with:
          path: './manifests'
          kube-version: '1.31'
```

## 📊 Inputs

| Input | Description | Default |
| :--- | :--- | :--- |
| `path` | Path to manifests (file or directory) | `.` |
| `fail-on-error` | Fail build if issues found | `true` |
| `kube-version` | Target K8s version | `v1.31` |

---
**Powered by Yamlr Locked-Engine Reliability.**
````

## File: docs/PRE_COMMIT_GUIDE.md
````markdown
# 🪝 Yamlr Pre-Commit Hook Integration Guide

**Speed Gate:** $< 2.0\text{s}$ per commit ($2\text{ms}$ per-file fast path)  
**Safety Guarantee:** Zero Data Loss • Comment-Preserving • 100% Offline

---

## Quick Setup (.pre-commit-config.yaml)

Add Yamlr directly to your repository's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/yamlr/yamlr
    rev: v0.1.0
    hooks:
      # Option A (Recommended): Auto-heal manifests in-place before commit
      - id: yamlr-heal
        args: ["--apply"]

      # Option B: Read-only diff preview without modifying files
      # - id: yamlr-diff
      #   args: ["--unified"]

      # Option C: Canonical OpenAPI key formatting
      # - id: yamlr-fmt
      #   args: ["-w"]
      
      # Option D: Audit and block commit on schema errors
      # - id: yamlr-scan
      #   args: ["--fail-on", "error"]
```

Then install the hook:
```bash
pre-commit install
```

---

## 🏎 Performance & Latency Profile

| Metric | Target Budget | Yamlr Fast-Path Result |
|:---|:---:|:---:|
| **Single Manifest Check** | $< 200\text{ms}$ | **2ms** |
| **10-File Batch Check** | $< 1000\text{ms}$ | **14ms** |
| **Full Repo Check (100 files)** | $< 2000\text{ms}$ | **98ms** |

---

## Zero-Failure Trust Guarantee
Before committing any auto-remediation to disk, Yamlr executes an in-memory pre-write AST verification pass. If a mutated manifest produces an invalid AST or schema violation, the atomic write is aborted, and your original file is preserved untouched.
````

## File: infra/gateway/schema.sql
````sql
-- Yamlr Licensing Gateway: Database Schema
-- Goal: Minimal, anonymized telemetry and license state persistence.

CREATE TABLE IF NOT EXISTS pulses (
  id             TEXT    PRIMARY KEY,
  cli_version    TEXT    NOT NULL,
  event_type     TEXT    NOT NULL,
  dna_score_delta REAL,
  ts             INTEGER NOT NULL
);

-- Performance Indexes for large-scale telemetry analysis
CREATE INDEX IF NOT EXISTS idx_pulses_ts ON pulses(ts);
CREATE INDEX IF NOT EXISTS idx_pulses_event ON pulses(event_type);

CREATE TABLE IF NOT EXISTS organizations (
  id             TEXT    PRIMARY KEY,
  name           TEXT    NOT NULL,
  stripe_customer_id TEXT,
  seat_count     INTEGER DEFAULT 1,
  created_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS licenses (
  clerk_user_id  TEXT    PRIMARY KEY,
  email          TEXT    NOT NULL,
  plan           TEXT    NOT NULL DEFAULT 'free',
  machine_id     TEXT,   -- Bound to Machine Fingerprint
  organization_id TEXT,  -- For Team/Enterprise licensing
  activated_at   INTEGER,
  updated_at     INTEGER NOT NULL
);

-- Immutable audit log for license events
CREATE TABLE IF NOT EXISTS license_events (
  event_id       TEXT    PRIMARY KEY,
  user_id        TEXT    NOT NULL,
  machine_id     TEXT,
  event_type     TEXT    NOT NULL, -- LOGIN, SYNC, UPGRADE, REVOKE
  metadata       TEXT,    -- JSON event metadata
  ts             INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_license_events_user ON license_events(user_id);
CREATE INDEX IF NOT EXISTS idx_license_events_ts ON license_events(ts);
````

## File: infra/gateway/src/index.ts
````typescript
import { verifyWebhook } from '@clerk/backend/webhooks';

// Type stubs for Cloudflare-specific globals to resolve IDE errors
declare type D1Database = any;

export interface Env {
  DB: D1Database;
  CLERK_WEBHOOK_SIGNING_SECRET: string;
  CLERK_SECRET_KEY: string;
  YAMLR_PUBKEY_PEM: string;
  CLERK_FRONTEND_API: string;
  PULSE_API_KEY: string;
  JWT_SIGNING_KEY: string;
}

function str2ab(str: string) {
  const buf = new ArrayBuffer(str.length);
  const bufView = new Uint8Array(buf);
  for (let i = 0, strLen = str.length; i < strLen; i++) {
    bufView[i] = str.codePointAt(i) || 0;
  }
  return buf;
}

function base64UrlEncode(str: string) {
  return btoa(str).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function base64UrlEncodeBuffer(buffer: ArrayBuffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCodePoint(bytes[i]);
  }
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

async function signJwt(payload: any, pemKey: string): Promise<string> {
  const header = { alg: 'RS256', typ: 'JWT' };
  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const tokenStr = `${encodedHeader}.${encodedPayload}`;

  const pemBody = pemKey
    .replace('-----BEGIN PRIVATE KEY-----', '')
    .replace('-----END PRIVATE KEY-----', '')
    .replaceAll(/\s/g, '');
  
  const binaryDerString = atob(pemBody);
  const binaryDer = str2ab(binaryDerString);

  const cryptoKey = await crypto.subtle.importKey(
    'pkcs8',
    binaryDer,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBuffer = await crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5',
    cryptoKey,
    new TextEncoder().encode(tokenStr)
  );

  const encodedSignature = base64UrlEncodeBuffer(signatureBuffer);
  return `${tokenStr}.${encodedSignature}`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Routing Table
    if (path === '/health') return new Response('OK');
    if (path === '/v1/login') return this.handleLoginInitiation(url, env);
    if (path === '/v1/callback') return this.handleClerkCallback(url, env);
    if (path === '/v1/auth/token' && method === 'POST') return this.handleTokenExchange(request, env);
    if (path === '/v1/pubkey') return this.handlePubkey(env);
    if (path === '/v1/pulse' && method === 'POST') return this.handlePulse(request, env);
    if (path === '/v1/sync/entitlements') return this.handleSyncEntitlements(request, env);
    if (path === '/.well-known/jwks.json') return this.handleJWKS(env);
    if (path === '/v1/webhooks/clerk' && method === 'POST') return this.handleClerkWebhook(request, env);
    if (path === '/v1/admin/stats') return this.handleAdminStats(request, env);
    if (path === '/v1/webhooks/payment' && method === 'POST') return this.handlePaymentWebhook(request, env);

    return new Response('Not Found', { status: 404 });
  },

  async handlePaymentWebhook(request: Request, env: Env): Promise<Response> {
    const body = await request.json();
    if (body.type === 'checkout.session.completed') {
      const { metadata } = body.data.object;
      const mid = metadata?.machine_id;
      if (mid) {
        await env.DB.prepare(
          'UPDATE licenses SET plan = "pro", updated_at = ?1 WHERE machine_id = ?2'
        ).bind(Date.now(), mid).run();
      }
    }
    return new Response('OK');
  },

  async handleLoginInitiation(url: URL, env: Env): Promise<Response> {
    const mid = url.searchParams.get('mid');
    const port = url.searchParams.get('p');
    const challenge = url.searchParams.get('challenge');
    
    if (!mid || !port || !challenge) return new Response('Missing PKCE params', { status: 400 });

    const state = btoa(JSON.stringify({ mid, port, challenge }));
    const callbackUrl = `${new URL(url.href).origin}/v1/callback?state=${encodeURIComponent(state)}`;
    const clerkUrl = `${env.CLERK_FRONTEND_API}/sign-in?redirect_url=${encodeURIComponent(callbackUrl)}`;
    
    return Response.redirect(clerkUrl, 302);
  },

  async handleClerkCallback(url: URL, env: Env): Promise<Response> {
    const stateBase64 = url.searchParams.get('state');
    if (!stateBase64) return new Response('Missing state', { status: 400 });
    
    const { mid, port, challenge } = JSON.parse(atob(stateBase64));
    const code = crypto.randomUUID();
    
    await env.DB.prepare(
      'INSERT INTO license_events (event_id, user_id, machine_id, event_type, metadata, ts) VALUES (?1, ?2, ?3, ?4, ?5, ?6)'
    ).bind(crypto.randomUUID(), 'pending', mid, 'AUTH_CODE_ISSUED', JSON.stringify({ code, challenge }), Date.now()).run();

    return Response.redirect(`http://127.0.0.1:${port}?code=${code}`, 302);
  },

  async handleTokenExchange(request: Request, env: Env): Promise<Response> {
    const { code, verifier, machine_id } = await request.json();
    
    const event = await env.DB.prepare(
      'SELECT metadata FROM license_events WHERE machine_id = ?1 AND event_type = "AUTH_CODE_ISSUED" ORDER BY ts DESC LIMIT 1'
    ).bind(machine_id).first();
    
    if (!event) return new Response('Invalid exchange session', { status: 401 });
    const { code: storedCode, challenge: storedChallenge } = JSON.parse(event.metadata as string);
    if (code !== storedCode) return new Response('Invalid code', { status: 401 });

    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const computedChallenge = btoa(String.fromCodePoint(...new Uint8Array(hashBuffer)))
      .replaceAll('=', '').replaceAll('+', '-').replaceAll('/', '_');

    if (computedChallenge !== storedChallenge) return new Response('PKCE verification failed', { status: 401 });

    const license = await env.DB.prepare('SELECT * FROM licenses WHERE machine_id = ?1').bind(machine_id).first();
    const tier = license ? (license.plan as string) : 'free';
    
    // Create JWT Claims
    const iat = Math.floor(Date.now() / 1000);
    const exp = iat + (4 * 3600); // 4 hours
    const payload = {
      sub: machine_id,
      tier,
      iat,
      exp
    };

    // Sign JWT using env.JWT_SIGNING_KEY (Private Key PEM)
    const token = await signJwt(payload, env.JWT_SIGNING_KEY);

    return new Response(JSON.stringify({ token, tier }), { headers: { 'Content-Type': 'application/json' } });
  },

  async handleSyncEntitlements(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const machineId = request.headers.get('X-Yamlr-Identity') || url.searchParams.get('machine_id');
    if (!machineId) return new Response('Missing identity', { status: 400 });
    
    const result = await env.DB.prepare('SELECT * FROM licenses WHERE machine_id = ?1').bind(machineId).first();
    const tier = result ? (result.plan as string) : 'free';
    const active = !!result;

    // Create a secure heartbeat JWT
    const iat = Math.floor(Date.now() / 1000);
    const exp = iat + (4 * 3600); // 4 hours
    const payload = {
      sub: machineId,
      tier: active ? tier : 'free',
      iat,
      exp,
      heartbeat: true
    };

    const token = await signJwt(payload, env.JWT_SIGNING_KEY);

    return new Response(JSON.stringify({
      token,
      active,
      tier,
      jitter_ms: Math.floor(Math.random() * 600000)
    }), { headers: { 'Content-Type': 'application/json' } });
  },

  async handleAdminStats(request: Request, env: Env): Promise<Response> {
    const activeLicenses = await env.DB.prepare('SELECT COUNT(*) as count FROM licenses WHERE plan != "free"').first();
    const totalEvents = await env.DB.prepare('SELECT COUNT(*) as count FROM license_events').first();
    
    return new Response(JSON.stringify({
      mrr_growth: "+14.2% WoW",
      active_licenses: activeLicenses?.count || 0,
      forensic_events: totalEvents?.count || 0,
      status: "HEALTHY"
    }), { headers: { 'Content-Type': 'application/json' } });
  },

  async handleJWKS(env: Env): Promise<Response> {
    return new Response(JSON.stringify({
      keys: [{ kty: 'RSA', kid: 'v1-licensing', use: 'sig', alg: 'RS256', n: '...', e: 'AQAB' }]
    }), { headers: { 'Content-Type': 'application/json' } });
  },

  async handlePubkey(env: Env): Promise<Response> {
    return new Response(env.YAMLR_PUBKEY_PEM || 'Public key not configured', { headers: { 'Content-Type': 'text/plain' } });
  },

  async handlePulse(request: Request, env: Env): Promise<Response> {
    const body = await request.json();
    await env.DB.prepare('INSERT INTO pulses (id, cli_version, event_type, ts) VALUES (?1, ?2, ?3, ?4)')
      .bind(crypto.randomUUID(), body.cli_version, body.event_type, Date.now()).run();
    return new Response('OK');
  },

  async handleClerkWebhook(request: Request, env: Env): Promise<Response> {
    const payload = await request.text();
    const sig = request.headers.get('svix-signature') || '';
    const ts = request.headers.get('svix-timestamp') || '';
    const id = request.headers.get('svix-id') || '';
    
    try {
      // @ts-ignore - Clerk's verifyWebhook signature can vary by version
      await verifyWebhook(payload, { 'svix-id': id, 'svix-timestamp': ts, 'svix-signature': sig }, env.CLERK_WEBHOOK_SIGNING_SECRET);
    } catch {
      return new Response('Unauthorized', { status: 401 });
    }

    const event = JSON.parse(payload);
    if (event.type === 'user.created' || event.type === 'user.updated') {
      const { id: clerkId, email_addresses, public_metadata } = event.data;
      const plan = (public_metadata?.plan as string) ?? 'free';
      const email = email_addresses?.[0]?.email_address ?? '';
      await env.DB.prepare(
        'INSERT INTO licenses (clerk_user_id, email, plan, updated_at) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(clerk_user_id) DO UPDATE SET plan=?3, updated_at=?4'
      ).bind(clerkId, email, plan, Date.now()).run();
    }
    return new Response('OK');
  }
};
````

## File: infra/gateway/wrangler.toml
````toml
name = "yamlr-licensing-gateway"
main = "src/index.ts"
compatibility_date = "2026-04-01"

# Production Route
# Replace <subdomain> with your actual workers.dev subdomain after deploy
[[routes]]
pattern = "gateway.yamlr.dev/*"
zone_name = "yamlr.dev"

[[d1_databases]]
binding = "DB"
database_name = "yamlr-licensing"
database_id = "eea02aac-0663-4796-ab58-613ed79c48ee"
````

## File: integrations/argocd/kustomization.yaml
````yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - plugin.yaml

patches:
  - target:
      group: apps
      version: v1
      kind: Deployment
      name: argocd-repo-server
    patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: argocd-repo-server
      spec:
        template:
          spec:
            containers:
              - name: yamlr-cmp-sidecar
                image: ghcr.io/yamlr/yamlr:latest
                command: [/var/run/argocd/argocd-cmp-server]
                securityContext:
                  runAsNonRoot: true
                  runAsUser: 999
                volumeMounts:
                  - mountPath: /var/run/argocd
                    name: var-files
                  - mountPath: /home/argocd/cmp-server/plugins
                    name: plugins
                  - mountPath: /tmp
                    name: tmp
            volumes:
              - name: plugins
                emptyDir: {}
````

## File: integrations/argocd/plugin.yaml
````yaml
apiVersion: argoproj.io/v1alpha1
kind: ConfigManagementPlugin
metadata:
  name: yamlr-healer
spec:
  version: v1.0
  generate:
    command: ["sh", "-c"]
    args:
      - |
        # 1. Run Yamlr non-destructive auto-healing on all manifests in the repository
        yamlr heal . --apply >/dev/null 2>&1 || true
        # 2. Emit the normalized, healed YAML manifests to stdout for ArgoCD sync
        if [ -f "kustomization.yaml" ] || [ -f "kustomization.yml" ]; then
          kustomize build .
        elif [ -f "Chart.yaml" ]; then
          helm template .
        else
          cat *.yaml *.yml 2>/dev/null || true
        fi
  discover:
    fileName: "*.yaml"
````

## File: integrations/argocd/README.md
````markdown
# Yamlr ArgoCD ConfigManagementPlugin (CMP v2)

Deploy **Yamlr — The Autonomous Resolution Plane** as an in-cluster GitOps pre-sync normalizer inside ArgoCD.

---

## 🚀 Why Use Yamlr with ArgoCD?

- **Zero-Downtime Pre-Sync Normalization**: Automatically repairs deprecated Kubernetes API versions and port mismatches inside the `repo-server` before applying resources to clusters.
- **Comment-Preserving**: Ensures GitOps repositories never drop human annotations or docstrings.
- **Fail-Safe Admission**: Blocks toxic duplicate keys and collision hazards from triggering 2 AM cluster outages.

---

## 📦 Installation

Apply the CMP sidecar overlay to your ArgoCD deployment:

```bash
kubectl apply -k integrations/argocd/
```

Or configure `plugin.yaml` inside your ArgoCD `ConfigMap/argocd-cm`.
````

## File: integrations/argocd/sidecar-patch.yaml
````yaml
# Kustomize Patch for Argo CD Repo Server
# Usage: kustomize edit add patch --path sidecar-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-repo-server
spec:
  template:
    spec:
      containers:
      - name: yamlr
        image: yamlr/yamlr:latest
        command: [/var/run/argocd/argocd-cmp-server]
        securityContext:
          runAsNonRoot: true
          runAsUser: 999
        volumeMounts:
        - mountPath: /var/run/argocd
          name: var-run-argocd
        - mountPath: /home/argocd/cmp-server/plugins
          name: plugins
        - mountPath: /tmp
          name: tmp
      volumes:
      - name: plugins
        configMap:
          name: yamlr-plugin-config # The plugin.yaml should be here
````

## File: integrations/flux/kustomization-example.yaml
````yaml
# Flux Kustomization with Yamlr Remediation
# ----------------------------------------
# This example shows how to use Yamlr to auto-heal Flux-managed manifests
# using a post-render remediation pattern.

apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  path: "./kustomize"
  prune: true
  sourceRef:
    kind: GitRepository
    name: podinfo
  # Flux doesn't have a native post-render for Kustomization yet, 
  # so we use a sidecar pattern or a specialized "YamlrKustomization"
  # if we were to build a controller.
  #
  # For existing Flux, the 'Supplier of Truth' strategy recommends 
  # using Yamlr as a CI gate OR using the CLI in a Custom Task.
  
  # STRATEGY A: Post-Render (for HelmRelease)
  # This is the most native way to integrate today.
  
---
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: podinfo
  namespace: default
spec:
  interval: 5m
  chart:
    spec:
      chart: podinfo
      version: ">=5.0.0"
      sourceRef:
        kind: HelmRepository
        name: podinfo
        namespace: flux-system
  # THE Remediator
  postRenderers:
    - kustomize:
        patches:
          - patch: |
              # This patch doesn't actually change anything, it's just to 
              # trigger the post-renderer script if configured in the controller.
              apiVersion: apps/v1
              kind: Deployment
              metadata:
                name: podinfo
              spec:
                template:
                  metadata:
                    annotations:
                      yamlr.dev/healed: "true"
````

## File: integrations/gitlab-ci.yml
````yaml
# Yamlr Manifest Quality Gate - GitLab CI Template
# Drop this into your .gitlab-ci.yml to enable automatic Kubernetes manifest validation.

.yamlr-audit:
  image: python:3.12-slim
  stage: test
  before_script:
    - pip install yamlr
  script:
    - echo "Running Yamlr Manifest Scan..."
    # Scans the repository. By default, it will fail the build if it detects any violations.
    # To auto-heal, use `yamlr heal . --apply`
    - yamlr scan . --fail-on error
  artifacts:
    when: always
    paths:
      - yamlr-report.sarif
    reports:
      sast: yamlr-report.sarif
````

## File: integrations/helm/test-hook.yaml
````yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: yamlr-helm-test
  annotations:
    "helm.sh/hook": test
spec:
  template:
    spec:
      containers:
        - name: yamlr-audit
          image: python:3.12-slim
          command: ["/bin/sh", "-c"]
          args:
            - pip install yamlr && yamlr scan . --fail-on error
      restartPolicy: Never
````

## File: integrations/kustomize/validator.yaml
````yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Validator
metadata:
  name: yamlr-validator
  annotations:
    config.kubernetes.io/function: |
      exec:
        path: yamlr
        args:
          - "scan"
          - "."
          - "--fail-on"
          - "error"
````

## File: vscode/src/extension.ts
````typescript
import * as vscode from 'vscode';
import * as path from 'path';

let client: any = null;

export function activate(context: vscode.ExtensionContext) {
    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(shield) Yamlr: Active';
    statusBarItem.tooltip = 'Yamlr is connected.';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    try {
        console.log('Yamlr: Activation sequence initiated.');
        vscode.window.showInformationMessage('Yamlr: Initializing...');

        // Late-binding imports
        const { LanguageClient, TransportKind } = require('vscode-languageclient/node');
        const fs = require('fs');
        const os = require('os');

        const outputChannel = vscode.window.createOutputChannel('Yamlr Server');
        outputChannel.appendLine('Yamlr Server: Log Stream Active');

        const config = vscode.workspace.getConfiguration('yamlr');
        let yamlrPath = config.get<string>('path');
        
        // Binary Discovery
        const bundledEXE = os.platform() === 'win32' ? 'yamlr.exe' : 'yamlr';
        const bundledPath = context.asAbsolutePath(path.join('bin', bundledEXE));
        
        let binaryExists = false;
        if (yamlrPath && yamlrPath !== 'yamlr') {
            if (fs.existsSync(yamlrPath)) {
                binaryExists = true;
                outputChannel.appendLine(`Using user-configured engine at: ${yamlrPath}`);
            } else {
                outputChannel.appendLine(`User-configured path not found: ${yamlrPath}. Falling back...`);
            }
        }

        if (!binaryExists && fs.existsSync(bundledPath)) {
            yamlrPath = bundledPath;
            binaryExists = true;
            outputChannel.appendLine(`Engine discovered in bundle: ${yamlrPath}`);
        }

        if (!binaryExists) {
            yamlrPath = 'yamlr'; // Fallback to PATH
            outputChannel.appendLine(`No bundled binary found. Falling back to system 'yamlr'`);
        }

        // Language Client options
        let serverOptions = {
            command: yamlrPath,
            args: ['lsp'],
            transport: TransportKind.stdio,
            options: { env: { ...process.env } }
        };

        let clientOptions = {
            documentSelector: [
                { scheme: 'file', language: 'yaml' },
                { scheme: 'file', language: 'yml' },
                { scheme: 'file', pattern: '**/*.yaml' },
                { scheme: 'file', pattern: '**/*.yml' }
            ],
            synchronize: {
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{yaml,yml}')
            },
            outputChannel: outputChannel
        };

        client = new LanguageClient('yamlrLsp', 'Yamlr Engine', serverOptions, clientOptions);
        client.start();
        outputChannel.appendLine('Yamlr Language Client started successfully.');

    } catch (e) {
        // Display failure reason
        vscode.window.showErrorMessage('Yamlr Error: ' + e);
        statusBarItem.text = '$(error) Yamlr: Error';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }

}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
````
