import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  handleTeamBillingEvent,
  initializeTeamBilling,
  suspendExpiredTeamBilling,
  teamBillingGracePeriodSeconds,
} from './stripe_lifecycle.ts';

class D1TestDatabase {
  private readonly database = new DatabaseSync(':memory:');

  constructor() {
    this.database.exec(readFileSync(fileURLToPath(new URL('../schema.sql', import.meta.url)), 'utf8'));
  }

  prepare(sql: string) {
    const database = this.database;
    let values: unknown[] = [];
    return {
      bind(...parameters: unknown[]) { values = parameters; return this; },
      first() { return database.prepare(sql).get(...(values as any[])); },
      run() {
        const result = database.prepare(sql).run(...(values as any[]));
        return { meta: { changes: Number(result.changes) } };
      },
    };
  }

  async batch(statements: any[]) {
    this.database.exec('BEGIN');
    try {
      const results = statements.map(statement => statement.run());
      this.database.exec('COMMIT');
      return results;
    } catch (error) {
      this.database.exec('ROLLBACK');
      throw error;
    }
  }

  close() { this.database.close(); }
}

function fixture() {
  const DB = new D1TestDatabase();
  DB.prepare('INSERT INTO organizations (id, name, created_at, seat_count) VALUES (?1, ?2, ?3, ?4)')
    .bind('org-1', 'Org 1', 1, 3).run();
  DB.prepare(`INSERT INTO license_grants
    (subject_id, subject_kind, organization_id, plan, seat_count, status, expires_at, updated_at)
    VALUES (?1, 'organization', ?1, 'team', 3, 'active', ?2, ?3)`)
    .bind('org-1', 2_000_000_000, 1).run();
  DB.prepare(`INSERT INTO team_billing
    (organization_id, stripe_subscription_id, status, current_period_end, grace_until, updated_at)
    VALUES ('org-1', 'sub_1', 'active', ?1, NULL, ?2)`)
    .bind(1_700_000_100, 1).run();
  return { DB, env: { DB } };
}

function event(id: string, type: string, created: number, object: Record<string, any>) {
  return { id, type, created, data: { object } };
}

async function billingState(DB: D1TestDatabase) {
  const billing = await DB.prepare('SELECT * FROM team_billing WHERE organization_id=?1').bind('org-1').first();
  const grant = await DB.prepare('SELECT * FROM license_grants WHERE subject_id=?1').bind('org-1').first();
  const organization = await DB.prepare('SELECT seat_count FROM organizations WHERE id=?1').bind('org-1').first();
  return { billing, grant, organization } as any;
}

