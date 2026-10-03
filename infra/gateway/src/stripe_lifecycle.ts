import { applyBillingTransition, GRACE_PERIOD_SECONDS } from './billing_core.ts';
import type { GatewayDatabase } from './storage.ts';

interface BillingEvent {
  id?: unknown;
  type?: unknown;
  created?: unknown;
  data?: { object?: Record<string, any> };
}

type BillingDatabase = GatewayDatabase;

interface BillingEnvironment {
  DB: BillingDatabase;
  STRIPE_SECRET_KEY?: string;
}

interface BillingRecord {
  organization_id: string;
  status: string;
  current_period_end: number;
  grace_until: number | null;
}

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}

function subscriptionIdFor(event: BillingEvent, object: Record<string, any>): string | null {
  if (String(event.type).startsWith('customer.subscription.')) {
    return typeof object.id === 'string' ? object.id : null;
  }
  const direct = object.subscription;
  if (typeof direct === 'string') return direct;
  if (typeof direct?.id === 'string') return direct.id;
  const parent = object.parent?.subscription_details?.subscription;
  if (typeof parent === 'string') return parent;
  return typeof parent?.id === 'string' ? parent.id : null;
}

function invoicePeriodEnd(object: Record<string, any>): number | null {
  const ends = (object.lines?.data || [])
    .map((line: any) => line?.period?.end)
    .filter((value: unknown): value is number => Number.isSafeInteger(value) && Number(value) > 0);
  return ends.length ? Math.max(...ends) : null;
}

function subscriptionPeriodEnd(object: Record<string, any>): number | null {
  const itemEnds = (object.items?.data || [])
    .map((item: any) => item?.current_period_end)
    .filter((value: unknown): value is number => Number.isSafeInteger(value) && Number(value) > 0);
  if (itemEnds.length) return Math.min(...itemEnds);
  return Number.isSafeInteger(object.current_period_end) && object.current_period_end > 0
    ? object.current_period_end
    : null;
}

function subscriptionSeats(object: Record<string, any>): number | null {
  const items = object.items?.data;
  if (!Array.isArray(items) || items.length !== 1) return null;
  const quantity = items[0]?.quantity;
  return Number.isSafeInteger(quantity) && quantity > 0 && quantity <= 10_000 ? quantity : null;
}

export async function handleTeamBillingEvent(
  event: BillingEvent,
  env: BillingEnvironment,
  nowMs = Date.now(),
): Promise<Response | null> {
  const eventType = typeof event.type === 'string' ? event.type : '';
  const handledTypes = new Set([
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.payment_failed',
    'invoice.paid',
  ]);
  if (!handledTypes.has(eventType)) return null;

  const object = event.data?.object;
  const eventId = typeof event.id === 'string' ? event.id : '';
  const created = Number(event.created);
  if (!object || !eventId || !Number.isSafeInteger(created) || created <= 0) {
    return jsonResponse({ error: 'Stripe billing event is missing its identity or timestamp' }, 400);
  }

  const subscriptionId = subscriptionIdFor(event, object);
  if (!subscriptionId) return jsonResponse({ error: 'Stripe billing event is missing its subscription' }, 400);
  const billing = await env.DB.prepare(
    'SELECT organization_id, status, current_period_end, grace_until FROM team_billing WHERE stripe_subscription_id=?1'
  ).bind(subscriptionId).first() as BillingRecord | null;
  if (!billing) return null;

  const now = Math.floor(nowMs / 1000);
  const objectStatus = String(object.status || '').toLowerCase();
  if (eventType === 'customer.subscription.updated' &&
      !['canceled', 'incomplete_expired'].includes(objectStatus) && subscriptionSeats(object) === null) {
    return jsonResponse({ error: 'Stripe Team subscription has an invalid seat quantity' }, 400);
  }
  let status: 'active' | 'past_due' | 'suspended' | 'canceled';
  let periodEnd = subscriptionPeriodEnd(object) || billing.current_period_end;
  let seats: number | null = subscriptionSeats(object);

  if (billing.status === 'canceled' || eventType === 'customer.subscription.deleted' ||
      objectStatus === 'canceled' || objectStatus === 'incomplete_expired') {
    status = 'canceled';
    periodEnd = now;
    seats = null;
  } else if (eventType === 'invoice.payment_failed' || objectStatus === 'past_due' || objectStatus === 'unpaid') {
    status = 'past_due';
    periodEnd = eventType.startsWith('customer.subscription.') ? periodEnd : billing.current_period_end;
    seats = eventType.startsWith('customer.subscription.') ? seats : null;
  } else if (eventType === 'invoice.paid' && billing.status === 'past_due') {
    status = 'past_due';
    periodEnd = billing.current_period_end;
    seats = null;
  } else if (eventType === 'invoice.paid' || objectStatus === 'active' || objectStatus === 'trialing') {
    status = 'active';
    periodEnd = eventType === 'invoice.paid' ? Math.max(periodEnd, invoicePeriodEnd(object) || 0) : periodEnd;
    seats = eventType.startsWith('customer.subscription.') ? seats : null;
  } else {
    status = 'suspended';
    periodEnd = now;
    seats = null;
  }

  try {
    await applyBillingTransition(env.DB, {
      eventId, eventType, created, organizationId: billing.organization_id,
      subscriptionId, status, periodEnd, seats,
    }, nowMs);
  } catch (error) {
    if (error instanceof TypeError) return jsonResponse({error: 'Invalid billing transition'}, 400);
    throw error;
  }
  return jsonResponse({ status: 'PROCESSED', event_id: eventId });
}

