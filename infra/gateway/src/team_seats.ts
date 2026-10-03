import { decodeBase64Url, normalizeEmail, type OidcEnv, type OidcIdentity } from './oidc.ts';

interface TeamEnv extends OidcEnv {
  JWT_SIGNING_KEY: string;
  YAMLR_PUBKEY_PEM: string;
  EMAIL_SENDER_URL?: string;
  EMAIL_SENDER_TOKEN?: string;
  EMAIL_FROM?: string;
}

const DAY_SECONDS = 24 * 60 * 60;
const MAX_SEATS = 10000;

export function availableTeamSeats(purchased: number, assigned: number, pending: number): number {
  if (![purchased, assigned, pending].every(Number.isSafeInteger) || purchased < 0 || assigned < 0 || pending < 0) return 0;
  return Math.max(0, purchased - assigned - pending);
}

export function teamAccessClaims(identity: OidcIdentity, organizationId: string, seats: number, now: number) {
  return {
    license_version: 1,
    sub: identity.email,
    email: identity.email,
    org_id: organizationId,
    tier: 'team',
    seats: 1,
    org_seats: seats,
    iss: 'yamlr-entitlement',
    aud: 'yamlr',
    iat: now,
    exp: now + DAY_SECONDS,
    jti: crypto.randomUUID(),
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
}

function randomToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

async function tokenHash(token: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token));
  const bytes = new Uint8Array(digest);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function base64Url(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

async function signTeamAccessToken(identity: OidcIdentity, organizationId: string, seats: number, keyPem: string): Promise<string> {
  const header = base64Url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const now = Math.floor(Date.now() / 1000);
  const payload = base64Url(JSON.stringify(teamAccessClaims(identity, organizationId, seats, now)));
  const pem = keyPem.replace('-----BEGIN PRIVATE KEY-----', '').replace('-----END PRIVATE KEY-----', '').replaceAll(/\s/g, '');
  const der = Uint8Array.from(atob(pem), (char) => char.charCodeAt(0));
  const key = await crypto.subtle.importKey('pkcs8', der.buffer as ArrayBuffer,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const signingInput = `${header}.${payload}`;
  const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(signingInput));
  const bytes = new Uint8Array(signature);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return `${signingInput}.${btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')}`;
}

async function sendEmail(env: TeamEnv, recipient: string, subject: string, text: string): Promise<void> {
  if (!env.EMAIL_SENDER_URL || !env.EMAIL_SENDER_TOKEN || !env.EMAIL_FROM) throw new Error('Email delivery is not configured.');
  const endpoint = new URL(env.EMAIL_SENDER_URL);
  if (endpoint.protocol !== 'https:') throw new Error('Email sender endpoint must use HTTPS.');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.EMAIL_SENDER_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: env.EMAIL_FROM, to: recipient, subject, text }),
  });
  if (!response.ok) throw new Error(`Email delivery failed (${response.status}).`);
}

