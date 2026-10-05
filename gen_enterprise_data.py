#!/usr/bin/env python3
"""
gen_enterprise_data.py
======================
Synthetic, *relational* enterprise corpus for testing a RAG knowledge assistant.
Pure standard library (pandas/pyarrow/reportlab are optional extras).

Tables produced
---------------
departments, employees, projects, project_members, services,
documents (+ document_versions, document_acl), emails, tickets,
query_log (usage/monitoring), eval_queries + eval_qrels (ground truth for MRR/nDCG)

Retrieval-testing features built in
-----------------------------------
* Facts (numbers, names, dates) are embedded in document text, and every eval
  question has a known answer and a known source document.
* Hard negatives: the same policy exists for several regions with different
  values, and some policies have an ARCHIVED older version with outdated values.
* Facts appear at random positions inside long documents (good for chunk-size tuning).
* Emails and tickets restate facts from documents (relevance-1 / noisy duplicates).

Examples
--------
  python gen_enterprise_data.py --scale small  --out data_small
  python gen_enterprise_data.py --scale medium --out data --formats csv,parquet,sqlite
  python gen_enterprise_data.py --employees 3000 --docs 5000 --doc-length long --seed 7
"""
import argparse
import csv
import json
import math
import os
import random
import sqlite3
import re
import sys
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------
COMPANY = "Northwind Analytics"
DOMAIN = "northwind-analytics.example.com"

FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Arjun", "Sneha", "Vikram", "Meera", "Rahul", "Ishita",
         "Sourav", "Debjani", "Amit", "Kavya", "Nikhil", "Pooja", "Sanjay", "Riya", "Karan", "Neha",
         "James", "Emily", "Oliver", "Sophie", "Daniel", "Hannah", "Michael", "Chloe", "William", "Grace",
         "Lukas", "Anna", "Felix", "Marta", "Jonas", "Lena", "Wei", "Mei", "Jun", "Li",
         "Carlos", "Sofia", "Omar", "Layla", "Tom", "Zara", "Ethan", "Maya", "Noah", "Ava"]
LAST = ["Sharma", "Banerjee", "Chatterjee", "Mukherjee", "Iyer", "Reddy", "Nair", "Gupta", "Singh", "Das",
        "Patel", "Kapoor", "Mehta", "Bose", "Ghosh", "Menon", "Rao", "Joshi", "Verma", "Sen",
        "Smith", "Johnson", "Taylor", "Brown", "Wilson", "Clarke", "Walker", "Hughes", "Evans", "Wright",
        "Muller", "Schmidt", "Fischer", "Weber", "Wagner", "Becker", "Tan", "Lim", "Chen", "Wong",
        "Garcia", "Silva", "Khan", "Ali", "Cohen", "Novak", "Larsen", "Kim", "Park", "Nguyen"]

REGION_INFO = {  # region -> currency, fx multiplier for money amounts, slug, cities, headcount weight
    "India":          dict(cur="INR", fx=80, slug="india", cities=["Kolkata", "Bengaluru", "Pune", "Hyderabad"], w=40),
    "United Kingdom": dict(cur="GBP", fx=1, slug="uk", cities=["London", "Manchester"], w=15),
    "United States":  dict(cur="USD", fx=1, slug="us", cities=["New York", "Austin", "Seattle"], w=20),
    "Singapore":      dict(cur="SGD", fx=1, slug="sg", cities=["Singapore"], w=10),
    "Germany":        dict(cur="EUR", fx=1, slug="de", cities=["Berlin", "Munich"], w=15),
}
REGIONS = list(REGION_INFO)

DEPARTMENTS = [  # code, name, headcount weight
    ("EXE", "Executive Office", 0), ("ENG", "Engineering", 28), ("SAL", "Sales", 12),
    ("SUP", "Customer Support", 14), ("OPS", "Operations", 10), ("DAT", "Data & Analytics", 8),
    ("FIN", "Finance", 6), ("HR", "Human Resources", 5), ("IT", "IT Services", 6),
    ("MKT", "Marketing", 6), ("LEG", "Legal & Compliance", 3),
]
DEPT_NAME = {c: n for c, n, _ in DEPARTMENTS}
TITLES = {
    "ENG": ["Software Engineer", "Platform Engineer", "QA Engineer", "DevOps Engineer"],
    "HR": ["HR Business Partner", "Recruiter", "Compensation Analyst"],
    "FIN": ["Financial Analyst", "Accountant", "Payroll Specialist"],
    "SAL": ["Account Executive", "Sales Engineer", "Business Development Rep"],
    "MKT": ["Content Strategist", "Marketing Analyst", "Campaign Manager"],
    "IT": ["IT Support Engineer", "Systems Administrator", "Security Analyst"],
    "LEG": ["Legal Counsel", "Compliance Analyst", "Contracts Specialist"],
    "OPS": ["Operations Analyst", "Program Manager", "Facilities Coordinator"],
    "SUP": ["Support Specialist", "Support Engineer", "Customer Success Manager"],
    "DAT": ["Data Engineer", "Data Analyst", "ML Engineer"],
    "EXE": ["Chief of Staff"],
}
LEVEL_PREFIX = {1: "Associate ", 2: "", 3: "Senior "}

CODENAMES = ["Atlas", "Borealis", "Cascade", "Dynamo", "Ember", "Falcon", "Glacier", "Harbor", "Ibis", "Juniper",
             "Kestrel", "Lantern", "Meridian", "Nimbus", "Orion", "Pinnacle", "Quartz", "Rift", "Summit", "Tundra",
             "Umbra", "Vertex", "Willow", "Xenon", "Yonder", "Zephyr", "Aurora", "Beacon", "Comet", "Delta",
             "Eclipse", "Fjord", "Granite", "Horizon", "Indigo", "Jade", "Keystone", "Lotus", "Mosaic", "Nebula"]
SVC_PREFIX = ["billing", "identity", "catalog", "orders", "payments", "notification", "search", "inventory",
              "reporting", "pricing", "ledger", "shipping", "audit", "scheduler", "profile", "recommendation",
              "ingestion", "analytics", "auth", "tenant"]
SVC_SUFFIX = ["api", "service", "worker", "gateway", "engine", "hub", "sync"]
LANGS = ["Python", "Java", "Go", "Node.js", "Kotlin"]
DBS = ["PostgreSQL", "MySQL", "MongoDB", "DynamoDB", "Cassandra"]
QUEUES = ["Kafka", "RabbitMQ", "Amazon SQS", "Azure Service Bus"]
ALERTS = ["High error rate", "Elevated latency", "Queue backlog", "Disk usage high", "Certificate expiring"]
DELIVERABLES = ["data migration plan", "security review", "load test report", "vendor contract", "user training deck",
                "API specification", "rollout checklist", "cost forecast"]

