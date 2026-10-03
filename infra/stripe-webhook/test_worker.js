/**
 * Offline Verification Test Suite for Yamlr Stripe Webhook & License Generator
 */

import assert from "node:assert";
import crypto from "node:crypto";
import worker, { verifyStripeSignature, generateSignedLicenseJwt, dispatchLicenseEmail, forwardTeamPaymentEvent } from "./worker.js";

async function runTests() {
  console.log("Running Stripe Webhook & License Delivery Tests...");

  // 1. Test HMAC signature verification
  const secret = "whsec_test_mock_secret_12345";
  const payload = JSON.stringify({ type: "ping" });
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signedPayload = `${timestamp}.${payload}`;
  const validSig = crypto.createHmac("sha256", secret).update(signedPayload).digest("hex");
  const header = `t=${timestamp},v1=${validSig}`;

  const isVerified = await verifyStripeSignature(payload, header, secret);
  assert.strictEqual(isVerified, true, "Valid Stripe HMAC signature must verify successfully");

  const isInvalid = await verifyStripeSignature(payload, "t=123,v1=bad_sig", secret);
  assert.strictEqual(isInvalid, false, "Invalid Stripe signature must be rejected");

  // Team checkouts must use the membership gateway instead of direct token delivery.
  const teamRawBody = JSON.stringify({ type: "checkout.session.completed", data: { object: { metadata: { tier: "team" } } } });
  let forwardedRequest;
  const forwarded = await forwardTeamPaymentEvent(teamRawBody, JSON.parse(teamRawBody), {
    GATEWAY_PAYMENT_WEBHOOK_URL: "https://gateway.example.test/v1/webhooks/payment",
    GATEWAY_WEBHOOK_SECRET: "gateway-secret",
  }, async (url, options) => {
    forwardedRequest = { url: String(url), options };
    return new Response("{}", { status: 200 });
  });
  assert.strictEqual(forwarded.status, 200);
  assert.deepStrictEqual(forwardedRequest, {
    url: "https://gateway.example.test/v1/webhooks/payment",
    options: {
      method: "POST",
      headers: { Authorization: "Bearer gateway-secret", "Content-Type": "application/json" },
      body: teamRawBody,
    },
  });
  assert.strictEqual((await forwarded.json()).license_issued, false);
  const missingGateway = await forwardTeamPaymentEvent(teamRawBody, JSON.parse(teamRawBody), {});
  assert.strictEqual(missingGateway.status, 503);

  const invoiceEvent = {
    id: "evt_invoice_failed_1",
    type: "invoice.payment_failed",
    data: { object: { subscription: "sub_team_1", parent: { subscription_details: { metadata: { tier: "team" } } } } },
  };
  const invoiceBody = JSON.stringify(invoiceEvent);
  let invoiceForwarded = false;
  const invoiceResponse = await forwardTeamPaymentEvent(invoiceBody, invoiceEvent, {
    GATEWAY_PAYMENT_WEBHOOK_URL: "https://gateway.example.test/v1/webhooks/payment",
    GATEWAY_WEBHOOK_SECRET: "gateway-secret",
  }, async (_url, options) => {
    invoiceForwarded = options.body === invoiceBody;
    return new Response("{}", { status: 200 });
  });
  assert.strictEqual(invoiceResponse.status, 200);
  assert.strictEqual(invoiceForwarded, true, "Payment failures must reach the Team billing gateway");
  const unclassifiedInvoice = await forwardTeamPaymentEvent("{}", {
    type: "invoice.payment_failed", data: { object: { subscription: "sub_unclassified" } },
  }, {});
  assert.strictEqual(unclassifiedInvoice, null, "Unclassified invoices must not be treated as Team subscriptions");

  const enterpriseSubscription = {
    type: "customer.subscription.updated",
    data: { object: { metadata: { tier: "enterprise" } } },
  };
  assert.strictEqual(await forwardTeamPaymentEvent("{}", enterpriseSubscription, {}), null);

  // 2. Test License JWT Generation
  const { privateKey: jwtKey, publicKey: jwtPublicKey } = crypto.generateKeyPairSync("rsa", {
    modulusLength: 2048,
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
    publicKeyEncoding: { type: "spki", format: "pem" },
  });
  const claims = {
    license_version: 1,
    sub: "org-enterprise-1",
    tier: "enterprise",
    seats: 25,
    nodes: 12,
    org_id: "org-enterprise-1",
    iss: "yamlr-entitlement",
    aud: "yamlr",
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
  const token = await generateSignedLicenseJwt(claims, jwtKey);
  assert.ok(token, "JWT token must be non-empty");
  const parts = token.split(".");
  assert.strictEqual(parts.length, 3, "JWT must contain header, payload, and signature");

  const decodedHeader = JSON.parse(Buffer.from(parts[0], "base64url").toString());
  const decodedPayload = JSON.parse(Buffer.from(parts[1], "base64url").toString());
  assert.strictEqual(decodedHeader.alg, "RS256");
  assert.strictEqual(decodedPayload.sub, "org-enterprise-1");
  assert.strictEqual(decodedPayload.tier, "enterprise");
  assert.strictEqual(decodedPayload.seats, 25);
  assert.strictEqual(decodedPayload.org_id, "org-enterprise-1");
  assert.strictEqual(decodedPayload.nodes, 12);
  assert.strictEqual(decodedPayload.iss, "yamlr-entitlement");
  assert.strictEqual(decodedPayload.aud, "yamlr");
  assert.strictEqual(
    crypto.verify(
      "RSA-SHA256",
      Buffer.from(`${parts[0]}.${parts[1]}`),
      jwtPublicKey,
      Buffer.from(parts[2], "base64url")
    ),
    true,
    "License JWT must verify with its paired public key"
  );
  await assert.rejects(
    generateSignedLicenseJwt({ ...claims, aud: "another-product" }, jwtKey),
    /canonical entitlement contract/
  );

  // 3. Test Full Worker Checkout Event Processing
  const checkoutEvent = {
    type: "checkout.session.completed",
    data: {
      object: {
        id: "cs_test_mock_session_123",
        customer: "org-enterprise-1",
        customer_email: "lead@google.com",
        amount_total: 99000,
        metadata: {
          tier: "enterprise",
          seats: "50",
          nodes: "12",
          org_id: "org-enterprise-1",
        },
      },
    },
  };

  const reqPayload = JSON.stringify(checkoutEvent);
  const reqTimestamp = Math.floor(Date.now() / 1000).toString();
  const reqSig = crypto.createHmac("sha256", secret).update(`${reqTimestamp}.${reqPayload}`).digest("hex");

  const mockRequest = new Request("https://license.yamlr.dev/webhook", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "stripe-signature": `t=${reqTimestamp},v1=${reqSig}`,
    },
    body: reqPayload,
  });

  const env = {
    STRIPE_WEBHOOK_SECRET: secret,
    JWT_PRIVATE_KEY: jwtKey,
    ENVIRONMENT: "development",
  };

  const response = await worker.fetch(mockRequest, env);
  assert.strictEqual(response.status, 200, "Webhook endpoint must return HTTP 200");

  const resJson = await response.json();
  assert.strictEqual(resJson.received, true);
  assert.strictEqual(resJson.license_issued, true);
  assert.strictEqual(resJson.customer, "lead@google.com");
  assert.strictEqual(resJson.tier, "enterprise");
  assert.strictEqual(resJson.seats, 50);
  assert.ok(resJson.token, "Response must include signed activation token");

  const issuedClaims = JSON.parse(Buffer.from(resJson.token.split(".")[1], "base64url").toString());
  assert.strictEqual(issuedClaims.sub, "org-enterprise-1");
  assert.strictEqual(issuedClaims.org_id, "org-enterprise-1");
  assert.strictEqual(issuedClaims.nodes, 12);
  assert.strictEqual(issuedClaims.iss, "yamlr-entitlement");
  assert.strictEqual(issuedClaims.aud, "yamlr");

  const missingOrganizationEvent = structuredClone(checkoutEvent);
  delete missingOrganizationEvent.data.object.metadata.org_id;
  delete missingOrganizationEvent.data.object.customer;
  const missingOrganizationRequest = new Request("https://license.yamlr.dev/webhook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(missingOrganizationEvent),
  });
  const missingOrganizationResponse = await worker.fetch(missingOrganizationRequest, env);
  assert.strictEqual(missingOrganizationResponse.status, 400);

  const teamToken = await generateSignedLicenseJwt({
    license_version: 1,
    sub: "developer@example.test",
    email: "developer@example.test",
    tier: "team",
    org_id: "org-team-1",
    seats: 1,
    org_seats: 5,
    iss: "yamlr-entitlement",
    aud: "yamlr",
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600,
  }, jwtKey);
  const teamClaims = JSON.parse(Buffer.from(teamToken.split(".")[1], "base64url").toString());
  assert.strictEqual(teamClaims.sub, "developer@example.test");
  assert.strictEqual(teamClaims.email, "developer@example.test");
  assert.strictEqual(teamClaims.seats, 1);
  assert.strictEqual(teamClaims.org_seats, 5);

  // 4. Test Email Activation Instructions Content
  const emailText = await dispatchLicenseEmail("test@yamlr.dev", "SAMPLE_JWT", "team", 5, {});
  assert.ok(emailText.includes("yamlr auth activate SAMPLE_JWT"));
  assert.ok(emailText.includes("Tier: TEAM"));

  console.log("All Stripe Webhook & License Delivery Tests Passed Successfully (4/4)!");
}

runTests().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