async function isAdmin(env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<boolean> {
  const result = await env.DB.prepare(
    'SELECT 1 AS allowed FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND role=\'admin\' AND revoked_at IS NULL'
  ).bind(organizationId, new URL(env.OIDC_ISSUER).toString().replace(/\/$/, ''), identity.subject).first();
  return !!result;
}

async function listTeam(env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  const member = await env.DB.prepare(
    'SELECT role, has_seat FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND revoked_at IS NULL'
  ).bind(organizationId, new URL(env.OIDC_ISSUER).toString().replace(/\/$/, ''), identity.subject).first() as any;
  if (!member) return json({ error: 'Organization membership required' }, 403);
  const org = await env.DB.prepare(
    'SELECT o.name, o.seat_count, g.status, g.expires_at FROM organizations o JOIN license_grants g ON g.organization_id=o.id AND g.subject_id=o.id WHERE o.id=?1 AND g.plan=\'team\' AND g.status=\'active\' AND g.expires_at>?2'
  ).bind(organizationId, Math.floor(Date.now() / 1000)).first() as any;
  if (!org) return json({ error: 'Active Team subscription not found' }, 404);
  if (member.role !== 'admin') return json({ error: 'Organization administrator role required to view the member roster' }, 403);
  const [members, invitations, counts] = await Promise.all([
    env.DB.prepare('SELECT email, role, has_seat, created_at FROM team_memberships WHERE organization_id=?1 AND revoked_at IS NULL ORDER BY created_at')
      .bind(organizationId).all(),
    env.DB.prepare('SELECT email, expires_at FROM team_invitations WHERE organization_id=?1 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?2 ORDER BY created_at')
      .bind(organizationId, Math.floor(Date.now() / 1000)).all(),
    env.DB.prepare(
      `SELECT
        (SELECT COUNT(*) FROM team_memberships WHERE organization_id=?1 AND has_seat=1 AND revoked_at IS NULL) AS assigned,
        (SELECT COUNT(*) FROM team_invitations WHERE organization_id=?1 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?2) AS pending`
    ).bind(organizationId, Math.floor(Date.now() / 1000)).first() as Promise<any>,
  ]);
  return json({ organization_id: organizationId, name: org.name, role: member.role,
    seats: { purchased: org.seat_count, assigned: counts?.assigned || 0,
      pending: counts?.pending || 0, available: availableTeamSeats(org.seat_count, counts?.assigned || 0, counts?.pending || 0) },
    members: members.results || [], invitations: invitations.results || [] });
}

async function createOrganization(request: Request, env: TeamEnv, identity: OidcIdentity): Promise<Response> {
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const name = typeof body?.name === 'string' ? body.name.trim() : '';
  if (name.length < 2 || name.length > 100 || /[\u0000-\u001f]/.test(name)) {
    return json({ error: 'Organization name must contain 2 to 100 printable characters' }, 400);
  }
  const organizationId = crypto.randomUUID();
  const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
  const now = Math.floor(Date.now() / 1000);
  await env.DB.batch([
    env.DB.prepare('INSERT INTO organizations (id, name, seat_count, created_at) VALUES (?1, ?2, 0, ?3)')
      .bind(organizationId, name, Date.now()),
    env.DB.prepare('INSERT INTO team_memberships (organization_id, issuer, subject, email, role, has_seat, created_at) VALUES (?1, ?2, ?3, ?4, \'admin\', 0, ?5)')
      .bind(organizationId, issuer, identity.subject, identity.email, now),
  ]);
  return json({ organization_id: organizationId, name, role: 'admin', seats: 0 }, 201);
}

async function listOrganizations(env: TeamEnv, identity: OidcIdentity): Promise<Response> {
  const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
  const rows = await env.DB.prepare(
    `SELECT o.id AS organization_id, o.name, o.seat_count, m.role, m.has_seat
     FROM team_memberships m JOIN organizations o ON o.id=m.organization_id
     WHERE m.issuer=?1 AND m.subject=?2 AND m.revoked_at IS NULL ORDER BY m.created_at`
  ).bind(issuer, identity.subject).all();
  return json({ organizations: rows.results || [] });
}

async function createInvitation(request: Request, env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  if (!await isAdmin(env, identity, organizationId)) return json({ error: 'Organization administrator role required' }, 403);
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const email = normalizeEmail(body?.email);
  if (!email) return json({ error: 'A valid developer email is required' }, 400);
  if (!env.EMAIL_SENDER_URL || !env.EMAIL_SENDER_TOKEN || !env.EMAIL_FROM) return json({ error: 'Invitation email is not configured' }, 503);

  const invitation = randomToken();
  const now = Math.floor(Date.now() / 1000);
  const expiresAt = now + 7 * DAY_SECONDS;
  const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
  await env.DB.prepare(
    'UPDATE team_invitations SET revoked_at=?1 WHERE organization_id=?2 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at<=?1'
  ).bind(now, organizationId).run();
  const inserted = await env.DB.prepare(
    `INSERT INTO team_invitations (token_hash, organization_id, email, invited_by, expires_at, created_at)
     SELECT ?1, ?2, ?3, ?4, ?5, ?6
     WHERE EXISTS (
       SELECT 1 FROM license_grants g WHERE g.organization_id=?2 AND g.subject_id=?2 AND g.plan='team' AND g.status='active' AND g.expires_at>?6
         AND g.seat_count > (
           SELECT COUNT(*) FROM team_memberships m WHERE m.organization_id=?2 AND m.has_seat=1 AND m.revoked_at IS NULL
         ) + (
           SELECT COUNT(*) FROM team_invitations i WHERE i.organization_id=?2 AND i.accepted_at IS NULL AND i.revoked_at IS NULL AND i.expires_at>?6
         )
     )
       AND NOT EXISTS (SELECT 1 FROM team_memberships m WHERE m.organization_id=?2 AND m.email=?3 AND m.revoked_at IS NULL)
       AND NOT EXISTS (SELECT 1 FROM team_invitations i WHERE i.organization_id=?2 AND i.email=?3 AND i.accepted_at IS NULL AND i.revoked_at IS NULL AND i.expires_at>?6)`
  ).bind(await tokenHash(invitation), organizationId, email, `${issuer}:${identity.subject}`, expiresAt, now).run();
  if (!inserted.meta?.changes) return json({ error: 'No unassigned Team seat is available, or this developer already has an invitation' }, 409);

  const acceptUrl = new URL('/team/invite', env.APP_ORIGIN);
  acceptUrl.searchParams.set('token', invitation);
  try {
    await sendEmail(env, email, 'You are invited to a Yamlr Team',
      `An organization administrator invited ${email} to a Yamlr Team. Sign in with this verified email and accept the invitation: ${acceptUrl.toString()}\n\nThis invitation expires in seven days.`);
  } catch (error) {
    await env.DB.prepare('UPDATE team_invitations SET revoked_at=?1 WHERE token_hash=?2 AND accepted_at IS NULL')
      .bind(now, await tokenHash(invitation)).run();
    console.error('Team invitation email delivery failed', error instanceof Error ? error.message : 'unknown error');
    return json({ error: 'Invitation could not be delivered' }, 502);
  }
  return json({ invited: true, email, expires_at: expiresAt }, 201);
}

async function acceptInvitation(request: Request, env: TeamEnv, identity: OidcIdentity): Promise<Response> {
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const token = typeof body?.token === 'string' ? body.token : '';
  if (token.length < 32 || token.length > 256) return json({ error: 'Invalid invitation token' }, 400);
  const hash = await tokenHash(token);
  const now = Math.floor(Date.now() / 1000);
  const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
  const invite = await env.DB.prepare(
    'SELECT organization_id, email FROM team_invitations WHERE token_hash=?1 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?2'
  ).bind(hash, now).first() as any;
  if (!invite) return json({ error: 'Invitation is invalid, expired, or already used' }, 410);
  if (invite.email !== identity.email) return json({ error: 'Sign in with the invited verified email address' }, 403);
  const grant = await env.DB.prepare(
    'SELECT seat_count FROM license_grants WHERE organization_id=?1 AND subject_id=?1 AND plan=\'team\' AND status=\'active\' AND expires_at>?2'
  ).bind(invite.organization_id, now).first() as any;
  if (!grant || !Number.isSafeInteger(grant.seat_count) || grant.seat_count < 1) return json({ error: 'Active Team subscription not found' }, 409);

  const results = await env.DB.batch([
    env.DB.prepare(
    `INSERT INTO team_memberships (organization_id, issuer, subject, email, role, has_seat, created_at)
     SELECT ?1, ?2, ?3, ?4, 'member', 1, ?5
     WHERE EXISTS (SELECT 1 FROM team_invitations WHERE token_hash=?6 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?5 AND email=?4)
       AND (
         EXISTS (SELECT 1 FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND has_seat=1 AND revoked_at IS NULL)
         OR (SELECT COUNT(*) FROM team_memberships WHERE organization_id=?1 AND has_seat=1 AND revoked_at IS NULL) <
           (SELECT seat_count FROM license_grants WHERE organization_id=?1 AND subject_id=?1 AND plan='team' AND status='active' AND expires_at>?5)
       )
     ON CONFLICT (organization_id, issuer, subject) DO UPDATE SET
       email=excluded.email, role='member', has_seat=1, revoked_at=NULL, created_at=excluded.created_at`
    ).bind(invite.organization_id, issuer, identity.subject, identity.email, now, hash),
    env.DB.prepare(
      `UPDATE team_invitations SET accepted_at=?1, accepted_issuer=?2, accepted_sub=?3
       WHERE token_hash=?4 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?1
         AND EXISTS (SELECT 1 FROM team_memberships WHERE organization_id=?5 AND issuer=?2 AND subject=?3 AND email=?6 AND has_seat=1 AND revoked_at IS NULL)`
    ).bind(now, issuer, identity.subject, hash, invite.organization_id, identity.email),
  ]);
  if (!results[0]?.meta?.changes || !results[1]?.meta?.changes) {
    if (results[0]?.meta?.changes) {
      await env.DB.prepare('UPDATE team_memberships SET revoked_at=?1 WHERE organization_id=?2 AND issuer=?3 AND subject=?4 AND role=\'member\'')
        .bind(now, invite.organization_id, issuer, identity.subject).run();
    }
    return json({ error: 'Invitation could not be accepted' }, 409);
  }

  const accessToken = await signTeamAccessToken(identity, invite.organization_id, grant.seat_count, env.JWT_SIGNING_KEY);
  const activationUrl = new URL('/team/activate', env.APP_ORIGIN).toString();
  try {
    await sendEmail(env, identity.email, 'Your Yamlr Team seat is ready',
      `Your Yamlr Team seat is active for 24 hours. Activate it in the CLI with:\n\nyamlr auth activate ${accessToken}\n\nAfter activation, sign in to Yamlr to renew the entitlement. Renewal is required at least once every 24 hours. ${activationUrl}`);
  } catch (error) {
    console.error('Team access-token delivery failed', error instanceof Error ? error.message : 'unknown error');
    return json({ error: 'Your seat is assigned, but the activation email could not be delivered. Ask an administrator to resend it.' }, 502);
  }
  return json({ accepted: true, organization_id: invite.organization_id, tier: 'team', expires_at: Math.floor(Date.now() / 1000) + DAY_SECONDS });
}

export async function handleTeamSeats(request: Request, env: TeamEnv, identity: OidcIdentity): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === '/v1/team/invitations/accept' && request.method === 'POST') return acceptInvitation(request, env, identity);
  if (url.pathname === '/v1/team/organizations') {
    if (request.method === 'GET') return listOrganizations(env, identity);
    if (request.method === 'POST') return createOrganization(request, env, identity);
  }
  const match = url.pathname.match(/^\/v1\/team\/organizations\/([^/]+)(?:\/(invitations|members\/seat|members))?$/);
  const accessTokenMatch = url.pathname.match(/^\/v1\/team\/organizations\/([^/]+)\/access-token$/);
  if (accessTokenMatch && request.method === 'POST') return sendCurrentAccessToken(env, identity, decodeURIComponent(accessTokenMatch[1]));
  if (!match) return json({ error: 'Not found' }, 404);
  const organizationId = decodeURIComponent(match[1]);
  const action = match[2];
  if (!action && request.method === 'GET') return listTeam(env, identity, organizationId);
  if (action === 'invitations' && request.method === 'POST') return createInvitation(request, env, identity, organizationId);
  if (action === 'invitations' && request.method === 'DELETE') return revokeInvitation(request, env, identity, organizationId);
  if (action === 'members/seat' && request.method === 'PATCH') return updateSeat(request, env, identity, organizationId);
  if (action === 'members' && request.method === 'DELETE') return revokeMember(request, env, identity, organizationId);
  return json({ error: 'Method not allowed' }, 405);
}

