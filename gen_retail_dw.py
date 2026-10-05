#!/usr/bin/env python3
"""
gen_retail_dw.py
================
Retail data-warehouse (star schema) generator. Pure standard library
(pandas/pyarrow optional for parquet).

DIMENSIONS : dim_date, dim_product, dim_customer (SCD Type 2), dim_store (physical + online),
             dim_supplier, dim_promotion
FACTS      : fact_sales (order-line grain), fact_returns, fact_product_reviews,
             fact_inventory_snapshot (weekly, store x product), fact_purchase_orders

Also writes schema.sql (DDL with PK/FK), sample_queries.sql, _manifest.json, and optionally
CSV / Parquet / JSONL / a ready-to-query SQLite database.

Realism built in: Zipf product popularity, Pareto customer activity, weekday/month/holiday
seasonality, yearly growth, promo windows, return rates by department, review ratings tied to
a latent product quality, inventory driven by actual sales with replenishment POs.

Examples
--------
  python gen_retail_dw.py --scale small  --out retail_small
  python gen_retail_dw.py --scale medium --out retail --formats csv,parquet,sqlite
  python gen_retail_dw.py --orders 500000 --customers 80000 --products 5000 --stores 40 --seed 7
"""
import argparse
import csv
import json
import math
import os
import random
import sqlite3
import sys
from bisect import bisect
from collections import defaultdict
from datetime import date, timedelta
from itertools import accumulate

# --------------------------------------------------------------------------
# Schema (single source of truth for DDL, CSV headers and SQLite)
# --------------------------------------------------------------------------
SCHEMA = {
    "dim_date": [("date_key", "INTEGER"), ("full_date", "DATE"), ("day_of_week", "SMALLINT"), ("day_name", "VARCHAR(10)"),
                 ("day_of_month", "SMALLINT"), ("week_of_year", "SMALLINT"), ("month_num", "SMALLINT"), ("month_name", "VARCHAR(10)"),
                 ("quarter", "SMALLINT"), ("year", "SMALLINT"), ("fiscal_year", "SMALLINT"), ("fiscal_quarter", "SMALLINT"),
                 ("is_weekend", "SMALLINT"), ("is_holiday", "SMALLINT"), ("is_peak_season", "SMALLINT")],
    "dim_supplier": [("supplier_key", "INTEGER"), ("supplier_name", "VARCHAR(100)"), ("country", "VARCHAR(50)"), ("lead_time_days", "SMALLINT"),
                     ("payment_terms", "VARCHAR(20)"), ("quality_rating", "DECIMAL(3,1)"), ("contract_start_date", "DATE")],
    "dim_product": [("product_key", "INTEGER"), ("sku", "VARCHAR(20)"), ("product_name", "VARCHAR(150)"), ("department", "VARCHAR(50)"),
                    ("category", "VARCHAR(50)"), ("subcategory", "VARCHAR(50)"), ("brand", "VARCHAR(50)"), ("supplier_key", "INTEGER"),
                    ("list_price", "DECIMAL(12,2)"), ("unit_cost", "DECIMAL(12,2)"), ("description", "VARCHAR(2000)"),
                    ("attributes_json", "VARCHAR(500)"), ("launch_date", "DATE"), ("discontinued_date", "DATE"), ("is_active", "SMALLINT")],
    "dim_customer": [("customer_key", "INTEGER"), ("customer_id", "VARCHAR(12)"), ("first_name", "VARCHAR(50)"), ("last_name", "VARCHAR(50)"),
                     ("email", "VARCHAR(120)"), ("gender", "VARCHAR(10)"), ("birth_date", "DATE"), ("city", "VARCHAR(50)"),
                     ("state", "VARCHAR(50)"), ("country", "VARCHAR(50)"), ("loyalty_tier", "VARCHAR(10)"), ("signup_date", "DATE"),
                     ("acquisition_channel", "VARCHAR(30)"), ("effective_from", "DATE"), ("effective_to", "DATE"), ("is_current", "SMALLINT")],
    "dim_store": [("store_key", "INTEGER"), ("store_id", "VARCHAR(10)"), ("store_name", "VARCHAR(100)"), ("store_type", "VARCHAR(20)"),
                  ("channel", "VARCHAR(10)"), ("city", "VARCHAR(50)"), ("state", "VARCHAR(50)"), ("country", "VARCHAR(50)"),
                  ("region", "VARCHAR(20)"), ("open_date", "DATE"), ("square_feet", "INTEGER"), ("manager_name", "VARCHAR(100)")],
    "dim_promotion": [("promo_key", "INTEGER"), ("promo_name", "VARCHAR(100)"), ("promo_type", "VARCHAR(20)"), ("discount_pct", "DECIMAL(5,2)"),
                      ("start_date", "DATE"), ("end_date", "DATE"), ("channel", "VARCHAR(10)"), ("target_department", "VARCHAR(50)")],
    "fact_sales": [("sales_line_key", "BIGINT"), ("order_id", "VARCHAR(14)"), ("line_number", "SMALLINT"), ("date_key", "INTEGER"),
                   ("order_timestamp", "TIMESTAMP"), ("product_key", "INTEGER"), ("customer_key", "INTEGER"), ("store_key", "INTEGER"),
                   ("promo_key", "INTEGER"), ("payment_method", "VARCHAR(20)"), ("quantity", "SMALLINT"), ("unit_price", "DECIMAL(12,2)"),
                   ("discount_amount", "DECIMAL(12,2)"), ("net_sales", "DECIMAL(12,2)"), ("tax_amount", "DECIMAL(12,2)"),
                   ("cost_amount", "DECIMAL(12,2)"), ("gross_margin", "DECIMAL(12,2)")],
    "fact_returns": [("return_key", "BIGINT"), ("sales_line_key", "BIGINT"), ("order_id", "VARCHAR(14)"), ("date_key", "INTEGER"),
                     ("product_key", "INTEGER"), ("customer_key", "INTEGER"), ("store_key", "INTEGER"), ("quantity_returned", "SMALLINT"),
                     ("refund_amount", "DECIMAL(12,2)"), ("reason_code", "VARCHAR(30)"), ("item_condition", "VARCHAR(20)"),
                     ("customer_comment", "VARCHAR(500)")],
    "fact_product_reviews": [("review_key", "BIGINT"), ("sales_line_key", "BIGINT"), ("product_key", "INTEGER"), ("customer_key", "INTEGER"),
                             ("date_key", "INTEGER"), ("rating", "SMALLINT"), ("review_title", "VARCHAR(150)"), ("review_text", "VARCHAR(2000)"),
                             ("helpful_votes", "INTEGER"), ("verified_purchase", "SMALLINT")],
    "fact_inventory_snapshot": [("snapshot_date_key", "INTEGER"), ("product_key", "INTEGER"), ("store_key", "INTEGER"), ("on_hand_qty", "INTEGER"),
                                ("units_sold_week", "INTEGER"), ("reorder_point", "INTEGER"), ("stockout_flag", "SMALLINT"),
                                ("inventory_value", "DECIMAL(14,2)")],
    "fact_purchase_orders": [("po_key", "BIGINT"), ("po_number", "VARCHAR(12)"), ("supplier_key", "INTEGER"), ("product_key", "INTEGER"),
                             ("store_key", "INTEGER"), ("order_date_key", "INTEGER"), ("expected_date_key", "INTEGER"),
                             ("received_date_key", "INTEGER"), ("qty_ordered", "INTEGER"), ("qty_received", "INTEGER"),
                             ("unit_cost", "DECIMAL(12,2)"), ("status", "VARCHAR(12)")],
}
PKS = {"dim_date": ["date_key"], "dim_supplier": ["supplier_key"], "dim_product": ["product_key"], "dim_customer": ["customer_key"],
       "dim_store": ["store_key"], "dim_promotion": ["promo_key"], "fact_sales": ["sales_line_key"], "fact_returns": ["return_key"],
       "fact_product_reviews": ["review_key"], "fact_inventory_snapshot": ["snapshot_date_key", "product_key", "store_key"],
       "fact_purchase_orders": ["po_key"]}
