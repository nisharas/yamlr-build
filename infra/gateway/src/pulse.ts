import type { GatewayDatabase } from './storage.ts';
export interface PulseEnvironment {
  DB: GatewayDatabase;
  YAMLR_PUBKEY_PEM?: string;
}

interface EntitlementClaims {
  license_version?: unknown;
  sub?: unknown;
  org_id?: unknown;
  tier?: unknown;
  iss?: unknown;
  aud?: unknown;
  exp?: unknown;
  iat?: unknown;
}

function decodeBase64Url(value: string): Uint8Array | null {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return null;
  try {
    const normalized = value.replaceAll('-', '+').replaceAll('_', '/');
    const binary = atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  } catch {
    return null;
  }
}

function decodeJsonSegment<T>(segment: string): T | null {
  const bytes = decodeBase64Url(segment);
  if (!bytes) return null;
  try {
    return JSON.parse(new TextDecoder().decode(bytes)) as T;
  } catch {
    return null;
  }
}

async function verifyEnterpriseToken(token: string, pem: string, nowSeconds = Math.floor(Date.now() / 1000)) {
  if (token.length > 8192) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  const header = decodeJsonSegment<{ alg?: unknown; typ?: unknown }>(parts[0]);
  const claims = decodeJsonSegment<EntitlementClaims>(parts[1]);
  const signature = decodeBase64Url(parts[2]);
  if (!header || header.alg !== 'RS256' || (header.typ !== undefined && header.typ !== 'JWT') || !claims || !signature) return false;
  if (claims.license_version !== 1 || claims.iss !== 'yamlr-entitlement' || claims.aud !== 'yamlr' || claims.tier !== 'enterprise') return false;
  if (typeof claims.sub !== 'string' || claims.sub.trim() === '' || claims.org_id !== claims.sub) return false;
  if (!Number.isSafeInteger(claims.iat) || Number(claims.iat) > nowSeconds + 60 ||
      !Number.isSafeInteger(claims.exp) || Number(claims.exp) <= nowSeconds || Number(claims.exp) <= Number(claims.iat)) return false;

  const pemBody = pem.replace(/-----BEGIN PUBLIC KEY-----|-----END PUBLIC KEY-----|\s/g, '');
  let keyBytes: Uint8Array;
  try {
    keyBytes = Uint8Array.from(atob(pemBody), (character) => character.charCodeAt(0));
  } catch {
    return false;
  }
  try {
    const keyData = new ArrayBuffer(keyBytes.byteLength);
    new Uint8Array(keyData).set(keyBytes);
    const signatureData = new ArrayBuffer(signature.byteLength);
    new Uint8Array(signatureData).set(signature);
    const key = await crypto.subtle.importKey(
      'spki', keyData, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify'],
    );
    return await crypto.subtle.verify(
      'RSASSA-PKCS1-v1_5', key, signatureData, new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
    );
  } catch {
    return false;
  }
}

export async function handlePulse(request: Request, env: PulseEnvironment): Promise<Response> {
  const authorization = request.headers.get('Authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token || !env.YAMLR_PUBKEY_PEM || !await verifyEnterpriseToken(token, env.YAMLR_PUBKEY_PEM)) {
    return new Response('Enterprise entitlement required', { status: 401 });
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json() as Record<string, unknown>;
  } catch {
    return new Response('Invalid telemetry payload', { status: 400 });
  }
  if (!body || typeof body !== 'object' || Array.isArray(body)
    || Object.keys(body).some((key) => !['cli_version', 'event_type', 'ts'].includes(key))
    || typeof body.cli_version !== 'string' || body.cli_version.length < 1 || body.cli_version.length > 64
    || !/^[A-Za-z0-9.+_-]+$/.test(body.cli_version)
    || body.event_type !== 'scan_complete'
    || !Number.isSafeInteger(body.ts) || Number(body.ts) <= 0) {
    return new Response('Invalid telemetry payload', { status: 400 });
  }

  await env.DB.prepare('INSERT INTO pulses (id, cli_version, event_type, ts) VALUES (?1, ?2, ?3, ?4)')
    .bind(crypto.randomUUID(), body.cli_version, body.event_type, Date.now()).run();
  return new Response('OK');
}
