import type { GatewayDatabase } from './storage.ts';

export const GRACE_PERIOD_SECONDS = 7 * 24 * 60 * 60;
export interface BillingTransition {
  eventId: string;
  eventType: string;
  created: number;
  organizationId: string;
  subscriptionId: string;
  status: 'active' | 'past_due' | 'suspended' | 'canceled';
  periodEnd: number;
  seats: number | null;
}

/** Apply authenticated, normalized billing transitions independently of a provider.
 * The legacy stripe_subscription_id column stores the bound provider reference.
 * Existing pools only: events cannot create organizations or initial grants.
 */
export async function applyBillingTransition(db: GatewayDatabase, update: BillingTransition, nowMs = Date.now()) {
  const {eventId, eventType, created, organizationId, subscriptionId, seats} = update;
  const now = Math.floor(nowMs / 1000);
  if (![eventId, eventType, organizationId, subscriptionId].every(value => typeof value === 'string' && value.length > 0 && value.length <= 256)
      || !Number.isSafeInteger(created) || created <= 0 || created > now + 60
      || !Number.isSafeInteger(update.periodEnd) || update.periodEnd <= 0
      || !['active', 'past_due', 'suspended', 'canceled'].includes(update.status)
      || (seats !== null && (!Number.isSafeInteger(seats) || seats < 1 || seats > 10000))) {
    throw new TypeError('Invalid normalized billing transition');
  }
  const binding = await db.prepare(`SELECT b.status FROM team_billing b JOIN license_grants g
    ON g.organization_id=b.organization_id AND g.subject_id=b.organization_id AND g.plan='team'
    WHERE b.organization_id=?1 AND b.stripe_subscription_id=?2`)
    .bind(organizationId, subscriptionId).first();
  if (!binding) throw new TypeError('Billing provider reference is not bound to this organization');
  const status = binding.status === 'canceled' ? 'canceled' : update.status;
  const grantStatus = status === 'canceled' ? 'revoked' : status === 'suspended' ? 'suspended' : 'active';
  const periodEnd = status === 'canceled' || status === 'suspended' ? now : update.periodEnd;
  const graceUntil = now + GRACE_PERIOD_SECONDS;
  const guard = `EXISTS (
    SELECT 1 FROM team_billing_events current_event
    WHERE current_event.event_id=?1 AND current_event.status='processing'
  ) AND NOT EXISTS (
    SELECT 1 FROM team_billing_events newer_event WHERE newer_event.organization_id=?2
      AND (newer_event.created_at>?3 OR (newer_event.created_at=?3 AND newer_event.event_id>?1))
  )`;
  const event = db.prepare(`INSERT OR IGNORE INTO team_billing_events
    (event_id, organization_id, event_type, created_at, status) VALUES (?1, ?2, ?3, ?4, 'processing')`)
    .bind(eventId, organizationId, eventType, created);
  const billing = db.prepare(`UPDATE team_billing SET
    current_period_end=CASE WHEN status='canceled' THEN current_period_end ELSE ?5 END,
    status=CASE WHEN status='canceled' THEN 'canceled' ELSE ?4 END,
    grace_until=CASE WHEN status='canceled' THEN NULL WHEN ?4='past_due' THEN COALESCE(grace_until, ?6) ELSE NULL END, updated_at=?7
    WHERE organization_id=?2 AND stripe_subscription_id=?8 AND ${guard}`)
    .bind(eventId, organizationId, created, status, periodEnd, graceUntil, nowMs, subscriptionId);
  const expiry = status === 'past_due' ? 'COALESCE((SELECT grace_until FROM team_billing WHERE organization_id=?2), ?6)' : '?5';
  const grant = db.prepare(`UPDATE license_grants SET
    status=CASE WHEN (SELECT status FROM team_billing WHERE organization_id=?2)='canceled' THEN 'revoked' ELSE ?4 END,
    expires_at=CASE WHEN (SELECT status FROM team_billing WHERE organization_id=?2)='canceled'
      THEN (SELECT current_period_end FROM team_billing WHERE organization_id=?2) ELSE ${expiry} END,
    seat_count=COALESCE(?9, seat_count), updated_at=?7
    WHERE organization_id=?2 AND subject_id=?2 AND plan='team' AND ${guard}`)
    .bind(eventId, organizationId, created, grantStatus, periodEnd, graceUntil, nowMs, subscriptionId, seats);
  const organization = db.prepare(`UPDATE organizations SET seat_count=?9 WHERE id=?2 AND ?9 IS NOT NULL
    AND (SELECT status FROM team_billing WHERE organization_id=?2)!='canceled' AND ${guard}`)
    .bind(eventId, organizationId, created, status, periodEnd, graceUntil, nowMs, subscriptionId, seats);
  const receipt = db.prepare("UPDATE team_billing_events SET status='processed' WHERE event_id=?1 AND status='processing'").bind(eventId);
  await db.batch([event, billing, grant, organization, receipt]);
}
