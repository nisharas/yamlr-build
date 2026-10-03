import assert from 'node:assert/strict';
import test from 'node:test';
import { SQLiteGatewayDatabase } from './sqlite_storage.ts';

test('SQLite bindings are values and failed batches roll back all prior changes', async () => {
  const db = new SQLiteGatewayDatabase(':memory:');
  try {
    db.database.exec('CREATE TABLE examples (id TEXT PRIMARY KEY)');
    db.prepare('INSERT INTO examples VALUES (?1)').bind("value'); DROP TABLE examples; --").run();
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM examples').first()?.count, 1);
    await assert.rejects(db.batch([
      db.prepare('INSERT INTO examples VALUES (?1)').bind('new'),
      db.prepare('INSERT INTO examples VALUES (?1)').bind('new'),
    ]));
    assert.equal(db.prepare('SELECT COUNT(*) AS count FROM examples').first()?.count, 1);
    assert.throws(() => db.prepare('SELECT ?1').bind({ secret: 'invalid' }), TypeError);
    assert.equal(db.prepare('SELECT ?3 AS value').bind('unused', 'unused', 'used').first()?.value, 'used');
  } finally { db.close(); }
});