FKS = {
    "dim_product": [("supplier_key", "dim_supplier")],
    "fact_sales": [("date_key", "dim_date"), ("product_key", "dim_product"), ("customer_key", "dim_customer"), ("store_key", "dim_store"), ("promo_key", "dim_promotion")],
    "fact_returns": [("sales_line_key", "fact_sales"), ("date_key", "dim_date"), ("product_key", "dim_product"), ("customer_key", "dim_customer"), ("store_key", "dim_store")],
    "fact_product_reviews": [("sales_line_key", "fact_sales"), ("product_key", "dim_product"), ("customer_key", "dim_customer"), ("date_key", "dim_date")],
    "fact_inventory_snapshot": [("snapshot_date_key", "dim_date"), ("product_key", "dim_product"), ("store_key", "dim_store")],
    "fact_purchase_orders": [("supplier_key", "dim_supplier"), ("product_key", "dim_product"), ("store_key", "dim_store"),
                             ("order_date_key", "dim_date"), ("expected_date_key", "dim_date"), ("received_date_key", "dim_date")],
}

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------
FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Arjun", "Sneha", "Vikram", "Meera", "Rahul", "Ishita", "Sourav", "Debjani", "Amit", "Kavya",
         "James", "Emily", "Oliver", "Sophie", "Daniel", "Hannah", "Michael", "Chloe", "Wei", "Mei", "Carlos", "Sofia", "Omar", "Layla", "Zara", "Noah"]
LAST = ["Sharma", "Banerjee", "Chatterjee", "Iyer", "Reddy", "Nair", "Gupta", "Singh", "Das", "Patel", "Kapoor", "Mehta", "Bose", "Ghosh", "Rao",
        "Smith", "Johnson", "Taylor", "Brown", "Wilson", "Clarke", "Walker", "Chen", "Wong", "Garcia", "Silva", "Khan", "Ali", "Kim", "Nguyen"]
GEO = [  # city, state, country, region, weight
    ("Kolkata", "West Bengal", "India", "East", 10), ("Mumbai", "Maharashtra", "India", "West", 12), ("Delhi", "Delhi", "India", "North", 12),
    ("Bengaluru", "Karnataka", "India", "South", 11), ("Chennai", "Tamil Nadu", "India", "South", 7), ("Hyderabad", "Telangana", "India", "South", 7),
    ("Pune", "Maharashtra", "India", "West", 6), ("Ahmedabad", "Gujarat", "India", "West", 4), ("Jaipur", "Rajasthan", "India", "North", 3),
    ("Guwahati", "Assam", "India", "East", 2), ("London", "England", "United Kingdom", "Europe", 5), ("Manchester", "England", "United Kingdom", "Europe", 2),
    ("New York", "New York", "United States", "Americas", 6), ("Austin", "Texas", "United States", "Americas", 3), ("Singapore", "Singapore", "Singapore", "APAC", 4)]