FILLER = [
    "All employees are expected to follow this guidance in addition to applicable local laws in {region}.",
    "Exceptions must be approved in writing by the department head and recorded in the {dept} register.",
    "Questions about this document should be directed to the {dept} team through the internal service desk.",
    "This document is reviewed annually and whenever there is a material change to the underlying process.",
    "Managers are responsible for ensuring that their teams have read and understood these requirements.",
    "Records related to this process are stored in the approved system of record and retained according to the data retention policy.",
    "Where this document conflicts with local regulation, the stricter requirement applies.",
    "Training materials supporting this guidance are available on the learning platform.",
    "Feedback and suggested improvements are welcome and are triaged at the monthly process review.",
    "Contractors and temporary staff are covered unless their agreement states otherwise.",
    "Audit and compliance teams may request evidence of adherence at any time.",
    "Escalations that cannot be resolved at team level are raised to the relevant steering committee.",
    "{company} values transparency, so material changes are announced on the intranet before they take effect.",
    "Teams should document any workaround they adopt so that it can be reviewed and, where appropriate, standardised.",
    "Metrics for this process are reported quarterly to the leadership team as part of the operating review.",
    "Third-party vendors who support this process must meet the same standards through contractual obligations.",
    "Personal data handled as part of this process must be processed in line with the privacy notice.",
    "Cross-functional dependencies should be identified early and tracked in the shared planning board.",
]
FILLER_HEADINGS = ["Roles and Responsibilities", "Compliance and Exceptions", "Related Resources", "Review and Maintenance",
                   "Background", "Glossary and Definitions", "Scope and Applicability", "Reporting and Metrics",
                   "Dependencies", "Frequently Raised Concerns"]

# ----- spec-driven documents (policies + FAQs). Params get (rng, ctx); money is scaled by ctx["fx"]. -----
SPECS = [
    dict(key="pto", kind="policy", dept="HR", title="Paid Time Off Policy",
         params=lambda r, c: dict(days=r.randint(15, 30), carry=r.randint(3, 10), notice=r.choice([3, 5, 7, 10, 14]), sick=r.randint(6, 15)),
         sections=[("Purpose", "This policy explains how {company} employees in {region} accrue and use paid time off."),
                   ("Entitlement", "Full-time employees in {region} receive {days} days of paid time off per calendar year. In addition, employees receive {sick} days of paid sick leave."),
                   ("Carryover", "Unused paid time off may be carried over to the next year up to a maximum of {carry} days. Days above this cap expire on 31 March."),
                   ("Requesting Leave", "Leave of more than three consecutive days must be requested at least {notice} working days in advance through the HR portal.")],
         facts=[("How many days of paid time off do employees in {region} get each year?", "{days} days"),
                ("What is the maximum number of PTO days that can be carried over in {region}?", "{carry} days"),
                ("How much notice is required for leave longer than three days in {region}?", "{notice} working days"),
                ("How many paid sick days do employees in {region} receive?", "{sick} days")]),
    dict(key="expense", kind="policy", dept="FIN", title="Expense Reimbursement Policy",
         params=lambda r, c: dict(meal=r.choice([25, 30, 40, 50, 60, 75]) * c["fx"], hotel=r.choice([100, 125, 150, 200, 250, 300]) * c["fx"],
                                  receipt=r.choice([10, 15, 20, 25]) * c["fx"], approval=r.choice([250, 500, 1000, 2500]) * c["fx"], submit=r.choice([15, 30, 45, 60])),
         sections=[("Overview", "This policy sets the rules for business expenses claimed by {company} employees in {region}."),
                   ("Limits", "The daily meal allowance is {cur} {meal:,}. Hotel stays are reimbursed up to {cur} {hotel:,} per night."),
                   ("Receipts", "Receipts are required for any single expense above {cur} {receipt:,}."),
                   ("Approvals and Deadlines", "Claims above {cur} {approval:,} need approval from the department head. Claims must be submitted within {submit} days of the expense date.")],
         facts=[("What is the daily meal allowance in {region}?", "{cur} {meal:,}"),
                ("What is the nightly hotel limit for employees in {region}?", "{cur} {hotel:,}"),
                ("Above what amount are receipts required in {region}?", "{cur} {receipt:,}"),
                ("Within how many days must expense claims be submitted in {region}?", "{submit} days")]),
    dict(key="remote", kind="policy", dept="HR", title="Remote and Hybrid Work Policy",
         params=lambda r, c: dict(wfh=r.choice([1, 2, 3, 5]), cfrom=r.choice(["09:00", "10:00", "11:00"]), cto=r.choice(["15:00", "16:00", "17:00"]),
                                  stipend=r.choice([20, 30, 40, 50]) * c["fx"]),
         sections=[("Eligibility", "Employees in {region} whose role allows it may work remotely under this policy."),
                   ("Remote Days", "Eligible employees may work remotely up to {wfh} days per week, agreed with their manager."),
                   ("Core Hours", "Regardless of location, everyone must be available between {cfrom} and {cto} local time."),
                   ("Home Office Stipend", "A monthly home-office stipend of {cur} {stipend:,} is paid to eligible employees.")],
         facts=[("How many days per week can employees in {region} work remotely?", "{wfh} days"),
                ("What are the core working hours in {region}?", "{cfrom} to {cto}"),
                ("What is the monthly home-office stipend in {region}?", "{cur} {stipend:,}")]),
    dict(key="security", kind="policy", dept="IT", title="Information Security Standard",
         params=lambda r, c: dict(pwlen=r.choice([10, 12, 14, 16]), rot=r.choice([60, 90, 180]), lock=r.choice([3, 5, 10])),
         sections=[("Passwords", "Passwords must be at least {pwlen} characters long and must be changed every {rot} days."),
                   ("Account Lockout", "Accounts are locked after {lock} consecutive failed sign-in attempts and can be unlocked through the IT service desk."),
                   ("Multi-factor Authentication", "Multi-factor authentication is mandatory for all corporate systems accessed from {region}.")],
         facts=[("What is the minimum password length under the security standard in {region}?", "{pwlen} characters"),
                ("How often must passwords be changed in {region}?", "every {rot} days"),
                ("After how many failed sign-in attempts is an account locked in {region}?", "{lock} attempts")]),
    dict(key="retention", kind="policy", dept="LEG", title="Data Retention Policy",
         params=lambda r, c: dict(contracts=r.choice([5, 7, 10]), finance=r.choice([6, 7, 8, 10]), hr=r.choice([3, 5, 7]), email=r.choice([1, 2, 3])),
         sections=[("Retention Schedule", "Contracts are retained for {contracts} years after expiry. Financial records are retained for {finance} years. HR records are retained for {hr} years after employment ends. Email is retained for {email} years.")],
         facts=[("How many years are contracts retained in {region}?", "{contracts} years"),
                ("How long are financial records kept in {region}?", "{finance} years"),
                ("How long is email retained in {region}?", "{email} years")]),
    dict(key="travel", kind="policy", dept="FIN", title="Business Travel Policy",
         params=lambda r, c: dict(advance=r.choice([7, 14, 21]), hours=r.choice([4, 5, 6, 8]), perdiem=r.choice([30, 40, 50, 60]) * c["fx"]),
         sections=[("Booking", "All travel must be booked at least {advance} days in advance through the approved travel portal."),
                   ("Class of Travel", "Business class may be booked only for flights longer than {hours} hours."),
                   ("Per Diem", "Employees based in {region} receive a per diem of {cur} {perdiem:,} on approved trips.")],
         facts=[("How many days in advance must travel be booked in {region}?", "{advance} days"),
                ("For flights longer than how many hours is business class permitted in {region}?", "{hours} hours"),
                ("What is the travel per diem in {region}?", "{cur} {perdiem:,}")]),
    dict(key="incident", kind="policy", dept="IT", title="Incident Response Procedure",
         params=lambda r, c: dict(sev1=r.choice([5, 10, 15]), sev2=r.choice([15, 30, 60]), pm=r.choice([3, 5, 7])),
         sections=[("Response Targets", "Severity 1 incidents must be acknowledged within {sev1} minutes. Severity 2 incidents must be acknowledged within {sev2} minutes."),
                   ("Post-incident Review", "A written post-mortem must be published within {pm} working days of resolving any Severity 1 incident.")],
         facts=[("Within how many minutes must a Severity 1 incident be acknowledged in {region}?", "{sev1} minutes"),
                ("Within how many minutes must a Severity 2 incident be acknowledged in {region}?", "{sev2} minutes"),
                ("How soon must a post-mortem be published after a Severity 1 incident in {region}?", "{pm} working days")]),
    dict(key="codereview", kind="policy", dept="ENG", title="Code Review and Quality Standard",
         params=lambda r, c: dict(rev=r.choice([1, 2, 3]), cov=r.choice([70, 75, 80, 85, 90]), lines=r.choice([300, 400, 500, 800])),
         sections=[("Reviews", "Every pull request requires approval from at least {rev} reviewer(s) before merging."),
                   ("Quality Gates", "Automated test coverage must remain at or above {cov} percent. Pull requests should not exceed {lines} changed lines.")],
         facts=[("How many reviewers must approve a pull request for the {region} engineering teams?", "{rev}"),
                ("What is the minimum test coverage required by the {region} code review standard?", "{cov} percent"),
                ("What is the recommended maximum pull request size in {region}?", "{lines} lines")]),
    dict(key="procurement", kind="policy", dept="FIN", title="Procurement Policy",
         params=lambda r, c: dict(thr=r.choice([1000, 5000, 10000, 25000]) * c["fx"], quotes=r.choice([2, 3]), legal=r.choice([25000, 50000, 100000]) * c["fx"]),
         sections=[("Competitive Quotes", "Purchases above {cur} {thr:,} require at least {quotes} competitive quotes."),
                   ("Legal Review", "Any contract with a value above {cur} {legal:,} must be reviewed by Legal & Compliance before signature.")],
         facts=[("Above what value are competitive quotes required in {region}?", "{cur} {thr:,}"),
                ("How many quotes are required for larger purchases in {region}?", "{quotes}"),
                ("Above what contract value is legal review needed in {region}?", "{cur} {legal:,}")]),
    dict(key="parental", kind="policy", dept="HR", title="Parental Leave Policy",
         params=lambda r, c: dict(mat=r.choice([12, 16, 20, 26]), pat=r.choice([2, 4, 6, 8])),
         sections=[("Entitlement", "Birth mothers in {region} receive {mat} weeks of fully paid maternity leave. Partners receive {pat} weeks of fully paid paternity leave.")],
         facts=[("How many weeks of paid maternity leave are offered in {region}?", "{mat} weeks"),
                ("How many weeks of paid paternity leave are offered in {region}?", "{pat} weeks")]),
    dict(key="learning", kind="policy", dept="HR", title="Learning and Development Budget Policy",
         params=lambda r, c: dict(bud=r.choice([500, 750, 1000, 1500, 2000]) * c["fx"], hrs=r.choice([20, 30, 40])),
         sections=[("Annual Budget", "Each employee in {region} has an annual learning budget of {cur} {bud:,} and may spend up to {hrs} working hours on learning each quarter.")],
         facts=[("What is the annual learning budget per employee in {region}?", "{cur} {bud:,}"),
                ("How many working hours per quarter can be spent on learning in {region}?", "{hrs} hours")]),
    dict(key="onboarding", kind="policy", dept="HR", title="New Joiner Onboarding Guide",
         params=lambda r, c: dict(laptop=r.choice([1, 2, 3, 5]), buddy=r.choice([4, 6, 8, 12]), prob=r.choice([3, 6])),
         sections=[("First Week", "New joiners in {region} receive their laptop within {laptop} working days of their start date."),
                   ("Support", "Every new joiner is paired with an onboarding buddy for {buddy} weeks."),
                   ("Probation", "The probation period lasts {prob} months.")],
         facts=[("Within how many working days do new joiners in {region} receive a laptop?", "{laptop} working days"),
                ("For how many weeks does an onboarding buddy support a new joiner in {region}?", "{buddy} weeks"),
                ("How long is the probation period in {region}?", "{prob} months")]),
    dict(key="it_faq", kind="faq", dept="IT", title="IT Services FAQ",
         params=lambda r, c: dict(vpn=r.choice(["GlobalConnect", "SecureLink", "PulseVPN", "WireGuard Enterprise"]), ext=r.randint(1000, 9999), refresh=r.choice([3, 4])),
         sections=[("Q: Which VPN client should I use?", "Use {vpn}, available from the self-service software portal."),
                   ("Q: How do I reach the IT helpdesk?", "Dial extension {ext} from any office phone or raise a ticket through the service desk."),
                   ("Q: How often are laptops replaced?", "Laptops are refreshed every {refresh} years.")],
         facts=[("Which VPN client do employees in {region} use?", "{vpn}"),
                ("What is the IT helpdesk extension in {region}?", "{ext}"),
                ("How often are laptops refreshed in {region}?", "every {refresh} years")]),
    dict(key="hr_faq", kind="faq", dept="HR", title="HR Services FAQ",
         params=lambda r, c: dict(payday=r.choice([25, 28, 30]), hols=r.randint(9, 16)),
         sections=[("Q: When are payslips released?", "Payslips are released on day {payday} of each month."),
                   ("Q: How many public holidays are there?", "Employees in {region} get {hols} public holidays per year."),
                   ("Q: Who do I contact for HR questions?", "Email hr-{slug}@" + DOMAIN + " or use the HR portal.")],
         facts=[("On which day of the month are payslips released in {region}?", "day {payday}"),
                ("How many public holidays do employees in {region} get?", "{hols}"),
                ("What email address should I use for HR questions in {region}?", "hr-{slug}@" + DOMAIN)]),
]

