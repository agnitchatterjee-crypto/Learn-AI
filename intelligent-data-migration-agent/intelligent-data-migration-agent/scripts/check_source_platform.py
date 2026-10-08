#!/usr/bin/env python3
"""Static consistency checks for the synthetic SQL Server source platform.

What this verifies (no database required):
  1. Every schema-qualified object referenced in code is defined somewhere in the repo.
  2. data/expected/object_catalog.yaml agrees with the code (reads / writes / calls / sequences).
  3. etl.pipeline_step seed rows point at real procedures and tables, and match the catalog's dynamic_calls.
  4. Object counts match the catalog.
  5. (informational) how many files sqlglot's T-SQL dialect can parse.

What it does NOT verify: that the T-SQL executes on SQL Server. Run deploy.sql against a real instance for that.
"""
import re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
CATALOG = ROOT / "data" / "expected" / "object_catalog.yaml"
SCHEMAS = ("lnd", "stg", "ref", "dim", "fact", "agg", "rpt", "etl", "dbo")
REF_RE = re.compile(r"\b(" + "|".join(SCHEMAS) + r")\.([A-Za-z_][A-Za-z0-9_]*)\b")
DEF_RE = re.compile(
    r"\bCREATE\s+(?:OR\s+ALTER\s+)?(TABLE|VIEW|PROCEDURE|PROC|FUNCTION|SEQUENCE)\s+"
    r"(" + "|".join(SCHEMAS) + r")\.([A-Za-z_][A-Za-z0-9_]*)", re.I)
DYNAMIC_OK = {"agg.customer_revenue_trailing"}   # created via SELECT INTO from dynamic SQL


