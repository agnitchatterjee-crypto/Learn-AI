#!/usr/bin/env python3
"""Synthetic data generator for the SQL Server retail order-to-cash platform.

Builds ONE coherent timeline (customers, products, orders, returns, payments, shipments), then slices it into
two loads that mirror how the pipeline is run:

    initial/      history_start .. history_end      (first run of etl.usp_run_daily_load)
    incremental/  a few new days + corrections       (second run: SCD2 changes, late data, orphan reconciliation)

Only the landing tables (lnd.*) and ref.currency_rate are generated. Staging, dimensions, facts and aggregates are
populated by the stored procedures; manifest.json records the row counts those procedures SHOULD produce, computed
by construction from the planted defects. Those expectations are unverified until run against SQL Server: any
mismatch is either a generator bug or a stored-procedure bug, which is exactly what they are for.

Usage:  python scripts/generate_data.py --profile medium
"""
import argparse
import csv
import json
import math
import random
import sys
import time as _time
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FMT = "%Y-%m-%d %H:%M:%S"
ISO = "%Y-%m-%dT%H:%M:%S"

FIRST = ("James Mary Robert Patricia John Jennifer Michael Linda David Elizabeth William Barbara Richard Susan Joseph "
         "Jessica Thomas Sarah Charles Karen Priya Arjun Anika Rahul Sofia Mateo Lucas Emma Noah Olivia Liam Ava "
         "Hannah Oliver Isla Jack Chloe Ravi Meera Amit Sneha Luca Giulia Hans Greta Pierre Camille Chen Mei").split()
LAST = ("Smith Johnson Williams Brown Jones Garcia Miller Davis Rodriguez Martinez Hernandez Lopez Wilson Anderson "
        "Taylor Moore Jackson Martin Lee Thompson White Harris Clark Lewis Robinson Walker Young Allen King Wright "
        "Scott Patel Sharma Gupta Singh Kumar Mukherjee Banerjee Muller Schmidt Fischer Dubois Moreau Bernard "
        "Rossi Russo Ferrari Wong Chan Nguyen Kim Park Campbell Murphy Kelly").split()
COUNTRIES = [("US", "USD", 55), ("GB", "GBP", 12), ("DE", "EUR", 8), ("FR", "EUR", 5), ("IN", "INR", 8),
             ("AU", "AUD", 6), ("CA", "CAD", 6)]
CITIES = {
    "US": [("New York", "NY"), ("Austin", "TX"), ("Seattle", "WA"), ("Chicago", "IL"), ("Denver", "CO")],
    "GB": [("London", "LND"), ("Manchester", "MAN"), ("Leeds", "LDS")],
    "DE": [("Berlin", "BE"), ("Munich", "BY"), ("Hamburg", "HH")],
    "FR": [("Paris", "IDF"), ("Lyon", "ARA"), ("Nantes", "PDL")],
    "IN": [("Kolkata", "WB"), ("Mumbai", "MH"), ("Bengaluru", "KA"), ("Delhi", "DL")],
    "AU": [("Sydney", "NSW"), ("Melbourne", "VIC"), ("Perth", "WA")],
    "CA": [("Toronto", "ON"), ("Vancouver", "BC"), ("Montreal", "QC")],
}
STREETS = "Oak Maple Cedar Pine Elm Lake Hill Park River Sunset Church Mill High Station Garden".split()
CATEGORIES = {
    "Electronics": ["Audio", "Phones", "Computers", "Accessories"],
    "Home": ["Kitchen", "Furniture", "Decor", "Lighting"],
    "Apparel": ["Men", "Women", "Kids", "Footwear"],
    "Sports": ["Fitness", "Outdoor", "Cycling"],
    "Beauty": ["Skincare", "Haircare", "Fragrance"],
    "Toys": ["Games", "Puzzles", "Dolls"],
    "Grocery": ["Snacks", "Beverages", "Pantry"],
    "Books": ["Fiction", "Non-fiction", "Children"],
}
CARRIERS = [("UPS", 3), ("FEDEX", 2), ("DHL", 4), ("USPS", 5), ("ROYAL_MAIL", 4), ("BLUE_DART", 6)]   # (name, promise days)
FX_BASE = {"GBP": 1.27, "EUR": 1.08, "INR": 0.012, "AUD": 0.66, "CAD": 0.74}
FX_OK = {"USD", *FX_BASE}


def fts(t):
    return t.strftime(FMT)


class Line:
    __slots__ = ("no", "pid", "qty", "price", "pct", "typ")

    def __init__(self, no, pid, qty, price, pct, typ):
        self.no, self.pid, self.qty, self.price, self.pct, self.typ = no, pid, qty, price, pct, typ


class Order:
    __slots__ = ("id", "ts", "cust", "cid", "country", "currency", "ship_country", "channel", "cancelled", "disc",
                 "lines", "bad_date", "held", "mod1", "touch_mod", "ret_ts", "ret_line", "paid_total")


