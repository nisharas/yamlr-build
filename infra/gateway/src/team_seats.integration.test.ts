import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { SQLiteGatewayDatabase } from './sqlite_storage.ts';

import { handleTeamSeats, renewTeamAccessToken } from './team_seats.ts';


test('Team invite acceptance consumes one seat and revocation blocks renewal', async () => {
  const database = new SQLiteGatewayDatabase(':memory:');
  database.database.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  const issuer = 'https://identity.example.test';
  const now = Math.floor(Date.now() / 1000);
  database.prepare('INSERT INTO identities (issuer, subject, email, email_verified, updated_at) VALUES (?1, ?2, ?3, 1, ?4)')
    .bind(issuer, 'admin-sub', 'admin@example.test', now).run();
  database.prepare('INSERT INTO identities (issuer, subject, email, email_verified, updated_at) VALUES (?1, ?2, ?3, 1, ?4)')
    .bind(issuer, 'developer-sub', 'developer@example.test', now).run();

  const env: any = {
    DB: database,
    OIDC_ISSUER: issuer,
    OIDC_CLIENT_ID: 'yamlr-test',
    OIDC_CLIENT_SECRET: 'not-used-in-this-test',
    OIDC_REDIRECT_URI: 'https://gateway.example.test/v1/oidc/callback',
    APP_ORIGIN: 'https://yamlr.example.test',
    JWT_SIGNING_KEY: readFileSync(new URL('../../../native_core/tests/fixtures/licensing_test_private.pem', import.meta.url), 'utf8'),
    YAMLR_PUBKEY_PEM: readFileSync(new URL('../../../native_core/tests/fixtures/licensing_test_public.pem', import.meta.url), 'utf8'),
    EMAIL_SENDER_URL: 'https://email.example.test/send',
    EMAIL_SENDER_TOKEN: 'email-token',
    EMAIL_FROM: 'Yamlr <licenses@example.test>',
  };
  const admin = { subject: 'admin-sub', email: 'admin@example.test', emailVerified: true as const };
  const developer = { subject: 'developer-sub', email: 'developer@example.test', emailVerified: true as const };
  const emailBodies: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_input, init) => {
    emailBodies.push(String(init?.body || ''));
    return new Response('{}', { status: 200 });
  };

  try {
    const create = await handleTeamSeats(new Request('https://gateway.example.test/v1/team/organizations', {
      method: 'POST', body: JSON.stringify({ name: 'Example Team' }),
    }), env, admin);
    assert.equal(create.status, 201);
    const { organization_id: organizationId } = await create.json() as any;
    database.prepare('UPDATE organizations SET seat_count=1 WHERE id=?1').bind(organizationId).run();
    database.prepare(`INSERT INTO license_grants (subject_id, subject_kind, organization_id, plan, seat_count, status, expires_at, updated_at)
      VALUES (?1, 'organization', ?1, 'team', 1, 'active', ?2, ?3)`)
      .bind(organizationId, now + 31_536_000, now).run();

    const invite = await handleTeamSeats(new Request(`https://gateway.example.test/v1/team/organizations/${organizationId}/invitations`, {
      method: 'POST', body: JSON.stringify({ email: 'Developer@example.test' }),
    }), env, admin);
    assert.equal(invite.status, 201);
    const inviteToken = new URL(JSON.parse(emailBodies[0]).text.match(/https:\/\/[^\s]+/)[0]).searchParams.get('token');
    assert.ok(inviteToken);

    const adminSeat = await handleTeamSeats(new Request(`https://gateway.example.test/v1/team/organizations/${organizationId}/members/seat`, {
      method: 'PATCH', body: JSON.stringify({ email: admin.email, assigned: true }),
    }), env, admin);
    assert.equal(adminSeat.status, 409, 'pending invite reserves the only paid seat');

    const wrongIdentity = await handleTeamSeats(new Request('https://gateway.example.test/v1/team/invitations/accept', {
      method: 'POST', body: JSON.stringify({ token: inviteToken }),
    }), env, { ...developer, email: 'different@example.test' });
    assert.equal(wrongIdentity.status, 403);

    const accepted = await handleTeamSeats(new Request('https://gateway.example.test/v1/team/invitations/accept', {
      method: 'POST', body: JSON.stringify({ token: inviteToken }),
    }), env, developer);
    assert.equal(accepted.status, 200);
    assert.equal(emailBodies.length, 2, 'the accepted developer receives an activation token');
    const accessToken = emailBodies[1].match(/yamlr auth activate ([^\s\\]+)/)?.[1];
    assert.ok(accessToken);

    const overview = await handleTeamSeats(new Request(`https://gateway.example.test/v1/team/organizations/${organizationId}`, {
      method: 'GET',
    }), env, admin);
    const team = await overview.json() as any;
    assert.deepEqual(team.seats, { purchased: 1, assigned: 1, pending: 0, available: 0 });
    assert.equal(team.members.find((member: any) => member.email === developer.email).has_seat, 1);
    assert.equal(team.members.find((member: any) => member.email === admin.email).has_seat, 0);

    const renewed = await renewTeamAccessToken(new Request('https://gateway.example.test/v1/auth/renew', {
      method: 'POST', body: JSON.stringify({ token: accessToken }),
    }), env);
    assert.equal(renewed.status, 200);
    const newToken = (await renewed.json() as any).token;
    assert.notEqual(newToken, accessToken);

    const removed = await handleTeamSeats(new Request(`https://gateway.example.test/v1/team/organizations/${organizationId}/members`, {
      method: 'DELETE', body: JSON.stringify({ email: developer.email }),
    }), env, admin);
    assert.equal(removed.status, 200);
    const blocked = await renewTeamAccessToken(new Request('https://gateway.example.test/v1/auth/renew', {
      method: 'POST', body: JSON.stringify({ token: newToken }),
    }), env);
    assert.equal(blocked.status, 403);
  } finally {
    globalThis.fetch = originalFetch;
    database.database.close();
  }
});
