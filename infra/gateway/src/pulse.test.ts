import assert from 'node:assert/strict';
import { generateKeyPairSync, sign } from 'node:crypto';
import test from 'node:test';

import { handlePulse } from './pulse.ts';

const { privateKey, publicKey } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
  privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  publicKeyEncoding: { type: 'spki', format: 'pem' },
});

function token(tier = 'enterprise', expiry = Math.floor(Date.now() / 1000) + 600) {
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const header = encode({ alg: 'RS256', typ: 'JWT' });
  const payload = encode({
    license_version: 1, sub: 'org-1', org_id: 'org-1', tier, iss: 'yamlr-entitlement', aud: 'yamlr',
    iat: Math.floor(Date.now() / 1000), exp: expiry,
  });
  const signingInput = `${header}.${payload}`;
  return `${signingInput}.${sign('RSA-SHA256', Buffer.from(signingInput), privateKey).toString('base64url')}`;
}

function request(credential: string, body: unknown) {
  return new Request('https://gateway.example.test/v1/pulse', {
    method: 'POST', headers: { Authorization: credential, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function environment() {
  const writes: unknown[][] = [];
  return {
    writes,
    env: {
      YAMLR_PUBKEY_PEM: publicKey,
      DB: { prepare: () => ({ bind: (...values: unknown[]) => ({ run: async () => { writes.push(values); } }) }) },
    },
  };
}

test('pulse accepts a valid Enterprise entitlement and stores only approved fields', async () => {
  const fixture = environment();
  const response = await handlePulse(request(`Bearer ${token()}`, {
    cli_version: '1.2.3', event_type: 'scan_complete', ts: 1_800_000_000,
  }), fixture.env);
  assert.equal(response.status, 200);
  assert.equal(fixture.writes.length, 1);
  assert.equal(fixture.writes[0][1], '1.2.3');
  assert.equal(fixture.writes[0][2], 'scan_complete');
});

test('pulse rejects missing, Team, tampered, and expired entitlements', async () => {
  const fixture = environment();
  const teamResponse = await handlePulse(request(`Bearer ${token('team')}`, {
    cli_version: '1.2.3', event_type: 'scan_complete', ts: 1_800_000_000,
  }), fixture.env);
  const missingResponse = await handlePulse(request('', {}), fixture.env);
  const valid = token();
  const [header, claims, signature] = valid.split('.');
  const tampered = `${header}.${claims}.${signature[0] === 'a' ? 'b' : 'a'}${signature.slice(1)}`;
  const tamperedResponse = await handlePulse(request(`Bearer ${tampered}`, {}), fixture.env);
  const expiredResponse = await handlePulse(request(`Bearer ${token('enterprise', 1)}`, {}), fixture.env);
  assert.equal(teamResponse.status, 401);
  assert.equal(missingResponse.status, 401);
  assert.equal(tamperedResponse.status, 401);
  assert.equal(expiredResponse.status, 401);
  assert.equal(fixture.writes.length, 0);
});

test('pulse rejects payloads containing unapproved or malformed telemetry', async () => {
  const fixture = environment();
  const response = await handlePulse(request(`Bearer ${token()}`, {
    cli_version: '1.2.3', event_type: 'scan_complete', ts: 1_800_000_000, manifest: 'private data',
  }), fixture.env);
  assert.equal(response.status, 400);
  assert.equal(fixture.writes.length, 0);
});