export async function renewTeamAccessToken(request: Request, env: TeamEnv): Promise<Response> {
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const token = typeof body?.token === 'string' ? body.token : '';
  const parts = token.split('.');
  if (parts.length !== 3) return json({ error: 'A valid Team access token is required' }, 401);

  let header: any;
  let claims: any;
  try {
    header = JSON.parse(new TextDecoder().decode(decodeBase64Url(parts[0])));
    claims = JSON.parse(new TextDecoder().decode(decodeBase64Url(parts[1])));
  } catch {
    return json({ error: 'A valid Team access token is required' }, 401);
  }
  if (header.alg !== 'RS256' || claims.license_version !== 1 || claims.iss !== 'yamlr-entitlement' || claims.aud !== 'yamlr' || claims.tier !== 'team' ||
      typeof claims.sub !== 'string' || claims.sub !== normalizeEmail(claims.email) || typeof claims.org_id !== 'string' || !claims.org_id.trim() ||
      claims.seats !== 1 || !Number.isSafeInteger(claims.org_seats) || claims.org_seats < 1 ||
      !Number.isSafeInteger(claims.iat) || claims.iat > Math.floor(Date.now() / 1000) + 60 ||
      !Number.isSafeInteger(claims.exp) || claims.exp <= claims.iat) {
    return json({ error: 'A valid Team access token is required' }, 401);
  }
  try {
    const publicBody = env.YAMLR_PUBKEY_PEM.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '').replaceAll(/\s/g, '');
    const publicDer = Uint8Array.from(atob(publicBody), (char) => char.charCodeAt(0));
    const publicKey = await crypto.subtle.importKey('spki', publicDer.buffer as ArrayBuffer,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    const signedData = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
    const signature = Uint8Array.from(decodeBase64Url(parts[2])).buffer as ArrayBuffer;
    if (!await crypto.subtle.verify('RSASSA-PKCS1-v1_5', publicKey, signature,
      Uint8Array.from(signedData).buffer as ArrayBuffer)) return json({ error: 'A valid Team access token is required' }, 401);
  } catch {
    return json({ error: 'Team token verification is unavailable' }, 503);
  }

  const now = Math.floor(Date.now() / 1000);
  const member = await env.DB.prepare(
    'SELECT 1 AS active FROM team_memberships WHERE organization_id=?1 AND lower(email)=?2 AND has_seat=1 AND revoked_at IS NULL'
  ).bind(claims.org_id, claims.sub).first();
  const grant = await env.DB.prepare(
    'SELECT seat_count FROM license_grants WHERE organization_id=?1 AND subject_id=?1 AND plan=\'team\' AND status=\'active\' AND expires_at>?2'
  ).bind(claims.org_id, now).first() as any;
  if (!member || !grant || !Number.isSafeInteger(grant.seat_count) || grant.seat_count < 1) {
    return json({ error: 'Team seat is inactive or revoked' }, 403);
  }

  const identity: OidcIdentity = { subject: claims.sub, email: claims.sub, emailVerified: true };
  const renewed = await signTeamAccessToken(identity, claims.org_id, grant.seat_count, env.JWT_SIGNING_KEY);
  return json({ token: renewed, expires_at: now + DAY_SECONDS });
}

