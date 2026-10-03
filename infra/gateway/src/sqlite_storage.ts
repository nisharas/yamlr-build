import { DatabaseSync, type SQLInputValue } from 'node:sqlite';
import type { GatewayDatabase, GatewayStatement } from './storage.ts';

class SQLiteStatement implements GatewayStatement {
  readonly database: DatabaseSync;
  readonly sql: string;
  readonly values: SQLInputValue[];
  constructor(database: DatabaseSync, sql: string, values: SQLInputValue[] = []) {
    this.database = database; this.sql = sql; this.values = values;
  }
  bind(...values: unknown[]): SQLiteStatement {
    if (!values.every(value => value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'bigint' || value instanceof Uint8Array)) {
      throw new TypeError('Unsupported SQL binding type');
    }
    return new SQLiteStatement(this.database, this.sql, values as SQLInputValue[]);
  }
  private statement() {
    const statement = this.database.prepare(this.sql);
    // D1 SQL uses ?1.. bindings; Node SQLite treats those as named parameters.
    statement.setAllowBareNamedParameters(true);
    // SQLite/D1 permit gaps in numbered positional slots (e.g. ?1 and ?9).
    // Node exposes these as a name map; unused slots must not reject a batch.
    statement.setAllowUnknownNamedParameters(true);
    return statement;
  }
  private bindings(): Record<string, SQLInputValue> {
    return Object.fromEntries(this.values.map((value, index) => [String(index + 1), value]));
  }
  first() { return this.statement().get(this.bindings()) ?? null; }
  all() { return { results: this.statement().all(this.bindings()) }; }
  run() { return { meta: { changes: Number(this.statement().run(this.bindings()).changes) } }; }
}

export class SQLiteGatewayDatabase implements GatewayDatabase {
  readonly database: DatabaseSync;
  constructor(path: string) {
    this.database = new DatabaseSync(path);
    this.database.exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;');
  }
  prepare(sql: string) { return new SQLiteStatement(this.database, sql); }
  async batch(statements: GatewayStatement[]) {
    if (!statements.every(statement => statement instanceof SQLiteStatement && statement.database === this.database)) {
      throw new TypeError('Batch contains a statement from another storage adapter');
    }
    this.database.exec('BEGIN IMMEDIATE');
    try {
      const results = statements.map(statement => (statement as SQLiteStatement).run());
      this.database.exec('COMMIT');
      return results;
    } catch (error) {
      this.database.exec('ROLLBACK');
      throw error;
    }
  }
  close() { this.database.close(); }
}