def strip(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def main() -> int:
    problems = []
    files = sorted(SRC.rglob("*.sql"))
    files = [f for f in files if f.name != "deploy.sql"]
    raw = {f: f.read_text() for f in files}
    code = {f: strip(t) for f, t in raw.items()}

    # ---- definitions
    defined, kinds = set(), {}
    for f, c in code.items():
        for kind, sch, name in DEF_RE.findall(c):
            key = f"{sch}.{name}".lower()
            defined.add(key)
            kinds[key] = kind.upper().replace("PROC", "PROCEDURE") if kind.upper() == "PROC" else kind.upper()
    counts = {k: sum(1 for v in kinds.values() if v == k) for k in ("TABLE", "VIEW", "FUNCTION", "PROCEDURE", "SEQUENCE")}

    # ---- 1. unresolved references
    refs_by_file = {}
    for f, c in code.items():
        refs = {f"{s}.{n}".lower() for s, n in REF_RE.findall(c)}
        refs_by_file[f] = refs
        for r in sorted(refs - defined - DYNAMIC_OK):
            problems.append(f"UNRESOLVED  {f.relative_to(SRC)} -> {r}")

    # ---- 2. catalog vs code
    cat = yaml.safe_load(CATALOG.read_text())
    for section in ("functions", "views", "procedures"):
        for obj in cat[section]:
            name = obj["name"].lower()
            matches = [f for f in files if f.name.lower() == f"{name}.sql"]
            if len(matches) != 1:
                problems.append(f"CATALOG     {obj['name']}: expected one file, found {len(matches)}")
                continue
            if name not in defined:
                problems.append(f"CATALOG     {obj['name']}: not defined in its file")
            actual = refs_by_file[matches[0]] - {name}
            declared = {x.lower() for k in ("reads", "writes", "calls", "sequences") for x in obj.get(k, [])}
            for extra in sorted(actual - declared):
                problems.append(f"CATALOG     {obj['name']}: code references {extra} but catalog does not list it")
            for missing in sorted(declared - actual):
                problems.append(f"CATALOG     {obj['name']}: catalog lists {missing} but code does not reference it")
    for t in cat["tables"]:
        if t["name"].lower() not in defined:
            problems.append(f"CATALOG     table {t['name']} has no DDL")
    for k, plural in (("TABLE", "tables"), ("VIEW", "views"), ("FUNCTION", "functions"), ("PROCEDURE", "procedures")):
        if counts[k] != len(cat[plural]):
            problems.append(f"COUNTS      {plural}: code defines {counts[k]}, catalog lists {len(cat[plural])}")

    # ---- 3. pipeline seed
    seed = raw[SRC / "seed" / "02_pipeline_steps.sql"]
    rows = re.findall(r"\(\s*\d+\s*,\s*'[^']+'\s*,\s*'([^']+)'\s*,\s*'([^']+)'", seed)
    seed_procs = {p.lower() for p, _ in rows}
    for p, t in rows:
        if p.lower() not in defined:
            problems.append(f"SEED        pipeline_step proc {p} does not exist")
        if t.lower() not in defined:
            problems.append(f"SEED        pipeline_step target {t} does not exist")
    orch = next(o for o in cat["procedures"] if o["name"] == "etl.usp_run_daily_load")
    if seed_procs != {x.lower() for x in orch["dynamic_calls"]}:
        problems.append("SEED        pipeline_step procs differ from catalog dynamic_calls for etl.usp_run_daily_load")

    # ---- 4. structural lint (catches missing END / unbalanced parentheses / orphaned transactions)
    for f, c in code.items():
        if c.count("(") != c.count(")"):
            problems.append(f"LINT        {f.name}: unbalanced parentheses ({c.count('(')} open, {c.count(')')} close)")
        for kw in ("TRY", "CATCH"):
            b = len(re.findall(rf"\bBEGIN\s+{kw}\b", c, re.I)); e = len(re.findall(rf"\bEND\s+{kw}\b", c, re.I))
            if b != e:
                problems.append(f"LINT        {f.name}: BEGIN {kw} x{b} vs END {kw} x{e}")
        begins = len(re.findall(r"\bBEGIN\b(?!\s+(?:TRY|CATCH|TRAN|TRANSACTION)\b)", c, re.I))
        ends = len(re.findall(r"\bEND\b(?!\s+(?:TRY|CATCH)\b)", c, re.I))
        cases = len(re.findall(r"\bCASE\b", c, re.I))
        if ends != begins + cases:
            problems.append(f"LINT        {f.name}: END x{ends} != BEGIN x{begins} + CASE x{cases}")
        bt = len(re.findall(r"\bBEGIN\s+TRAN(?:SACTION)?\b", c, re.I))
        ct = len(re.findall(r"\bCOMMIT\s+TRAN(?:SACTION)?\b", c, re.I))
        if bt != ct:
            problems.append(f"LINT        {f.name}: BEGIN TRANSACTION x{bt} vs COMMIT x{ct}")

    # ---- 4b. generated CSV headers vs table DDL (only when data has been generated)
    def table_columns(sql):
        body = sql[sql.index("(") + 1:]
        cols = {}
        depth, seg, segs = 0, "", []
        for ch in body:
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            if ch == "," and depth == 0:
                segs.append(seg); seg = ""
            else:
                seg += ch
        segs.append(seg)
        for sg in segs:
            sg = " ".join(sg.split())
            if not sg or re.match(r"(CONSTRAINT|PRIMARY|UNIQUE|FOREIGN)\b", sg, re.I):
                continue
            name = sg.split()[0]
            required = bool(re.search(r"\bNOT NULL\b", sg, re.I)) and not re.search(r"\bDEFAULT\b|\bIDENTITY\b", sg, re.I)
            cols[name.lower()] = required
        return cols

    gen = ROOT / "data" / "generated"
    for prof_dir in sorted(gen.glob("*")) if gen.exists() else []:
        for csv_path in sorted(prof_dir.glob("*/*.csv")):
            tbl = csv_path.stem.lower()
            ddl = next((code[f] for f in code if f.name.lower() == f"{tbl}.sql" and f.parent.name == tbl.split(".")[0]), None)
            if ddl is None:
                problems.append(f"CSV         {csv_path.relative_to(ROOT)}: no DDL for {tbl}")
                continue
            cols = table_columns(ddl)
            header = [h.lower() for h in csv_path.open(encoding="utf-8").readline().strip().split(",")]
            for h in header:
                if h not in cols:
                    problems.append(f"CSV         {prof_dir.name}/{csv_path.parent.name}/{csv_path.name}: column {h} not in {tbl}")
            for c, req in cols.items():
                if req and c not in header:
                    problems.append(f"CSV         {prof_dir.name}/{csv_path.parent.name}/{csv_path.name}: NOT NULL column {c} missing from CSV")

    # ---- 5. sqlglot (informational)
    # sqlglot parses T-SQL queries well but degrades procedural blocks (BEGIN TRY, cursors, WHILE, DECLARE)
    # to opaque Command nodes without raising. Count those separately: it shows which files need a
    # procedural splitter before sqlglot can see the SQL inside them.
    try:
        import logging
        import sqlglot
        from sqlglot import exp
        logging.getLogger("sqlglot").setLevel(logging.ERROR)
        full = degraded = failed = 0
        degraded_files = []
        for f in files:
            try:
                trees = sqlglot.parse(raw[f], read="tsql")
                if any(t is not None and t.find(exp.Command) for t in trees):
                    degraded += 1
                    degraded_files.append(f.name)
                else:
                    full += 1
            except Exception:
                failed += 1
                degraded_files.append(f.name)
        glot = (f"sqlglot(tsql): {full} files fully parsed, {degraded} parsed only as opaque Command nodes, "
                f"{failed} failed to parse (total {len(files)})")
    except ImportError:
        glot = "sqlglot not installed (pip install sqlglot) - parse check skipped"

    print(f"Files scanned : {len(files)}")
    print(f"Objects       : {counts}")
    print(f"Pipeline steps: {len(rows)}")
    print(glot)
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK - all references resolve and the catalog matches the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
