/**
 * Yamlr Cloudflare Worker: Stripe Checkout & License Delivery Webhook
 * 
 * Why: Automates zero-touch license key generation and delivery upon Stripe checkout.
 * Verifies standard HMAC-SHA256 stripe signatures and issues cryptographically signed
 * RS256 JWT license tokens consumable by `yamlr auth activate <JWT>`.
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. Health check endpoint
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return new Response(JSON.stringify({ status: "healthy", service: "yamlr-stripe-webhook", timestamp: new Date().toISOString() }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      });
    }

    if (request.method !== "POST" || url.pathname !== "/webhook") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const signature = request.headers.get("stripe-signature");
    const rawBody = await request.text();
    const webhookSecret = env.STRIPE_WEBHOOK_SECRET || "whsec_test_mock_secret_for_development";

    // 2. Cryptographic signature verification
    const isValidSignature = await verifyStripeSignature(rawBody, signature, webhookSecret);
    if (!isValidSignature && env.ENVIRONMENT === "production") {
      return new Response(JSON.stringify({ error: "Invalid signature" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    let event;
    try {
      event = JSON.parse(rawBody);
    } catch (err) {
      return new Response(JSON.stringify({ error: "Invalid JSON payload" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (isTeamPaymentLifecycleEvent(event)) {
      const forwarded = await forwardTeamPaymentEvent(rawBody, event, env);
      if (forwarded) return forwarded;
    }

    // 3. Process checkout.session.completed event
    if (event.type === "checkout.session.completed") {
      const session = event.data.object;
      const customerEmail = session.customer_details?.email || session.customer_email || "";
      const metadata = session.metadata || {};
      const requestedTier = (metadata.tier || "team")
        .trim()
        .toLowerCase();
      const tier = requestedTier === "pro" ? "team" : requestedTier;
      const seats = parseInt(metadata.seats || "1", 10);
      const nodes = metadata.nodes == null ? null : parseInt(metadata.nodes, 10);
      const organizationId = metadata.org_id || session.customer;
      const developerEmail = String(metadata.developer_email || customerEmail).trim().toLowerCase();

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customerEmail) ||
          (tier === "team" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(developerEmail))) {
        return new Response(JSON.stringify({ error: "A valid license recipient email is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (!["team", "enterprise"].includes(tier)) {
        return new Response(JSON.stringify({ error: "Unsupported license tier" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (!organizationId || !String(organizationId).trim()) {
        return new Response(JSON.stringify({ error: "Missing organization identity" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (!Number.isSafeInteger(seats) || seats < 1 ||
          (nodes !== null && (!Number.isSafeInteger(nodes) || nodes < 1)) ||
          (tier === "enterprise" && !seats && !nodes)) {
        return new Response(JSON.stringify({ error: "Invalid contracted seat or node count" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      const now = Math.floor(Date.now() / 1000);
      const claims = tier === "team" ? {
        sub: developerEmail,
        email: developerEmail,
        tier,
        org_id: organizationId,
        seats: 1,
        org_seats: seats,
      } : {
        sub: organizationId,
        tier,
        org_id: organizationId,
        seats: metadata.seats == null ? undefined : seats,
        nodes: nodes == null ? undefined : nodes,
      };

      // Team seats identify a developer; Enterprise grants identify the organization.
      const licenseToken = await generateSignedLicenseJwt({
        ...claims,
        license_version: 1,
        iss: "yamlr-entitlement",
        aud: "yamlr",
        iat: now,
        exp: now + (365 * 24 * 60 * 60),
      }, env.JWT_PRIVATE_KEY);

      // Dispatch license email (e.g. Resend, SendGrid)
      await dispatchLicenseEmail(tier === "team" ? developerEmail : customerEmail, licenseToken, tier, seats, env);

      return new Response(JSON.stringify({
        received: true,
        license_issued: true,
        customer: customerEmail,
        tier: tier,
        seats: seats,
        token: licenseToken,
      }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ received: true, ignored_event: event.type }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  },
};

export async function forwardTeamPaymentEvent(rawBody, event, env, fetchImpl = fetch) {
  if (!isTeamPaymentLifecycleEvent(event)) return null;
  const gatewayUrl = env?.GATEWAY_PAYMENT_WEBHOOK_URL;
  const secret = env?.GATEWAY_WEBHOOK_SECRET;
  if (!gatewayUrl || !secret) {
    return new Response(JSON.stringify({ error: "Team license fulfillment is not configured" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
  let endpoint;
  try {
    endpoint = new URL(gatewayUrl);
    if (endpoint.protocol !== "https:") throw new Error("HTTPS is required");
  } catch {
    return new Response(JSON.stringify({ error: "Team license gateway URL is invalid" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
  try {
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${secret}`, "Content-Type": "application/json" },
      body: rawBody,
    });
    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Team license fulfillment failed" }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ received: true, seat_pool_fulfilled: true, license_issued: false }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(JSON.stringify({ error: "Team license gateway is unavailable" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export function isTeamPaymentLifecycleEvent(event) {
  const eventType = String(event?.type || "");
  const object = event?.data?.object || {};
  const subscriptionMetadata = object.subscription_details?.metadata ||
    object.parent?.subscription_details?.metadata ||
    object.lines?.data?.find((line) => line?.type === "subscription")?.metadata || {};
  const tier = String(object.metadata?.tier || subscriptionMetadata.tier || "").trim().toLowerCase();
  if (eventType === "checkout.session.completed") {
    return ["team", "pro"].includes(String(object.metadata?.tier || "team").trim().toLowerCase());
  }
  if (["customer.subscription.updated", "customer.subscription.deleted"].includes(eventType)) {
    return ["team", "pro"].includes(tier);
  }
  return ["invoice.payment_failed", "invoice.paid"].includes(eventType) && ["team", "pro"].includes(tier);
}

/**
 * Verifies standard Stripe HMAC-SHA256 signature (t=timestamp,v1=signature).
 */
