import type { GatewayDatabase } from './storage.ts';
export interface OidcEnv {
  DB: GatewayDatabase;
  OIDC_ISSUER: string;
  OIDC_CLIENT_ID: string;
  OIDC_CLIENT_SECRET: string;
  OIDC_REDIRECT_URI: string;
  APP_ORIGIN: string;
}

export interface OidcIdentity {
  subject: string;
  email: string;
  emailVerified: true;
}

const SESSION_COOKIE = 'yamlr_session';
const STATE_COOKIE = 'yamlr_oidc_state';
const SESSION_TTL_SECONDS = 30 * 24 * 60 * 60;

function base64Url(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

export function decodeBase64Url(value: string): Uint8Array {
  const normalized = value.replaceAll('-', '+').replaceAll('_', '/');
  const binary = atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

export function normalizeEmail(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const email = value.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

export function parseCookie(header: string | null, name: string): string | null {
  if (!header) return null;
  for (const part of header.split(';')) {
    const separator = part.indexOf('=');
    if (separator < 0 || part.slice(0, separator).trim() !== name) continue;
    try { return decodeURIComponent(part.slice(separator + 1).trim()); }
    catch { return null; }
  }
  return null;
}

async function sha256(value: string): Promise<string> {
  return base64Url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))));
}

function randomToken(bytes = 32): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(bytes)));
}

function issuerUrl(env: OidcEnv): string {
  const issuer = new URL(env.OIDC_ISSUER);
  if (issuer.protocol !== 'https:' || issuer.username || issuer.password || issuer.search || issuer.hash) {
    throw new Error('OIDC issuer must be an HTTPS issuer URL without credentials or query parameters.');
  }
  return issuer.toString().replace(/\/$/, '');
}

