from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# License management database utility
# Local store for tracking offline enterprise license activations.

DB_PATH = Path("founder_data") / "licenses.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            machine_id TEXT PRIMARY KEY,
            customer_name TEXT,
            tier TEXT,
            expiry_date TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def issue_license(mid: str, customer: str, tier: str, days: int):
    from datetime import timezone
    now = datetime.now(timezone.utc)
    expiry = (now + timedelta(days=days)).isoformat()
    created = now.isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO licenses (machine_id, customer_name, tier, expiry_date, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (mid, customer, tier, expiry, created))
    conn.commit()
    conn.close()
    print(f"✅ License issued for {customer} ({mid}) until {expiry}")

def list_licenses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT machine_id, customer_name, tier, expiry_date FROM licenses WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    print("\n[bold]Active Licenses[/bold]")
    print("-" * 60)
    for row in rows:
        print(f"MID: {row[0][:12]}... | {row[1]:<15} | {row[2]:<8} | Exp: {row[3][:10]}")

if __name__ == "__main__":
    init_db()
    parser = argparse.ArgumentParser(description="Yamlr Founder License Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    issue_p = subparsers.add_parser("issue")
    issue_p.add_argument("--mid", required=True)
    issue_p.add_argument("--customer", required=True)
    issue_p.add_argument("--tier", default="PRO")
    issue_p.add_argument("--days", type=int, default=365)
    
    subparsers.add_parser("list")
    
    args = parser.parse_args()
    if args.command == "issue":
        issue_license(args.mid, args.customer, args.tier, args.days)
    elif args.command == "list":
        list_licenses()
