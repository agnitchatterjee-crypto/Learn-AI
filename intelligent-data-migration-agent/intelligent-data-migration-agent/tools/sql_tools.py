"""Four migration tools: plain Python functions plus Anthropic-style tool schemas.

Each function takes simple JSON-friendly arguments and returns a dict, so an LLM
can call them through tool use and read the result directly.
"""
import json
import re
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("mock_catalog.json")


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _strip_comments_and_strings(sql: str) -> str:
    """Blank out comments and string literals so keywords inside them are not counted."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"N?'(?:[^']|'')*'", "''", sql)


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.I))


# --------------------------------------------------------------------------- #
# Tool 1 — analyze_sql
# --------------------------------------------------------------------------- #
TSQL_FUNCTIONS = [
    "ISNULL", "GETDATE", "GETUTCDATE", "SYSDATETIME", "DATEFROMPARTS", "DATENAME",
    "CONVERT", "TRY_CONVERT", "IIF", "LEN", "CHARINDEX", "STRING_AGG", "HASHBYTES",
    "NEWID", "SCOPE_IDENTITY", "OBJECT_NAME", "OBJECT_SCHEMA_NAME", "FORMAT",
    "OPENJSON", "JSON_VALUE",
]

# Constructs with no direct Snowflake SQL equivalent (need a rewrite, not a replacement).
UNSUPPORTED_PATTERNS = {
    "TRY_CATCH": r"\bBEGIN\s+TRY\b",
    "WHILE_LOOP": r"\bWHILE\b",
    "T_SQL_VARIABLES": r"\bDECLARE\s+@",
    "SYSTEM_VARIABLES": r"@@\w+",
    "XML_METHODS": r"\.\s*(?:nodes|value|query|exist)\s*\(",
    "FOR_XML": r"\bFOR\s+XML\b",
    "OPENJSON": r"\bOPENJSON\b",
    "WAITFOR": r"\bWAITFOR\b",
    "RAISERROR_THROW": r"\b(?:RAISERROR|THROW)\b",
    "TABLE_HINTS": r"\bWITH\s*\(\s*(?:NOLOCK|ROWLOCK|UPDLOCK|HOLDLOCK)",
}


def analyze_sql(sql: str) -> dict:
    """Return basic statistics about a SQL Server SQL string."""
    if not isinstance(sql, str) or not sql.strip():
        return {"error": "sql must be a non-empty string"}

    clean = _strip_comments_and_strings(sql)

    statements = {
        "select": _count(r"\bSELECT\b", clean),
        "join": _count(r"\bJOIN\b", clean),
        "insert": _count(r"\bINSERT\b", clean),
        "update": _count(r"(?<!\bFOR\s)(?<!\bON\s)\bUPDATE\b", clean),
        "delete": _count(r"\bDELETE\b", clean),
    }

    temp_tables = sorted({m.lower() for m in re.findall(r"(?<![\w@])(##?\w+)", clean)})
    cursors = _count(r"\bDECLARE\s+\w+\s+CURSOR\b", clean)
    dynamic_sql = _count(r"\bsp_executesql\b", clean) + _count(
        r"\bEXEC(?:UTE)?\s*\(|\bEXEC(?:UTE)?\s+@\w+", clean
    )

    functions = {}
    for fn in TSQL_FUNCTIONS:
        n = _count(rf"\b{fn}\s*\(", clean)
        if n:
            functions[fn] = n

    unsupported = {}
    for name, pat in UNSUPPORTED_PATTERNS.items():
        n = _count(pat, clean)
        if n:
            unsupported[name] = n

    return {
        "statement_counts": statements,
        "temp_tables": {"count": len(temp_tables), "names": temp_tables,
                        "has_global": any(t.startswith("##") for t in temp_tables)},
        "cursor_count": cursors,
        "dynamic_sql_count": dynamic_sql,
        "sqlserver_functions": functions,
        "unsupported_constructs": unsupported,
        "has_temp_tables": bool(temp_tables),
        "has_cursors": cursors > 0,
        "has_dynamic_sql": dynamic_sql > 0,
    }


# --------------------------------------------------------------------------- #
# Tool 2 — convert_sql_to_snowflake
# --------------------------------------------------------------------------- #
# (rule name, regex, replacement). Applied in order, only to well-defined patterns.
_FUNCTION_RULES = [
    ("ISNULL -> COALESCE", r"\bISNULL\s*\(", "COALESCE("),
    ("GETDATE -> CURRENT_TIMESTAMP", r"\bGETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP()"),
    ("SYSDATETIME -> CURRENT_TIMESTAMP", r"\bSYSDATETIME\s*\(\s*\)", "CURRENT_TIMESTAMP()"),
    ("GETUTCDATE -> SYSDATE", r"\bGETUTCDATE\s*\(\s*\)", "SYSDATE()"),
    ("LEN -> LENGTH", r"\bLEN\s*\(", "LENGTH("),
    ("NEWID -> UUID_STRING", r"\bNEWID\s*\(\s*\)", "UUID_STRING()"),
    ("IIF -> IFF", r"\bIIF\s*\(", "IFF("),
]
_TYPE_RULES = [
    ("NVARCHAR -> VARCHAR", r"\bNVARCHAR\b", "VARCHAR"),
    ("NCHAR -> CHAR", r"\bNCHAR\b", "CHAR"),
    ("DATETIME2 -> TIMESTAMP_NTZ", r"\bDATETIME2(?:\s*\(\s*\d+\s*\))?", "TIMESTAMP_NTZ"),
    ("DATETIME -> TIMESTAMP_NTZ", r"\bDATETIME\b", "TIMESTAMP_NTZ"),
    ("BIT -> BOOLEAN", r"\bBIT\b", "BOOLEAN"),
    ("SYSNAME -> VARCHAR", r"\bSYSNAME\b", "VARCHAR"),
]

_WARNING_PATTERNS = [
    (r"\bDECLARE\s+\w+\s+CURSOR\b",
     "Cursor found: rewrite set-based (window functions) or Snowflake Scripting CURSOR/FOR loop."),
    (r"\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(|\bEXEC(?:UTE)?\s+@\w+",
     "Dynamic SQL found: needs EXECUTE IMMEDIATE / Snowflake Scripting; review by hand."),
    (r"(?<![\w@])##?\w+",
     "Temp table found: use CREATE TEMPORARY TABLE; global (##) temp tables have no equivalent."),
    (r"\bBEGIN\s+TRY\b", "TRY/CATCH: convert to Snowflake Scripting EXCEPTION block."),
    (r"\bWHILE\b", "WHILE loop: only valid inside Snowflake Scripting; consider set-based rewrite."),
    (r"@@\w+", "System variable (@@ROWCOUNT etc.): use SQLROWCOUNT in Snowflake Scripting."),
    (r"\bDECLARE\s+@", "T-SQL @variables: use Snowflake Scripting DECLARE (no @ prefix)."),
    (r"\.\s*(?:nodes|value|query|exist)\s*\(|\bFOR\s+XML\b",
     "XML methods: rewrite with Snowflake XMLGET / LATERAL FLATTEN on a VARIANT."),
    (r"\bOPENJSON\b", "OPENJSON: rewrite with PARSE_JSON + LATERAL FLATTEN."),
    (r"\bIDENTITY\s*\(", "IDENTITY(): use AUTOINCREMENT or a SEQUENCE."),
    (r"\bDATEDIFF\s*\(\s*(?:week|wk|ww)\b",
     "DATEDIFF(week): Snowflake week boundaries depend on WEEK_START; verify results."),
    (r"\bDATENAME\b|\bDATEFIRST\b",
     "DATENAME/DATEFIRST are language-dependent: use DAYNAME()/WEEK_START session param."),
    (r"\bSELECT\b[^;]*?\bINTO\s+#", "SELECT INTO #tmp: use CREATE TEMPORARY TABLE ... AS SELECT."),
    (r"\bCROSS\s+APPLY\b|\bOUTER\s+APPLY\b", "APPLY: rewrite as JOIN LATERAL."),
]


def convert_sql_to_snowflake(sql: str) -> dict:
    """Propose a Snowflake version of SQL Server SQL using deterministic rewrites.

    Only well-defined patterns are rewritten; everything else is reported in
    `warnings` so the LLM (or a human) can decide what to do.
    """
    if not isinstance(sql, str) or not sql.strip():
        return {"error": "sql must be a non-empty string"}

    out = sql
    applied = []

    def apply(rule, pattern, repl, flags=re.I):
        nonlocal out
        new, n = re.subn(pattern, repl, out, flags=flags)
        if n:
            applied.append({"rule": rule, "occurrences": n})
            out = new

    for rule, pat, repl in _FUNCTION_RULES + _TYPE_RULES:
        apply(rule, pat, repl)

    apply("[ident] -> ident", r"\[(\w+)\]", r"\1")
    apply("remove WITH (NOLOCK)", r"\s+WITH\s*\(\s*NOLOCK\s*\)", "")
    apply("CONVERT(type, x) -> CAST(x AS type)",
          r"\bCONVERT\s*\(\s*(\w+(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?)\s*,\s*([^(),]+?)\s*\)",
          r"CAST(\2 AS \1)")

    warnings = []
    scan = _strip_comments_and_strings(sql)

    # TOP n -> LIMIT n only when it is unambiguous (single SELECT, single TOP).
    top = re.findall(r"\bSELECT\s+TOP\s*\(?\s*(\d+)\s*\)?", scan, flags=re.I)
    if top:
        if len(top) == 1 and _count(r"\bSELECT\b", scan) == 1:
            out = re.sub(r"\bTOP\s*\(?\s*\d+\s*\)?\s*", "", out, count=1, flags=re.I)
            out = re.sub(r"\s*;?\s*$", f"\nLIMIT {top[0]};", out)
            applied.append({"rule": "TOP n -> LIMIT n", "occurrences": 1})
        else:
            warnings.append("TOP found in a multi-SELECT statement: rewrite as LIMIT / QUALIFY manually.")

    for pat, msg in _WARNING_PATTERNS:
        if re.search(pat, scan, flags=re.I | re.S):
            warnings.append(msg)

    if re.search(r"\bLEN\s*\(", scan, flags=re.I):
        warnings.append("LEN -> LENGTH: LEN ignores trailing spaces in SQL Server, LENGTH does not.")
    if re.search(r"'\s*\+|\+\s*N?'", scan):
        warnings.append("String concatenation with '+': use || or CONCAT().")
    if re.search(r"\bCONVERT\s*\(", out, flags=re.I):
        warnings.append("CONVERT with style argument or nested expression left unconverted.")

    return {"converted_sql": out, "applied_rules": applied, "warnings": warnings}


# --------------------------------------------------------------------------- #
# Tool 3 — inspect_table_schema
# --------------------------------------------------------------------------- #
def _find_bundle(bundle_path=None) -> Path:
    """Locate bundle.md: explicit path, else this project folder or any parent folder."""
    if bundle_path:
        return Path(bundle_path)
    for folder in Path(__file__).resolve().parents:
        if (folder / "bundle.md").exists():
            return folder / "bundle.md"
    raise FileNotFoundError("bundle.md not found; pass bundle_path")


def _split_top_level(text: str) -> list:
    """Split on commas that are not inside parentheses or quotes."""
    parts, depth, quote, cur = [], 0, False, []
    for ch in text:
        if ch == "'":
            quote = not quote
        elif not quote and ch == "(":
            depth += 1
        elif not quote and ch == ")":
            depth -= 1
        if ch == "," and depth == 0 and not quote:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def build_catalog_from_bundle(bundle_path=None) -> dict:
    """Parse every CREATE TABLE in bundle.md into {schema.table: {columns, primary_key}}."""
    text = _find_bundle(bundle_path).read_text(encoding="utf-8")
    catalog = {}
    for m in re.finditer(r"CREATE\s+TABLE\s+([\w.\[\]]+)\s*\((.*?)\n\);", text, flags=re.S | re.I):
        name = re.sub(r"[\[\]]", "", m.group(1)).lower()
        body = re.sub(r"/\*.*?\*/", " ", m.group(2), flags=re.S)
        body = re.sub(r"--[^\n]*", " ", body)
        columns, pk = [], []
        for item in _split_top_level(body):
            if re.match(r"CONSTRAINT\b", item, flags=re.I):
                pk_m = re.search(r"PRIMARY\s+KEY\s*(?:\w+\s*)?\(([^)]*)\)", item, flags=re.I)
                if pk_m:
                    pk = [re.sub(r"\s+(ASC|DESC)$", "", c.strip(), flags=re.I) for c in pk_m.group(1).split(",")]
                continue
            col = re.match(r"(\w+)\s+(\w+(?:\s*\(\s*[\w,\s]+\))?)(.*)", item, flags=re.S)
            if not col:
                continue
            rest = col.group(3)
            columns.append({"name": col.group(1), "type": re.sub(r"\s+", "", col.group(2)).lower(),
                            "nullable": not re.search(r"NOT\s+NULL", rest, flags=re.I),
                            "identity": bool(re.search(r"\bIDENTITY\b", rest, flags=re.I)),
                            "inline_pk": bool(re.search(r"PRIMARY\s+KEY", rest, flags=re.I))})
        pk = pk or [c["name"] for c in columns if c.pop("inline_pk")]
        for c in columns:
            c.pop("inline_pk", None)
            if c["name"] in pk:
                c["nullable"] = False
        catalog[name] = {"columns": columns, "primary_key": pk}
    return catalog


def refresh_catalog(bundle_path=None) -> dict:
    """Parse bundle.md and create mock_catalog.json, overwriting it only if the content changed."""
    catalog = build_catalog_from_bundle(bundle_path)
    text = json.dumps(catalog, indent=2)
    if not CATALOG_PATH.exists() or CATALOG_PATH.read_text(encoding="utf-8") != text:
        CATALOG_PATH.write_text(text, encoding="utf-8")
    return catalog


def inspect_table_schema(table_name: str) -> dict:
    """Look up a table in the metadata catalog generated from bundle.md.

    Every call re-reads bundle.md and creates/overwrites mock_catalog.json from it.
    """
    if not isinstance(table_name, str) or not table_name.strip():
        return {"error": "table_name must be a non-empty string"}

    try:
        catalog = refresh_catalog()
    except FileNotFoundError as exc:
        return {"error": str(exc)}
    wanted = re.sub(r"[\[\]\"]", "", table_name).strip().lower()

    matches = [t for t in catalog if t == wanted or t.split(".")[-1] == wanted]
    if len(matches) != 1:
        hint = matches or sorted(catalog)
        key = "ambiguous_matches" if matches else "available_tables"
        return {"error": f"Table '{table_name}' not found" if not matches
                else f"Table name '{table_name}' is ambiguous; use schema.table",
                key: hint}

    name = matches[0]
    entry = catalog[name]
    pk = set(entry["primary_key"])
    columns = [{"name": c["name"], "data_type": c["type"], "nullable": c["nullable"],
                "is_primary_key": c["name"] in pk, "is_identity": c.get("identity", False)}
               for c in entry["columns"]]
    return {"table": name, "columns": columns, "primary_key": entry["primary_key"]}


# --------------------------------------------------------------------------- #
# Tool 4 — estimate_migration_complexity
# --------------------------------------------------------------------------- #
WEIGHTS = {
    "dynamic_sql": 25,          # per occurrence, max 2 counted
    "cursor": 20,               # per occurrence, max 2 counted
    "temp_table": 10,           # per distinct temp table, max 3 counted
    "global_temp_table": 5,     # extra if any ## table
    "unsupported_construct": 5, # per distinct construct type, max 5 counted
    "sqlserver_function": 1,    # per distinct function, max 10 counted
    "join_over_3": 1,           # per JOIN beyond the third, max 10 counted
}
RISK_BANDS = [(20, "LOW"), (50, "MEDIUM"), (101, "HIGH")]


def estimate_migration_complexity(analysis: dict) -> dict:
    """Score migration risk (0-100) from an analyze_sql() result using fixed weights."""
    if not isinstance(analysis, dict) or "statement_counts" not in analysis:
        return {"error": "pass the dict returned by analyze_sql()"}

    factors = []

    def add(label, units, cap, weight_key):
        counted = min(units, cap)
        if counted:
            pts = counted * WEIGHTS[weight_key]
            factors.append({"factor": label, "count": units, "points": pts,
                            "rule": f"{WEIGHTS[weight_key]} pts each, max {cap} counted"})

    add("dynamic SQL", analysis.get("dynamic_sql_count", 0), 2, "dynamic_sql")
    add("cursors", analysis.get("cursor_count", 0), 2, "cursor")
    temp = analysis.get("temp_tables", {})
    add("temporary tables", temp.get("count", 0), 3, "temp_table")
    if temp.get("has_global"):
        add("global temp table (##)", 1, 1, "global_temp_table")
    unsupported = analysis.get("unsupported_constructs", {})
    add("unsupported constructs (" + ", ".join(sorted(unsupported)) + ")" if unsupported
        else "unsupported constructs", len(unsupported), 5, "unsupported_construct")
    add("SQL Server-specific functions", len(analysis.get("sqlserver_functions", {})), 10,
        "sqlserver_function")
    add("joins beyond the third", max(0, analysis["statement_counts"].get("join", 0) - 3), 10,
        "join_over_3")

    score = min(100, sum(f["points"] for f in factors))
    category = next(label for limit, label in RISK_BANDS if score < limit)
    return {"score": score, "risk_category": category, "contributing_factors": factors,
            "bands": "LOW <20, MEDIUM 20-49, HIGH >=50"}


# --------------------------------------------------------------------------- #
# Tool schemas (Anthropic Messages API format) and dispatcher
# --------------------------------------------------------------------------- #
TOOL_SCHEMAS = [
    {
        "name": "analyze_sql",
        "description": "Count SELECT/JOIN/INSERT/UPDATE/DELETE, detect temp tables, cursors, dynamic SQL, "
                       "SQL Server-specific functions and unsupported constructs in a SQL Server SQL string.",
        "input_schema": {"type": "object",
                         "properties": {"sql": {"type": "string", "description": "SQL Server SQL text"}},
                         "required": ["sql"]},
    },
    {
        "name": "convert_sql_to_snowflake",
        "description": "Apply deterministic SQL Server -> Snowflake rewrites (ISNULL, GETDATE, types, "
                       "brackets...) and return converted_sql plus warnings for constructs needing manual work.",
        "input_schema": {"type": "object",
                         "properties": {"sql": {"type": "string", "description": "SQL Server SQL text"}},
                         "required": ["sql"]},
    },
    {
        "name": "inspect_table_schema",
        "description": "Return columns, data types, nullability and primary key for a table from the "
                       "metadata catalog. Accepts 'schema.table' or a bare table name.",
        "input_schema": {"type": "object",
                         "properties": {"table_name": {"type": "string", "description": "e.g. dim.customer"}},
                         "required": ["table_name"]},
    },
    {
        "name": "estimate_migration_complexity",
        "description": "Compute a transparent 0-100 risk score and LOW/MEDIUM/HIGH category from the "
                       "output of analyze_sql.",
        "input_schema": {"type": "object",
                         "properties": {"analysis": {"type": "object",
                                                     "description": "The exact dict returned by analyze_sql"}},
                         "required": ["analysis"]},
    },
]

TOOL_FUNCTIONS = {
    "analyze_sql": analyze_sql,
    "convert_sql_to_snowflake": convert_sql_to_snowflake,
    "inspect_table_schema": inspect_table_schema,
    "estimate_migration_complexity": estimate_migration_complexity,
}


def run_tool(name: str, arguments: dict) -> dict:
    """Execute a tool call by name; used by the agent loop for each tool_use block."""
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        return fn(**arguments)
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}
