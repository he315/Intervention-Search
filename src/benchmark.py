"""Citation benchmark (CLAUDE.md section 8.5).

Selects in-scope research articles published 2019 to 2023 in the four target-tier
journals plus NEJM, Lancet and JAMA, pulls citation counts (OpenAlex, falling
back to Europe PMC), tabulates by design, data source, sample-size band and
domain, and identifies the archetypes in each journal's top citation decile.
Counts are stored in data/citations/benchmark_YYYY-MM-DD.json.
"""
import json
import re
from collections import defaultdict, Counter
from datetime import date

from . import config, store
from .sources import openalex

JOURNALS = {
    "European heart journal": "European Heart Journal",
    "Circulation": "Circulation",
    "Journal of the American College of Cardiology": "JACC",
    "JAMA cardiology": "JAMA Cardiology",
    "The New England journal of medicine": "NEJM",
    "Lancet (London, England)": "Lancet",
    "JAMA": "JAMA",
}
RESEARCH = {"rct", "rct_secondary", "ipd_ma", "ma", "nma", "sr_no_ma", "trial_emulation",
            "registry_or_cohort", "case_control", "decision_model"}
YEARS = {"2019", "2020", "2021", "2022", "2023"}


def data_source(r):
    d = r.get("design")
    text = ((r.get("title") or "") + " " + (r.get("abstract") or "")).lower()
    if d == "ipd_ma":
        return "IPD"
    if d in ("ma", "nma", "sr_no_ma"):
        return "pooled trials or studies"
    if d in ("rct", "rct_secondary"):
        return "single trial"
    if "uk biobank" in text or "biobank" in text:
        return "biobank"
    if re.search(r"medicare|claims|administrative (data|database)|insurance database|national inpatient sample|medicaid", text):
        return "claims or administrative"
    if d == "decision_model":
        return "model"
    return "registry or cohort"


def size_band(r):
    text = r.get("abstract") or ""
    nums = []
    for m in re.finditer(r"(\d{1,3}(?:[,\s]\d{3})+|\d+)\s+(?:patients|participants|individuals|adults|subjects|women|men|people|studies|trials)", text):
        try:
            nums.append(int(re.sub(r"[,\s]", "", m.group(1))))
        except ValueError:
            pass
    if not nums:
        return "not stated"
    n = max(nums)
    if r.get("design") in ("ma", "nma", "ipd_ma", "sr_no_ma"):
        pass
    return "<500" if n < 500 else "500-1999" if n < 2000 else "2000-9999" if n < 10000 else ">=10000"


def select():
    out = []
    for r in store.iter_records():
        if r.get("journal") not in JOURNALS or r.get("is_preprint") or not r.get("domains"):
            continue
        y = ((r.get("dates") or {}).get("published") or (r.get("dates") or {}).get("epub") or "")[:4]
        if y in YEARS and r.get("design") in RESEARCH:
            out.append(r)
    return out


def run():
    recs = select()
    counts, source = openalex.citation_counts(recs)
    rows = []
    for r in recs:
        c = counts.get(r["id"])
        if c is None and r.get("pmid"):
            c = counts.get(r["pmid"])
        if c is None:
            continue
        rows.append({"id": r["id"], "journal": JOURNALS[r["journal"]], "design": r["design"],
                     "source": data_source(r), "band": size_band(r), "domains": r.get("domains") or [],
                     "year": ((r.get("dates") or {}).get("published") or "")[:4], "citations": c,
                     "title": r.get("title")})
    today = date.today().isoformat()
    p = config.ROOT / "data" / "citations"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"benchmark_{today}.json").write_text(json.dumps({"date": today, "source": source, "n_selected": len(recs), "rows": rows}))
    write_report(rows, source, len(recs), today)
    return {"selected": len(recs), "with_counts": len(rows), "source": source}