class Cust:
    __slots__ = ("idx", "id", "first", "last", "country", "currency", "segment", "addr", "city", "state", "email",
                 "phone", "created", "weight", "is_new", "changed", "addr2", "segment2", "first_order")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="medium")
    ap.add_argument("--out", default=None, help="output directory (default data/generated/<profile>)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "data" / "generator" / "profiles.yaml").read_text())
    com, R = cfg["common"], cfg["rates"]
    if args.profile not in cfg["profiles"]:
        sys.exit(f"unknown profile {args.profile}; choose from {list(cfg['profiles'])}")
    prof = cfg["profiles"][args.profile]
    seed = args.seed if args.seed is not None else com["seed"]
    rng = random.Random(seed)
    out = Path(args.out) if args.out else ROOT / "data" / "generated" / args.profile
    t0 = _time.time()

    hs = date.fromisoformat(com["history_start"])
    he = date.fromisoformat(com["history_end"])
    incr = com["incremental_days"]
    ie = he + timedelta(days=incr)
    as_of = date.fromisoformat(com["as_of"])
    C1 = datetime.combine(he, time(23, 59, 59))
    C2 = datetime.combine(ie, time(23, 59, 59))
    hist_days = (he - hs).days + 1

    def phase(ts):
        return 1 if ts <= C1 else 2

    def hit(rate, n=None):
        return rng.random() < rate

    def at_least_one(rate, n):
        return max(1, round(rate * n)) if rate > 0 else 0

    # ------------------------------------------------------------------ currency rates (weekdays only)
    fx_rows = {1: [], 2: []}
    cur = dict(FX_BASE)
    d = hs - timedelta(days=60)
    while d <= ie:
        if d.weekday() < 5:
            for c in FX_BASE:
                cur[c] *= math.exp(rng.gauss(0, 0.003))
                fx_rows[1 if d <= he else 2].append([d.isoformat(), c, "USD", f"{cur[c]:.8f}"])
        d += timedelta(days=1)

    # ------------------------------------------------------------------ products
    n_prod = prof["products"]
    cats = list(CATEGORIES)
    prod = []   # dicts
    for i in range(1, n_prod + 1):
        cat = rng.choice(cats)
        price = round(min(900.0, max(2.0, math.exp(rng.gauss(3.4, 0.9)))), 2)
        prod.append(dict(id=f"P{i:05d}", name=f"{cat} item {i}", cat=cat, sub=rng.choice(CATEGORIES[cat]),
                         brand=f"Brand-{rng.randint(1, 30):02d}", price1=price, price2=price,
                         cost=round(price * rng.uniform(0.4, 0.7), 2),
                         status="ACTIVE" if rng.random() > 0.08 else "DISCONTINUED",
                         weight=math.exp(rng.gauss(0, 1.2)), mod="2023-%02d-%02d 09:00:00" % (rng.randint(1, 12), rng.randint(1, 28)),
                         removed=False, new=False, status2=None))
    n_new_p = at_least_one(R["product_new_rate"], n_prod)
    for i in range(n_prod + 1, n_prod + n_new_p + 1):
        cat = rng.choice(cats)
        price = round(min(900.0, max(2.0, math.exp(rng.gauss(3.4, 0.9)))), 2)
        prod.append(dict(id=f"P{i:05d}", name=f"{cat} item {i}", cat=cat, sub=rng.choice(CATEGORIES[cat]),
                         brand=f"Brand-{rng.randint(1, 30):02d}", price1=price, price2=price,
                         cost=round(price * rng.uniform(0.4, 0.7), 2), status="ACTIVE", weight=math.exp(rng.gauss(0, 1.2)),
                         mod=fts(C1 + timedelta(hours=rng.randint(1, 60))), removed=False, new=True, status2=None))
    base_p = [p for p in prod if not p["new"]]
    for p in rng.sample(base_p, at_least_one(R["product_price_change_rate"], n_prod)):
        p["price2"] = round(max(1.0, p["price1"] * rng.uniform(0.9, 1.15)), 2)
        p["mod"] = fts(C1 + timedelta(hours=rng.randint(1, 60)))
    for p in rng.sample(base_p, at_least_one(R["product_status_flip_rate"], n_prod)):
        p["status2"] = "DISCONTINUED" if p["status"] == "ACTIVE" else "ACTIVE"
        p["mod"] = fts(C1 + timedelta(hours=rng.randint(1, 60)))
    for p in rng.sample([p for p in base_p if p["status2"] is None], at_least_one(R["product_removed_rate"], n_prod)):
        p["removed"] = True
    n_test_p = at_least_one(R["product_test_rate"], n_prod)

    # weighted product pickers per phase (phase 2 excludes removed, adds new)
    p_phase1 = [p for p in prod if not p["new"]]
    p_phase2 = [p for p in prod if not p["removed"]]
    cum1, cum2 = [], []
    acc = 0.0
    for p in p_phase1:
        acc += p["weight"]; cum1.append(acc)
    acc = 0.0
    for p in p_phase2:
        acc += p["weight"]; cum2.append(acc)

    # ------------------------------------------------------------------ customers (attributes only; rows later)
    n_cust = prof["customers"]
    n_new_c = at_least_one(R["customer_new_rate"], n_cust)
    cw = [c[2] for c in COUNTRIES]
    segs = ["RETAIL"] * 70 + ["WHOLESALE"] * 10 + ["CORPORATE"] * 20
    custs = []

    def new_cust(i, is_new):
        c = Cust()
        c.idx, c.id, c.is_new = i, f"C{i:06d}", is_new
        c.first, c.last = rng.choice(FIRST), rng.choice(LAST)
        cc = rng.choices(COUNTRIES, weights=cw)[0]
        c.country, c.currency = cc[0], cc[1]
        c.city, c.state = rng.choice(CITIES[c.country])
        c.addr = f"{rng.randint(1, 9999)} {rng.choice(STREETS)} {rng.choice(['St', 'Ave', 'Rd', 'Lane'])}"
        c.segment = rng.choice(segs)
        c.email = f"{c.first}.{c.last}{i}@example.com".lower()
        c.phone = "".join(str(rng.randint(0, 9)) for _ in range(10))
        c.weight = math.exp(rng.gauss(0, 1.0))
        c.changed = False
        c.addr2 = c.segment2 = None
        c.first_order = None
        c.created = None
        return c

    for i in range(1, n_cust + 1):
        custs.append(new_cust(i, False))
    for i in range(n_cust + 1, n_cust + n_new_c + 1):
        custs.append(new_cust(i, True))
    base_c = custs[:n_cust]
    ccum, acc = [], 0.0
    for c in base_c:
        acc += c.weight; ccum.append(acc)

    # ------------------------------------------------------------------ order timestamps
    def day_weights(d0, n):
        ws = []
        for k in range(n):
            dd = d0 + timedelta(days=k)
            t = (dd - hs).days / hist_days
            ws.append((1 + 0.25 * t) * (1.35 if dd.month in (11, 12) else 1.0) * (0.9 if dd.weekday() == 5 else 1.0))
        return ws

    def stamp(dd):
        return datetime.combine(dd, time.min) + timedelta(seconds=int(rng.triangular(6 * 3600, 23 * 3600, 15 * 3600)))

    n_hist = prof["orders"]
    n_incr = max(8, round(n_hist / hist_days * incr * 1.05))
    days_h = rng.choices(range(hist_days), weights=day_weights(hs, hist_days), k=n_hist)
    days_i = rng.choices(range(incr), weights=day_weights(he + timedelta(days=1), incr), k=n_incr)
    stamps = [stamp(hs + timedelta(days=x)) for x in days_h] + [stamp(he + timedelta(days=1 + x)) for x in days_i]

    # customer for each order; new customers get 1-2 phase-2 orders of their own
    order_cust = []
    for ts in stamps:
        order_cust.append(rng.choices(range(n_cust), cum_weights=ccum)[0])
    extra = []   # (ts, custidx) for new customers and twin orders
    for c in custs[n_cust:]:
        for _ in range(rng.randint(1, 2)):
            extra.append((stamp(he + timedelta(days=1 + rng.randrange(incr))), c.idx - 1))
    twin_n = round(R["twin_order_rate"] * len(stamps))
    for k in rng.sample(range(len(stamps)), twin_n):
        t2 = stamps[k] + timedelta(seconds=rng.randint(3600, 4 * 86400))
        if t2 <= C2:
            extra.append((t2, order_cust[k]))
    allo = sorted(zip(stamps + [e[0] for e in extra], order_cust + [e[1] for e in extra]), key=lambda x: x[0])

    # ------------------------------------------------------------------ orders
    ld = R["lines_per_order"]
    ld_vals, ld_w = [x[0] for x in ld], [x[1] for x in ld]
    unk_cust_n = at_least_one(R["unknown_customer_order_rate"], len(allo))
    unk_set = set(rng.sample(range(len(allo)), unk_cust_n))
    orders = []
    nonce = 0
    for k, (ts, ci) in enumerate(allo):
        o = Order()
        o.id = f"O{k + 1:08d}"
        o.ts = ts
        if k in unk_set:
            o.cust = None
            o.cid = f"C9{rng.randint(0, 99999):05d}"
            cc = rng.choices(COUNTRIES, weights=cw)[0]
            o.country, o.currency = cc[0], cc[1]
        else:
            c = custs[ci]
            o.cust = c
            o.cid = c.id
            o.country, o.currency = c.country, c.currency
            if c.first_order is None:
                c.first_order = ts
        o.ship_country = o.country
        o.channel = rng.choices(["WEB", "STORE", "APP"], weights=[55, 30, 15])[0]
        o.cancelled = hit(R["cancelled_order_rate"])
        o.bad_date = o.held = False
        o.touch_mod = o.ret_ts = o.ret_line = None
        o.mod1 = ts + timedelta(minutes=rng.randint(1, 180))
        # lines
        in_p2 = ts > C1
        pool, cum = (p_phase2, cum2) if in_p2 else (p_phase1, cum1)
        nl = rng.choices(ld_vals, weights=ld_w)[0]
        seen, lines = set(), []
        for j in range(nl):
            for _ in range(3):
                p = pool[rng.choices(range(len(pool)), cum_weights=cum)[0]]
                if p["id"] not in seen:
                    break
            seen.add(p["id"])
            price = p["price2"] if in_p2 else p["price1"]
            qty = rng.choices([1, 2, 3, 4, 5], weights=[60, 25, 8, 5, 2])[0]
            pct = rng.choice([5, 10, 15, 20]) if hit(R["line_discount_rate"]) else 0
            typ = "CANCEL" if (j > 0 and not o.cancelled and hit(R["cancel_line_rate"])) else "SALE"
            lines.append(Line(j + 1, p["id"], qty, price, pct, typ))
        o.lines = lines
        # planted line defects (mutually exclusive per line)
        for ln in lines:
            u = rng.random()
            if u < R["unknown_product_line_rate"]:
                ln.pid = f"PX{rng.randint(0, 99999):05d}"
            elif u < R["unknown_product_line_rate"] + R["bad_quantity_line_rate"]:
                ln.qty = rng.choice([0, -1])
            elif u < R["unknown_product_line_rate"] + R["bad_quantity_line_rate"] + R["null_price_line_rate"]:
                ln.price = None
        orders.append(o)

    # guarantee at least one of each line defect even in tiny profiles
    def ensure_line_defect(kind, apply):
        if any(kind(l) for o in orders for l in o.lines):
            return
        for o in orders:
            ln = next((l for l in o.lines if l.typ == "SALE" and l.price is not None and l.qty > 0 and l.pid.startswith("P0")), None)
            if ln and not o.cancelled:
                apply(ln)
                return
    ensure_line_defect(lambda l: l.pid.startswith("PX"), lambda l: setattr(l, "pid", "PX00001"))
    ensure_line_defect(lambda l: l.qty <= 0, lambda l: setattr(l, "qty", 0))
    ensure_line_defect(lambda l: l.price is None, lambda l: setattr(l, "price", None))

    cand = [o for o in orders if not o.cancelled]
    # CHF / no-FX orders
    for o in rng.sample(cand, at_least_one(R["no_fx_order_rate"], len(orders))):
        o.currency, o.ship_country = "CHF", "CH"
    # bad order dates
    for o in rng.sample(orders, at_least_one(R["bad_order_date_rate"], len(orders))):
        o.bad_date = True
    # late arriving (old orders whose header shows up 5-40 days later)
    old = [o for o in orders if o.ts <= C1 - timedelta(days=45) and not o.cancelled and not o.bad_date]
    late_set = set()
    for o in rng.sample(old, min(len(old), at_least_one(R["late_arriving_order_rate"], len(orders)))):
        o.mod1 = o.ts + timedelta(days=rng.randint(5, 40), minutes=rng.randint(0, 600))
        late_set.add(o.id)
    # held back: header/lines arrive in the incremental load, payments and shipments arrive on time
    recent = [o for o in orders if C1 - timedelta(days=60) <= o.ts <= C1 and not o.cancelled and not o.bad_date and o.id not in late_set]
    for o in rng.sample(recent, min(len(recent), at_least_one(R["held_back_order_rate"], len(orders)))):
        o.held = True
        o.mod1 = C1 + timedelta(hours=rng.randint(2, 60))
        late_set.add(o.id)
    # header discounts
    for o in orders:
        sale = sum(round(l.qty * l.price, 2) - round(l.qty * l.price * l.pct / 100.0, 2)
                   for l in o.lines if l.typ == "SALE" and l.price is not None and l.qty > 0)
        o.disc = round(sale * rng.choice([0.05, 0.10, 0.15]), 2) if (sale > 20 and hit(R["header_discount_rate"])) else 0.0
        o.paid_total = round(sale - o.disc, 2)

    # returns
    ret_candidates = [o for o in orders if not o.cancelled and o.id not in late_set]
    n_ret = at_least_one(R["return_rate"], len(ret_candidates))
    no_orig_target = at_least_one(R["return_no_original_rate"], n_ret)
    returned = 0
    for o in rng.sample(ret_candidates, min(len(ret_candidates), n_ret * 2)):
        if returned >= n_ret:
            break
        sales = [l for l in o.lines if l.typ == "SALE" and l.price is not None and l.qty > 0 and l.pid.startswith("P0")]
        if not sales:
            continue
        rts = o.mod1 + timedelta(days=rng.randint(3, 30), minutes=rng.randint(0, 600))
        if rts > C2:
            continue
        src = rng.choice(sales)
        no_orig = returned < no_orig_target
        if no_orig:
            others = [p for p in p_phase1 if p["id"] not in {l.pid for l in o.lines}]
            pid, price = (rng.choice(others)["id"] if others else src.pid), src.price
            if not others:
                continue
        else:
            pid = src.pid
            price = None if hit(0.6) else src.price
        o.ret_line = Line(len(o.lines) + 1, pid, rng.randint(1, src.qty), price, 0, "RETURN")
        o.ret_ts = rts
        returned += 1
    # touched orders (header-only correction in the incremental load)
    touch_pool = [o for o in orders if o.ts <= C1 and not o.cancelled and not o.held and not o.bad_date and phase(o.mod1) == 1]
    for o in rng.sample(touch_pool, min(len(touch_pool), at_least_one(R["touched_order_rate"], len(orders)))):
        o.touch_mod = C1 + timedelta(hours=rng.randint(1, 70))

    # ------------------------------------------------------------------ emit order tables
    hdr = {1: [], 2: []}
    lin = {1: [], 2: []}

    def status_at(o, mod):
        if o.cancelled:
            return "CANCELLED"
        age = ((C1 if phase(mod) == 1 else C2) - o.ts).total_seconds()
        return "PROCESSING" if age < 2 * 86400 else ("SHIPPED" if age < 10 * 86400 else "COMPLETE")

    def date_raw(o):
        if o.bad_date:
            return rng.choice(["N/A", "2025-02-31 10:00:00", "31/13/2025"])
        return fts(o.ts)

    def hdr_row(o, mod, channel=None):
        cur_raw = o.currency.lower() if hit(0.01) else o.currency
        sc = o.ship_country
        if hit(0.02):
            sc = sc.lower() if hit(0.5) else (sc + "A")
        return [o.id, o.cid, date_raw(o), status_at(o, mod), cur_raw, channel or o.channel, sc,
                "" if o.disc == 0 else f"{o.disc:.2f}", fts(mod), phase(mod)]

    def line_row(o, ln, mod):
        return [o.id, ln.no, ln.pid, ln.qty, "" if ln.price is None else f"{ln.price:.4f}", f"{ln.pct:.2f}", ln.typ, fts(mod), phase(mod)]

    for o in orders:
        hdr[phase(o.mod1)].append(hdr_row(o, o.mod1))
        for ln in o.lines:
            lin[phase(o.mod1)].append(line_row(o, ln, o.mod1))
        if o.touch_mod:
            alt = {"WEB": "APP", "APP": "WEB", "STORE": "STORE"}[o.channel]
            hdr[2].append(hdr_row(o, o.touch_mod, alt))
            o.channel = alt
        if o.ret_line:
            hdr[phase(o.ret_ts)].append(hdr_row(o, o.ret_ts))
            lin[phase(o.ret_ts)].append(line_row(o, o.ret_line, o.ret_ts))

    # ------------------------------------------------------------------ pairing helper (combined payments / shipments)
    by_cust = defaultdict(list)
    for o in orders:
        if o.cust is not None and not o.cancelled:
            by_cust[o.cust.idx].append(o)

    def make_pairs(rate, gap_days, used):
        pairs = []
        for lst in by_cust.values():
            lst.sort(key=lambda x: x.ts)
            i = 0
            while i < len(lst) - 1:
                a, b = lst[i], lst[i + 1]
                if (a.id not in used and b.id not in used and b.ts - a.ts <= timedelta(days=gap_days)
                        and a.paid_total > 0 and b.paid_total > 0 and hit(rate)):
                    pairs.append((a, b)); used.add(a.id); used.add(b.id); i += 2
                else:
                    i += 1
        return pairs

    # ------------------------------------------------------------------ payments
    pay_docs = {1: [], 2: []}     # rows [payment_src_id, payload, received_at]
    pay_alloc = []                # (doc_id, status, type, currency, [(oid, amt)], rec_ts)  for expectations
    pay_n = [0]

    def add_payment(allocs, ptype, status, currency, ev_ts, valid=True):
        pay_n[0] += 1
        pid = f"PAY{pay_n[0]:09d}"
        rec = ev_ts + timedelta(seconds=rng.randint(5, 120))
        body = {"payment_id": pid, "method": rng.choices(["CARD", "PAYPAL", "BANK", "WALLET"], weights=[70, 15, 8, 7])[0],
                "type": ptype, "currency": currency, "status": status, "event_ts": ev_ts.strftime(ISO),
                "gateway": {"ref": f"gw_{rng.getrandbits(32):08x}"},
                "allocations": [{"order_id": a, "amount": m} for a, m in allocs]}
        payload = json.dumps(body, separators=(",", ":"))
        if not valid:
            payload = payload[: len(payload) // 2]
        row = [pid, payload, fts(rec)]
        pay_docs[phase(rec)].append(row)
        if rng.random() < R["duplicate_payment_doc_rate"] and valid:
            rec2 = rec + timedelta(minutes=rng.randint(1, 10))
            pay_docs[phase(rec2)].append([pid, payload, fts(rec2)])
        if valid:
            pay_alloc.append((pid, status.upper(), ptype, currency, list(allocs), rec))
        return pid

    def stat():
        return "OK" if hit(0.85) else "settled"

    paired = set()
    for a, b in make_pairs(R["combined_payment_rate"], 7, paired):
        ev = max(a.ts, b.ts) + timedelta(minutes=rng.randint(1, 60))
        add_payment([(a.id, a.paid_total), (b.id, b.paid_total)], "CAPTURE", stat(), a.currency, ev)
    for o in orders:
        if o.cancelled or o.paid_total <= 0 or o.id in paired:
            continue
        ev = o.ts + timedelta(minutes=rng.randint(1, 60))
        if hit(R["failed_payment_rate"]):
            add_payment([(o.id, o.paid_total)], "CAPTURE", "FAILED", o.currency, ev - timedelta(minutes=5))
        if hit(R["split_payment_rate"]) and o.paid_total > 10:
            first = round(o.paid_total * 0.6, 2)
            add_payment([(o.id, first)], "CAPTURE", stat(), o.currency, ev)
            add_payment([(o.id, round(o.paid_total - first, 2))], "CAPTURE", stat(), o.currency, ev + timedelta(days=rng.randint(1, 3)))
        else:
            add_payment([(o.id, o.paid_total)], "CAPTURE", stat(), o.currency, ev)
        if hit(R["chargeback_rate"]):
            cb = ev + timedelta(days=rng.randint(20, 60))
            if cb <= C2:
                add_payment([(o.id, o.paid_total)], "CHARGEBACK", "OK", o.currency, cb)
    n_refunds = 0
    for o in orders:
        if o.ret_line and hit(R["refund_rate"]):
            eff = o.ret_line.price
            if eff is None:
                eff = next((l.price for l in o.lines if l.pid == o.ret_line.pid and l.typ == "SALE"), None)
            if eff:
                add_payment([(o.id, round(o.ret_line.qty * eff, 2))], "REFUND", "OK", o.currency, o.ret_ts + timedelta(hours=1))
                n_refunds += 1
    n_pay_docs = sum(len(v) for v in pay_docs.values())
    for _ in range(at_least_one(R["invalid_json_doc_rate"], n_pay_docs)):
        o = rng.choice(orders)
        ev = o.ts + timedelta(minutes=rng.randint(1, 60))
        add_payment([(o.id, 1.0)], "CAPTURE", "OK", o.currency, ev, valid=False)

    # ------------------------------------------------------------------ shipments
    ship_docs = {1: [], 2: []}    # rows [shipment_src_id, payload_xml, received_at]
    ship_entities = []            # (id, [order ids], first_doc_rec_ts)
    ship_n = [0]
    cdict = dict(CARRIERS)

    def promised_midnight(t_ship, carrier):
        return datetime.combine((t_ship + timedelta(days=cdict[carrier])).date(), time.min)

    def add_shipment(orders_in, t_ship):
        ship_n[0] += 1
        sid = f"SHP{ship_n[0]:09d}"
        carrier = rng.choices([c[0] for c in CARRIERS], weights=[4, 3, 2, 4, 2, 1])[0]
        prom = promised_midnight(t_ship, carrier)
        if hit(R["lost_shipment_rate"]):
            t_del = None
        elif hit(R["late_delivery_rate"]):
            t_del = prom + timedelta(days=rng.randint(1, 4), hours=rng.randint(8, 18))
        else:
            t_del = max(t_ship + timedelta(hours=18), prom - timedelta(days=rng.randint(0, 1)) + timedelta(hours=rng.randint(8, 18)))
        weight = f"{rng.uniform(0.2, 12):.3f}"
        orders_xml = "".join(f'<Order ref="{x.id}"/>' for x in orders_in)

        def doc(delivered):
            ev = f'<Event type="SHIPPED" ts="{t_ship.strftime(ISO)}"/>'
            if delivered:
                ev += f'<Event type="DELIVERED" ts="{t_del.strftime(ISO)}"/>'
            return (f'<Shipment id="{sid}" carrier="{carrier}">{orders_xml}<Events>{ev}</Events>'
                    f'<Promise by="{prom.strftime(ISO)}"/><Parcel weightKg="{weight}"/></Shipment>')
        rec_a = t_ship + timedelta(minutes=rng.randint(1, 30))
        if rec_a > C2:
            return
        ship_docs[phase(rec_a)].append([sid, doc(False), fts(rec_a)])
        ship_entities.append((sid, [x.id for x in orders_in], rec_a))
        if t_del is not None:
            rec_b = t_del + timedelta(minutes=rng.randint(1, 30))
            if rec_b <= C2:
                ship_docs[phase(rec_b)].append([sid, doc(True), fts(rec_b)])

    sp_used = set()
    for a, b in make_pairs(R["consolidated_shipment_rate"], 2, sp_used):
        add_shipment([a, b], max(a.ts, b.ts) + timedelta(hours=rng.randint(4, 48)))
    for o in orders:
        if o.cancelled or o.id in sp_used:
            continue
        add_shipment([o], o.ts + timedelta(hours=rng.randint(4, 48)))
    n_ship_docs = sum(len(v) for v in ship_docs.values())
    for i in range(at_least_one(R["invalid_xml_doc_rate"], n_ship_docs)):
        t = he - timedelta(days=rng.randint(0, 20))
        rec = datetime.combine(t, time(12, 0))
        ship_docs[1].append([f"SHPBAD{i + 1:05d}",
                             f'<Shipment id="SHPBAD{i + 1:05d}" carrier="UPS"><Events/></Shipment>', fts(rec)])

    # ------------------------------------------------------------------ customers & products: landing rows
    for c in custs:
        base_created = (c.first_order.date() - timedelta(days=rng.randint(0, 5))) if c.first_order else \
            hs - timedelta(days=rng.randint(0, 900))
        if c.is_new:
            base_created = he + timedelta(days=rng.randint(1, incr))
        c.created = base_created

    def cust_row(c, addr, segment, mod, extract, id_variant=True):
        name = f"{c.first} {c.last}"
        r = rng.random()
        name = name.lower() if r < 0.10 else name.upper() if r < 0.18 else ("  " + name.replace(" ", "   ") + " ") if r < 0.28 else name
        email = c.email
        r = rng.random()
        if r < R["email_invalid_rate"]:
            email = email.replace("@", "")
        elif r < 0.05:
            email = email.upper()
        ph = c.phone
        fmt = rng.choice(["({0}) {1}-{2}", "{0}-{1}-{2}", "{0}{1}{2}", "{0} {1} {2}"])
        ph = fmt.format(ph[:3], ph[3:6], ph[6:])
        seg = segment
        r = rng.random()
        seg = seg.lower() if r < 0.07 else seg.title() if r < 0.12 else f" {seg} " if r < 0.15 else seg
        cc = c.country
        r = rng.random()
        cc = cc.lower() if r < 0.04 else (cc + "A") if r < 0.07 else f" {cc}" if r < 0.09 else cc
        cid = c.id
        if id_variant:
            r = rng.random()
            cid = cid.lower() if r < 0.005 else f" {cid} " if r < 0.01 else cid
        created = c.created.isoformat() if hit(0.7) else c.created.strftime("%d/%m/%Y")
        return [cid, name, email, ph, addr, c.city, c.state, cc, seg, created, fts(mod), extract]

    cust_rows = {1: [], 2: []}
    for c in base_c:
        mod = datetime.combine(c.created, time(10, 0)) + timedelta(days=rng.randint(0, max(0, (he - c.created).days)))
        mod = min(mod, C1)
        cust_rows[1].append(cust_row(c, c.addr, c.segment, mod, 1))
        if hit(R["customer_dup_rate"]):
            old_mod = mod - timedelta(days=rng.randint(30, 400))
            cust_rows[1].append(cust_row(c, f"{rng.randint(1, 9999)} {rng.choice(STREETS)} Old Rd", c.segment, old_mod, 1))
    blank_n = at_least_one(R["customer_blank_id_rate"], n_cust)
    for i in range(blank_n):
        c = rng.choice(base_c)
        row = cust_row(c, c.addr, c.segment, C1 - timedelta(days=rng.randint(1, 100)), 1, id_variant=False)
        row[0] = rng.choice(["", "   "]) if i % 2 == 0 else "   "
        cust_rows[1].append(row)
    n_changed = at_least_one(R["customer_change_rate"], n_cust)
    for c in rng.sample(base_c, n_changed):
        c.changed = True
        c.addr2 = f"{rng.randint(1, 9999)} {rng.choice(STREETS)} New Blvd"
        c.segment2 = rng.choice([s for s in ("RETAIL", "WHOLESALE", "CORPORATE") if s != c.segment])
        mod = C1 + timedelta(hours=rng.randint(1, 70))
        cust_rows[2].append(cust_row(c, c.addr2, c.segment2 if hit(0.5) else c.segment, mod, 2))
    for c in custs[n_cust:]:
        cust_rows[2].append(cust_row(c, c.addr, c.segment, datetime.combine(c.created, time(9, 0)) + timedelta(minutes=rng.randint(0, 600)), 2))

    def prod_row(p, price, status, extract):
        lp = f"{price:.2f}"
        if hit(0.01):
            lp = ""
        return [p["id"], "  " + p["name"] + " " if hit(0.05) else p["name"], p["cat"], p["sub"],
                p["brand"] if not hit(0.02) else "", lp, f"{p['cost']:.2f}", status, p["mod"], extract]

    prod_rows = {1: [], 2: []}
    for p in prod:
        if not p["new"]:
            prod_rows[1].append(prod_row(p, p["price1"], p["status"], 1))
    for i in range(n_test_p):
        prod_rows[1].append([f"T{i + 1:05d}", "Test product", "Test", "Test", "Test", "1.00", "1.00", "TEST", "2023-01-01 00:00:00", 1])
    for p in prod:
        if not p["removed"]:
            prod_rows[2].append(prod_row(p, p["price2"], p["status2"] or p["status"], 2))
    for i in range(n_test_p):
        prod_rows[2].append([f"T{i + 1:05d}", "Test product", "Test", "Test", "Test", "1.00", "1.00", "TEST", "2023-01-01 00:00:00", 2])

    # ------------------------------------------------------------------ write CSVs
    files = {
        "lnd.customer": (["customer_src_id", "full_name", "email", "phone", "address_line", "city", "state_code", "country_code",
                          "customer_segment", "created_date", "modified_at", "extract_id"], cust_rows),
        "lnd.product": (["product_src_id", "product_name", "category", "subcategory", "brand", "list_price", "unit_cost",
                         "status", "modified_at", "extract_id"], prod_rows),
        "lnd.order_header": (["order_src_id", "customer_src_id", "order_date", "order_status", "currency_code", "channel",
                              "ship_country", "order_discount_amt", "modified_at", "extract_id"], hdr),
        "lnd.order_line": (["order_src_id", "line_no", "product_src_id", "quantity", "unit_price", "line_discount_pct",
                            "line_type", "modified_at", "extract_id"], lin),
        "lnd.payment": (["payment_src_id", "payload", "received_at"], pay_docs),
        "lnd.shipment": (["shipment_src_id", "payload_xml", "received_at"], ship_docs),
        "ref.currency_rate": (["rate_date", "from_currency", "to_currency", "rate"], fx_rows),
    }
    lnd_rows = {"initial": {}, "incremental": {}}
    for tbl, (cols, by_phase) in files.items():
        for ph, name in ((1, "initial"), (2, "incremental")):
            d = out / name
            d.mkdir(parents=True, exist_ok=True)
            rows = by_phase[ph]
            with open(d / f"{tbl}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(cols)
                w.writerows(rows)
            lnd_rows[name][tbl] = len(rows)

    # ------------------------------------------------------------------ expectations (by construction)
    known = {1: {p["id"] for p in prod if not p["new"]}, 2: {p["id"] for p in prod}}

    def reject_code(o, ln, P):
        sale_pids = {}
        for l in o.lines:
            if l.typ == "SALE":
                sale_pids.setdefault(l.pid, l)      # proc picks the lowest line_no (TOP 1 ... ORDER BY line_no)
        if ln.qty <= 0:
            return "BAD_QUANTITY"
        if ln.pid not in known[P]:
            return "UNKNOWN_PRODUCT"
        if ln.typ == "RETURN" and ln.pid not in sale_pids:
            return "RETURN_NO_ORIGINAL"
        eff = ln.price if ln.price else None
        if ln.typ == "RETURN" and eff is None:
            eff = sale_pids[ln.pid].price if sale_pids.get(ln.pid) and sale_pids[ln.pid].price else None
        if eff is None or eff < 0:
            return "BAD_PRICE"
        if o.currency not in FX_OK:
            return "NO_FX_RATE"
        return None

    exp = {}
    detail = {}
    window_start = date(as_of.year - 2, as_of.month, 1)          # months_back = 24
    pivot_from = date(as_of.year - 1 if as_of.month < 12 else as_of.year, (as_of.month % 12) + 1 if as_of.month < 12 else 1, 1)
    for P, label in ((1, "after_initial"), (2, "after_incremental")):
        visible = [o for o in orders if not o.bad_date and phase(o.mod1) <= P]
        stg_lines = fact_lines = 0
        rej = defaultdict(int)
        unk_cust_lines = 0
        has_fact = set()
        agg_keys = set()
        trailing_custs = set()
        trailing_months = set()
        for o in visible:
            ls = list(o.lines) + ([o.ret_line] if (o.ret_line and phase(o.ret_ts) <= P) else [])
            stg_lines += len(ls)
            if o.cancelled:
                continue
            for ln in ls:
                if ln.typ not in ("SALE", "RETURN"):
                    continue
                rc = reject_code(o, ln, P)
                if rc:
                    rej[rc] += 1
                    continue
                fact_lines += 1
                has_fact.add(o.id)
                if o.cust is None:
                    unk_cust_lines += 1
                else:
                    if o.ts.date() >= window_start:
                        agg_keys.add((o.cust.idx, o.ts.year, o.ts.month))
                    if date(o.ts.year, o.ts.month, 1) >= pivot_from:
                        trailing_custs.add(o.cust.idx)
                        trailing_months.add((o.ts.year, o.ts.month))
        stg_pay = {(pid, oid) for pid, st, ty, cu, al, rec in pay_alloc if phase(rec) <= P for oid, _ in al}
        fact_pay = {(pid, oid) for pid, st, ty, cu, al, rec in pay_alloc
                    if phase(rec) <= P and st in ("OK", "SETTLED") and ty in ("CAPTURE", "REFUND", "CHARGEBACK") and cu in FX_OK
                    for oid, _ in al}
        orphans = sum(1 for _, oid in fact_pay if oid not in has_fact)
        ship_rows = sum(len(oids) for sid, oids, rec in ship_entities if phase(rec) <= P)
        n_cust_P = n_cust if P == 1 else n_cust + n_new_c
        changed = sum(1 for c in base_c if c.changed) if P == 2 else 0
        n_prod_P = n_prod - 0 if P == 1 else n_prod + n_new_p - sum(1 for p in prod if p["removed"])
        exp[label] = {
            "stg.customer": n_cust_P,
            "stg.product": n_prod_P,
            "stg.order_header": len(visible),
            "stg.order_line": stg_lines,
            "stg.payment": len(stg_pay),
            "stg.shipment": ship_rows,
            "dim.date": 7670 + 1,
            "dim.product": (n_prod if P == 1 else n_prod + n_new_p) + 1,
            "dim.customer": n_cust_P + changed + 1,
            "fact.order_line": fact_lines,
            "fact.order_line_reject": sum(rej.values()),
            "fact.payment": len(fact_pay),
            "fact.shipment": ship_rows,
            "agg.customer_monthly_revenue (as_of %s)" % as_of: len(agg_keys),
            "agg.customer_revenue_trailing rows (as_of %s)" % as_of: len(trailing_custs),
        }
        detail[label] = {"rejects_by_code": dict(rej), "unknown_customer_fact_lines": unk_cust_lines,
                         "orphan_payments": orphans, "customer_versions_current": n_cust_P + 1,
                         "trailing_pivot_month_columns": len(trailing_months)}
    exp["after_incremental"]["dim.customer"] = n_cust + n_new_c + sum(1 for c in base_c if c.changed) + 1

    # static tables
    fx_n = len(fx_rows[1]) + len(fx_rows[2])
    static = {"ref.currency_rate": fx_n, "etl.pipeline_step": 12, "etl.watermark": 4,
              "etl.load_audit": "about 20-45 rows per run (1-2 per step plus RUN_SUMMARY)"}
    planted = {
        "customers_with_dup_rows": sum(1 for r in cust_rows[1]) - n_cust - blank_n,
        "blank_id_customer_rows": blank_n,
        "customers_changed_incremental": sum(1 for c in base_c if c.changed),
        "customers_new_incremental": n_new_c,
        "unknown_customer_orders": unk_cust_n,
        "bad_date_orders": sum(1 for o in orders if o.bad_date),
        "late_arriving_orders": len(late_set) - sum(1 for o in orders if o.held),
        "held_back_orders": sum(1 for o in orders if o.held),
        "touched_orders": sum(1 for o in orders if o.touch_mod),
        "cancelled_orders": sum(1 for o in orders if o.cancelled),
        "cancel_lines": sum(1 for o in orders for l in o.lines if l.typ == "CANCEL"),
        "returns": sum(1 for o in orders if o.ret_line),
        "refund_payments": n_refunds,
        "chf_no_fx_orders": sum(1 for o in orders if o.currency == "CHF"),
        "failed_payment_docs": sum(1 for p in pay_alloc if p[1] == "FAILED"),
        "invalid_json_docs": at_least_one(R["invalid_json_doc_rate"], n_pay_docs),
        "invalid_xml_docs": at_least_one(R["invalid_xml_doc_rate"], n_ship_docs),
        "product_price_changes": sum(1 for p in prod if p["price2"] != p["price1"]),
        "products_removed": sum(1 for p in prod if p["removed"]),
        "products_new": n_new_p,
        "test_products": n_test_p,
    }
    manifest = {
        "profile": args.profile, "seed": seed,
        "anchors": {"customers": n_cust, "products": n_prod, "orders_requested": n_hist, "orders_generated": len(orders)},
        "dates": {"history_start": str(hs), "history_end": str(he), "incremental_end": str(ie), "as_of": str(as_of)},
        "lnd_rows": lnd_rows, "static_tables": static,
        "expected_warehouse_rows_by_construction": exp, "expected_details": detail, "planted_defects": planted,
        "note": "Expectations are derived from the generator's model, not from running SQL Server. "
                "A mismatch is either a generator bug or a stored-procedure bug.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"profile={args.profile}  seed={seed}  orders={len(orders):,}  elapsed={_time.time() - t0:.1f}s  -> {out}")
    for ph in ("initial", "incremental"):
        print(f"  {ph:<12}", {k: v for k, v in lnd_rows[ph].items()})


if __name__ == "__main__":
    main()
