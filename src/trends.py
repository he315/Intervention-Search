"""Trend corpus (CLAUDE.md 8.2): monthly PubMed counts per domain and design.

Counts use the entrez date. Publication-type indexing lags by weeks to
months, so RCT, meta-analysis and guideline counts for the most recent
months are provisional and are re-counted at each monthly maintenance.
"""
import csv
from datetime import date

from . import config
from .sources import pubmed

PATH = config.TRENDS / "monthly_counts.csv"
FIELDS = ["month", "domain", "design", "count", "counted_on"]
DESIGN_FILTERS = {
    "all": None,
    "rct": '"Randomized Controlled Trial"[pt]',
    "ma": '("Meta-Analysis"[pt] OR "Systematic Review"[pt])',
    "guideline": '("Practice Guideline"[pt] OR "Guideline"[pt] OR "Consensus Statement"[pt])',
    "observational": '("Observational Study"[pt] OR "registry"[tiab] OR "cohort"[tiab])',
}


def months(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def month_bounds(y, m):
    first = date(y, m, 1)
    nxt = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return first, date.fromordinal(nxt.toordinal() - 1)


def load():
    if not PATH.exists():
        return {}
    with open(PATH, newline="", encoding="utf-8") as fh:
        return {(r["month"], r["domain"], r["design"]): r for r in csv.DictReader(fh)}


def save(rows):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (r["month"], r["domain"], r["design"]))
    tmp = PATH.with_name(".tmp_" + PATH.name)
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ordered)
    tmp.replace(PATH)


def update(start=date(2016, 1, 1), end=None, recount_recent_months=0, domains=None, deadline=None, now=None):
    """Fill missing cells; re-count the most recent months. Stops at `deadline` (monotonic seconds)."""
    import time
    end = end or config.london_today()
    rows = load()
    q = config.queries()
    today = config.iso_date(config.london_today())
    recent = set()
    if recount_recent_months:
        ms = list(months(start, end))[-recount_recent_months:]
        recent = {f"{y:04d}-{m:02d}" for y, m in ms}
    done = 0
    for y, m in months(start, end):
        key_m = f"{y:04d}-{m:02d}"
        lo, hi = month_bounds(y, m)
        for d in (domains or config.DOMAINS):
            for design, flt in DESIGN_FILTERS.items():
                k = (key_m, d, design)
                if k in rows and key_m not in recent:
                    continue
                if deadline and time.monotonic() > deadline:
                    save(rows)
                    return {"complete": False, "counted": done}
                term = q[d] if not flt else f"({q[d]}) AND {flt}"
                n, _ = pubmed.count(term, lo, hi)
                rows[k] = {"month": key_m, "domain": d, "design": design, "count": n, "counted_on": today}
                done += 1
                if done % 50 == 0:
                    save(rows)
    save(rows)
    return {"complete": True, "counted": done}


def series(domain, design="all"):
    rows = load()
    return sorted(((r["month"], int(r["count"])) for r in rows.values()
                   if r["domain"] == domain and r["design"] == design), key=lambda x: x[0])