async function sendCurrentAccessToken(env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  const issuer = new URL(env.OIDC_ISSUER).toString().replace(/\/$/, '');
  const now = Math.floor(Date.now() / 1000);
  const member = await env.DB.prepare(
    'SELECT has_seat FROM team_memberships WHERE organization_id=?1 AND issuer=?2 AND subject=?3 AND email=?4 AND revoked_at IS NULL'
  ).bind(organizationId, issuer, identity.subject, identity.email).first() as any;
  if (!member || member.has_seat !== 1) return json({ error: 'An assigned Team developer seat is required' }, 403);
  const grant = await env.DB.prepare(
    'SELECT seat_count FROM license_grants WHERE organization_id=?1 AND subject_id=?1 AND plan=\'team\' AND status=\'active\' AND expires_at>?2'
  ).bind(organizationId, now).first() as any;
  if (!grant || !Number.isSafeInteger(grant.seat_count) || grant.seat_count < 1) return json({ error: 'Active Team subscription not found' }, 409);
  const token = await signTeamAccessToken(identity, organizationId, grant.seat_count, env.JWT_SIGNING_KEY);
  try {
    await sendEmail(env, identity.email, 'Your Yamlr Team access token',
      `Your Yamlr Team access token is valid for 24 hours. Activate it with:\n\nyamlr auth activate ${token}\n\nTo continue after it expires, sign in to your Yamlr Team account and request a new token.`);
  } catch (error) {
    console.error('Team access-token delivery failed', error instanceof Error ? error.message : 'unknown error');
    return json({ error: 'Access token could not be delivered' }, 502);
  }
  return json({ delivered: true, expires_at: now + DAY_SECONDS });
}