CATALOG = {  # department -> category -> subcategories
    "Apparel": {"Men's Clothing": ["T-Shirts", "Jeans", "Jackets"], "Women's Clothing": ["Dresses", "Tops", "Kurtas"], "Footwear": ["Sneakers", "Sandals", "Boots"]},
    "Home & Kitchen": {"Kitchen": ["Cookware", "Appliances", "Storage"], "Furniture": ["Chairs", "Tables", "Shelves"], "Decor": ["Lamps", "Wall Art", "Cushions"]},
    "Electronics": {"Mobile": ["Smartphones", "Cases", "Chargers"], "Audio": ["Headphones", "Speakers"], "Computing": ["Laptops", "Keyboards", "Monitors"]},
    "Grocery": {"Pantry": ["Rice & Grains", "Spices", "Snacks"], "Beverages": ["Tea", "Coffee", "Juices"]},
    "Beauty": {"Skincare": ["Moisturisers", "Sunscreen"], "Haircare": ["Shampoo", "Hair Oil"]},
    "Sports": {"Fitness": ["Yoga Mats", "Dumbbells"], "Outdoor": ["Backpacks", "Water Bottles"]},
}
DEPT_PRICE = {"Apparel": (8, 120), "Home & Kitchen": (10, 600), "Electronics": (15, 1500), "Grocery": (1, 25), "Beauty": (3, 60), "Sports": (8, 200)}
DEPT_TAX = {"Grocery": 0.05}
DEPT_WEIGHT = {"Apparel": 24, "Home & Kitchen": 16, "Electronics": 16, "Grocery": 22, "Beauty": 12, "Sports": 10}
RETURN_RATE = {"Apparel": 0.12, "Electronics": 0.08, "Home & Kitchen": 0.06, "Beauty": 0.04, "Sports": 0.05, "Grocery": 0.01}
BRANDS = {"Apparel": ["UrbanLoom", "Threadwell", "Kasturi", "NorthPeak"], "Home & Kitchen": ["Hearthstone", "CasaNova", "Brightware", "OakLine"],
          "Electronics": ["Voltix", "Nexora", "Zenbyte", "AudioMint"], "Grocery": ["Freshfarm", "Spice Route", "GreenLeaf", "Daily Bowl"],
          "Beauty": ["Glowlab", "Pure Roots", "Velvetique"], "Sports": ["Stridefit", "Peakline", "TrailMate"]}
ADJ = ["Classic", "Premium", "Everyday", "Ultra", "Essential", "Signature", "Eco", "Compact", "Pro", "Lite"]
MATERIAL = {"Apparel": ["organic cotton", "linen blend", "recycled polyester", "denim", "leather"], "Home & Kitchen": ["stainless steel", "solid oak", "ceramic", "bamboo", "tempered glass"],
            "Electronics": ["aluminium alloy", "polycarbonate", "tempered glass", "ABS plastic"], "Grocery": ["natural ingredients", "organic ingredients"],
            "Beauty": ["plant-based ingredients", "dermatologist-tested formula"], "Sports": ["recycled rubber", "ripstop nylon", "stainless steel"]}
COLORS = ["black", "white", "navy", "olive", "terracotta", "grey", "sand", "red", "teal"]
FEATURES = ["Designed for everyday use and easy to maintain.", "Backed by a manufacturer warranty and free returns.", "Lightweight and built to last through daily wear.",
            "Ships in recyclable packaging.", "A bestseller among customers in its category.", "Tested for quality and safety before dispatch."]
PAYMENT = ["Credit Card", "Debit Card", "UPI", "Cash", "Wallet", "Gift Card", "EMI"]
CHANNELS = ["Organic Search", "Paid Social", "Referral", "Email", "Walk-in", "Marketplace"]
RETURN_REASONS = {
    "DEFECTIVE": ["Item stopped working after two days.", "Arrived damaged in transit.", "Stitching came apart on first wash.", "Screen had a visible crack on arrival."],
    "WRONG_SIZE": ["Too small, ordering a larger size.", "Fit was not what I expected from the size chart.", "Runs large compared to other brands."],
    "NOT_AS_DESCRIBED": ["Colour looks different from the photos.", "Material feels cheaper than the description suggests.", "Missing accessories listed on the page."],
    "CHANGED_MIND": ["No longer needed.", "Bought a duplicate by mistake.", "Decided on a different model."],
    "LATE_DELIVERY": ["Arrived after the event I needed it for.", "Delivery took far longer than promised."],
    "BETTER_PRICE": ["Found it cheaper elsewhere."],
}
REASON_W = {"DEFECTIVE": 22, "WRONG_SIZE": 22, "NOT_AS_DESCRIBED": 18, "CHANGED_MIND": 24, "LATE_DELIVERY": 8, "BETTER_PRICE": 6}
REVIEW_TXT = {
    "pos": ["Absolutely love this {p}. {a} is excellent and it arrived on time.", "Great value. The {a} exceeded my expectations, would buy again.",
            "Very happy with the {p}. {a} is exactly as described.", "Solid purchase - {a} is outstanding for the price."],
    "mid": ["The {p} is okay. {a} is average but it does the job.", "Decent product, though {a} could be better.", "Not bad. {a} is fine, nothing special."],
    "neg": ["Disappointed with the {p}. {a} is poor and not worth the money.", "Would not recommend - {a} was much worse than expected.", "Returned it. {a} did not match the listing."],
}
ASPECTS = ["Build quality", "Fit", "Packaging", "Value for money", "Finish", "Battery life", "Taste", "Durability"]
SUPPLIER_WORDS = ["Apex", "Bluewave", "Crestline", "Dunmore", "Evergreen", "Fortis", "Globex", "Harbor", "Ironbridge", "Jadeline", "Kestrel", "Lumina"]
SUPPLIER_TYPE = ["Textiles", "Trading", "Manufacturing", "Distribution", "Exports", "Industries"]
MONTH_F = {1: .95, 2: .85, 3: .9, 4: .95, 5: .95, 6: .9, 7: .95, 8: 1.0, 9: .95, 10: 1.25, 11: 1.5, 12: 1.6}
FIXED_PROMOS = [  # name, (m1,d1), (m2,d2), pct, dept, channel
    ("New Year Sale", (1, 1), (1, 7), 15, "All", "All"), ("Republic Day Sale", (1, 24), (1, 28), 20, "All", "All"),
    ("Summer Clearance", (4, 20), (5, 10), 25, "Apparel", "All"), ("Monsoon Home Sale", (7, 1), (7, 15), 20, "Home & Kitchen", "All"),
    ("Independence Day Sale", (8, 10), (8, 15), 15, "All", "All"), ("Festive Season Sale", (10, 10), (11, 5), 18, "All", "All"),
    ("Black Friday Week", (11, 24), (11, 30), 30, "Electronics", "All"), ("Year End Sale", (12, 20), (12, 31), 25, "All", "All")]

