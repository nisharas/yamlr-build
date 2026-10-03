/** Self-hosted HTTP transport for the same gateway handler used on Workers. */
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import gateway, { type Env } from './index.ts';
import { SQLiteGatewayDatabase } from './sqlite_storage.ts';

const MAX_BODY_BYTES = 256 * 1024;

export function createGatewayServer(env: Env) {
  const origin = new URL(env.OIDC_REDIRECT_URI).origin;
  return createServer({ requestTimeout: 30_000, headersTimeout: 10_000 }, async (incoming, outgoing) => {
    try {
      if (!incoming.url?.startsWith('/') || incoming.url.startsWith('//')) {
        outgoing.writeHead(400).end('Invalid request target'); return;
      }
      const chunks: Buffer[] = [];
      let size = 0;
      for await (const chunk of incoming) {
        const bytes = Buffer.from(chunk);
        size += bytes.length;
        if (size > MAX_BODY_BYTES) {
          outgoing.writeHead(413).end('Request body too large'); incoming.resume(); return;
        }
        chunks.push(bytes);
      }
      const headers = new Headers();
      for (const [name, value] of Object.entries(incoming.headers)) {
        if (value !== undefined) headers.set(name, Array.isArray(value) ? value.join(', ') : value);
      }
      const method = incoming.method ?? 'GET';
      const request = new Request(new URL(incoming.url, origin), {
        method, headers,
        body: method === 'GET' || method === 'HEAD' ? undefined : Buffer.concat(chunks),
      });
      const response = await gateway.fetch(request, env);
      outgoing.statusCode = response.status;
      response.headers.forEach((value, name) => { if (name !== 'set-cookie') outgoing.setHeader(name, value); });
      const cookies = response.headers.getSetCookie();
      if (cookies.length) outgoing.setHeader('set-cookie', cookies);
      outgoing.end(Buffer.from(await response.arrayBuffer()));
    } catch {
      // Never return database, signing key, or identity-provider diagnostics.
      if (!outgoing.headersSent) outgoing.writeHead(500);
      outgoing.end('Gateway request failed');
    }
  });
}

export function startGateway(settings: NodeJS.ProcessEnv = process.env) {
  for (const key of ['OIDC_ISSUER', 'OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET', 'OIDC_REDIRECT_URI', 'APP_ORIGIN', 'JWT_SIGNING_KEY', 'YAMLR_PUBKEY_PEM', 'YAMLR_GATEWAY_DATABASE']) {
    if (!settings[key]?.trim()) throw new Error(`Missing gateway configuration: ${key}`);
  }
  for (const key of ['OIDC_ISSUER', 'OIDC_REDIRECT_URI', 'APP_ORIGIN']) {
    if (new URL(settings[key]!).protocol !== 'https:') throw new Error(`${key} requires HTTPS`);
  }
  const port = Number(settings.PORT ?? 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid gateway port');
  const database = new SQLiteGatewayDatabase(settings.YAMLR_GATEWAY_DATABASE!);
  database.database.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  const env = { ...settings, DB: database } as unknown as Env;
  const server = createGatewayServer(env);
  server.on('close', () => database.close());
  server.listen(port, '127.0.0.1');
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = startGateway();
  for (const signal of ['SIGINT', 'SIGTERM'] as const) process.once(signal, () => server.close());
}
