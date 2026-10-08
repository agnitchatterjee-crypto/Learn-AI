#!/usr/bin/env python3
"""Builds docs/data-volumes.md from the manifest.json files written by generate_data.py.

    python scripts/generate_data.py --profile tiny && ... small && ... medium
    python scripts/make_volume_doc.py
"""
import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generated"
PROFILES = ["tiny", "small", "medium"]
n = lambda v: f"{v:,}" if isinstance(v, int) else str(v)


def load(p):
    f = GEN / p / "manifest.json"
    return json.loads(f.read_text()) if f.exists() else None


def main():
    m = {p: load(p) for p in PROFILES}
    missing = [p for p, v in m.items() if v is None]
    if missing:
        raise SystemExit(f"generate these profiles first: {missing}")
    cfg = yaml.safe_load((ROOT / "data" / "generator" / "profiles.yaml").read_text())
    med = m["medium"]
    hs, he = date.fromisoformat(med["dates"]["history_start"]), date.fromisoformat(med["dates"]["history_end"])
    hist_days = (he - hs).days + 1
    incr_days = (date.fromisoformat(med["dates"]["incremental_end"]) - he).days
    L = []
    w = L.append

    w("# Data volumes")
    w("")
    w("> Generated from `data/generated/*/manifest.json` by `scripts/make_volume_doc.py`. Do not edit by hand.")
    w("")
    w(f"The default **medium** profile models a mid-size online retailer: **{n(cfg['profiles']['medium']['customers'])} customers, "
      f"{n(cfg['profiles']['medium']['products'])} products and about {n(med['anchors']['orders_generated'])} orders over "
      f"{hist_days:,} days** ({hs} to {he}), followed by a {incr_days}-day incremental load. Volumes scale linearly with the three anchors in "
      f"`data/generator/profiles.yaml`; everything else follows from the ratios in the same file.")
    w("")
    w("| Profile | Customers | Products | Orders | Use |")
    w("|---|---:|---:|---:|---|")
    uses = {"tiny": "unit tests / CI (seconds)", "small": "laptop development (~4 s to generate)",
            "medium": "default benchmark (~40 s, ~1.5 GB RAM, ~340 MB CSV)"}
    for p in PROFILES:
        a = m[p]["anchors"]
        w(f"| {p} | {n(a['customers'])} | {n(a['products'])} | {n(a['orders_generated'])} | {uses[p]} |")
    w(f"| large | {n(cfg['profiles']['large']['customers'])} | {n(cfg['profiles']['large']['products'])} | "
      f"~{n(cfg['profiles']['large']['orders'])} | **not generated or tested**: roughly 10x medium, so expect ~15 GB RAM and ~3.4 GB of CSV |")
    w("")

    # ---- landing + reference
    w("## 1. Source tables (generated)")
    w("")
    w("These are loaded from CSV. `incremental` is the second load (new days plus corrections to history).")
    w("")
    w("| Table | tiny | small | medium initial | medium incremental | medium avg per day |")
    w("|---|---:|---:|---:|---:|---:|")
    for t in ["lnd.customer", "lnd.product", "lnd.order_header", "lnd.order_line", "lnd.payment", "lnd.shipment", "ref.currency_rate"]:
        vals = [m[p]["lnd_rows"]["initial"][t] for p in ("tiny", "small")]
        mi, mn = med["lnd_rows"]["initial"][t], med["lnd_rows"]["incremental"][t]
        avg = "static" if t in ("lnd.customer", "lnd.product", "ref.currency_rate") else n(round(mi / hist_days))
        w(f"| {t} | {n(vals[0])} | {n(vals[1])} | {n(mi)} | {n(mn)} | {avg} |")
    w("")
    w("`lnd.order_header` exceeds the order count because orders are re-sent when they are returned, corrected or arrive late. "
      "`lnd.shipment` is about twice the shipment count because the carrier sends a SHIPPED document and later a DELIVERED one. "
      "`lnd.customer` includes stale duplicate rows (about 20%).")
    w("")

    # ---- warehouse
    w("## 2. Warehouse tables (expected after the pipeline runs)")
    w("")
    w("Populated by the stored procedures, so these are *expected by construction*, not loaded. They have **not been verified against SQL Server**: "
      "on a real run, any difference is either a generator bug or a stored-procedure bug.")
    w("")
    w("| Table | tiny | small | medium after initial | medium after incremental |")
    w("|---|---:|---:|---:|---:|")
    keys = list(med["expected_warehouse_rows_by_construction"]["after_initial"].keys())
    for k in keys:
        v = [m[p]["expected_warehouse_rows_by_construction"]["after_initial"][k] for p in ("tiny", "small")]
        a = med["expected_warehouse_rows_by_construction"]["after_initial"][k]
        b = med["expected_warehouse_rows_by_construction"]["after_incremental"][k]
        w(f"| {k} | {n(v[0])} | {n(v[1])} | {n(a)} | {n(b)} |")
    w("")
    w("Notes: `dim.*` counts include the unknown member (key -1). `dim.customer` counts SCD2 versions. "
      "The `agg` rows depend on the run date because the aggregate rebuilds a rolling 24-month window; the figures assume the run date shown.")
    w("")

    # ---- control
    w("## 3. Control and static tables")
    w("")
    w("| Table | Rows | Notes |")
    w("|---|---:|---|")
    st = med["static_tables"]
    w(f"| etl.pipeline_step | {st['etl.pipeline_step']} | seeded |")
    w(f"| etl.watermark | {st['etl.watermark']} | lnd.order_header, lnd.payment, lnd.shipment, fact.order_line |")
    w(f"| etl.load_audit | ~20-45 per run | 1-2 rows per step plus a RUN_SUMMARY; grows with each run and each retry |")
    w(f"| dim.date | {n(med['expected_warehouse_rows_by_construction']['after_initial']['dim.date'])} | 2015-01-01 to 2035-12-31 plus unknown member |")
    w("")

    # ---- ratios
    ex = med["expected_warehouse_rows_by_construction"]["after_initial"]
    li = med["lnd_rows"]["initial"]
    orders = med["anchors"]["orders_generated"]
    w("## 4. Ratios worth knowing (medium)")
    w("")
    w("| Ratio | Value |")
    w("|---|---:|")
    w(f"| Orders per day (average) | {orders / (hist_days + incr_days):,.0f} |")
    w(f"| Orders per customer (average, all customers) | {orders / med['anchors']['customers']:.1f} |")
    w(f"| Order lines per order | {ex['stg.order_line'] / ex['stg.order_header']:.2f} |")
    w(f"| Fact lines per order | {ex['fact.order_line'] / ex['stg.order_header']:.2f} |")
    w(f"| Payment rows per order | {ex['fact.payment'] / ex['stg.order_header']:.2f} |")
    w(f"| Shipment rows per order | {ex['fact.shipment'] / ex['stg.order_header']:.2f} |")
    w(f"| Landing rows loaded per order (all lnd tables) | {sum(li[t] for t in li if t.startswith('lnd.order') or t in ('lnd.payment', 'lnd.shipment')) / orders:.1f} |")
    w(f"| Largest table | lnd.shipment ({n(li['lnd.shipment'])} rows) |")
    w(f"| Total landing rows, initial | {n(sum(li[t] for t in li if t.startswith('lnd.')))} |")
    w("")

    # ---- defects
    w("## 5. Planted data-quality defects (medium)")
    w("")
    w("Each defect is planted at a known rate so the agent's validation and root-cause analysis have ground truth to find. "
      "Rates are set in `profiles.yaml`; every defect appears at least once even in the tiny profile.")
    w("")
    w("| Defect | Count (whole timeline) | Expected downstream effect |")
    w("|---|---:|---|")
    pd_, det = med["planted_defects"], med["expected_details"]["after_incremental"]
    effects = {
        "customers_with_dup_rows": "stale duplicate rows; latest modified_at must win",
        "blank_id_customer_rows": "dropped in stg.customer (counted as rejected)",
        "customers_changed_incremental": "new SCD2 version in dim.customer",
        "customers_new_incremental": "new rows in dim.customer",
        "unknown_customer_orders": "fact lines load with customer_key = -1",
        "bad_date_orders": "header rejected in staging; their lines and payments never resolve",
        "late_arriving_orders": "is_late_arriving = 1, picked up out of date order",
        "held_back_orders": "payments arrive first -> orphan payments, reconciled one load later",
        "touched_orders": "header-only correction -> fact UPDATE path",
        "cancelled_orders": "in staging, excluded from facts",
        "cancel_lines": "kept in stg.order_line, excluded from facts",
        "returns": "RETURN lines priced from the original sale line when price is NULL",
        "refund_payments": "negative payments netted against order value",
        "chf_no_fx_orders": "reject NO_FX_RATE; their payments skipped",
        "failed_payment_docs": "in stg.payment, excluded from fact.payment",
        "invalid_json_docs": "counted as rejected in stg.usp_load_payments",
        "invalid_xml_docs": "counted as rejected in stg.usp_load_shipments",
        "product_price_changes": "SCD1 overwrite in dim.product",
        "products_removed": "soft delete (is_active = 0) in dim.product",
        "products_new": "inserted in dim.product",
        "test_products": "excluded in stg.product",
    }
    for k, v in pd_.items():
        w(f"| {k.replace('_', ' ')} | {n(v)} | {effects.get(k, '')} |")
    rb = det["rejects_by_code"]
    w("")
    w("Rejected order lines by reason (cumulative): " + ", ".join(f"{k} {n(v)}" for k, v in sorted(rb.items())) +
      f". Fact lines with an unknown customer: {n(det['unknown_customer_fact_lines'])}. "
      f"Orphan payments remaining after the incremental load: {n(det['orphan_payments'])}.")
    w("")

    w("## 6. Generating and loading")
    w("")
    w("```bash")
    w("python scripts/generate_data.py --profile medium      # writes data/generated/medium/{initial,incremental}/*.csv + manifest.json")
    w("python scripts/load_data.py --phase initial     --profile medium --conn \"<odbc connection string>\"")
    w("# run the pipeline:  EXEC etl.usp_run_daily_load;")
    w("python scripts/load_data.py --phase incremental --profile medium --conn \"<odbc connection string>\"")
    w("# run the pipeline again, then compare table counts with manifest.json")
    w("```")
    (ROOT / "docs" / "data-volumes.md").write_text("\n".join(L) + "\n")
    print("wrote docs/data-volumes.md")


if __name__ == "__main__":
    main()
