/** Portable SQL adapter boundary. D1 and SQLite implement the same operations.
 * Batch statements must execute atomically, in order, or roll back together.
 * Bindings are values and must never be interpolated into SQL.
 */
export type StorageResult<T> = T | Promise<T>;
export interface GatewayStatement {
  bind(...values: unknown[]): GatewayStatement;
  first(): StorageResult<Record<string, any> | null>;
  all(): StorageResult<{ results: Record<string, any>[] }>;
  run(): StorageResult<{ meta: { changes: number } }>;
}
export interface GatewayDatabase {
  prepare(sql: string): GatewayStatement;
  batch(statements: GatewayStatement[]): Promise<{ meta: { changes: number } }[]>;
}
