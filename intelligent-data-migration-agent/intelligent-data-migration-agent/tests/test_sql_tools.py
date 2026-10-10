import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from sql_tools import (analyze_sql, convert_sql_to_snowflake, estimate_migration_complexity,
                       inspect_table_schema, run_tool)

CURSOR_PROC = """
/* SELECT in a comment should not count */
DECLARE @sql nvarchar(max);
CREATE TABLE #monthly (a int);
DECLARE cur CURSOR LOCAL FOR SELECT a FROM #monthly;
SET @sql = N'SELECT * FROM x';
EXEC sp_executesql @sql;
SELECT ISNULL(a, 0), SYSDATETIME() FROM t1 JOIN t2 ON 1=1 JOIN t3 ON 1=1 JOIN t4 ON 1=1 JOIN t5 ON 1=1;
"""


def test_analyze_counts_and_flags():
    r = analyze_sql(CURSOR_PROC)
    assert r["statement_counts"]["select"] == 2
    assert r["statement_counts"]["join"] == 4
    assert r["has_cursors"] and r["has_dynamic_sql"] and r["has_temp_tables"]
    assert r["sqlserver_functions"] == {"ISNULL": 1, "SYSDATETIME": 1}


def test_convert_basic():
    r = convert_sql_to_snowflake("SELECT ISNULL(x, 0), GETDATE() FROM [dbo].[t] WITH (NOLOCK)")
    assert "COALESCE(x, 0)" in r["converted_sql"]
    assert "CURRENT_TIMESTAMP()" in r["converted_sql"]
    assert "NOLOCK" not in r["converted_sql"] and "[" not in r["converted_sql"]


def test_convert_top_and_warnings():
    assert "LIMIT 5" in convert_sql_to_snowflake("SELECT TOP (5) a FROM t ORDER BY a;")["converted_sql"]
    assert any("Cursor" in w for w in convert_sql_to_snowflake(CURSOR_PROC)["warnings"])


def test_inspect_schema():
    r = inspect_table_schema("DIM.Customer")
    assert r["primary_key"] == ["customer_key"]
    assert r["columns"][0]["is_primary_key"] is True
    assert "available_tables" in inspect_table_schema("nope")


def test_estimate_risk():
    simple = estimate_migration_complexity(analyze_sql("SELECT ISNULL(a,0) FROM t"))
    hard = estimate_migration_complexity(analyze_sql(CURSOR_PROC))
    assert simple["risk_category"] == "LOW"
    assert hard["risk_category"] == "HIGH"
    assert hard["score"] == sum(f["points"] for f in hard["contributing_factors"])


def test_run_tool_dispatch():
    assert "error" in run_tool("missing", {})
    assert run_tool("analyze_sql", {"sql": "SELECT 1"})["statement_counts"]["select"] == 1


def test_catalog_built_from_bundle():
    from sql_tools import CATALOG_PATH, refresh_catalog
    cat = refresh_catalog()
    assert len(cat) == 24 and CATALOG_PATH.exists()
    assert cat["dim.date"]["primary_key"] == ["date_key"]
    assert cat["fact.payment"]["columns"][0]["identity"] is True
    assert inspect_table_schema("stg.payment")["primary_key"] == ["payment_src_id", "order_src_id"]