export async function handleTeamPaymentWebhook(event: BillingEvent, env: BillingEnvironment): Promise<Response> {
  return (await handleTeamBillingEvent(event, env)) || jsonResponse({ status: 'PROCESSED' });
}

export function addTeamSubscriptionMetadata(
  form: URLSearchParams,
  organizationId: string,
  seats: number,
  issuer: string,
  subject: string,
): void {
  form.set('subscription_data[metadata][tier]', 'team');
  form.set('subscription_data[metadata][org_id]', organizationId);
  form.set('subscription_data[metadata][seats]', String(seats));
  form.set('subscription_data[metadata][owner_issuer]', issuer);
  form.set('subscription_data[metadata][owner_sub]', subject);
}

export async function initializeTeamBilling(
  env: BillingEnvironment,
  organizationId: string,
  seats: number,
  stripeSubscription: string | { id?: string } | null | undefined,
  nowMs: number,
  fetcher: typeof fetch = fetch,
): Promise<number> {
  const subscriptionId = typeof stripeSubscription === 'string' ? stripeSubscription : stripeSubscription?.id;
  const subscription = await retrieveTeamSubscription(subscriptionId || '', env.STRIPE_SECRET_KEY, fetcher);
  if (!['active', 'trialing'].includes(String(subscription.status)) ||
      subscription.metadata?.org_id !== organizationId || Number(subscription.metadata?.seats) !== seats ||
      subscription.id !== subscriptionId || subscriptionSeats(subscription) !== seats) {
    throw new Error('Stripe subscription does not match the purchased Team seat pool');
  }
  await env.DB.prepare(
    `INSERT INTO team_billing (organization_id, stripe_subscription_id, status, current_period_end, grace_until, updated_at)
     VALUES (?1, ?2, 'active', ?3, NULL, ?4)
     ON CONFLICT(organization_id) DO UPDATE SET stripe_subscription_id=?2, status='active',
       current_period_end=?3, grace_until=NULL, updated_at=?4`
  ).bind(organizationId, subscriptionId, subscription.current_period_end, nowMs).run();
  return subscription.current_period_end;
}

export async function suspendExpiredTeamBilling(db: BillingDatabase, nowMs = Date.now()): Promise<void> {
  const now = Math.floor(nowMs / 1000);
  await db.batch([
    db.prepare(
      "UPDATE team_billing SET status='suspended', updated_at=?1 WHERE status='past_due' AND grace_until IS NOT NULL AND grace_until<=?2"
    ).bind(nowMs, now),
    db.prepare(
      `UPDATE license_grants SET status='suspended', updated_at=?1
       WHERE plan='team' AND status='active' AND expires_at<=?2
         AND EXISTS (SELECT 1 FROM team_billing b WHERE b.organization_id=license_grants.organization_id AND b.status='suspended')`
    ).bind(nowMs, now),
  ]);
}

export async function retrieveTeamSubscription(
  subscriptionId: string,
  apiKey: string | undefined,
  fetcher: typeof fetch = fetch,
): Promise<Record<string, any>> {
  if (!apiKey || !/^sub_[A-Za-z0-9]+$/.test(subscriptionId)) {
    throw new Error('A valid Stripe subscription and API key are required');
  }
  const response = await fetcher(`https://api.stripe.com/v1/subscriptions/${encodeURIComponent(subscriptionId)}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!response.ok) throw new Error(`Stripe subscription lookup failed with status ${response.status}`);
  const subscription = await response.json() as Record<string, any>;
  const currentPeriodEnd = subscriptionPeriodEnd(subscription);
  if (!currentPeriodEnd) {
    throw new Error('Stripe subscription did not include a valid current period end');
  }
  return { ...subscription, current_period_end: currentPeriodEnd };
}

export const teamBillingGracePeriodSeconds = GRACE_PERIOD_SECONDS;
