import assert from 'node:assert/strict';
import test from 'node:test';
import { beginOidcLogin, completeOidcLogin, currentOidcIdentity } from './oidc.ts';

import { normalizeEmail, parseCookie } from './oidc.ts';

test('normalizeEmail accepts and canonicalizes email addresses', () => {
  assert.equal(normalizeEmail('  Developer@Example.com '), 'developer@example.com');
});

test('normalizeEmail rejects malformed or non-string values', () => {
  for (const value of ['', 'a@b', 'a b@example.com', 'a@example.com extra', null, 42]) {
    assert.equal(normalizeEmail(value), null);
  }
});

test('parseCookie returns the named value among other cookies', () => {
  assert.equal(parseCookie('other=x; yamlr_session=abc%2B123; last=y', 'yamlr_session'), 'abc+123');
});

test('parseCookie rejects missing, malformed, and empty headers', () => {
  assert.equal(parseCookie(null, 'yamlr_session'), null);
  assert.equal(parseCookie('other=value', 'yamlr_session'), null);
  assert.equal(parseCookie('yamlr_session=%E0%A4%A', 'yamlr_session'), null);
});

test('OIDC authorization uses PKCE and creates a session only for a verified signed identity', async () => {
  const keyPair = await crypto.subtle.generateKey({
    name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: Uint8Array.of(1, 0, 1), hash: 'SHA-256',
  }, true, ['sign', 'verify']);
  const jwk = await crypto.subtle.exportKey('jwk', keyPair.publicKey) as JsonWebKey & { kid?: string; use?: string };
  jwk.kid = 'oidc-test-key';
  jwk.use = 'sig';
  const database = {
    loginRequest: null as any,
    session: null as any,
    identity: null as any,
    prepare(sql: string) {
      const statement = {
        values: [] as any[],
        bind(...values: any[]) { this.values = values; return this; },
        async run() {
          if (sql.includes('INSERT INTO oidc_login_requests')) database.loginRequest = {
            nonce: this.values[1], verifier: this.values[2], expires_at: this.values[3],
          };
          if (sql.includes('DELETE FROM oidc_login_requests')) database.loginRequest = null;
          if (sql.includes('INSERT INTO identities')) database.identity = {
            issuer: this.values[0], subject: this.values[1], email: this.values[2], email_verified: 1,
          };
          if (sql.includes('INSERT INTO web_sessions')) database.session = {
            token_hash: this.values[0], issuer: this.values[1], subject: this.values[2], expires_at: this.values[3],
          };
          return { meta: { changes: 1 } };
        },
        async first() {
          if (sql.includes('SELECT nonce, verifier, expires_at')) return database.loginRequest;
          if (sql.includes('SELECT i.subject, i.email')) return database.identity && {
            subject: database.identity.subject, email: database.identity.email, email_verified: true,
          };
          return null;
        },
      };
      return statement;
    },
  };
  const env = {
    DB: database,
    OIDC_ISSUER: 'https://issuer.example.test',
    OIDC_CLIENT_ID: 'yamlr-client',
    OIDC_CLIENT_SECRET: 'test-secret',
    OIDC_REDIRECT_URI: 'https://gateway.example.test/v1/oidc/callback',
    APP_ORIGIN: 'https://yamlr.example.test',
  };
  const originalFetch = globalThis.fetch;
  let verifierFromRequest = '';
  let expectedNonce = '';
  globalThis.fetch = async (input, init) => {
    const url = String(input);
    if (url.endsWith('/.well-known/openid-configuration')) return Response.json({
      issuer: env.OIDC_ISSUER,
      authorization_endpoint: 'https://issuer.example.test/authorize',
      token_endpoint: 'https://issuer.example.test/token',
      jwks_uri: 'https://issuer.example.test/jwks',
    });
    if (url.endsWith('/token')) {
      const params = new URLSearchParams(String(init?.body || ''));
      verifierFromRequest = params.get('code_verifier') || '';
      const now = Math.floor(Date.now() / 1000);
      const encode = (value: string) => Buffer.from(value).toString('base64url');
      const header = encode(JSON.stringify({ alg: 'RS256', typ: 'JWT', kid: 'oidc-test-key' }));
      const claims = encode(JSON.stringify({ iss: env.OIDC_ISSUER, aud: env.OIDC_CLIENT_ID, sub: 'user-123',
        email: 'User@Example.test', email_verified: true, iat: now, exp: now + 3600, nonce: expectedNonce }));
      const input = `${header}.${claims}`;
      const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', keyPair.privateKey, new TextEncoder().encode(input));
      return Response.json({ id_token: `${input}.${Buffer.from(signature).toString('base64url')}` });
    }
    if (url.endsWith('/jwks')) return Response.json({ keys: [jwk] });
    throw new Error(`Unexpected OIDC endpoint: ${url}`);
  };

  try {
    const start = await beginOidcLogin(new Request('https://gateway.example.test/v1/oidc/login'), env);
    assert.equal(start.status, 302);
    const authorize = new URL(start.headers.get('Location')!);
    assert.equal(authorize.searchParams.get('code_challenge_method'), 'S256');
    assert.ok(authorize.searchParams.get('code_challenge'));
    expectedNonce = database.loginRequest.nonce;
    const state = authorize.searchParams.get('state')!;
    const stateCookie = start.headers.get('Set-Cookie')!.split(';')[0];
    const callback = await completeOidcLogin(new Request(
      `https://gateway.example.test/v1/oidc/callback?code=authorization-code&state=${encodeURIComponent(state)}`,
      { headers: { Cookie: stateCookie } },
    ), env);
    assert.equal(callback.status, 302);
    assert.equal(callback.headers.get('Location'), 'https://yamlr.example.test/team');
    assert.ok(verifierFromRequest.length >= 43);
    assert.equal(database.identity.email, 'user@example.test');

    const sessionCookie = callback.headers.get('Set-Cookie')!.split(';')[0];
    const identity = await currentOidcIdentity(new Request('https://gateway.example.test/v1/team/organizations', {
      headers: { Cookie: sessionCookie },
    }), env);
    assert.deepEqual(identity, { subject: 'user-123', email: 'user@example.test', emailVerified: true });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
