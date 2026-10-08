# Source platform: retail order-to-cash

## Lineage

```
 lnd.customer ──► stg.usp_load_customer ──► stg.customer ──► dim.usp_load_dim_customer ──► dim.customer (SCD2) ─┐
 lnd.product ───► stg.usp_load_product ───► stg.product ───► dim.usp_load_dim_product ───► dim.product (SCD1)  ─┤
 lnd.order_* ───► stg.usp_load_orders ────► stg.order_* ───────────────────────────────────────────────────────┼─► fact.usp_load_fact_order_line ─► fact.order_line (+ _reject)
 lnd.payment ───► stg.usp_load_payments ──► stg.payment ───────────────────────────────────────────────────────┼─► fact.usp_load_fact_payment ───► fact.payment
 lnd.shipment ──► stg.usp_load_shipments ─► stg.shipment ──────────────────────────────────────────────────────┴─► fact.usp_load_fact_shipment ──► fact.shipment
 ref.currency_rate ─► dbo.fn_convert_currency (used by order_line, payment)          dim.usp_load_dim_date ─► dim.date
 fact.order_line ─► agg.usp_refresh_customer_monthly_revenue ─► agg.customer_monthly_revenue (+ dynamic agg.customer_revenue_trailing)
 fact.* / dim.* / agg.* ─► rpt.vw_* (5 reporting views)
 etl.usp_run_daily_load drives all 12 load steps from etl.pipeline_step via dynamic SQL
```

## Procedure complexity map

| Procedure | Level | What makes it hard |
|---|---|---|
| etl.usp_write_audit, etl.usp_get_set_watermark | TRIVIAL | OUTPUT params, SCOPE_IDENTITY; semantically replaced by dbt features |
| stg.usp_load_product, stg.usp_load_customer | LOW | CONVERT/TRY_CONVERT style codes, ROW_NUMBER dedup, string parsing |
| stg.usp_load_orders | MEDIUM | watermark incremental, temp tables, delete+insert in a transaction |
| stg.usp_load_payments | MEDIUM | OPENJSON ... WITH, nested array via CROSS APPLY |
| stg.usp_load_shipments | HIGH | XML nodes()/value()/exist(), XPath predicates, parent axis |
| dim.usp_load_dim_date | MEDIUM | recursive CTE, DATEFIRST dependence, WHILE loop |
| dim.usp_load_dim_product | MEDIUM | SCD1 MERGE with NOT MATCHED BY SOURCE (unsupported in Snowflake) |
| dim.usp_load_dim_customer | HIGH | SCD2 MERGE + OUTPUT INTO + follow-up INSERT, HASHBYTES |
| fact.usp_load_fact_order_line | **EXTREME** | PIT SCD2 joins, discount allocation with rounding remainder, return netting, reject routing, windowed batches |
| fact.usp_load_fact_payment | HIGH | PIVOT, running totals over old+new rows, orphan reconciliation |
| fact.usp_load_fact_shipment | MEDIUM | scalar UDF in SELECT, unknown-member date keys |
| agg.usp_refresh_customer_monthly_revenue | **EXTREME** | cursor with running balance, dynamic PIVOT, global temp table, SELECT INTO |
| etl.usp_run_daily_load | **EXTREME** | applock, dynamic EXEC, retry/WAITFOR, nested TRY/CATCH, INSERT…EXEC; an orchestration concern, not a dbt model |
| etl.usp_rebuild_indexes | MEDIUM | should be *retired*; Snowflake has no user-managed indexes |

## Migration traps worth testing the agent against

| T-SQL behaviour | Snowflake difference |
|---|---|
| `=` ignores trailing spaces (ANSI padding) | trailing spaces are significant |
| Case-insensitive default collation | comparisons are case-sensitive unless collated |
| `DATEDIFF(week, ...)`, `DATENAME`, `DATEFIRST` | week boundaries and names depend on session parameters (`WEEK_START`) |
| `MERGE ... WHEN NOT MATCHED BY SOURCE` | not supported; needs a separate UPDATE/DELETE |
| `OUTPUT $action INTO` | no equivalent; compute counts from MERGE result or query history |
| `IDENTITY` surrogate keys, `SET IDENTITY_INSERT` | AUTOINCREMENT / sequences / dbt surrogate keys; no identity insert |
| `TOP (1) ... ORDER BY` | `QUALIFY ROW_NUMBER() = 1` or `LIMIT` |
| `TRY_CONVERT`, `CONVERT(style)`, `ISNULL`, `IIF` | `TRY_TO_*`, `TO_*` with format, `COALESCE/IFNULL`, `IFF` |
| `HASHBYTES('SHA2_256', ...)` | `SHA2(..., 256)` returns hex text, not binary(32) |
| `OPENJSON`, `.nodes()/.value()` XML | `LATERAL FLATTEN` on VARIANT; `PARSE_XML` + `XMLGET` |
| `#temp` / `##global` temp tables | session-scoped temp tables; not visible across dbt models |
| Cursors, `WHILE`, dynamic SQL | rewrite set-based, Jinja loops, or Snowflake Scripting |
| Scalar UDFs doing table lookups | joins / as-of joins in models |
| `sp_getapplock`, `WAITFOR`, `XACT_STATE` | orchestrator concerns (Tasks / Airflow) |

## Known legacy behaviours (not bugs to hide - things the agent should surface)

These came up while designing the test data. Some are deliberate trade-offs; none are exercised as failures by the generated data unless stated.

| Behaviour | Where | Consequence |
|---|---|---|
| An order cancelled *after* its lines were loaded is not removed from `fact.order_line` | `fact.usp_load_fact_order_line` | stale revenue; the generator does not produce post-load cancellations |
| SALE lines priced exactly 0 are rejected as `BAD_PRICE` (`NULLIF(unit_price, 0)`) | same | free items never reach the fact |
| A customer change detected on the same day the open SCD2 row began is ignored until the next run | `dim.usp_load_dim_customer` | one-day delay, avoids an inverted validity interval |
| The aggregate rebuilds only a rolling 24-month window | `agg.usp_refresh_customer_monthly_revenue` | older months are never corrected |
| Payments for orders that never load (bad date, every line rejected) stay orphans forever | `fact.usp_load_fact_payment` | permanent `is_orphan = 1` rows |
| `is_order_paid_in_full` uses a 10 cent tolerance | same | per-line USD rounding can differ from the payment total by a few cents |

Fixed during data design: the aggregate was keyed on the SCD2 *version* surrogate key, splitting a customer's lifetime value whenever their address changed. It now uses the customer's anchor (first) key.
