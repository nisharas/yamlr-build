# Optional hosted gateway adapter

This directory contains Yamlr's hosted account and licensing integration. It is not part of the local scan, heal, format, or report engine. Those core workflows run from the CLI and native library without deploying this gateway or creating a provider account.

## Current provider implementation

The deployable adapter currently targets Cloudflare Workers and Cloudflare D1, configured in `wrangler.toml`. It uses standard OpenID Connect for browser login and Stripe for optional team billing. These are implementation choices for this hosted adapter, not requirements of the Yamlr manifest engine. Clerk-specific legacy login and webhook routes have been removed; identity integration uses the OIDC protocol.

The shared gateway handler consumes the `GatewayDatabase` interface in
`src/storage.ts`. Cloudflare D1 satisfies that interface; the self-hosted
`SQLiteGatewayDatabase` implements parameter bindings and atomic batches using
Node's SQLite API. Both transports run the same HTTP and token handlers. The
engine consumes HTTPS endpoints and signed entitlement claims and does not
require Cloudflare or Stripe libraries.

## Engine-facing contracts

- **Team entitlement renewal:** `POST /v1/auth/renew` accepts a stored signed token and returns a renewed signed token. The CLI defaults to `https://gateway.yamlr.dev`; set `YAMLR_LICENSE_GATEWAY_URL` to another HTTPS gateway base URL to use a replacement. Renewal is used for expiring Team entitlements; local scan and heal remain available without it.
- **Enterprise scan telemetry:** `POST /v1/pulse` accepts only the documented aggregate event. The CLI sends it only when `--push-telemetry` is explicitly requested and telemetry policy permits it. Set `YAMLR_TELEMETRY_GATEWAY_URL` to an alternate HTTPS gateway base URL. This adapter is optional.
- **Entitlement tokens:** replacement services must issue tokens accepted by the native verifier, with the configured Yamlr signing key and the required issuer, audience, tier, and expiry claims. Do not make local analysis depend on an online account check.

## Deployment boundary

Only deploy this service when hosted licensing, account login, or billing is
needed. Local scan/heal requires neither transport. Stripe remains an optional
billing adapter; renewal consumes stored grants rather than contacting Stripe
on every renewal. A signed operator-receipt adapter updates existing contracted
Team pools without an online payment provider. Both adapters use the same
atomic grant-update logic. This is development evidence, not a production deployment.

## Operator-managed billing

Set `BILLING_PROVIDER=offline` and configure a separate high-entropy
`OFFLINE_BILLING_SECRET` of at least 32 UTF-8 bytes. Do not use an entitlement
signing key, customer token, or source-controlled value for this secret.
`POST /v1/webhooks/payment` then accepts operator receipts; Stripe checkout is
disabled. The adapter makes no external payment calls.

Receipts are UTF-8 JSON objects containing exactly:

```json
{"eventId":"offline:receipt-123","eventType":"operator.renewed","created":1700000000,"organizationId":"org-id","subscriptionId":"offline:contract-id","status":"active","periodEnd":1702592000,"seats":5}
```

Sign the exact request body bytes with HMAC-SHA256 and send the lowercase
hexadecimal MAC in `X-Yamlr-Receipt-Signature`. `created` and `periodEnd` are Unix
seconds. Allowed states are `active`, `past_due`, `suspended`, and `canceled`;
seats may be null or an integer from 1 to 10000. Bodies are limited to 16 KiB.
Use unique `offline:` event IDs and monotonically ordered creation timestamps.
Future events beyond 60 seconds are rejected. Duplicate/stale events cannot
replace newer grants, failure retries cannot extend grace, and cancellation is
terminal for the bound subscription.

This adapter updates existing organizations and Team grant records only.
The provider reference must already match the pool's stored binding. Initial
pool provisioning is an operator-controlled fulfillment action. The compatibility
database column remains named `stripe_subscription_id`; offline pools store an
`offline:` reference in it. Existing Stripe bindings are not migrated automatically.

Keep secrets and provisioning access under operator control, retain receipt
records, and review migrations and backup/recovery before deploying. The tests
use disposable fixture secrets and do not issue customer licenses.

## Self-hosted transport

Use Node 24 with the locked development dependencies. Set the following through
your service's secret/environment configuration:

- `YAMLR_GATEWAY_DATABASE`: path to a persistent SQLite database owned by the service.
- `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`.
- `APP_ORIGIN`: the trusted browser application's HTTPS origin.
- `JWT_SIGNING_KEY` and `YAMLR_PUBKEY_PEM`: the entitlement signing key and public key.
- Optional email delivery and Stripe settings documented by the existing adapter.
- `PORT`: defaults to 8787.

Run `npm run start:self-hosted` from this directory. The server binds to
`127.0.0.1`; place it behind your HTTPS reverse proxy. Public URLs must use
HTTPS. The request URL uses the configured callback origin, never an untrusted
Host or forwarded header. Request bodies are limited to 256 KiB. The existing
idempotent database schema initializes missing tables; schema changes still
require reviewed migrations and backups. There is no production service or
key created by these instructions.

`npm test` exercises OIDC, telemetry, seats, billing lifecycle, storage rollback,
and the actual self-hosted HTTP transport. Seat acceptance and revoked-token
renewal use the production SQLite adapter. CI runs these tests and type-checks
the alternate adapter. These are local development contract tests, not live
identity-provider, payment, load, or deployment certification.

The current storage adapter implements the gateway's numbered `?1`, `?2`, etc.
SQL bindings. Database batches are atomic and reject foreign-adapter statements.
Node's SQLite module currently emits an experimental API warning; record and
review runtime upgrades before a production deployment.
