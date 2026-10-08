#!/usr/bin/env python3
"""Loads generated CSVs into the SQL Server landing tables.

    python scripts/load_data.py --profile medium --phase initial --conn "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=MigrationSource;UID=sa;PWD=...;TrustServerCertificate=yes"
    python scripts/load_data.py --profile medium --phase incremental --conn "..."

--dry-run reads the CSVs and checks them against manifest.json without connecting to anything.

STATUS: --dry-run is tested. The database path (pyodbc) has NOT been run against a real SQL Server in the environment
this was written in. If fast_executemany misbehaves on the nvarchar(max)/xml columns, retry with --no-fast.
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOAD_ORDER = ["ref.currency_rate", "lnd.customer", "lnd.product", "lnd.order_header", "lnd.order_line", "lnd.payment", "lnd.shipment"]
TRUNCATE_ORDER = list(reversed(LOAD_ORDER))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.reader(fh)
        cols = next(r)
        rows = [[None if v == "" else v for v in row] for row in r]   # blank -> NULL; whitespace-only values are preserved
    return cols, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="medium")
    ap.add_argument("--phase", choices=["initial", "incremental"], required=True)
    ap.add_argument("--conn", default=os.environ.get("MIGRATION_SOURCE_CONN"), help="ODBC connection string (or env MIGRATION_SOURCE_CONN)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--batch-size", type=int, default=10000)
    ap.add_argument("--truncate-first", action="store_true", help="empty the landing tables before an initial load")
    ap.add_argument("--no-fast", action="store_true", help="disable pyodbc fast_executemany")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    base = Path(a.data_dir) if a.data_dir else ROOT / "data" / "generated" / a.profile
    manifest = json.loads((base / "manifest.json").read_text())
    phases = ["initial"] if a.phase == "initial" else ["initial", "incremental"]

    cur = conn = None
    if not a.dry_run:
        if not a.conn:
            sys.exit("provide --conn or set MIGRATION_SOURCE_CONN (or use --dry-run)")
        import pyodbc
        conn = pyodbc.connect(a.conn, autocommit=False)
        cur = conn.cursor()
        cur.fast_executemany = not a.no_fast
        if a.truncate_first:
            if a.phase != "initial":
                sys.exit("--truncate-first only makes sense with --phase initial")
            for t in TRUNCATE_ORDER:
                cur.execute(f"DELETE FROM {t}")        # DELETE rather than TRUNCATE: works with FKs and keeps permissions simple
                cur.execute(f"IF OBJECTPROPERTY(OBJECT_ID('{t}'), 'TableHasIdentity') = 1 DBCC CHECKIDENT ('{t}', RESEED, 0) WITH NO_INFOMSGS")
            conn.commit()
            print("landing tables emptied")

    problems = 0
    for t in LOAD_ORDER:
        t0 = time.time()
        loaded = 0
        phase = a.phase
        path = base / phase / f"{t}.csv"
        cols, rows = read_csv(path)
        expected = manifest["lnd_rows"][phase][t]
        if len(rows) != expected:
            print(f"  MISMATCH {t} {phase}: csv has {len(rows)} rows, manifest says {expected}")
            problems += 1
        if not a.dry_run:
            sql = f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
            for i in range(0, len(rows), a.batch_size):
                cur.executemany(sql, rows[i:i + a.batch_size])
                loaded += len(rows[i:i + a.batch_size])
            conn.commit()
            cur.execute(f"SELECT COUNT_BIG(*) FROM {t}")
            in_db = cur.fetchone()[0]
            want = sum(manifest["lnd_rows"][p][t] for p in phases)
            flag = "ok" if in_db == want else f"EXPECTED {want:,}"
            if in_db != want:
                problems += 1
            print(f"  {t:<22} +{loaded:>9,} rows  table now {in_db:>9,}  [{flag}]  {time.time() - t0:5.1f}s")
        else:
            print(f"  {t:<22} {len(rows):>9,} rows read from {phase}/  [dry run]")
    if conn:
        conn.close()
    print("done" if not problems else f"done with {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