async function discovery(env: OidcEnv): Promise<any> {
  const issuer = issuerUrl(env);
  const response = await fetch(`${issuer}/.well-known/openid-configuration`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error('OIDC discovery failed.');
  const document = await response.json() as any;
  if (document.issuer !== issuer || typeof document.authorization_endpoint !== 'string' ||
      typeof document.token_endpoint !== 'string' || typeof document.jwks_uri !== 'string') {
    throw new Error('OIDC discovery document is invalid.');
  }
  for (const endpoint of [document.authorization_endpoint, document.token_endpoint, document.jwks_uri]) {
    if (new URL(endpoint).protocol !== 'https:') throw new Error('OIDC endpoints must use HTTPS.');
  }
  return document;
}

export async function beginOidcLogin(request: Request, env: OidcEnv): Promise<Response> {
  try {
    if (!env.OIDC_CLIENT_ID || !env.OIDC_CLIENT_SECRET || !env.OIDC_REDIRECT_URI || !env.APP_ORIGIN) {
      return new Response('OIDC sign-in is not configured', { status: 503 });
    }
    const metadata = await discovery(env);
    const state = randomToken();
    const nonce = randomToken();
    const verifier = randomToken(48);
    const challenge = base64Url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
    const expiresAt = Math.floor(Date.now() / 1000) + 600;
    await env.DB.prepare(
      'INSERT INTO oidc_login_requests (state_hash, nonce, verifier, expires_at) VALUES (?1, ?2, ?3, ?4)'
    ).bind(await sha256(state), nonce, verifier, expiresAt).run();

    const authorize = new URL(metadata.authorization_endpoint);
    authorize.search = new URLSearchParams({
      response_type: 'code', client_id: env.OIDC_CLIENT_ID, redirect_uri: env.OIDC_REDIRECT_URI,
      scope: 'openid email profile', state, nonce, code_challenge: challenge,
      code_challenge_method: 'S256',
    }).toString();
    return new Response(null, {
      status: 302,
      headers: {
        Location: authorize.toString(),
        'Set-Cookie': `${STATE_COOKIE}=${encodeURIComponent(state)}; Path=/; Max-Age=600; Secure; HttpOnly; SameSite=Lax`,
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    console.error('OIDC login initiation failed', error instanceof Error ? error.message : 'unknown error');
    return new Response('Unable to start sign-in', { status: 503 });
  }
}

async function verifyIdToken(token: string, env: OidcEnv, metadata: any, nonce: string): Promise<OidcIdentity> {
  const parts = token.split('.');
  if (parts.length !== 3) throw new Error('Malformed OIDC ID token.');
  const header = JSON.parse(new TextDecoder().decode(decodeBase64Url(parts[0]))) as any;
  const claims = JSON.parse(new TextDecoder().decode(decodeBase64Url(parts[1]))) as any;
  if (header.alg !== 'RS256' || typeof header.kid !== 'string') throw new Error('Unsupported OIDC signing algorithm.');

  const jwksResponse = await fetch(metadata.jwks_uri, { headers: { Accept: 'application/json' } });
  if (!jwksResponse.ok) throw new Error('Unable to fetch OIDC signing keys.');
  const jwks = await jwksResponse.json() as any;
  const jwk = Array.isArray(jwks.keys) ? jwks.keys.find((key: any) => key.kid === header.kid && key.kty === 'RSA' && key.use !== 'enc') : null;
  if (!jwk) throw new Error('OIDC signing key was not found.');
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const signingInput = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
  const signature = decodeBase64Url(parts[2]);
  const signatureBuffer = Uint8Array.from(signature).buffer as ArrayBuffer;
  const inputBuffer = Uint8Array.from(signingInput).buffer as ArrayBuffer;
  if (!await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, signatureBuffer, inputBuffer)) {
    throw new Error('OIDC ID token signature is invalid.');
  }

  const now = Math.floor(Date.now() / 1000);
  const audience = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (claims.iss !== issuerUrl(env) || !audience.includes(env.OIDC_CLIENT_ID) ||
      (audience.length > 1 && claims.azp !== env.OIDC_CLIENT_ID) ||
      !Number.isSafeInteger(claims.exp) || claims.exp <= now ||
      (claims.nbf != null && (!Number.isSafeInteger(claims.nbf) || claims.nbf > now)) ||
      !Number.isSafeInteger(claims.iat) || claims.iat > now + 60 ||
      claims.nonce !== nonce || typeof claims.sub !== 'string' || !claims.sub.trim() ||
      claims.email_verified !== true) {
    throw new Error('OIDC ID token claims are invalid.');
  }
  const email = normalizeEmail(claims.email);
  if (!email) throw new Error('OIDC account must provide a verified email address.');
  return { subject: claims.sub, email, emailVerified: true };
}

export async function completeOidcLogin(request: Request, env: OidcEnv): Promise<Response> {
  const url = new URL(request.url);
  const state = url.searchParams.get('state');
  const code = url.searchParams.get('code');
  const stateCookie = parseCookie(request.headers.get('Cookie'), STATE_COOKIE);
  const clearState = `${STATE_COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax`;
  if (!state || state !== stateCookie || !code) return new Response('Invalid sign-in response', { status: 400, headers: { 'Set-Cookie': clearState } });

  try {
    const stateHash = await sha256(state);
    const pending = await env.DB.prepare(
      'SELECT nonce, verifier, expires_at FROM oidc_login_requests WHERE state_hash = ?1'
    ).bind(stateHash).first() as any;
    if (!pending || pending.expires_at <= Math.floor(Date.now() / 1000)) return new Response('Sign-in expired', { status: 401, headers: { 'Set-Cookie': clearState } });
    await env.DB.prepare('DELETE FROM oidc_login_requests WHERE state_hash = ?1').bind(stateHash).run();

    const metadata = await discovery(env);
    const tokenResponse = await fetch(metadata.token_endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
      body: new URLSearchParams({ grant_type: 'authorization_code', code, redirect_uri: env.OIDC_REDIRECT_URI,
        client_id: env.OIDC_CLIENT_ID, client_secret: env.OIDC_CLIENT_SECRET, code_verifier: pending.verifier }),
    });
    if (!tokenResponse.ok) throw new Error('OIDC code exchange failed.');
    const tokenResult = await tokenResponse.json() as any;
    if (typeof tokenResult.id_token !== 'string') throw new Error('OIDC response did not contain an ID token.');
    const identity = await verifyIdToken(tokenResult.id_token, env, metadata, pending.nonce);
    const now = Math.floor(Date.now() / 1000);
    await env.DB.prepare(
      'INSERT INTO identities (issuer, subject, email, email_verified, updated_at) VALUES (?1, ?2, ?3, 1, ?4) ON CONFLICT(issuer, subject) DO UPDATE SET email=?3, email_verified=1, updated_at=?4'
    ).bind(issuerUrl(env), identity.subject, identity.email, now).run();

    const session = randomToken();
    await env.DB.prepare('INSERT INTO web_sessions (token_hash, issuer, subject, expires_at, created_at) VALUES (?1, ?2, ?3, ?4, ?5)')
      .bind(await sha256(session), issuerUrl(env), identity.subject, now + SESSION_TTL_SECONDS, now).run();
    const appOrigin = new URL(env.APP_ORIGIN);
    if (appOrigin.protocol !== 'https:') throw new Error('Application origin must use HTTPS.');
    return new Response(null, { status: 302, headers: {
      Location: new URL('/team', appOrigin).toString(),
      'Set-Cookie': `${SESSION_COOKIE}=${encodeURIComponent(session)}; Path=/; Max-Age=${SESSION_TTL_SECONDS}; Secure; HttpOnly; SameSite=Lax`,
      'Cache-Control': 'no-store',
    } });
  } catch (error) {
    console.error('OIDC callback failed', error instanceof Error ? error.message : 'unknown error');
    return new Response('Sign-in could not be completed', { status: 401, headers: { 'Set-Cookie': clearState } });
  }
}

export async function currentOidcIdentity(request: Request, env: OidcEnv): Promise<OidcIdentity | null> {
  const session = parseCookie(request.headers.get('Cookie'), SESSION_COOKIE);
  if (!session) return null;
  const row = await env.DB.prepare(
    'SELECT i.subject, i.email, i.email_verified FROM web_sessions s JOIN identities i ON i.issuer=s.issuer AND i.subject=s.subject WHERE s.token_hash=?1 AND s.expires_at>?2 AND i.email_verified=1'
  ).bind(await sha256(session), Math.floor(Date.now() / 1000)).first() as any;
  if (!row || typeof row.subject !== 'string' || typeof row.email !== 'string') return null;
  return { subject: row.subject, email: row.email, emailVerified: true };
}

export async function endOidcSession(request: Request, env: OidcEnv): Promise<Response> {
  const session = parseCookie(request.headers.get('Cookie'), SESSION_COOKIE);
  if (session) await env.DB.prepare('DELETE FROM web_sessions WHERE token_hash=?1').bind(await sha256(session)).run();
  return new Response(JSON.stringify({ signed_out: true }), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      'Set-Cookie': `${SESSION_COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax`,
    },
  });
}

export function oidcTestHelpers() {
  return { base64Url, decodeBase64Url, SESSION_COOKIE, STATE_COOKIE };
}