SCALES = {  # customers, products, stores, suppliers, orders, inventory_weeks, inventory_sku_share
    "small": dict(customers=2000, products=300, stores=12, suppliers=25, orders=25000, inventory_weeks=26, inventory_sku_share=0.4),
    "medium": dict(customers=40000, products=3000, stores=60, suppliers=120, orders=250000, inventory_weeks=13, inventory_sku_share=0.12),
    "large": dict(customers=250000, products=12000, stores=150, suppliers=300, orders=1000000, inventory_weeks=8, inventory_sku_share=0.05),
}


def dkey(d):
    return d.year * 10000 + d.month * 100 + d.day


def pick(r, items, cum):
    return items[bisect(cum, r.random() * cum[-1])]


def money(x):
    return round(x + 1e-9, 2)


# --------------------------------------------------------------------------
class Warehouse:
    def __init__(self, a):
        self.a = a
        self.r = random.Random(a.seed)
        self.start, self.end = date.fromisoformat(a.start_date), date.fromisoformat(a.end_date)
        self.t = {k: [] for k in SCHEMA}
        self.wk_sales = defaultdict(int)

    # ---------- dimensions ----------
    def build_dim_date(self):
        d, last = self.start, self.end + timedelta(days=120)  # extra runway for PO expected dates
        hol = set()
        for y in range(self.start.year, last.year + 1):
            hol |= {date(y, 1, 1), date(y, 1, 26), date(y, 8, 15), date(y, 10, 2), date(y, 12, 25)}
            n = date(y, 11, 1)
            thursdays = [n + timedelta(days=i) for i in range(30) if (n + timedelta(days=i)).weekday() == 3]
            hol.add(thursdays[3] + timedelta(days=1))  # Black Friday
        rows = []
        while d <= last:
            fy = d.year if d.month >= 4 else d.year - 1
            fq = ((d.month - 4) % 12) // 3 + 1
            rows.append((dkey(d), d.isoformat(), d.weekday() + 1, d.strftime("%A"), d.day, d.isocalendar()[1], d.month, d.strftime("%B"),
                         (d.month - 1) // 3 + 1, d.year, fy, fq, int(d.weekday() >= 5), int(d in hol), int(d.month >= 10)))
            d += timedelta(days=1)
        self.t["dim_date"] = rows
        self.holidays = hol

    def build_dim_supplier(self):
        r = self.r
        for i in range(1, self.a.suppliers + 1):
            self.t["dim_supplier"].append((i, f"{r.choice(SUPPLIER_WORDS)} {r.choice(SUPPLIER_TYPE)} {i:03d}", r.choice(["India", "India", "China", "Vietnam", "Bangladesh", "Germany"]),
                                           r.choice([5, 7, 10, 14, 21, 30]), r.choice(["Net 30", "Net 45", "Net 60", "Advance"]),
                                           round(r.uniform(3.0, 5.0), 1), (self.start - timedelta(days=r.randint(30, 1500))).isoformat()))

    def build_dim_product(self):
        r = self.r
        depts = list(DEPT_WEIGHT)
        dcum = list(accumulate(DEPT_WEIGHT.values()))
        self.products = []
        for i in range(1, self.a.products + 1):
            dept = pick(r, depts, dcum)
            cat = r.choice(list(CATALOG[dept]))
            sub = r.choice(CATALOG[dept][cat])
            brand = r.choice(BRANDS[dept])
            lo, hi = DEPT_PRICE[dept]
            price = money(math.exp(r.uniform(math.log(lo), math.log(hi))))
            cost = money(price * r.uniform(0.45, 0.75))
            mat, col = r.choice(MATERIAL[dept]), r.choice(COLORS)
            name = f"{brand} {r.choice(ADJ)} {sub}"
            desc = (f"{name} is a {r.choice(ADJ).lower()} {sub.lower()} from {brand}, made from {mat} and available in {col}. "
                    f"{r.choice(FEATURES)} {r.choice(FEATURES)}")
            attrs = json.dumps({"color": col, "material": mat, "warranty_months": r.choice([0, 6, 12, 24]), "weight_g": r.randint(80, 5000)})
            launch = self.start - timedelta(days=r.randint(0, 900)) if r.random() < 0.7 else self.start + timedelta(days=r.randint(0, (self.end - self.start).days - 30))
            disc = launch + timedelta(days=r.randint(200, 1200)) if r.random() < 0.12 else None
            if disc and disc > self.end:
                disc = None
            p = dict(key=i, dept=dept, price=price, cost=cost, launch=launch, disc=disc, name=name, sup=r.randint(1, self.a.suppliers),
                     pop=1.0 / (r.randint(1, self.a.products) ** 0.9), quality=min(4.8, max(2.0, r.gauss(4.0, 0.55))))
            self.products.append(p)
            self.t["dim_product"].append((i, f"SKU-{i:06d}", name, dept, cat, sub, brand, p["sup"], price, cost, desc, attrs, launch.isoformat(),
                                          disc.isoformat() if disc else None, int(disc is None)))
        self.prod_cum = list(accumulate(p["pop"] for p in self.products))

    def build_dim_store(self):
        r = self.r
        geo_cum = list(accumulate(g[4] for g in GEO))
        self.stores = []
        online = [("Online - Web", "WEB"), ("Online - App", "APP")]
        rows = []
        for i, (nm, code) in enumerate(online, 1):
            rows.append((i, code, nm, "Online", "Online", "Bengaluru", "Karnataka", "India", "South", self.start.isoformat(), None, None))
            self.stores.append(dict(key=i, online=True, w=18.0, channel="Online"))
        for i in range(len(online) + 1, self.a.stores + len(online) + 1):
            c, s, co, reg, _ = pick(r, GEO, geo_cum)
            typ = r.choices(["Flagship", "Mall", "High Street", "Outlet"], [10, 40, 35, 15])[0]
            sq = {"Flagship": 30000, "Mall": 12000, "High Street": 6000, "Outlet": 9000}[typ] + r.randint(-2000, 2000)
            rows.append((i, f"ST{i:04d}", f"{c} {typ} {i:02d}", typ, "Store", c, s, co, reg,
                         (self.start - timedelta(days=r.randint(0, 3000))).isoformat(), sq, f"{r.choice(FIRST)} {r.choice(LAST)}"))
            self.stores.append(dict(key=i, online=False, w=sq / 6000.0 * r.uniform(0.7, 1.3), channel="Store"))
        self.t["dim_store"] = rows
        self.store_cum = list(accumulate(s["w"] for s in self.stores))

    def build_dim_customer(self):
        r = self.r
        geo_cum = list(accumulate(g[4] for g in GEO))
        rows = [(0, "GUEST", "Guest", "Customer", None, "Unknown", None, "Unknown", "Unknown", "Unknown", "None", None, "Unknown",
                 self.start.isoformat(), "9999-12-31", 1)]
        key = 1
        self.customers = []
        for i in range(1, self.a.customers + 1):
            fn, ln = r.choice(FIRST), r.choice(LAST)
            g = pick(r, GEO, geo_cum)
            signup = self.start - timedelta(days=730) + timedelta(days=r.randint(0, (self.end - self.start).days + 730 - 15))
            birth = date(r.randint(1955, 2005), r.randint(1, 12), r.randint(1, 28))
            tier = r.choices(["Bronze", "Silver", "Gold", "Platinum"], [55, 25, 15, 5])[0]
            ch = r.choice(CHANNELS)
            base = (f"C{i:07d}", fn, ln, f"{fn}.{ln}{i}@mail.example.com".lower(), r.choice(["F", "M", "Other"]), birth.isoformat())
            versions = [(key, signup, g, tier)]
            rows.append((key, *base, g[0], g[1], g[2], tier, signup.isoformat(), ch, signup.isoformat(), "9999-12-31", 1))
            if r.random() < self.a.scd_rate and (self.end - max(signup, self.start)).days > 120:  # SCD2: tier upgrade and/or relocation
                chg = max(signup, self.start) + timedelta(days=r.randint(60, (self.end - max(signup, self.start)).days - 30))
                g2 = pick(r, GEO, geo_cum) if r.random() < 0.5 else g
                tier2 = {"Bronze": "Silver", "Silver": "Gold", "Gold": "Platinum", "Platinum": "Platinum"}[tier]
                rows[-1] = rows[-1][:-3] + (signup.isoformat(), (chg - timedelta(days=1)).isoformat(), 0)
                key += 1
                rows.append((key, *base, g2[0], g2[1], g2[2], tier2, signup.isoformat(), ch, chg.isoformat(), "9999-12-31", 1))
                versions.append((key, chg, g2, tier2))
            key += 1
            self.customers.append(dict(signup=signup, versions=versions, w=min(r.paretovariate(1.4), 60.0)))
        self.t["dim_customer"] = rows
        self.cust_cum = list(accumulate(c["w"] for c in self.customers))

    def cust_key_on(self, c, d):
        k = c["versions"][0][0]
        for v in c["versions"]:
            if v[1] <= d:
                k = v[0]
        return k

    def build_dim_promotion(self):
        r = self.r
        rows = [(0, "No Promotion", "None", 0, self.start.isoformat(), "9999-12-31", "All", "All")]
        self.promos = []
        key = 1
        for y in range(self.start.year, self.end.year + 1):
            for nm, (m1, d1), (m2, d2), pct, dept, ch in FIXED_PROMOS:
                s, e = date(y, m1, d1), date(y, m2, d2)
                if e < self.start or s > self.end:
                    continue
                typ = "Clearance" if "Clearance" in nm else "Percent Off"
                rows.append((key, f"{nm} {y}", typ, pct, s.isoformat(), e.isoformat(), ch, dept))
                self.promos.append(dict(key=key, s=s, e=e, pct=pct, dept=dept, ch=ch))
                key += 1
            for _ in range(self.a.extra_promos_per_year):
                s = date(y, 1, 1) + timedelta(days=r.randint(0, 340))
                e = s + timedelta(days=r.randint(6, 20))
                if e < self.start or s > self.end:
                    continue
                dept = r.choice(list(DEPT_WEIGHT) + ["All"])
                typ = r.choice(["Percent Off", "BOGO", "Bundle", "Loyalty"])
                pct = {"Percent Off": r.choice([10, 15, 20]), "BOGO": 25, "Bundle": 12, "Loyalty": 10}[typ]
                ch = r.choice(["All", "Online", "In-Store"])
                rows.append((key, f"{dept if dept != 'All' else 'Storewide'} {typ} {s:%b} {y}", typ, pct, s.isoformat(), e.isoformat(), ch, dept))
                self.promos.append(dict(key=key, s=s, e=e, pct=pct, dept=dept, ch=ch))
                key += 1
        self.t["dim_promotion"] = rows
        self.promo_by_day = {}

    def promos_on(self, d):
        if d not in self.promo_by_day:
            self.promo_by_day[d] = [p for p in self.promos if p["s"] <= d <= p["e"]]
        return self.promo_by_day[d]

    # ---------- facts ----------
    def day_weight(self, d):
        w = MONTH_F[d.month] * (1.3 if d.weekday() >= 5 else 1.0) * (1.12 ** ((d - self.start).days / 365.0))
        if d in self.holidays:
            w *= 2.0 if d.month == 11 else 0.7
        return w

    def build_sales_returns_reviews(self):
        r, a = self.r, self.a
        days = [self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1)]
        dcum = list(accumulate(self.day_weight(d) for d in days))
        order_days = sorted(r.choices(days, cum_weights=dcum, k=a.orders))
        sales, rets, revs = self.t["fact_sales"], self.t["fact_returns"], self.t["fact_product_reviews"]
        line_key = ret_key = rev_key = 0
        for oi, d in enumerate(order_days, 1):
            store = pick(r, self.stores, self.store_cum)
            cust = None
            if r.random() > a.guest_rate:
                for _ in range(4):
                    c = pick(r, self.customers, self.cust_cum)
                    if c["signup"] <= d:
                        cust = c
                        break
            ckey = self.cust_key_on(cust, d) if cust else 0
            ts = f"{d.isoformat()} {r.choices(range(8, 23), [2, 3, 4, 5, 6, 7, 6, 5, 5, 6, 7, 8, 8, 6, 3])[0]:02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}"
            order_id = f"ORD-{d:%y%m%d}-{oi:06d}"
            pay = r.choice(PAYMENT)
            eligible = [p for p in self.promos_on(d) if p["ch"] in ("All", "Online" if store["online"] else "In-Store")]
            for ln in range(1, 2 + min(7, int(r.expovariate(0.55)))):
                prod = None
                for _ in range(5):
                    cand = pick(r, self.products, self.prod_cum)
                    if cand["launch"] <= d and (cand["disc"] is None or cand["disc"] >= d):
                        prod = cand
                        break
                if not prod:
                    continue
                qty = r.choices([1, 2, 3, 4], [70, 20, 7, 3])[0]
                price = money(prod["price"] * (1 + 0.03 * (d.year - self.start.year)))
                pk, pct = 0, 0
                best = [p for p in eligible if p["dept"] in ("All", prod["dept"])]
                if best and r.random() < 0.7:
                    b = max(best, key=lambda x: x["pct"])
                    pk, pct = b["key"], b["pct"]
                gross = price * qty
                disc = money(gross * pct / 100.0)
                net = money(gross - disc)
                tax = money(net * DEPT_TAX.get(prod["dept"], 0.18))
                cost = money(prod["cost"] * qty)
                line_key += 1
                sales.append((line_key, order_id, ln, dkey(d), ts, prod["key"], ckey, store["key"], pk, pay, qty, price, disc, net, tax, cost, money(net - cost)))
                if not store["online"]:
                    self.wk_sales[(store["key"], prod["key"], d - timedelta(days=d.weekday()))] += qty
                if r.random() < RETURN_RATE[prod["dept"]]:
                    rd = d + timedelta(days=r.randint(1, 30))
                    if rd <= self.end:
                        ret_key += 1
                        w = dict(REASON_W)
                        if prod["dept"] == "Apparel":
                            w["WRONG_SIZE"] *= 2
                        reason = r.choices(list(w), list(w.values()))[0]
                        rq = qty if r.random() < 0.8 else 1
                        rets.append((ret_key, line_key, order_id, dkey(rd), prod["key"], ckey, store["key"], rq, money(net * rq / qty), reason,
                                     r.choices(["New", "Opened", "Used", "Damaged"], [30, 35, 15, 20])[0],
                                     r.choice(RETURN_REASONS[reason]) if r.random() < 0.6 else None))
                if cust and r.random() < a.review_rate:
                    vd = d + timedelta(days=r.randint(3, 40))
                    if vd <= self.end:
                        rating = int(min(5, max(1, round(r.gauss(prod["quality"], 0.9)))))
                        kind = "pos" if rating >= 4 else "mid" if rating == 3 else "neg"
                        txt = r.choice(REVIEW_TXT[kind]).format(p=prod["name"], a=r.choice(ASPECTS))
                        title = {"pos": "Great purchase", "mid": "It's okay", "neg": "Not worth it"}[kind]
                        rev_key += 1
                        revs.append((rev_key, line_key, prod["key"], ckey, dkey(vd), rating, title, txt, int(r.expovariate(0.3)), 1))

    def build_inventory_and_pos(self):
        r, a = self.r, self.a
        last_sun = self.end - timedelta(days=(self.end.weekday() + 1) % 7)
        weeks = [(last_sun - timedelta(days=6 + 7 * k), last_sun - timedelta(days=7 * k)) for k in range(a.inventory_weeks - 1, -1, -1)]
        sup_lead = {s[0]: s[3] for s in self.t["dim_supplier"]}
        by_pop = sorted(self.products, key=lambda p: -p["pop"] * r.uniform(0.6, 1.4))
        n_sku = max(5, int(len(self.products) * a.inventory_sku_share))
        stocked = [p for p in by_pop if p["disc"] is None or p["disc"] > weeks[0][0]][:n_sku]
        snaps, pos, po_key = self.t["fact_inventory_snapshot"], self.t["fact_purchase_orders"], 0
        for st in self.stores:
            if st["online"]:
                continue
            for p in stocked:
                rp = r.randint(1, 4)
                target = rp * 3 + 2
                on_hand, arrivals = target, {}
                for wi, (mon, sun) in enumerate(weeks):
                    on_hand += arrivals.pop(wi, (0,))[0] if wi in arrivals else 0
                    sold = self.wk_sales.get((st["key"], p["key"], mon), 0)
                    stockout = int(sold > on_hand)
                    on_hand = max(0, on_hand - sold)
                    if on_hand <= rp and not arrivals:
                        qty = target - on_hand + r.randint(0, rp)
                        lead = sup_lead[p["sup"]]
                        delay = r.choice([0, 0, 0, 2, 4, 7])
                        recv = sun + timedelta(days=lead + delay)
                        got = qty if r.random() < 0.97 else int(qty * 0.8)
                        arrive_wi = wi + max(1, math.ceil((lead + delay) / 7))
                        if arrive_wi < len(weeks):
                            arrivals[arrive_wi] = (got,)
                        po_key += 1
                        pos.append((po_key, f"PO-{po_key:07d}", p["sup"], p["key"], st["key"], dkey(sun), dkey(sun + timedelta(days=lead)),
                                    dkey(recv) if recv <= self.end else None, qty, got if recv <= self.end else None, p["cost"],
                                    "Received" if recv <= self.end else "Open"))
                    snaps.append((dkey(sun), p["key"], st["key"], on_hand, sold, rp, stockout, money(on_hand * p["cost"])))

    def build_all(self):
        self.build_dim_date()
        self.build_dim_supplier()
        self.build_dim_product()
        self.build_dim_store()
        self.build_dim_customer()
        self.build_dim_promotion()
        self.build_sales_returns_reviews()
        self.build_inventory_and_pos()


# --------------------------------------------------------------------------
def ddl():
    out = ["-- Generated by gen_retail_dw.py (ANSI-style; works on Snowflake, Databricks SQL, Postgres, SQLite)", ""]
    for t, cols in SCHEMA.items():
        lines = [f"    {c} {ty}" for c, ty in cols]
        lines.append(f"    PRIMARY KEY ({', '.join(PKS[t])})")
        for col, ref in FKS.get(t, []):
            lines.append(f"    FOREIGN KEY ({col}) REFERENCES {ref}({PKS[ref][0]})")
        out.append(f"CREATE TABLE IF NOT EXISTS {t} (\n" + ",\n".join(lines) + "\n);\n")
    return "\n".join(out)


SAMPLE_SQL = """-- Monthly net sales, margin and return rate by department
SELECT d.year, d.month_num, p.department,
       SUM(s.net_sales) AS net_sales, SUM(s.gross_margin) AS margin,
       ROUND(100.0 * SUM(s.gross_margin) / NULLIF(SUM(s.net_sales), 0), 1) AS margin_pct
FROM fact_sales s JOIN dim_date d ON d.date_key = s.date_key JOIN dim_product p ON p.product_key = s.product_key
GROUP BY d.year, d.month_num, p.department ORDER BY 1, 2, 3;

-- Top 10 products by revenue with their average review rating
SELECT p.product_name, SUM(s.net_sales) AS revenue,
       (SELECT ROUND(AVG(rating), 2) FROM fact_product_reviews r WHERE r.product_key = p.product_key) AS avg_rating
FROM fact_sales s JOIN dim_product p ON p.product_key = s.product_key
GROUP BY p.product_key, p.product_name ORDER BY revenue DESC LIMIT 10;

-- Customer lifetime value by loyalty tier AS OF the order date (uses the SCD2 key)
SELECT c.loyalty_tier, COUNT(DISTINCT c.customer_id) AS customers, ROUND(SUM(s.net_sales), 2) AS revenue
FROM fact_sales s JOIN dim_customer c ON c.customer_key = s.customer_key
GROUP BY c.loyalty_tier ORDER BY revenue DESC;

-- Promotion lift: share of discounted lines and average discount by promotion
SELECT pr.promo_name, COUNT(*) AS lines, ROUND(SUM(s.discount_amount), 2) AS discount_given, ROUND(SUM(s.net_sales), 2) AS net_sales
FROM fact_sales s JOIN dim_promotion pr ON pr.promo_key = s.promo_key WHERE pr.promo_key <> 0
GROUP BY pr.promo_name ORDER BY net_sales DESC LIMIT 15;

-- Return rate and top reasons by department
SELECT p.department, COUNT(DISTINCT s.sales_line_key) AS lines, COUNT(DISTINCT r.return_key) AS returns,
       ROUND(100.0 * COUNT(DISTINCT r.return_key) / COUNT(DISTINCT s.sales_line_key), 2) AS return_rate_pct
FROM fact_sales s JOIN dim_product p ON p.product_key = s.product_key LEFT JOIN fact_returns r ON r.sales_line_key = s.sales_line_key
GROUP BY p.department ORDER BY return_rate_pct DESC;

-- Stock-outs and open purchase orders by store
SELECT st.store_name, SUM(i.stockout_flag) AS stockout_weeks, SUM(i.inventory_value) AS inventory_value
FROM fact_inventory_snapshot i JOIN dim_store st ON st.store_key = i.store_key
GROUP BY st.store_name ORDER BY stockout_weeks DESC LIMIT 10;
"""


def write_csv(out, name, rows):
    with open(os.path.join(out, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow([c for c, _ in SCHEMA[name]])
        for row in rows:
            w.writerow(["" if v is None else v for v in row])


def write_parquet(out, name, rows):
    try:
        import pandas as pd
        pd.DataFrame(rows, columns=[c for c, _ in SCHEMA[name]]).to_parquet(os.path.join(out, f"{name}.parquet"), index=False)
        return True
    except Exception as e:
        print("  [parquet skipped - pip install pyarrow]" if "pyarrow" in str(e) else f"  [parquet skipped: {e}]")
        return False


def write_sqlite(out, tables):
    path = os.path.join(out, "retail_dw.db")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript(ddl())
    for name, rows in tables.items():
        if rows:
            con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(SCHEMA[name]))})", rows)
    con.commit()
    con.close()