def _median(v):
    v = sorted(v)
    n = len(v)
    return 0 if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def _table(rows, key, head):
    g = defaultdict(list)
    for r in rows:
        keys = r[key] if isinstance(r[key], list) else [r[key]]
        for k in keys:
            g[k].append(r["citations"])
    lines = [f"| {head} | Articles | Median citations | Mean | Share in journal top decile |", "|---|---|---|---|---|"]
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {k} | {len(v)} | {_median(v):.0f} | {sum(v)/len(v):.1f} | {{share_{k}}} |")
    return lines, g


def write_report(rows, source, n_sel, today):
    by_j = defaultdict(list)
    for r in rows:
        by_j[r["journal"]].append(r)
    thresh = {}
    for j, v in by_j.items():
        s = sorted(x["citations"] for x in v)
        thresh[j] = s[int(len(s) * 0.9)] if len(s) >= 10 else None
    for r in rows:
        t = thresh[r["journal"]]
        r["top"] = t is not None and r["citations"] >= t and r["citations"] > 0
    L = ["# Citation benchmark", "",
         f"Retrieved {today}. Citation counts from {'OpenAlex (Europe PMC for records OpenAlex lacked)' if source == 'openalex' else 'Europe PMC citedByCount, because OpenAlex was unavailable without a key'}. "
         f"Scope: {n_sel} in-scope research articles (designs rct, rct_secondary, ipd_ma, ma, nma, sr_no_ma, trial_emulation, registry_or_cohort, case_control, decision_model) "
         f"published 2019 to 2023 in European Heart Journal, Circulation, JACC, JAMA Cardiology, NEJM, Lancet and JAMA that are held in the store; {len(rows)} have a citation count. "
         "Records are those the domain queries retrieved, so the table describes in-scope output and not each journal's whole content. "
         "Counts accrue with age, so 2023 articles are under-counted against 2019 articles; the top decile is therefore computed within journal across all five years, which favours older articles. "
         "The benchmark calibrates the citation-potential score and does not replace judgement.", ""]
    L += ["## Journals", "", "| Journal | Articles | Median citations | Top-decile threshold |", "|---|---|---|---|"]
    for j, v in sorted(by_j.items(), key=lambda kv: -len(kv[1])):
        L.append(f"| {j} | {len(v)} | {_median([x['citations'] for x in v]):.0f} | {thresh[j] if thresh[j] is not None else 'too few'} |")
    L.append("")
    tops = [r for r in rows if r["top"]]
    for key, head in (("design", "Design"), ("source", "Data source"), ("band", "Sample-size band"), ("domains", "Domain")):
        t, g = _table(rows, key, head)
        ntop = Counter()
        for r in tops:
            for k in (r[key] if isinstance(r[key], list) else [r[key]]):
                ntop[k] += 1
        t = [ln.replace("{share_%s}" % k, f"{100*ntop[k]/len(v):.0f}%") if "{share_%s}" % k in ln else ln for ln in t for k, v in g.items() if ("| %s |" % k) in ln][:0] or t
        for k, v in g.items():
            t = [ln.replace("{share_%s}" % k, f"{100*ntop[k]/len(v):.0f}%") for ln in t]
        L += [f"## By {head.lower()}", ""] + t + [""]
    L += ["## Archetypes in each journal's top decile", ""]
    for j, v in sorted(by_j.items(), key=lambda kv: -len(kv[1])):
        top = [r for r in v if r["top"]]
        if not top:
            continue
        c = Counter((r["design"], r["source"]) for r in top)
        desc = "; ".join(f"{d} from {s} ({n})" for (d, s), n in c.most_common(4))
        L.append(f"- {j}: {len(top)} articles at or above {thresh[j]} citations. Most frequent archetypes: {desc}.")
    L += ["", "## Ten most cited articles in the selection", "", "| PMID or ID | Journal | Year | Design | Citations |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["citations"])[:10]:
        L.append(f"| {r['id']} | {r['journal']} | {r['year']} | {r['design']} | {r['citations']} |")
    out = config.ROOT / "outputs" / "landscape" / "citation_benchmark.md"
    out.write_text("\n".join(L) + "\n")