async function revokeInvitation(request: Request, env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  if (!await isAdmin(env, identity, organizationId)) return json({ error: 'Organization administrator role required' }, 403);
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const email = normalizeEmail(body?.email);
  if (!email) return json({ error: 'A valid developer email is required' }, 400);
  const result = await env.DB.prepare(
    'UPDATE team_invitations SET revoked_at=?1 WHERE organization_id=?2 AND email=?3 AND accepted_at IS NULL AND revoked_at IS NULL'
  ).bind(Math.floor(Date.now() / 1000), organizationId, email).run();
  return result.meta?.changes ? json({ revoked: true, email }) : json({ error: 'Pending invitation was not found' }, 404);
}

async function revokeMember(request: Request, env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  if (!await isAdmin(env, identity, organizationId)) return json({ error: 'Organization administrator role required' }, 403);
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const email = normalizeEmail(body?.email);
  if (!email) return json({ error: 'A valid member email is required' }, 400);
  const target = await env.DB.prepare(
    'SELECT role FROM team_memberships WHERE organization_id=?1 AND email=?2 AND revoked_at IS NULL'
  ).bind(organizationId, email).first() as any;
  if (!target) return json({ error: 'Active organization member was not found' }, 404);
  if (target.role === 'admin') {
    const admins = await env.DB.prepare(
      'SELECT COUNT(*) AS count FROM team_memberships WHERE organization_id=?1 AND role=\'admin\' AND revoked_at IS NULL'
    ).bind(organizationId).first() as any;
    if (admins?.count <= 1) return json({ error: 'Transfer administrator access before removing the last administrator' }, 409);
  }
  const now = Math.floor(Date.now() / 1000);
  await env.DB.prepare('UPDATE team_memberships SET revoked_at=?1, has_seat=0 WHERE organization_id=?2 AND email=?3 AND revoked_at IS NULL')
    .bind(now, organizationId, email).run();
  return json({ revoked: true, email, access_expires_within_seconds: DAY_SECONDS });
}