def snowflake_load_sql(out_dir, counts):
    path = os.path.abspath(out_dir).replace("\\", "/")
    L = ["-- Snowflake load script generated by gen_retail_dw.py",
         "-- Run order: (1) this context block  (2) schema.sql  (3) the rest of this file.",
         "-- PUT only works from SnowSQL / Snowflake CLI / a connector, not from Snowsight worksheets.",
         "",
         "CREATE DATABASE IF NOT EXISTS RETAIL_DW;",
         "CREATE SCHEMA IF NOT EXISTS RETAIL_DW.CORE;",
         "USE SCHEMA RETAIL_DW.CORE;",
         "",
         "CREATE OR REPLACE FILE FORMAT retail_csv",
         "  TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' EMPTY_FIELD_AS_NULL = TRUE",
         "  DATE_FORMAT = 'YYYY-MM-DD' TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS' ENCODING = 'UTF8';",
         "CREATE OR REPLACE STAGE retail_stage FILE_FORMAT = retail_csv;",
         "",
         f"PUT 'file://{path}/*.csv' @retail_stage AUTO_COMPRESS = TRUE OVERWRITE = TRUE;",
         "",
         "-- Dimensions first, then facts (same order as schema.sql)"]
    for t in SCHEMA:
        L.append(f"COPY INTO {t} FROM @retail_stage/{t}.csv.gz ON_ERROR = ABORT_STATEMENT;")
    L += ["", "-- Self-check: loaded vs expected row counts"]
    L.append("\nUNION ALL\n".join(f"SELECT '{t}' AS tbl, (SELECT COUNT(*) FROM {t}) AS loaded, {n} AS expected" for t, n in counts.items()) + ";")
    with open(os.path.join(out_dir, "load_snowflake.sql"), "w") as f:
        f.write("\n".join(L) + "\n")


