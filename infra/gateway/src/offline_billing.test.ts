import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { SQLiteGatewayDatabase } from './sqlite_storage.ts';
import { handleOfflineBillingReceipt } from './offline_billing.ts';
import { applyBillingTransition, GRACE_PERIOD_SECONDS, type BillingTransition } from './billing_core.ts';
import gateway, {type Env} from './index.ts';

const SECRET = 'disposable-test-receipt-secret-32bytes';
const NOW = 1_700_000_000;

async function receipt(value: unknown, secret = SECRET) {
  const body = JSON.stringify(value);
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), {name:'HMAC', hash:'SHA-256'}, false, ['sign']);
  const mac = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body));
  const signature = Buffer.from(mac).toString('hex');
  return new Request('https://gateway.example.test/v1/webhooks/payment', {method:'POST', body,
    headers: {'X-Yamlr-Receipt-Signature': signature}});
}

function fixture() {
  const db = new SQLiteGatewayDatabase(':memory:');
  db.database.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  db.database.exec(`INSERT INTO organizations (id,name,seat_count,created_at) VALUES ('org','Org',3,1);
    INSERT INTO license_grants (subject_id,subject_kind,organization_id,plan,seat_count,status,expires_at,updated_at)
      VALUES ('org','organization','org','team',3,'active',2000000000,1);
    INSERT INTO team_billing (organization_id,stripe_subscription_id,status,current_period_end,updated_at)
      VALUES ('org','offline:contract-1','active',2000000000,1);`);
  const update = {eventId:'offline:event-1', eventType:'operator.renewed', created:NOW,
    organizationId:'org', subscriptionId:'offline:contract-1', status:'active', periodEnd:NOW+86400, seats:5};
  return {db, update};
}

test('Offline receipt adapter updates existing pools without Stripe or an external call', async () => {
  const {db, update} = fixture();
  try {
    assert.equal((await handleOfflineBillingReceipt(await receipt(update), db, SECRET, NOW*1000)).status, 200);
    assert.equal(db.prepare('SELECT seat_count FROM organizations WHERE id=?1').bind('org').first()?.seat_count, 5);
    assert.equal(db.prepare('SELECT expires_at FROM license_grants').first()?.expires_at, NOW+86400);
    assert.equal((await handleOfflineBillingReceipt(await receipt(update), db, SECRET, NOW*1000)).status, 200);
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM team_billing_events').first()?.count, 1);
  } finally {db.close();}
});

test('Offline receipt rejects tampering, unknown organization binding, and future events', async () => {
  const {db, update} = fixture();
  try {
    assert.equal((await handleOfflineBillingReceipt(await receipt(update, 'incorrect-disposable-signing-secret'), db, SECRET, NOW*1000)).status, 401);
    for (const bad of [{...update, organizationId:'other'}, {...update, created:NOW+61}, {...update, seats:10001}, {...update, extra:true}]) {
      assert.equal((await handleOfflineBillingReceipt(await receipt(bad), db, SECRET, NOW*1000)).status, 400);
    }
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM team_billing_events').first()?.count, 0);
  } finally {db.close();}
});

test('Offline failed-payment retries preserve grace, stale events do not override newer grants, cancellation is terminal', async () => {
  const {db, update} = fixture();
  try {
    const failure = {...update, status:'past_due', seats:null};
    await handleOfflineBillingReceipt(await receipt(failure), db, SECRET, NOW*1000);
    await handleOfflineBillingReceipt(await receipt({...failure, eventId:'offline:event-2', created:NOW+10}), db, SECRET, (NOW+10)*1000);
    assert.equal(db.prepare('SELECT expires_at FROM license_grants').first()?.expires_at, NOW+GRACE_PERIOD_SECONDS);
    await handleOfflineBillingReceipt(await receipt({...update, eventId:'offline:event-3', created:NOW+20}), db, SECRET, (NOW+20)*1000);
    await handleOfflineBillingReceipt(await receipt({...failure, eventId:'offline:old', created:NOW-1}), db, SECRET, (NOW+30)*1000);
    assert.equal(db.prepare('SELECT status FROM license_grants').first()?.status, 'active');
    await handleOfflineBillingReceipt(await receipt({...update, eventId:'offline:event-4', status:'canceled', created:NOW+40}), db, SECRET, (NOW+40)*1000);
    await handleOfflineBillingReceipt(await receipt({...update, eventId:'offline:event-5', created:NOW+50}), db, SECRET, (NOW+50)*1000);
    assert.equal(db.prepare('SELECT status FROM license_grants').first()?.status, 'revoked');
  } finally {db.close();}
});

test('Shared gateway routes to explicit offline billing and disables Stripe checkout', async () => {
  const {db, update} = fixture();
  try {
    const env = {DB:db, BILLING_PROVIDER:'offline', OFFLINE_BILLING_SECRET:SECRET} as Env;
    assert.equal((await gateway.fetch(await receipt(update), env)).status, 200);
    assert.equal((await gateway.fetch(new Request('https://gateway.example.test/v1/payment/checkout', {method:'POST'}), env)).status, 409);
  } finally {db.close();}
});

test('Concurrent renewal cannot reactivate a canceled pool after reading stale state', async () => {
  const {db, update} = fixture();
  try {
    await Promise.all([
      applyBillingTransition(db, {...update, status:'canceled'} as BillingTransition, NOW*1000),
      applyBillingTransition(db, {...update, eventId:'offline:newer', created:NOW+1} as BillingTransition, (NOW+1)*1000),
    ]);
    assert.equal(db.prepare('SELECT status FROM team_billing').first()?.status, 'canceled');
    assert.equal(db.prepare('SELECT status FROM license_grants').first()?.status, 'revoked');
    assert.equal(db.prepare('SELECT expires_at FROM license_grants').first()?.expires_at, NOW);
  } finally {db.close();}
});
