const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function base64UrlEncode(str) {
  return Buffer.from(str).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function generateDummyKey(machineId) {
  const privateKeyPath = path.join(__dirname, '..', 'keys', 'private_key.pem');
  if (!fs.existsSync(privateKeyPath)) {
    console.error(`[!] Private key not found at ${privateKeyPath}`);
    return;
  }
  const privateKey = fs.readFileSync(privateKeyPath, 'utf8');

  const header = { alg: 'RS256', typ: 'JWT' };
  const payload = {
    license_version: 1,
    sub: 'offline-enterprise-customer',
    machine_id: machineId,
    tier: 'pro',
    iss: 'yamlr-entitlement',
    aud: 'yamlr',
    org_id: 'org_yamlr_123',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (365 * 24 * 3600),
    heartbeat: false
  };

  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const tokenStr = `${encodedHeader}.${encodedPayload}`;

  const signer = crypto.createSign('RSA-SHA256');
  signer.update(tokenStr);
  const signature = signer.sign(privateKey, 'base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const jwt = `${tokenStr}.${signature}`;
  console.log(`Generated Offline License Key:\n${jwt}`);
  
  fs.writeFileSync(path.join(__dirname, '..', 'keys', 'dummy_license.txt'), jwt);
  console.log(`Saved to keys/dummy_license.txt`);
}

const machineId = process.argv[2];
if (!machineId || !machineId.trim()) {
  console.error('Usage: node generate_dummy_key.js <machine_id>');
  process.exitCode = 1;
} else {
  generateDummyKey(machineId.trim());
}
