import { beginOidcLogin, completeOidcLogin, currentOidcIdentity, endOidcSession, type OidcIdentity } from './oidc.ts';
import { handleTeamSeats, renewTeamAccessToken } from './team_seats.ts';
import { addTeamSubscriptionMetadata, handleTeamPaymentWebhook, initializeTeamBilling, suspendExpiredTeamBilling } from './stripe_lifecycle.ts';
import { handlePulse } from './pulse.ts';
import type { GatewayDatabase } from './storage.ts';
import { handleOfflineBillingReceipt } from './offline_billing.ts';

export interface Env {
  DB: GatewayDatabase;
  YAMLR_PUBKEY_PEM: string;
  PULSE_API_KEY: string;
  JWT_SIGNING_KEY: string;
  OIDC_ISSUER: string;
  OIDC_CLIENT_ID: string;
  OIDC_CLIENT_SECRET: string;
  OIDC_REDIRECT_URI: string;
  APP_ORIGIN: string;
  EMAIL_SENDER_URL?: string;
  EMAIL_SENDER_TOKEN?: string;
  EMAIL_FROM?: string;
  STRIPE_SECRET_KEY?: string;
  STRIPE_TEAM_PRICE_ID?: string;
  STRIPE_SUCCESS_URL?: string;
  STRIPE_CANCEL_URL?: string;
  BILLING_PROVIDER?: 'stripe' | 'offline';
  OFFLINE_BILLING_SECRET?: string;
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
  const bytes = new TextEncoder().encode(str);
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
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

function corsResponse(request: Request, env: Env, response: Response): Response {
  const origin = request.headers.get('Origin');
  if (!origin || origin !== new URL(env.APP_ORIGIN).origin) return response;
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', origin);
  headers.set('Access-Control-Allow-Credentials', 'true');
  headers.set('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');
  headers.append('Vary', 'Origin');
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function hasTrustedOrigin(request: Request, env: Env): boolean {
  const origin = request.headers.get('Origin');
  return !!origin && origin === new URL(env.APP_ORIGIN).origin;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (method === 'OPTIONS' && (path.startsWith('/v1/team') || path === '/v1/payment/checkout' || path === '/v1/auth/logout' || path === '/v1/auth/renew')) {
      const origin = request.headers.get('Origin');
      if (!origin || origin !== new URL(env.APP_ORIGIN).origin) return new Response('Forbidden', { status: 403 });
      return corsResponse(request, env, new Response(null, { status: 204 }));
    }

    // Routing Table
    if (path === '/health') return new Response('OK');
    if (path === '/v1/oidc/login') return beginOidcLogin(request, env);
    if (path === '/v1/oidc/callback') return completeOidcLogin(request, env);
    if (path === '/v1/auth/logout' && method === 'POST') {
      if (!hasTrustedOrigin(request, env)) return new Response('Forbidden', { status: 403 });
      return corsResponse(request, env, await endOidcSession(request, env));
    }
    if (path === '/v1/auth/renew' && method === 'POST') { await suspendExpiredTeamBilling(env.DB); return corsResponse(request, env, await renewTeamAccessToken(request, env)); }
    if (path.startsWith('/v1/team')) {
      if (!hasTrustedOrigin(request, env)) return new Response('Forbidden', { status: 403 });
      const identity = await currentOidcIdentity(request, env);
      if (!identity) return corsResponse(request, env, new Response(JSON.stringify({ error: 'Sign-in required' }), {
        status: 401, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
      }));
      return corsResponse(request, env, await handleTeamSeats(request, env, identity));
    }
    if (path === '/v1/pubkey') return this.handlePubkey(env);
    if (path === '/v1/pulse' && method === 'POST') return this.handlePulse(request, env);
    if (path === '/v1/admin/stats') return this.handleAdminStats(request, env);
    if (path === '/v1/webhooks/payment' && method === 'POST') return this.handlePaymentWebhook(request, env);
    if (path === '/v1/payment/checkout' && method === 'POST') {
      if (env.BILLING_PROVIDER === 'offline') return new Response('Checkout is operator-managed', {status: 409});
      if (!hasTrustedOrigin(request, env)) return new Response('Forbidden', { status: 403 });
      const identity = await currentOidcIdentity(request, env);
      if (!identity) return corsResponse(request, env, new Response(JSON.stringify({ error: 'Sign-in required' }), {
        status: 401, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
      }));
      return corsResponse(request, env, await this.handleCheckoutSession(request, env, identity));
    }

    return new Response('Not Found', { status: 404 });
  },

  async handleCheckoutSession(request: Request, env: Env, identity: OidcIdentity): Promise<Response> {
    let body: any;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: 'Invalid JSON body' }), { status: 400 });
    }
    const { tier: requestedTier, seats = 1, organization_id: organizationId } = body;
    const tier = String(requestedTier || 'team').trim().toLowerCase();
    const canonicalTier = tier === 'pro' ? 'team' : tier;
    if (canonicalTier === 'enterprise') {
      return new Response(JSON.stringify({ error: 'Enterprise licensing is sales-led' }), { status: 409 });
    }
    if (canonicalTier !== 'team') {
      return new Response(JSON.stringify({ error: 'Individual is free and does not require checkout' }), { status: 400 });
    }
    if (!Number.isSafeInteger(seats) || seats < 1 || seats > 10000) {
      return new Response(JSON.stringify({ error: 'Seat count must be between 1 and 10000' }), { status: 400 });
    }
    if (typeof organizationId !== 'string' || !organizationId.trim()) {
      return new Response(JSON.stringify({ error: 'Create or select a Yamlr organization before checkout' }), { status: 400 });
    }
    const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
    const isAdmin = await env.DB.prepare(
      'SELECT 1 AS allowed FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND role=\'admin\' AND revoked_at IS NULL'
    ).bind(organizationId, issuer, identity.subject).first();
    if (!isAdmin) return new Response(JSON.stringify({ error: 'Organization administrator role required' }), { status: 403 });
    if (!env.STRIPE_SECRET_KEY || !env.STRIPE_TEAM_PRICE_ID ||
        !env.STRIPE_SUCCESS_URL || !env.STRIPE_CANCEL_URL) {
      return new Response(JSON.stringify({ error: 'Team checkout is not configured' }), { status: 503 });
    }

    const form = new URLSearchParams({
      mode: 'subscription',
      'line_items[0][price]': env.STRIPE_TEAM_PRICE_ID,
      'line_items[0][quantity]': String(seats),
      success_url: env.STRIPE_SUCCESS_URL,
      cancel_url: env.STRIPE_CANCEL_URL,
      'metadata[tier]': 'team',
      'metadata[seats]': String(seats),
      'metadata[org_id]': organizationId,
      'metadata[owner_issuer]': issuer,
      'metadata[owner_sub]': identity.subject,
    });
    addTeamSubscriptionMetadata(form, organizationId, seats, issuer, identity.subject);
    form.set('customer_email', identity.email);
    const checkoutResponse = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Idempotency-Key': crypto.randomUUID(),
      },
      body: form,
    });
    const checkout = await checkoutResponse.json() as any;
    if (!checkoutResponse.ok || !checkout?.url) {
      console.error('Stripe checkout session creation failed', checkout?.error?.type || checkoutResponse.status);
      return new Response(JSON.stringify({ error: 'Unable to create Team checkout session' }), { status: 502 });
    }

    await env.DB.prepare(
      'INSERT INTO license_events (event_id, user_id, machine_id, event_type, metadata, ts) VALUES (?1, ?2, ?3, ?4, ?5, ?6)'
    ).bind(checkout.id, identity.email, null, 'CHECKOUT_INITIATED', JSON.stringify({ tier: 'team', seats, organization_id: organizationId }), Date.now()).run();

    return new Response(JSON.stringify({ url: checkout.url, session_id: checkout.id }), {
      headers: { 'Content-Type': 'application/json' }
    });
  },

  async handlePaymentWebhook(request: Request, env: Env): Promise<Response> {
    if (env.BILLING_PROVIDER === 'offline') return handleOfflineBillingReceipt(request, env.DB, env.OFFLINE_BILLING_SECRET);
    if (env.BILLING_PROVIDER && env.BILLING_PROVIDER !== 'stripe') return new Response('Unsupported billing provider', {status: 503});
    const authHeader = request.headers.get('Authorization') || request.headers.get('X-Webhook-Secret');
    const webhookSecret = (env as any).STRIPE_WEBHOOK_SECRET;
    if (!webhookSecret) return new Response('Webhook secret is not configured', { status: 503 });
    if (authHeader !== `Bearer ${webhookSecret}` && authHeader !== webhookSecret) {
      return new Response('Unauthorized Webhook', { status: 401 });
    }
    const body = await request.json();
    if (body.type !== 'checkout.session.completed') return handleTeamPaymentWebhook(body, env);
    if (body.type === 'checkout.session.completed') {
      const sessionObj = body.data?.object || {};
      const metadata = sessionObj.metadata || {};
      const organizationId = metadata?.org_id || metadata?.team_id || sessionObj.customer;
      const requestedTier = String(metadata?.tier || 'team').trim().toLowerCase();
      const tier = requestedTier === 'pro' ? 'team' : requestedTier;
      const userEmail = String(sessionObj.customer_details?.email || metadata?.email || '').trim();
      const parsedSeats = metadata?.seats == null ? null : Number.parseInt(metadata.seats, 10);
      const seats = tier === 'team' ? (parsedSeats ?? 1) : parsedSeats;
      const nodes = metadata?.nodes == null ? null : Number.parseInt(metadata.nodes, 10);
      const ownerIssuer = String(metadata?.owner_issuer || '').trim();
      const ownerSubject = String(metadata?.owner_sub || '').trim();

      if (!userEmail.includes('@')) return new Response('Missing valid purchaser email', { status: 400 });
      if (!organizationId) return new Response('Missing organization identity', { status: 400 });
      if (!['team', 'enterprise'].includes(tier)) {
        return new Response('Unsupported license tier', { status: 400 });
      }
      if (tier === 'team') {
        if (!ownerIssuer || !ownerSubject || !Number.isSafeInteger(seats) || !seats || seats > 10000) {
          return new Response('Team checkout is missing verified organization ownership or seat count', { status: 400 });
        }
        const owner = await env.DB.prepare(
          'SELECT 1 AS allowed FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND role=\'admin\' AND revoked_at IS NULL'
        ).bind(organizationId, ownerIssuer, ownerSubject).first();
        if (!owner) return new Response('Team checkout owner is not an organization administrator', { status: 403 });
      }
      if ((seats != null && (!Number.isSafeInteger(seats) || seats < 1)) ||
          (nodes !== null && (!Number.isSafeInteger(nodes) || nodes < 1))) {
        return new Response('Invalid contracted seat or node count', { status: 400 });
      }
      if (tier === 'enterprise' && seats == null && nodes == null) {
        return new Response('Enterprise requires contracted seats or nodes', { status: 400 });
      }

      const subjectId = organizationId;
      const subjectKind = 'organization';
      try {
        await env.DB.prepare(
          'INSERT INTO organizations (id, name, stripe_customer_id, seat_count, created_at) VALUES (?1, ?2, ?3, ?4, ?5) ON CONFLICT(id) DO UPDATE SET stripe_customer_id = ?3, seat_count = ?4'
        ).bind(organizationId, metadata?.organization_name || organizationId, sessionObj.customer || null, tier === 'team' ? seats : seats, Date.now()).run();

        const nowMs = Date.now();
        const expiresAt = tier === 'team'
          ? await initializeTeamBilling(env, organizationId, seats, sessionObj.subscription, nowMs)
          : Math.floor(nowMs / 1000) + (365 * 24 * 3600);
        const grantSeats = seats;
        await env.DB.prepare(
          'INSERT INTO license_grants (subject_id, subject_kind, organization_id, plan, seat_count, node_count, status, expires_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, \'active\', ?7, ?8) ON CONFLICT(subject_id) DO UPDATE SET subject_kind=?2, organization_id=?3, plan=?4, seat_count=?5, node_count=?6, status=\'active\', expires_at=?7, updated_at=?8'
        ).bind(subjectId, subjectKind, organizationId, tier, grantSeats, nodes, expiresAt, nowMs).run();


        await env.DB.prepare(
          'INSERT INTO licenses (clerk_user_id, email, plan, organization_id, activated_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(clerk_user_id) DO UPDATE SET email=?2, plan=?3, organization_id=?4, activated_at=?5, updated_at=?6'
        ).bind(subjectId, userEmail, tier, organizationId, nowMs, nowMs).run();

        const iat = Math.floor(nowMs / 1000);
        const licensePayload: Record<string, unknown> = {
          license_version: 1,
          sub: tier === 'team' ? ownerSubject : subjectId,
          org_id: organizationId,
          tier,
          iss: 'yamlr-entitlement',
          aud: 'yamlr',
          iat,
          exp: expiresAt,
        };
        if (tier === 'team') {
          licensePayload.seats = 1;
          licensePayload.org_seats = seats;
          licensePayload.email = userEmail.toLowerCase();
        } else {
          licensePayload.email = userEmail;
          if (metadata?.seats != null) licensePayload.seats = seats;
          if (nodes != null) licensePayload.nodes = nodes;
        }

        // Team grants issue per-developer access tokens only after a verified invite is accepted.
        // Enterprise's offline grant remains issued through the contracted fulfillment workflow.
        if (tier === 'enterprise') await signJwt(licensePayload, env.JWT_SIGNING_KEY);

        await env.DB.prepare(
          'INSERT INTO license_events (event_id, user_id, machine_id, event_type, metadata, ts) VALUES (?1, ?2, ?3, ?4, ?5, ?6)'
        ).bind(crypto.randomUUID(), subjectId, null, 'LICENSE_FULFILLED', JSON.stringify({ tier, organization_id: organizationId, seats, nodes, exp: expiresAt }), nowMs).run();
      } catch (e: any) {
        console.error('License fulfillment error:', e);
        return new Response('License fulfillment failed', { status: 500 });
      }
    }
    return new Response(JSON.stringify({ status: 'PROCESSED' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  },


  async handleAdminStats(request: Request, env: Env): Promise<Response> {
    const activeLicenses = await env.DB.prepare('SELECT COUNT(*) as count FROM licenses WHERE plan != "free"').first();
    const totalEvents = await env.DB.prepare('SELECT COUNT(*) as count FROM license_events').first();
    const pulseCount = await env.DB.prepare('SELECT COUNT(*) as count FROM pulses').first();
    
    return new Response(JSON.stringify({
      active_licenses: activeLicenses?.count || 0,
      forensic_events: totalEvents?.count || 0,
      pulses_recorded: pulseCount?.count || 0,
      status: "HEALTHY"
    }), { headers: { 'Content-Type': 'application/json' } });
  },

  async handlePubkey(env: Env): Promise<Response> {
    return new Response(env.YAMLR_PUBKEY_PEM || 'Public key not configured', { headers: { 'Content-Type': 'text/plain' } });
  },

  async handlePulse(request: Request, env: Env): Promise<Response> {
    return handlePulse(request, env);
  },

};