describe('Team subscription billing lifecycle', () => {
  it('grants one seven-day payment grace period and does not extend it on retries', async () => {
    const { DB, env } = fixture();
    const failedAt = 1_700_000_000;
    DB.prepare('UPDATE team_billing SET current_period_end=?1 WHERE organization_id=?2')
      .bind(failedAt + 45 * 24 * 60 * 60, 'org-1').run();
    const failure = event('evt-fail-1', 'invoice.payment_failed', failedAt, { subscription: 'sub_1' });
    await handleTeamBillingEvent(failure, env, failedAt * 1000);
    const first = await billingState(DB);
    assert.equal(first.billing.status, 'past_due');
    assert.equal(first.billing.grace_until, failedAt + teamBillingGracePeriodSeconds);
    assert.equal(first.grant.status, 'active');
    assert.equal(first.grant.expires_at, failedAt + teamBillingGracePeriodSeconds);

    await handleTeamBillingEvent(failure, env, (failedAt + 86_400) * 1000);
    await handleTeamBillingEvent(
      event('evt-fail-2', 'invoice.payment_failed', failedAt + 86_400, { subscription: 'sub_1' }),
      env,
      (failedAt + 86_400) * 1000,
    );
    const retried = await billingState(DB);
    assert.equal(retried.billing.grace_until, first.billing.grace_until);
    assert.equal(retried.grant.expires_at, first.grant.expires_at);
    DB.close();
  });

  it('deduplicates events and ignores stale failures after a successful renewal', async () => {
    const { DB, env } = fixture();
    const paidAt = 1_700_100_000;
    await handleTeamBillingEvent(
      event('evt-paid-1', 'invoice.paid', paidAt, {
        subscription: 'sub_1', lines: { data: [{ period: { end: paidAt + 2_592_000 } }] },
      }),
      env,
      paidAt * 1000,
    );
    await handleTeamBillingEvent(
      event('evt-fail-old', 'invoice.payment_failed', paidAt - 20, { subscription: 'sub_1' }),
      env,
      (paidAt + 1) * 1000,
    );
    const state = await billingState(DB);
    assert.equal(state.billing.status, 'active');
    assert.equal(state.billing.grace_until, null);
    assert.equal(state.grant.expires_at, paidAt + 2_592_000);
    assert.equal(
      (await DB.prepare('SELECT COUNT(*) AS count FROM team_billing_events').first() as any).count,
      2,
    );
    DB.close();
  });

  it('keeps a payment-failed subscription in grace until Stripe confirms it is active', async () => {
    const { DB, env } = fixture();
    const failedAt = 1_700_000_000;
    await handleTeamBillingEvent(
      event('evt-fail-before-paid', 'invoice.payment_failed', failedAt, { subscription: 'sub_1' }),
      env,
      failedAt * 1000,
    );
    await handleTeamBillingEvent(
      event('evt-paid-retry', 'invoice.paid', failedAt + 10, {
        subscription: 'sub_1', lines: { data: [{ period: { end: failedAt + 2_592_000 } }] },
      }),
      env,
      (failedAt + 10) * 1000,
    );
    let state = await billingState(DB);
    assert.equal(state.billing.status, 'past_due');
    assert.equal(state.grant.expires_at, failedAt + teamBillingGracePeriodSeconds);

    await handleTeamBillingEvent(
      event('evt-sub-active', 'customer.subscription.updated', failedAt + 20, {
        id: 'sub_1', status: 'active',
        items: { data: [{ quantity: 3, current_period_end: failedAt + 2_592_000 }] },
      }),
      env,
      (failedAt + 20) * 1000,
    );
    state = await billingState(DB);
    assert.equal(state.billing.status, 'active');
    assert.equal(state.billing.grace_until, null);
    assert.equal(state.grant.expires_at, failedAt + 2_592_000);
    DB.close();
  });

  it('updates contracted seats and revokes the grant on subscription deletion', async () => {
    const { DB, env } = fixture();
    const updatedAt = 1_700_000_010;
    await handleTeamBillingEvent(
      event('evt-sub-updated', 'customer.subscription.updated', updatedAt, {
        id: 'sub_1', status: 'active',
        items: { data: [{ quantity: 7, current_period_end: 1_700_100_000 }] },
      }),
      env,
      updatedAt * 1000,
    );
    let state = await billingState(DB);
    assert.equal(state.grant.seat_count, 7);
    assert.equal(state.organization.seat_count, 7);

    const deletedAt = updatedAt + 10;
    await handleTeamBillingEvent(
      event('evt-sub-deleted', 'customer.subscription.deleted', deletedAt, { id: 'sub_1', status: 'canceled' }),
      env,
      deletedAt * 1000,
    );
    state = await billingState(DB);
    assert.equal(state.billing.status, 'canceled');
    assert.equal(state.grant.status, 'revoked');
    assert.equal(state.grant.expires_at, deletedAt);
    DB.close();
  });

  it('rejects a subscription quantity outside the paid seat-pool limits', async () => {
    const { DB, env } = fixture();
    const response = await handleTeamBillingEvent(
      event('evt-seat-limit', 'customer.subscription.updated', 1_700_000_010, {
        id: 'sub_1', status: 'active', items: { data: [{ quantity: 10_001, current_period_end: 1_700_100_000 }] },
      }),
      env,
      1_700_000_010_000,
    );
    assert.equal(response?.status, 400);
    const state = await billingState(DB);
    assert.equal(state.billing.status, 'active');
    assert.equal(state.grant.seat_count, 3);
    DB.close();
  });

  it('suspends the Team grant when the seven-day grace expires', async () => {
    const { DB, env } = fixture();
    const failedAt = 1_700_000_000;
    await handleTeamBillingEvent(
      event('evt-fail-expiry', 'invoice.payment_failed', failedAt, { subscription: 'sub_1' }),
      env,
      failedAt * 1000,
    );
    await suspendExpiredTeamBilling(DB, (failedAt + teamBillingGracePeriodSeconds) * 1000);
    const state = await billingState(DB);
    assert.equal(state.billing.status, 'suspended');
    assert.equal(state.grant.status, 'suspended');
    DB.close();
  });

  it('does not change unrelated subscriptions or unsupported events', async () => {
    const { DB, env } = fixture();
    assert.equal(await handleTeamBillingEvent(event('evt-unrelated', 'invoice.paid', 1_700_000_001, { subscription: 'sub_other' }), env), null);
    assert.equal(await handleTeamBillingEvent(event('evt-unsupported', 'invoice.created', 1_700_000_001, { subscription: 'sub_1' }), env), null);
    const state = await billingState(DB);
    assert.equal(state.billing.status, 'active');
    DB.close();
  });

  it('uses Stripe current period end and validates the subscription before activating a seat pool', async () => {
    const { DB, env } = fixture();
    const currentPeriodEnd = 1_700_200_000;
    const fetcher = async (url: string | URL | Request) => {
      assert.equal(String(url), 'https://api.stripe.com/v1/subscriptions/sub_2');
      return new Response(JSON.stringify({
        id: 'sub_2', status: 'active', items: { data: [{ quantity: 8, current_period_end: currentPeriodEnd }] },
        metadata: { org_id: 'org-1', seats: '8' },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    };
    const expiresAt = await initializeTeamBilling(
      { DB, STRIPE_SECRET_KEY: 'sk_test_key' }, 'org-1', 8, 'sub_2', 1_700_000_000_000,
      fetcher as typeof fetch,
    );
    assert.equal(expiresAt, currentPeriodEnd);
    const billing = await DB.prepare('SELECT * FROM team_billing WHERE organization_id=?1').bind('org-1').first() as any;
    assert.equal(billing.stripe_subscription_id, 'sub_2');
    assert.equal(billing.current_period_end, currentPeriodEnd);
    DB.close();
  });
});
