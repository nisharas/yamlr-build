import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { once } from 'node:events';
import { createGatewayServer } from './node_server.ts';
import { SQLiteGatewayDatabase } from './sqlite_storage.ts';
import type { Env } from './index.ts';

test('Self-hosted adapter serves the shared contract and bounds unauthenticated requests', async () => {
  const DB = new SQLiteGatewayDatabase(':memory:');
  DB.database.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  const env = { DB, OIDC_REDIRECT_URI: 'https://gateway.example.test/v1/oidc/callback',
    APP_ORIGIN: 'https://app.example.test', YAMLR_PUBKEY_PEM: 'public-test-key' } as Env;
  const server = createGatewayServer(env);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  const base = `http://127.0.0.1:${address.port}`;
  try {
    assert.equal(await (await fetch(`${base}/health`)).text(), 'OK');
    assert.equal(await (await fetch(`${base}/v1/pubkey`)).text(), 'public-test-key');
    assert.equal((await fetch(`${base}/missing`)).status, 404);
    assert.equal((await fetch(`${base}/v1/auth/renew`, {method: 'POST', body: JSON.stringify({token: 'invalid'})})).status, 401);
    assert.equal((await fetch(`${base}/v1/pulse`, {method: 'POST', body: 'x'.repeat(256 * 1024 + 1)})).status, 413);
    assert.equal(DB.prepare('SELECT COUNT(*) AS count FROM pulses').first()?.count, 0);
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    DB.close();
  }
});