def parse_args():
    p = argparse.ArgumentParser(description="Generate a retail star-schema data warehouse.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--scale", choices=SCALES, default="small", help="preset sizes; individual flags override")
    for k in ["customers", "products", "stores", "suppliers", "orders", "inventory_weeks"]:
        p.add_argument(f"--{k.replace('_', '-')}", type=int)
    p.add_argument("--inventory-sku-share", type=float, help="share of catalogue (most popular first) stocked per physical store")
    p.add_argument("--guest-rate", type=float, default=0.12, help="share of orders without a known customer")
    p.add_argument("--scd-rate", type=float, default=0.15, help="share of customers with a 2nd SCD2 version (tier/city change)")
    p.add_argument("--review-rate", type=float, default=0.04, help="share of order lines that get a review")
    p.add_argument("--extra-promos-per-year", type=int, default=6)
    p.add_argument("--start-date", default="2023-01-01")
    p.add_argument("--end-date", default="2026-09-30")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="retail_dw")
    p.add_argument("--formats", default="csv,sqlite", help="comma list: csv,jsonl,parquet,sqlite")
    a = p.parse_args()
    for k, v in SCALES[a.scale].items():
        if getattr(a, k) is None:
            setattr(a, k, v)
    return a


def main():
    a = parse_args()
    os.makedirs(a.out, exist_ok=True)
    w = Warehouse(a)
    w.build_all()
    fmts = {f.strip() for f in a.formats.split(",")}
    for name, rows in w.t.items():
        if "csv" in fmts:
            write_csv(a.out, name, rows)
        if "jsonl" in fmts:
            cols = [c for c, _ in SCHEMA[name]]
            with open(os.path.join(a.out, f"{name}.jsonl"), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(dict(zip(cols, row)), default=str) + "\n")
    if "parquet" in fmts:
        for name, rows in w.t.items():
            if not write_parquet(a.out, name, rows):
                break
    if "sqlite" in fmts:
        write_sqlite(a.out, w.t)
    with open(os.path.join(a.out, "schema.sql"), "w") as f:
        f.write(ddl())
    with open(os.path.join(a.out, "sample_queries.sql"), "w") as f:
        f.write(SAMPLE_SQL)
    counts = {k: len(v) for k, v in w.t.items()}
    with open(os.path.join(a.out, "_manifest.json"), "w") as f:
        json.dump({"args": vars(a), "row_counts": counts}, f, indent=2)
    snowflake_load_sql(a.out, counts)
    print(f"Wrote retail DW to {a.out}")
    for k, n in counts.items():
        print(f"  {k:<26}{n:>10,}")


if __name__ == "__main__":
    sys.exit(main())
