# Data volumes

> Generated from `data/generated/*/manifest.json` by `scripts/make_volume_doc.py`. Do not edit by hand.

The default **medium** profile models a mid-size online retailer: **50,000 customers, 2,000 products and about 319,325 orders over 1,004 days** (2024-01-01 to 2026-09-30), followed by a 3-day incremental load. Volumes scale linearly with the three anchors in `data/generator/profiles.yaml`; everything else follows from the ratios in the same file.

| Profile | Customers | Products | Orders | Use |
|---|---:|---:|---:|---|
| tiny | 300 | 60 | 1,602 | unit tests / CI (seconds) |
| small | 5,000 | 400 | 31,936 | laptop development (~4 s to generate) |
| medium | 50,000 | 2,000 | 319,325 | default benchmark (~40 s, ~1.5 GB RAM, ~340 MB CSV) |
| large | 500,000 | 20,000 | ~3,000,000 | **not generated or tested**: roughly 10x medium, so expect ~15 GB RAM and ~3.4 GB of CSV |

## 1. Source tables (generated)

These are loaded from CSV. `incremental` is the second load (new days plus corrections to history).

| Table | tiny | small | medium initial | medium incremental | medium avg per day |
|---|---:|---:|---:|---:|---:|
| lnd.customer | 363 | 5,970 | 60,073 | 2,250 | static |
| lnd.product | 61 | 404 | 2,020 | 2,030 | static |
| lnd.order_header | 1,692 | 33,830 | 338,309 | 5,596 | 337 |
| lnd.order_line | 3,737 | 73,865 | 738,794 | 5,195 | 736 |
| lnd.payment | 1,666 | 33,380 | 333,671 | 1,455 | 332 |
| lnd.shipment | 2,982 | 60,010 | 600,719 | 2,077 | 598 |
| ref.currency_rate | 3,800 | 3,800 | 3,800 | 10 | static |

`lnd.order_header` exceeds the order count because orders are re-sent when they are returned, corrected or arrive late. `lnd.shipment` is about twice the shipment count because the carrier sends a SHIPPED document and later a DELIVERED one. `lnd.customer` includes stale duplicate rows (about 20%).

## 2. Warehouse tables (expected after the pipeline runs)

Populated by the stored procedures, so these are *expected by construction*, not loaded. They have **not been verified against SQL Server**: on a real run, any difference is either a generator bug or a stored-procedure bug.

| Table | tiny | small | medium after initial | medium after incremental |
|---|---:|---:|---:|---:|
| stg.customer | 300 | 5,000 | 50,000 | 50,250 |
| stg.product | 60 | 400 | 2,000 | 2,010 |
| stg.order_header | 1,583 | 31,665 | 316,682 | 319,006 |
| stg.order_line | 3,735 | 73,792 | 738,043 | 743,238 |
| stg.payment | 1,723 | 34,713 | 346,708 | 348,251 |
| stg.shipment | 1,531 | 30,821 | 307,939 | 309,141 |
| dim.date | 7,671 | 7,671 | 7,671 | 7,671 |
| dim.product | 61 | 401 | 2,001 | 2,021 |
| dim.customer | 301 | 5,001 | 50,001 | 52,251 |
| fact.order_line | 3,541 | 70,579 | 704,209 | 709,219 |
| fact.order_line_reject | 34 | 575 | 6,283 | 6,326 |
| fact.payment | 1,692 | 34,115 | 341,003 | 342,523 |
| fact.shipment | 1,531 | 30,821 | 307,939 | 309,141 |
| agg.customer_monthly_revenue (as_of 2026-10-05) | 927 | 17,982 | 179,197 | 180,933 |
| agg.customer_revenue_trailing rows (as_of 2026-10-05) | 186 | 3,368 | 33,834 | 34,297 |

Notes: `dim.*` counts include the unknown member (key -1). `dim.customer` counts SCD2 versions. The `agg` rows depend on the run date because the aggregate rebuilds a rolling 24-month window; the figures assume the run date shown.

## 3. Control and static tables

| Table | Rows | Notes |
|---|---:|---|
| etl.pipeline_step | 12 | seeded |
| etl.watermark | 4 | lnd.order_header, lnd.payment, lnd.shipment, fact.order_line |
| etl.load_audit | ~20-45 per run | 1-2 rows per step plus a RUN_SUMMARY; grows with each run and each retry |
| dim.date | 7,671 | 2015-01-01 to 2035-12-31 plus unknown member |

## 4. Ratios worth knowing (medium)

| Ratio | Value |
|---|---:|
| Orders per day (average) | 317 |
| Orders per customer (average, all customers) | 6.4 |
| Order lines per order | 2.33 |
| Fact lines per order | 2.22 |
| Payment rows per order | 1.08 |
| Shipment rows per order | 0.97 |
| Landing rows loaded per order (all lnd tables) | 6.3 |
| Largest table | lnd.shipment (600,719 rows) |
| Total landing rows, initial | 2,073,586 |

## 5. Planted data-quality defects (medium)

Each defect is planted at a known rate so the agent's validation and root-cause analysis have ground truth to find. Rates are set in `profiles.yaml`; every defect appears at least once even in the tiny profile.

| Defect | Count (whole timeline) | Expected downstream effect |
|---|---:|---|
| customers with dup rows | 10,023 | stale duplicate rows; latest modified_at must win |
| blank id customer rows | 50 | dropped in stg.customer (counted as rejected) |
| customers changed incremental | 2,000 | new SCD2 version in dim.customer |
| customers new incremental | 250 | new rows in dim.customer |
| unknown customer orders | 1,597 | fact lines load with customer_key = -1 |
| bad date orders | 319 | header rejected in staging; their lines and payments never resolve |
| late arriving orders | 3,193 | is_late_arriving = 1, picked up out of date order |
| held back orders | 958 | payments arrive first -> orphan payments, reconciled one load later |
| touched orders | 3,193 | header-only correction -> fact UPDATE path |
| cancelled orders | 9,643 | in staging, excluded from facts |
| cancel lines | 5,989 | kept in stg.order_line, excluded from facts |
| returns | 21,387 | RETURN lines priced from the original sale line when price is NULL |
| refund payments | 19,293 | negative payments netted against order value |
| chf no fx orders | 319 | reject NO_FX_RATE; their payments skipped |
| failed payment docs | 5,367 | in stg.payment, excluded from fact.payment |
| invalid json docs | 335 | counted as rejected in stg.usp_load_payments |
| invalid xml docs | 1,203 | counted as rejected in stg.usp_load_shipments |
| product price changes | 100 | SCD1 overwrite in dim.product |
| products removed | 10 | soft delete (is_active = 0) in dim.product |
| products new | 20 | inserted in dim.product |
| test products | 20 | excluded in stg.product |

Rejected order lines by reason (cumulative): BAD_PRICE 705, BAD_QUANTITY 1,475, NO_FX_RATE 724, RETURN_NO_ORIGINAL 642, UNKNOWN_PRODUCT 2,780. Fact lines with an unknown customer: 3,492. Orphan payments remaining after the incremental load: 822.

## 6. Generating and loading

```bash
python scripts/generate_data.py --profile medium      # writes data/generated/medium/{initial,incremental}/*.csv + manifest.json
python scripts/load_data.py --phase initial     --profile medium --conn "<odbc connection string>"
# run the pipeline:  EXEC etl.usp_run_daily_load;
python scripts/load_data.py --phase incremental --profile medium --conn "<odbc connection string>"
# run the pipeline again, then compare table counts with manifest.json
```