GENERIC_TICKETS = [
    ("VPN", "Cannot connect to VPN", "VPN client times out when connecting since this morning.", "Reinstalled the VPN client and reissued the user certificate; connection restored."),
    ("Laptop", "Laptop battery draining fast", "Battery lasts under two hours after the latest update.", "Battery replaced under warranty and device re-imaged."),
    ("Access", "Request access to shared drive", "Need read access to the {dept} shared drive for a new project.", "Access granted after manager approval."),
    ("Software", "Licence for design tool", "Requesting a licence for a design tool for a campaign.", "Licence allocated from the central pool."),
    ("Email", "Mailbox is full", "Mailbox is at quota and cannot send mail.", "Archive enabled and quota raised by 10 GB."),
    ("Payroll", "Payslip not visible", "Last month's payslip is not visible in the portal.", "Payroll republished the payslip; user confirmed it is visible."),
    ("MFA", "Lost phone - need MFA reset", "Phone was lost and I cannot approve sign-in prompts.", "Identity verified via manager; MFA reset and re-enrolled on new device."),
    ("Printer", "Printer offline", "Floor printer shows offline for everyone on the team.", "Print server restarted and queue cleared."),
]
MODELS = {  # illustrative price per 1M tokens (in, out) - NOT real pricing
    "gpt-4o-mini": (0.15, 0.60), "claude-sonnet": (3.00, 15.00), "gemini-flash": (0.10, 0.40),
}
PARAPHRASE = ["Can you tell me: {q}", "Quick question - {ql}", "I need to know. {q}", "{q} Please be specific.", "Hi, {ql}"]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def rand_date(r, a, b):
    return a + timedelta(days=r.randint(0, max(0, (b - a).days)))


