import { applyBillingTransition, type BillingTransition } from './billing_core.ts';
import type { GatewayDatabase } from './storage.ts';

/** Signed operator receipts are an alternative to an online payment provider.
 * MAC covers the exact body bytes, using a separate 32+ byte operator secret.
 */
export async function handleOfflineBillingReceipt(request: Request, db: GatewayDatabase, secret: string | undefined, nowMs = Date.now()): Promise<Response> {
  if (!secret || new TextEncoder().encode(secret).length < 32) return new Response('Receipt signing secret is not configured', {status: 503});
  const signature = request.headers.get('X-Yamlr-Receipt-Signature') ?? '';
  if (!/^[a-f0-9]{64}$/.test(signature)) return new Response('Invalid receipt signature', {status: 401});
  // Bound the stream on both transports, rather than trusting Content-Length.
  const reader = request.body?.getReader();
  if (!reader) return new Response('Missing receipt body', {status: 400});
  const chunks: Uint8Array[] = [];
  let length = 0;
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    length += chunk.value.length;
    if (length > 16 * 1024) { await reader.cancel(); return new Response('Receipt too large', {status: 413}); }
    chunks.push(chunk.value);
  }
  const raw = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { raw.set(chunk, offset); offset += chunk.length; }
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), {name: 'HMAC', hash: 'SHA-256'}, false, ['verify']);
  const mac = Uint8Array.from(signature.match(/../g)!, value => Number.parseInt(value, 16));
  if (!await crypto.subtle.verify('HMAC', key, mac, raw)) return new Response('Invalid receipt signature', {status: 401});
  try {
    const input = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(raw));
    const fields = ['eventId', 'eventType', 'created', 'organizationId', 'subscriptionId', 'status', 'periodEnd', 'seats'];
    if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length !== fields.length
        || !fields.every(field => Object.hasOwn(input, field))
        || typeof input.eventId !== 'string' || !input.eventId.startsWith('offline:')
        || typeof input.subscriptionId !== 'string' || !input.subscriptionId.startsWith('offline:')) {
      return new Response('Invalid receipt contract', {status: 400});
    }
    await applyBillingTransition(db, input as BillingTransition, nowMs);
    return Response.json({status: 'PROCESSED', event_id: input.eventId});
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) return new Response('Invalid receipt contract', {status: 400});
    throw error;
  }
}
