import assert from 'node:assert/strict';
import test from 'node:test';

import { availableTeamSeats, teamAccessClaims } from './team_seats.ts';

test('availableTeamSeats accounts for assigned seats and outstanding invitations', () => {
  assert.equal(availableTeamSeats(5, 2, 1), 2);
  assert.equal(availableTeamSeats(1, 1, 0), 0);
  assert.equal(availableTeamSeats(4, 1, 9), 0);
});

test('availableTeamSeats fails closed on invalid counts', () => {
  assert.equal(availableTeamSeats(-1, 0, 0), 0);
  assert.equal(availableTeamSeats(3.5, 1, 0), 0);
  assert.equal(availableTeamSeats(Number.NaN, 0, 0), 0);
});

test('team access claims are named, portable, organization-scoped and expire in one day', () => {
  const now = 1_800_000_000;
  const claims = teamAccessClaims({ subject: 'oidc-user-7', email: 'dev@example.com', emailVerified: true }, 'org-9', 8, now);
  assert.equal(claims.sub, 'dev@example.com');
  assert.equal(claims.license_version, 1);
  assert.equal(claims.email, 'dev@example.com');
  assert.equal(claims.org_id, 'org-9');
  assert.equal(claims.tier, 'team');
  assert.equal(claims.seats, 1);
  assert.equal(claims.org_seats, 8);
  assert.equal(claims.iat, now);
  assert.equal(claims.exp - claims.iat, 24 * 60 * 60);
  assert.equal('machine_id' in claims, false);
});