def rand_ts(r, a, b):
    d = rand_date(r, a, b)
    return datetime(d.year, d.month, d.day, r.randint(7, 20), r.randint(0, 59), r.randint(0, 59))


def fmt_ts(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def long_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


SCALES = {  # employees, docs, emails, tickets, queries, projects, services, eval
    "small":  dict(employees=200, docs=300, emails=1500, tickets=800, queries=2000, projects=30, services=20, eval_queries=150),
    "medium": dict(employees=1000, docs=1500, emails=8000, tickets=5000, queries=10000, projects=120, services=80, eval_queries=600),
    "large":  dict(employees=5000, docs=8000, emails=60000, tickets=40000, queries=100000, projects=500, services=300, eval_queries=2500),
}


# --------------------------------------------------------------------------
# Generator
# --------------------------------------------------------------------------
class Builder:
    def __init__(self, a):
        self.a = a
        self.r = random.Random(a.seed)
        self.start = date.fromisoformat(a.start_date)
        self.end = date.fromisoformat(a.end_date)
        self.t = {}
        self.emps = []
        self.by_dept = {}
        self.docs = []
        self.projects = []
        self.services = []

    def add_table(self, name, cols, rows):
        self.t[name] = (cols, rows)

    def ctx(self, region):
        i = REGION_INFO[region]
        return dict(company=COMPANY, region=region, cur=i["cur"], fx=i["fx"], slug=i["slug"])

    def pick_emp(self, dept=None, min_level=1, active=True):
        pool = self.by_dept.get(dept, self.emps) if dept else self.emps
        pool = [e for e in pool if e["level"] >= min_level and (not active or e["employment_status"] == "active")]
        return self.r.choice(pool or self.emps)

    # ---------------- people ----------------
    def build_departments_and_employees(self):
        r, n = self.r, self.a.employees
        used = set()
        weights = [w for _, _, w in DEPARTMENTS]
        codes = [c for c, _, _ in DEPARTMENTS]

        def mk(dept, level, mgr, title, hire_from, hire_to):
            region = r.choices(REGIONS, [REGION_INFO[x]["w"] for x in REGIONS])[0]
            fn, ln = r.choice(FIRST), r.choice(LAST)
            base, k = f"{fn}.{ln}".lower(), 1
            em = base
            while em in used:
                k += 1
                em = f"{base}{k}"
            used.add(em)
            hire = rand_date(r, hire_from, hire_to)
            status = "active" if r.random() > 0.06 or level >= 4 else "terminated"
            e = dict(employee_id=len(self.emps) + 1, first_name=fn, last_name=ln, full_name=f"{fn} {ln}",
                     email=f"{em}@{DOMAIN}", department_id=dept, title=title, level=level, manager_id=mgr,
                     location_city=r.choice(REGION_INFO[region]["cities"]), region=region, hire_date=iso(hire),
                     employment_status=status)
            self.emps.append(e)
            self.by_dept.setdefault(dept, []).append(e)
            return e

        old = (date(2012, 1, 1), date(2018, 12, 31))
        ceo = mk("EXE", 6, None, "Chief Executive Officer", *old)
        ceo["employment_status"] = "active"
        heads = {}
        for c in codes[1:]:
            heads[c] = mk(c, 5, ceo["employee_id"], f"Head of {DEPT_NAME[c]}", *old)
            heads[c]["employment_status"] = "active"
        n_mgr = max(len(codes), int(n * 0.10))
        mgrs = {c: [heads[c]] for c in codes[1:]}
        for _ in range(n_mgr):
            c = r.choices(codes[1:], weights[1:])[0]
            m = mk(c, 4, heads[c]["employee_id"], f"Manager, {DEPT_NAME[c]}", date(2014, 1, 1), date(2022, 12, 31))
            mgrs[c].append(m)
        while len(self.emps) < n:
            c = r.choices(codes[1:], weights[1:])[0]
            lvl = r.choices([1, 2, 3], [40, 35, 25])[0]
            mgr = r.choice(mgrs[c][1:] or mgrs[c])
            title = LEVEL_PREFIX[lvl] + r.choice(TITLES[c])
            mk(c, lvl, mgr["employee_id"], title, date(2015, 1, 1), self.end)

        self.add_table("departments", ["department_id", "name", "head_employee_id", "cost_center"],
                       [(c, nm, heads[c]["employee_id"] if c in heads else ceo["employee_id"], f"CC-{1000 + i * 10}")
                        for i, (c, nm, _) in enumerate(DEPARTMENTS)])
        cols = ["employee_id", "first_name", "last_name", "full_name", "email", "department_id", "title", "level",
                "manager_id", "location_city", "region", "hire_date", "employment_status"]
        self.add_table("employees", cols, [tuple(e[c] for c in cols) for e in self.emps])
        self.heads = heads

    # ---------------- projects & services ----------------
    def build_projects(self):
        r = self.r
        rows, members = [], []
        codes = [c for c in DEPT_NAME if c != "EXE"]
        names = CODENAMES[:]
        r.shuffle(names)
        for i in range(self.a.projects):
            base = names[i % len(names)]
            name = f"Project {base}" + (f"-{i // len(names) + 1}" if i >= len(names) else "")
            dept = r.choice(codes)
            owner = self.pick_emp(dept, 3)
            start = rand_date(r, self.start, self.end - timedelta(days=60))
            target = start + timedelta(days=r.randint(90, 540))
            p = dict(project_id=f"PRJ-{i + 1:04d}", name=name, department_id=dept, owner_id=owner["employee_id"],
                     sponsor_id=self.heads[dept]["employee_id"], status=r.choice(["Planning", "In Progress", "In Progress", "On Hold", "Completed"]),
                     start_date=start, target_date=target, budget_usd=r.randrange(50000, 5000000, 5000),
                     priority=r.choice(["P1", "P2", "P3"]))
            self.projects.append(p)
            rows.append((p["project_id"], name, dept, p["owner_id"], p["sponsor_id"], p["status"], iso(start), iso(target), p["budget_usd"], p["priority"]))
            members.append((p["project_id"], owner["employee_id"], "Project Owner"))
            for e in r.sample(self.emps, min(len(self.emps), r.randint(3, 8))):
                if e["employee_id"] != owner["employee_id"]:
                    members.append((p["project_id"], e["employee_id"], r.choice(["Engineer", "Analyst", "Stakeholder", "PM", "QA"])))
        self.add_table("projects", ["project_id", "name", "department_id", "owner_id", "sponsor_id", "status", "start_date", "target_date", "budget_usd", "priority"], rows)
        self.add_table("project_members", ["project_id", "employee_id", "role"], members)

    def build_services(self):
        r = self.r
        combos = [f"{p}-{s}" for p in SVC_PREFIX for s in SVC_SUFFIX]
        r.shuffle(combos)
        rows = []
        for i in range(self.a.services):
            name = combos[i] if i < len(combos) else f"{combos[i % len(combos)]}-{i // len(combos) + 1}"
            owner = self.pick_emp("ENG", 3)
            s = dict(service_id=f"SVC-{i + 1:04d}", name=name, owner=owner, lang=r.choice(LANGS), db=r.choice(DBS),
                     queue=r.choice(QUEUES), tier=r.choice([1, 2, 3]), slo=r.choice([99.5, 99.9, 99.95, 99.99]),
                     p95=r.choice([80, 120, 200, 300, 450, 600, 900]))
            s["repo"] = f"https://git.{DOMAIN}/platform/{name}"
            self.services.append(s)
            rows.append((s["service_id"], name, owner["employee_id"], "ENG", s["lang"], s["db"], s["queue"], s["tier"], s["slo"], s["p95"], s["repo"]))
        self.add_table("services", ["service_id", "name", "owner_employee_id", "owner_department_id", "language", "database", "message_queue", "tier", "availability_slo_pct", "p95_latency_ms", "repo_url"], rows)

    # ---------------- documents ----------------
    def filler_sections(self, dept, region):
        r = self.r
        n = {"short": 1, "medium": 3, "long": 8}[self.a.doc_length]
        heads = r.sample(FILLER_HEADINGS, min(n, len(FILLER_HEADINGS)))
        out = []
        for h in heads:
            sents = r.sample(FILLER, r.randint(3, 5))
            out.append((h, " ".join(s.format(region=region, dept=DEPT_NAME[dept], company=COMPANY) for s in sents)))
        return out

    def compose(self, title, meta, sections, dept, region):
        r = self.r
        secs = list(sections)
        for f in self.filler_sections(dept, region):  # facts end up at random depths
            secs.insert(r.randint(0, len(secs)), f)
        lines = [f"# {title}", ""] + [f"**{k}:** {v}" for k, v in meta.items()] + [""]
        for h, t in secs:
            lines += [f"## {h}", "", t, ""]
        return "\n".join(lines)

    def add_doc(self, title, doc_type, dept, sections, facts, region=None, project_id=None, topic_key=None,
                group_key=None, status="active", created=None, version=None, author=None, extra_meta=None, eval_ok=True):
        r = self.r
        did = f"DOC-{len(self.docs) + 1:06d}"
        created = created or rand_date(r, self.start, self.end)
        updated = min(self.end, created + timedelta(days=r.randint(0, 400)))
        version = version or r.randint(1, 5)
        author = author or self.pick_emp(dept)
        conf = r.choices(["Public", "Internal", "Confidential", "Restricted"],
                         {"policy": [15, 70, 15, 0], "faq": [30, 70, 0, 0], "runbook": [0, 55, 40, 5]}.get(doc_type, [0, 70, 25, 5]))[0]
        system = r.choice({"policy": ["SharePoint", "Confluence"], "faq": ["Confluence", "Notion"], "runbook": ["Confluence", "GitHub Wiki"],
                           "service_wiki": ["Confluence", "GitHub Wiki"], "meeting_notes": ["Google Drive", "Notion", "SharePoint"],
                           "project_brief": ["SharePoint", "Google Drive"]}[doc_type])
        meta = {"Document ID": did, "Owner": author["full_name"], "Department": DEPT_NAME[dept], "Status": status,
                "Version": version, "Last updated": iso(updated)}
        if region:
            meta["Region"] = region
        if extra_meta:
            meta.update(extra_meta)
        body = self.compose(title, meta, sections, dept, region or "all regions")
        d = dict(doc_id=did, title=title, doc_type=doc_type, department_id=dept, author_id=author["employee_id"], region=region,
                 project_id=project_id, source_system=system, url=f"https://{system.lower().replace(' ', '-')}.{DOMAIN}/{doc_type}/{did.lower()}",
                 status=status, version=version, confidentiality=conf, created_at=iso(created), updated_at=iso(updated),
                 word_count=len(body.split()), body=body, topic_key=topic_key, group_key=group_key, facts=facts if eval_ok else [])
        self.docs.append(d)
        return d

    def gen_spec_docs(self, count):
        r = self.r
        combos = [(s, reg) for s in SPECS for reg in REGIONS]
        r.shuffle(combos)
        made = 0
        for spec, region in combos[:count]:
            c = self.ctx(region)
            p = spec["params"](r, c)
            fm = {**c, **p}
            title = f"{spec['title']} - {region}"
            created = rand_date(r, self.start + timedelta(days=400), self.end)
            version = r.randint(2, 5)
            if r.random() < self.a.stale_rate:  # archived predecessor with OUTDATED values
                p2 = p
                for _ in range(8):
                    p2 = spec["params"](r, c)
                    if p2 != p:
                        break
                secs = [(h, t.format(**c, **p2)) for h, t in spec["sections"]]
                self.add_doc(title, spec["kind"], spec["dept"], secs, [], region=region, topic_key=spec["key"], status="archived",
                             created=created - timedelta(days=r.randint(300, 700)), version=version - 1,
                             extra_meta={"Note": "Superseded - do not use"}, eval_ok=False)
            secs = [(h, t.format(**fm)) for h, t in spec["sections"]]
            facts = [(q.format(**fm), a.format(**fm)) for q, a in spec["facts"]]
            self.add_doc(title, spec["kind"], spec["dept"], secs, facts, region=region, topic_key=spec["key"], created=created, version=version)
            made += 1
        return made

    def gen_wiki(self, s):
        r = self.r
        deps = ", ".join(x["name"] for x in r.sample(self.services, min(3, len(self.services))) if x is not s) or "none"
        owner = s["owner"]["full_name"]
        secs = [("Overview", f"{s['name']} is a tier-{s['tier']} backend component of the {COMPANY} platform. Source code lives at {s['repo']}."),
                ("Ownership", f"{s['name']} is owned by {owner} in Engineering."),
                ("Technology Stack", f"{s['name']} is written in {s['lang']}, stores data in {s['db']} and publishes events through {s['queue']}."),
                ("Reliability Targets", f"The availability SLO for {s['name']} is {s['slo']} percent and the p95 latency target is {s['p95']} ms."),
                ("Dependencies", f"{s['name']} depends on: {deps}.")]
        n = s["name"]
        facts = [(f"Who owns the {n} service?", owner), (f"Which database does {n} use?", s["db"]),
                 (f"What is the availability SLO for {n}?", f"{s['slo']} percent"),
                 (f"What is the p95 latency target for {n}?", f"{s['p95']} ms"),
                 (f"Which programming language is {n} written in?", s["lang"])]
        self.add_doc(f"Service Overview: {n}", "service_wiki", "ENG", secs, facts, topic_key="wiki", group_key=f"svc:{n}", author=s["owner"])

    def gen_runbook(self, s, alert):
        r = self.r
        esc, thr = r.choice([5, 10, 15, 30]), r.choice([2, 5, 10, 80, 90])
        n = s["name"]
        cmd = f"kubectl rollout restart deployment/{n}"
        chan = f"#oncall-{n}"
        secs = [("Alert", f"This runbook covers the '{alert}' alert for {n}. Trigger threshold: {thr} (see monitoring dashboard)."),
                ("Triage", f"1. Check the dashboard for {n}. 2. Review recent deployments. 3. Post updates in {chan}."),
                ("Mitigation", f"If the alert persists, restart the service with: {cmd}"),
                ("Escalation", f"If the '{alert}' alert is not resolved within {esc} minutes, page the secondary on-call engineer.")]
        facts = [(f"After how many minutes should the '{alert}' alert for {n} be escalated?", f"{esc} minutes"),
                 (f"Which Slack channel is used for incidents on {n}?", chan),
                 (f"What command is used to restart {n}?", cmd)]
        self.add_doc(f"Runbook: {n} - {alert}", "runbook", "ENG", secs, facts, topic_key=f"runbook:{alert}", group_key=f"svc:{n}", author=s["owner"])

    def gen_project_brief(self, p):
        r = self.r
        owner = next(e for e in self.emps if e["employee_id"] == p["owner_id"])["full_name"]
        sponsor = next(e for e in self.emps if e["employee_id"] == p["sponsor_id"])["full_name"]
        n = p["name"]
        secs = [("Goal", f"{n} aims to improve efficiency in {DEPT_NAME[p['department_id']]} and reduce operating cost."),
                ("Timeline", f"The project starts on {long_date(p['start_date'])} and the target launch date is {long_date(p['target_date'])}."),
                ("Budget", f"The approved budget for {n} is USD {p['budget_usd']:,}."),
                ("Stakeholders", f"The project owner is {owner}. The executive sponsor is {sponsor}."),
                ("Risks", "Key risks include resourcing constraints, vendor delays and changing requirements.")]
        facts = [(f"What is the approved budget for {n}?", f"USD {p['budget_usd']:,}"),
                 (f"What is the target launch date for {n}?", long_date(p["target_date"])),
                 (f"Who is the owner of {n}?", owner), (f"Who is the executive sponsor of {n}?", sponsor)]
        self.add_doc(f"Project Brief: {n}", "project_brief", p["department_id"], secs, facts, project_id=p["project_id"], group_key=f"prj:{p['project_id']}",
                     topic_key="project_brief", created=p["start_date"])

    def gen_meeting(self, p):
        r = self.r
        end = min(p["target_date"], self.end)
        d = rand_date(r, p["start_date"], max(p["start_date"], end))
        n, ds = p["name"], long_date(d)
        att = [e["full_name"] for e in r.sample(self.emps, 4)]
        decisions, facts = [], []
        kinds = r.sample(["launch", "budget", "action"], 2)
        if "launch" in kinds:
            nd = p["target_date"] + timedelta(days=r.randint(14, 90))
            decisions.append(f"The team agreed to move the launch date to {long_date(nd)}.")
            facts.append((f"What new launch date was agreed for {n} in the steering sync on {ds}?", long_date(nd)))
        if "budget" in kinds:
            amt = r.choice([25000, 50000, 75000, 100000, 150000])
            decisions.append(f"The sponsor approved an additional budget of USD {amt:,}.")
            facts.append((f"How much additional budget was approved for {n} in the steering sync on {ds}?", f"USD {amt:,}"))
        if "action" in kinds:
            who, dl = r.choice(att), r.choice(DELIVERABLES)
            due = d + timedelta(days=r.randint(7, 45))
            decisions.append(f"{who} will deliver the {dl} by {long_date(due)}.")
            facts.append((f"Who is responsible for the {dl} for {n} according to the steering sync on {ds}?", who))
        secs = [("Attendees", ", ".join(att)), ("Discussion", f"The group reviewed progress on {n}, open risks and upcoming milestones."),
                ("Decisions", " ".join(decisions))]
        self.add_doc(f"Meeting Notes: {n} - Steering Sync {ds}", "meeting_notes", p["department_id"], secs, facts, project_id=p["project_id"],
                     group_key=f"prj:{p['project_id']}", topic_key=None, created=d)

    def build_documents(self):
        r, total = self.r, self.a.docs
        n_spec = min(int(total * 0.25), len(SPECS) * len(REGIONS))
        self.gen_spec_docs(n_spec)
        for s in self.services[: max(0, min(len(self.services), int(total * 0.20)))]:
            self.gen_wiki(s)
        runbook_target = int(total * 0.15)
        pairs = [(s, a) for s in self.services for a in ALERTS]
        r.shuffle(pairs)
        for s, a in pairs[:runbook_target]:
            self.gen_runbook(s, a)
        for p in self.projects[: max(0, min(len(self.projects), int(total * 0.10)))]:
            self.gen_project_brief(p)
        while len(self.docs) < total and self.projects:
            self.gen_meeting(r.choice(self.projects))

        # aux tables
        cols = ["doc_id", "title", "doc_type", "department_id", "author_id", "region", "project_id", "source_system", "url", "status",
                "version", "confidentiality", "created_at", "updated_at", "word_count", "body"]
        self.add_table("documents", cols, [tuple(d[c] for c in cols) for d in self.docs])
        vers, acl = [], []
        for d in self.docs:
            c0 = date.fromisoformat(d["created_at"])
            for v in range(1, d["version"] + 1):
                when = c0 + timedelta(days=int((v - 1) * 60 * r.uniform(0.5, 1.5)))
                vers.append((d["doc_id"], v, self.pick_emp(d["department_id"])["employee_id"], iso(min(when, self.end)),
                             "Initial version" if v == 1 else r.choice(["Updated values", "Clarified wording", "Added new section", "Annual review", "Fixed typos"])))
            if d["confidentiality"] in ("Public", "Internal"):
                acl.append((d["doc_id"], "ALL", "*"))
            elif d["confidentiality"] == "Confidential":
                acl += [(d["doc_id"], "DEPARTMENT", d["department_id"]), (d["doc_id"], "DEPARTMENT", "LEG")]
            else:
                acl.append((d["doc_id"], "DEPARTMENT", d["department_id"]))
        self.add_table("document_versions", ["doc_id", "version", "changed_by", "changed_at", "change_summary"], vers)
        self.add_table("document_acl", ["doc_id", "principal_type", "principal_id"], acl)

    # ---------------- emails / tickets ----------------
    def build_emails(self):
        r, rows, k, m = self.r, [], 0, 0
        pool = [d for d in self.docs if d["facts"]]
        subjects = ["Question about {t}", "Clarification on {t}", "Quick check: {t}", "Need help with {t}"]
        while len(rows) < self.a.emails and pool:
            k += 1
            tid = f"THR-{k:06d}"
            doc = r.choice(pool)
            t0 = rand_ts(r, max(self.start, date.fromisoformat(doc["created_at"])), self.end)
            if r.random() < 0.25:  # announcement
                sender = next(e for e in self.emps if e["employee_id"] == doc["author_id"])
                to = [e["employee_id"] for e in r.sample(self.emps, 5)]
                m += 1
                rows.append((f"MSG-{m:07d}", tid, sender["employee_id"], ";".join(map(str, to)), "", f"FYI: {doc['title']} updated",
                             f"Hi all,\n\nWe have published version {doc['version']} of '{doc['title']}'. Please review: {doc['url']}\n\nThanks,\n{sender['first_name']}",
                             fmt_ts(t0), doc["doc_id"], 0, None))
                continue
            q, a = r.choice(doc["facts"])
            asker, resp = self.pick_emp(), self.pick_emp(doc["department_id"], 2)
            subj = r.choice(subjects).format(t=doc["title"])
            msgs = [(asker, resp, subj, f"Hi {resp['first_name']},\n\n{q}\n\nThanks,\n{asker['first_name']}"),
                    (resp, asker, "Re: " + subj, f"Hi {asker['first_name']},\n\nPer '{doc['title']}' ({doc['url']}): {a}.\n\nRegards,\n{resp['first_name']}"),
                    (asker, resp, "Re: " + subj, "Thanks, that helps!")][: r.randint(1, 3)]
            prev, t = None, t0
            for s_, to_, sj, body in msgs:
                m += 1
                mid = f"MSG-{m:07d}"
                t += timedelta(minutes=r.randint(5, 600))
                rows.append((mid, tid, s_["employee_id"], str(to_["employee_id"]), str(s_["manager_id"] or "") if r.random() < 0.2 else "",
                             sj, body, fmt_ts(t), doc["doc_id"], int(r.random() < 0.1), prev))
                prev = mid
        self.add_table("emails", ["message_id", "thread_id", "sender_id", "to_ids", "cc_ids", "subject", "body", "sent_at", "related_doc_id", "has_attachment", "in_reply_to"], rows[: self.a.emails])

    def build_tickets(self):
        r, rows = self.r, []
        pool = [d for d in self.docs if d["facts"]]
        cat = {"HR": "HR Query", "FIN": "Finance Query", "IT": "IT Query"}
        for i in range(self.a.tickets):
            req = self.pick_emp()
            asg = self.pick_emp("IT")
            created = rand_ts(r, self.start, self.end)
            hrs = r.lognormvariate(math.log(8), 1.0)
            resolved = created + timedelta(hours=hrs)
            status = "Resolved" if r.random() < 0.9 and resolved < datetime.combine(self.end, datetime.min.time()) else r.choice(["Open", "In Progress"])
            doc_id = None
            if pool and r.random() < 0.6:
                doc = r.choice(pool)
                q, a = r.choice(doc["facts"])
                category, subject, desc = cat.get(doc["department_id"], "General Query"), "Question: " + q[:70], q
                res, doc_id = f"Answered using '{doc['title']}' ({doc['url']}). The answer is: {a}.", doc["doc_id"]
            else:
                category, subject, desc, res = r.choice(GENERIC_TICKETS)
                desc = desc.format(dept=DEPT_NAME[req["department_id"]])
            done = status == "Resolved"
            rows.append((f"TKT-{i + 1:07d}", category, r.choices(["Low", "Medium", "High", "Critical"], [40, 40, 15, 5])[0], status,
                         req["employee_id"], asg["employee_id"], fmt_ts(created), fmt_ts(resolved) if done else None,
                         int(r.lognormvariate(math.log(30), 0.8)), subject, desc, res if done else None, doc_id,
                         r.choice([3, 4, 4, 5, 5, 2, 1]) if done and r.random() < 0.5 else None))
        self.add_table("tickets", ["ticket_id", "category", "priority", "status", "requester_id", "assignee_id", "created_at", "resolved_at",
                                   "first_response_minutes", "subject", "description", "resolution", "related_doc_id", "csat"], rows)

    # ---------------- evaluation set + usage log ----------------
    def build_eval_and_logs(self):
        r = self.r
        cands = [(d, f) for d in self.docs if d["status"] == "active" for f in d["facts"]]
        r.shuffle(cands)
        cands = cands[: self.a.eval_queries]
        by_group, by_topic = {}, {}
        for d in self.docs:
            if d["group_key"]:
                by_group.setdefault(d["group_key"], []).append(d)
            if d["topic_key"]:
                by_topic.setdefault(d["topic_key"], []).append(d)
        evq, qrels = [], []
        for i, (d, (q, a)) in enumerate(cands):
            qid = f"Q-{i + 1:05d}"
            if r.random() < 0.5:
                text, diff = q, "easy"
            else:
                text, diff = r.choice(PARAPHRASE).format(q=q, ql=q[0].lower() + q[1:]), "medium"
            peers = [x for x in by_group.get(d["group_key"], []) if x["doc_id"] != d["doc_id"] and x["status"] == "active"] if d["group_key"] else []
            peers = r.sample(peers, min(5, len(peers)))
            peer_ids = {x["doc_id"] for x in peers}
            negs = [x for x in by_topic.get(d["topic_key"], []) if x["doc_id"] != d["doc_id"] and (not d["group_key"] or x["group_key"] != d["group_key"])] if d["topic_key"] else []
            negs = r.sample(negs, min(5, len(negs)))
            evq.append((qid, text, a, d["doc_id"], d["doc_type"], diff, d["region"], ";".join(x["doc_id"] for x in negs)))
            qrels.append((qid, d["doc_id"], 2))
            qrels += [(qid, pid, 1) for pid in sorted(peer_ids)]
            qrels += [(qid, x["doc_id"], 0) for x in negs]
        self.add_table("eval_queries", ["query_id", "question", "expected_answer", "source_doc_id", "doc_type", "difficulty", "region", "hard_negative_doc_ids"], evq)
        self.add_table("eval_qrels", ["query_id", "doc_id", "relevance"], qrels)

        # usage / monitoring log
        rows, models = [], list(MODELS)
        sessions = {}
        active_docs = [d for d in self.docs if d["status"] == "active"]
        for i in range(self.a.queries):
            emp = self.pick_emp()
            ts = rand_ts(r, self.start + timedelta(days=(self.end - self.start).days // 2), self.end)
            linked = r.choice(evq) if evq and r.random() < 0.7 else None
            text = linked[1] if linked else f"How do I {r.choice(['request', 'renew', 'cancel', 'escalate', 'update'])} {r.choice(['access', 'a laptop', 'a licence', 'my benefits', 'a vendor contract'])}?"
            model = r.choices(models, [50, 25, 25])[0]
            ptok, ctok = int(r.lognormvariate(math.log(1800), 0.4)), int(r.lognormvariate(math.log(250), 0.5))
            pin, pout = MODELS[model]
            hit = None
            top = r.choice(active_docs)["doc_id"]
            if linked:
                hit = int(r.random() < 0.82)
                top = linked[3] if hit else top
            err = r.random() < 0.02
            sess = sessions.setdefault((emp["employee_id"], ts.date()), f"S-{len(sessions) + 1:07d}")
            rows.append((f"QL-{i + 1:07d}", sess, emp["employee_id"], fmt_ts(ts), text, linked[0] if linked else None, model,
                         int(r.lognormvariate(math.log(2200), 0.5)), ptok, ctok, round((ptok * pin + ctok * pout) / 1e6, 6), top, hit,
                         r.choices(["up", "down", None], [30, 10, 60])[0] if not err else "down", int(err)))
        self.add_table("query_log", ["log_id", "session_id", "employee_id", "asked_at", "query_text", "eval_query_id", "model", "latency_ms",
                                     "prompt_tokens", "completion_tokens", "cost_usd", "top1_doc_id", "top1_correct", "feedback", "error"], rows)

    def build_all(self):
        self.build_departments_and_employees()
        self.build_projects()
        self.build_services()
        self.build_documents()
        self.build_emails()
        self.build_tickets()
        self.build_eval_and_logs()


def iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else d


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------
def write_csv(out, name, cols, rows):
    with open(os.path.join(out, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(cols)
        for row in rows:
            w.writerow(["" if v is None else v for v in row])


def write_parquet(out, name, cols, rows):
    try:
        import pandas as pd
        pd.DataFrame(rows, columns=cols).to_parquet(os.path.join(out, f"{name}.parquet"), index=False)
    except Exception as e:  # pandas/pyarrow missing
        print(f"  [skip parquet for {name}: install pyarrow]" if "pyarrow" in str(e) else f"  [skip parquet for {name}: {e}]")


def write_sqlite(out, tables):
    path = os.path.join(out, "enterprise.db")
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    for name, (cols, rows) in tables.items():
        types = []
        for i, c in enumerate(cols):
            v = next((row[i] for row in rows if row[i] is not None), "")
            types.append("INTEGER" if isinstance(v, int) else "REAL" if isinstance(v, float) else "TEXT")
        con.execute(f"CREATE TABLE {name} ({', '.join(f'{c} {t}' for c, t in zip(cols, types))})")
        con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(cols))})", rows)
    con.commit()
    con.close()


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def sf_type(rows, i):
    v = next((row[i] for row in rows if row[i] is not None), "")
    if isinstance(v, int):
        return "INTEGER"
    if isinstance(v, float):
        return "FLOAT"
    return "TIMESTAMP" if TS_RE.match(v) else "DATE" if DATE_RE.match(v) else "VARCHAR"


def write_snowflake_scripts(out, tables):
    path = os.path.abspath(out).replace("\\", "/")
    ddl = ["-- Generated by gen_enterprise_data.py (types inferred from the data)", ""]
    for name, (cols, rows) in tables.items():
        ddl.append(f"CREATE TABLE IF NOT EXISTS {name} (\n" + ",\n".join(f"    {c} {sf_type(rows, i)}" for i, c in enumerate(cols)) + "\n);\n")
    with open(os.path.join(out, "schema.sql"), "w") as f:
        f.write("\n".join(ddl))
    L = ["-- Snowflake load script generated by gen_enterprise_data.py",
         "-- Run order: (1) this context block  (2) schema.sql  (3) the rest of this file.",
         "-- PUT only works from SnowSQL / Snowflake CLI / a connector, not from Snowsight worksheets.", "",
         "CREATE DATABASE IF NOT EXISTS ENTERPRISE_KB;", "CREATE SCHEMA IF NOT EXISTS ENTERPRISE_KB.RAW;", "USE SCHEMA ENTERPRISE_KB.RAW;", "",
         "-- Document bodies contain newlines and quotes, so quoted-field handling is required.",
         "CREATE OR REPLACE FILE FORMAT ent_csv",
         "  TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' EMPTY_FIELD_AS_NULL = TRUE",
         "  DATE_FORMAT = 'YYYY-MM-DD' TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS' ENCODING = 'UTF8';",
         "CREATE OR REPLACE STAGE ent_stage FILE_FORMAT = ent_csv;", "",
         f"PUT 'file://{path}/*.csv' @ent_stage AUTO_COMPRESS = TRUE OVERWRITE = TRUE;", ""]
    for name in tables:
        L.append(f"COPY INTO {name} FROM @ent_stage/{name}.csv.gz ON_ERROR = ABORT_STATEMENT;")
    L += ["", "-- Self-check: loaded vs expected row counts",
          "\nUNION ALL\n".join(f"SELECT '{n}' AS tbl, (SELECT COUNT(*) FROM {n}) AS loaded, {len(r)} AS expected" for n, (_, r) in tables.items()) + ";"]
    with open(os.path.join(out, "load_snowflake.sql"), "w") as f:
        f.write("\n".join(L) + "\n")


def write_document_files(out, docs, pdf_fraction, rng):
    pdf_ok = False
    if pdf_fraction > 0:
        try:
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            pdf_ok, styles = True, getSampleStyleSheet()
        except ImportError:
            print("  [reportlab not installed - skipping PDF output: pip install reportlab]")
    npdf = 0
    for d in docs:
        folder = os.path.join(out, "documents", d["doc_type"])
        os.makedirs(folder, exist_ok=True)
        if pdf_ok and rng.random() < pdf_fraction:
            story = []
            for line in d["body"].split("\n"):
                if line.startswith("# "):
                    story.append(Paragraph(line[2:], styles["Title"]))
                elif line.startswith("## "):
                    story.append(Paragraph(line[3:], styles["Heading2"]))
                elif line.strip():
                    story.append(Paragraph(line.replace("**", "").replace("&", "&amp;").replace("<", "&lt;"), styles["BodyText"]))
                story.append(Spacer(1, 4))
            SimpleDocTemplate(os.path.join(folder, d["doc_id"] + ".pdf")).build(story)
            npdf += 1
        else:
            with open(os.path.join(folder, d["doc_id"] + ".md"), "w", encoding="utf-8") as f:
                f.write(d["body"])
    return npdf


# --------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Generate related synthetic enterprise data for RAG testing.",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--scale", choices=SCALES, default="small", help="preset sizes; individual flags override it")
    for k in ["employees", "docs", "emails", "tickets", "queries", "projects", "services", "eval_queries"]:
        p.add_argument(f"--{k.replace('_', '-')}", type=int, default=None)
    p.add_argument("--doc-length", choices=["short", "medium", "long"], default="medium", help="amount of filler text per document")
    p.add_argument("--stale-rate", type=float, default=0.3, help="share of policies that also get an archived, outdated version")
    p.add_argument("--start-date", default="2023-01-01")
    p.add_argument("--end-date", default="2026-09-30")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="enterprise_data")
    p.add_argument("--formats", default="csv,sqlite", help="comma list of: csv,jsonl,parquet,sqlite")
    p.add_argument("--no-doc-files", action="store_true", help="do not write one file per document")
    p.add_argument("--pdf-fraction", type=float, default=0.0, help="fraction of document files written as PDF (needs reportlab)")
    a = p.parse_args()
    for k, v in SCALES[a.scale].items():
        if getattr(a, k) is None:
            setattr(a, k, v)
    if a.employees < 30:
        p.error("--employees must be >= 30")
    return a


def main():
    a = parse_args()
    os.makedirs(a.out, exist_ok=True)
    b = Builder(a)
    b.build_all()
    fmts = {f.strip() for f in a.formats.split(",")}
    for name, (cols, rows) in b.t.items():
        if "csv" in fmts:
            write_csv(a.out, name, cols, rows)
        if "parquet" in fmts:
            write_parquet(a.out, name, cols, rows)
        if "jsonl" in fmts:
            with open(os.path.join(a.out, f"{name}.jsonl"), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(dict(zip(cols, row)), ensure_ascii=False, default=str) + "\n")
    if "sqlite" in fmts:
        write_sqlite(a.out, b.t)
    write_snowflake_scripts(a.out, b.t)
    npdf = 0
    if not a.no_doc_files:
        npdf = write_document_files(a.out, b.docs, a.pdf_fraction, random.Random(a.seed))
    manifest = {"args": vars(a), "row_counts": {k: len(v[1]) for k, v in b.t.items()}, "pdf_files": npdf}
    with open(os.path.join(a.out, "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote dataset to {a.out}")
    for k, n in manifest["row_counts"].items():
        print(f"  {k:<20}{n:>9,}")
    words = sum(d["word_count"] for d in b.docs)
    print(f"  (documents total ~{words:,} words)")


if __name__ == "__main__":
    sys.exit(main())