export async function verifyStripeSignature(payload, sigHeader, secret) {
  if (!sigHeader) return false;

  const parts = sigHeader.split(",");
  let timestamp = null;
  let signature = null;

  for (const part of parts) {
    const [k, v] = part.trim().split("=");
    if (k === "t") timestamp = v;
    if (k === "v1") signature = v;
  }

  if (!timestamp || !signature) return false;

  const signedPayload = `${timestamp}.${payload}`;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sigBytes = await crypto.subtle.sign("HMAC", key, encoder.encode(signedPayload));
  const computedHex = Array.from(new Uint8Array(sigBytes))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");

  return computedHex === signature;
}

/**
 * Generates a signed RS256 JWT license using a PKCS#8 RSA private key.
 */
export async function generateSignedLicenseJwt(claims, privateKeyPem) {
  if (!privateKeyPem) throw new Error("JWT_PRIVATE_KEY is required");
  if (
    !claims ||
    typeof claims.sub !== "string" ||
    !claims.sub.trim() ||
    claims.license_version !== 1 ||
    claims.iss !== "yamlr-entitlement" ||
    claims.aud !== "yamlr" ||
    !["team", "enterprise"].includes(String(claims.tier).trim().toLowerCase()) ||
    !Number.isSafeInteger(claims.exp) ||
    !Number.isSafeInteger(claims.iat) ||
    claims.iat > Math.floor(Date.now() / 1000) + 60 ||
    claims.exp <= claims.iat ||
    claims.exp <= Math.floor(Date.now() / 1000)
  ) {
    throw new Error("License claims do not match the canonical entitlement contract");
  }

  const hasPositiveCount = (value) => Number.isSafeInteger(value) && value > 0;
  const validTeam = claims.tier === "team" &&
    typeof claims.email === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(claims.email.trim()) &&
    claims.sub.toLowerCase() === claims.email.trim().toLowerCase() &&
    typeof claims.org_id === "string" && claims.org_id.trim() &&
    claims.seats === 1 && hasPositiveCount(claims.org_seats) && !("nodes" in claims);
  const validEnterprise = claims.tier === "enterprise" &&
    typeof claims.org_id === "string" && claims.org_id.trim() &&
    claims.sub === claims.org_id &&
    (claims.seats == null || hasPositiveCount(claims.seats)) &&
    (claims.nodes == null || hasPositiveCount(claims.nodes)) &&
    (hasPositiveCount(claims.seats) || hasPositiveCount(claims.nodes)) &&
    !("machine_id" in claims);
  if (!validTeam && !validEnterprise) {
    throw new Error("License claims do not match the canonical entitlement contract");
  }

  const header = { alg: "RS256", typ: "JWT" };
  const base64UrlEncode = (obj) => {
    const json = typeof obj === "string" ? obj : JSON.stringify(obj);
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  };

  const encodedHeader = base64UrlEncode(header);
  const encodedPayload = base64UrlEncode(claims);
  const unsignedToken = `${encodedHeader}.${encodedPayload}`;

  const pemBody = privateKeyPem
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\s/g, "");
  const binaryDerString = atob(pemBody);
  const binaryDer = Uint8Array.from(binaryDerString, (character) => character.charCodeAt(0));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    binaryDer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sigBytes = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(unsignedToken)
  );
  const signature = btoa(String.fromCharCode(...new Uint8Array(sigBytes)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

  return `${unsignedToken}.${signature}`;
}

/**
 * Sends customer license activation instructions via email provider.
 */
export async function dispatchLicenseEmail(email, token, tier, seats, env) {
  const emailBody = `
Welcome to Yamlr ${tier.toUpperCase()}!

Your autonomous resolution plane license has been issued:
- Tier: ${tier.toUpperCase()}
  - Contracted Developer Seats: ${seats}
- Activation: Portable across the named developer's devices

To activate your installation, run:
  yamlr auth activate ${token}

Documentation: https://yamlr.dev/docs/getting-started
Support: support@yamlr.dev
  `.trim();

  // If RESEND_API_KEY is configured, call Resend API
  if (env && env.RESEND_API_KEY) {
    try {
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from: "licensing@yamlr.dev",
          to: email,
          subject: `Your Yamlr ${tier.toUpperCase()} License Key`,
          text: emailBody,
        }),
      });
    } catch (_) {
      // Non-blocking log
    }
  }

  return emailBody;
}