async function updateSeat(request: Request, env: TeamEnv, identity: OidcIdentity, organizationId: string): Promise<Response> {
  if (!await isAdmin(env, identity, organizationId)) return json({ error: 'Organization administrator role required' }, 403);
  let body: any;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const targetEmail = normalizeEmail(body?.email);
  const assigned = body?.assigned;
  if (!targetEmail || typeof assigned !== 'boolean') return json({ error: 'A valid member email and assigned boolean are required' }, 400);
  const now = Math.floor(Date.now() / 1000);
  const update = assigned
    ? `UPDATE team_memberships SET has_seat=1 WHERE organization_id=?1 AND email=?2 AND has_seat=0 AND revoked_at IS NULL
       AND ((SELECT COUNT(*) FROM team_memberships WHERE organization_id=?1 AND has_seat=1 AND revoked_at IS NULL) +
         (SELECT COUNT(*) FROM team_invitations WHERE organization_id=?1 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?3)) <
       (SELECT seat_count FROM license_grants WHERE organization_id=?1 AND subject_id=?1 AND plan='team' AND status='active' AND expires_at>?3)`
    : 'UPDATE team_memberships SET has_seat=0 WHERE organization_id=?1 AND email=?2 AND has_seat=1 AND revoked_at IS NULL';
  const result = await env.DB.prepare(update).bind(organizationId, targetEmail, now).run();
  if (!result.meta?.changes) return json({ error: assigned ? 'No seat is available or the member was not found' : 'Assigned member was not found' }, 409);
  return json({ email: targetEmail, has_seat: assigned });
}

export const teamTestHelpers = { base64Url, MAX_SEATS, DAY_SECONDS };
