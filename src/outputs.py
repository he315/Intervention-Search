"""Rendering of the daily digest, records CSV, weekly and monthly reports,
the calendar and the README dashboard (CLAUDE.md section 11)."""
import csv
import io
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import config, store, register, trials, state as st, appraise, trends

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]


def prose_date(d):
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    return f"{d.day} {MONTH_NAMES[d.month - 1]} {d.year}"


def first_author(r):
    a = (r.get("authors") or [""])[0]
    return a.split(" ")[0] if a else "Anonymous"


def cite(r):
    parts = [f"{first_author(r)} et al.", r.get("journal") or "", prose_date((r.get("dates") or {}).get("epub") or
             (r.get("dates") or {}).get("published") or (r.get("dates") or {}).get("entrez") or "")]
    ids = []
    if r.get("pmid"):
        ids.append(f"PMID {r['pmid']}")
    if r.get("doi"):
        ids.append(f"DOI {r['doi']}")
    s = ", ".join(p for p in parts if p) + ("; " + "; ".join(ids) if ids else "")
    if r.get("is_preprint"):
        s += " (preprint, not peer reviewed)"
    return s


def link(r):
    if r.get("pmid"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/"
    if r.get("doi"):
        return f"https://doi.org/{r['doi']}"
    return ""


def _clean(s):
    return (s or "").replace("—", ", ").replace("–", "-").replace("|", "/").strip()


# ---- daily ---------------------------------------------------------------------------
def digest(run, records, index, questions, today):
    tier_a = [r for r in records if r.get("tier") == "A"]
    tier_b = [r for r in records if r.get("tier") == "B"]
    backlog = len(appraise.load_backlog())
    health = run.get("health", {})
    status = run.get("status", "OK")
    lines = [f"# Daily digest, {prose_date(today)}", ""]
    srcs = ", ".join(f"{k} {'ok' if v == 'ok' else 'FAILED'}" for k, v in health.items())
    lines += [f"Status: {status}{(' (' + run.get('status_reason') + ')') if run.get('status_reason') else ''}. "
              f"Sources: {srcs}. New records: {len(records)}. Tier A: {len(tier_a)}. Tier B: {len(tier_b)}. "
              f"Backlog awaiting appraisal: {backlog}.", ""]
    alerts = []
    for k, v in health.items():
        if v != "ok":
            alerts.append(f"Source failure: {k} ({_clean(v)[:160]}). Its watermark was not advanced and the next run re-fetches the window.")
    for a in run.get("correction_alerts", []):
        alerts.append(f"Correction notice affecting a tracked record: PMID {a['pmid']} ({_clean(a.get('title'))[:120]}) flagged "
                      f"{', '.join(a['flags'])}; tier {a.get('tier') or 'unassigned'}; questions {', '.join(a.get('questions') or []) or 'none'}.")
    for r in records:
        for v in r.get("register_verdicts") or []:
            if v.get("verdict") and v["verdict"] != "unaffected":
                alerts.append(f"Register alert for {v['qid']}: PMID {r.get('pmid') or r['id']} is judged {v['verdict']}. {_clean(v.get('note'))}")
    for w in run.get("warnings", []):
        alerts.append(_clean(w))
    if len(tier_a) > 10:
        alerts.append(f"Calibration warning: {len(tier_a)} Tier A records today; the assignments were re-checked before this digest was written.")
    lines += ["## Alerts", ""] + ([f"- {a}" for a in alerts] if alerts else ["None."]) + [""]
    lines += ["## Tier A", ""]
    if not tier_a:
        lines += ["No Tier A records today.", ""]
    for r in tier_a:
        ap = r.get("appraisal") or {}
        lines += [f"### {_clean(r.get('title'))}", "", cite(r), "",
                  f"Design and size: {_clean(ap.get('design_and_n'))}", "",
                  f"Primary result as reported: {_clean(ap.get('primary_result_as_reported'))}", "",
                  f"Why it matters: {_clean(ap.get('why_it_matters'))}", "",
                  f"Main limitation: {_clean(ap.get('main_limitation'))}", "",
                  f"Linked questions: {', '.join(r.get('question_ids') or []) or 'none'}", ""]
    lines += ["## Tier B", ""]
    if not tier_b:
        lines += ["No Tier B records today.", ""]
    for r in tier_b:
        ap = r.get("appraisal") or {}
        pid = f"PMID {r['pmid']}" if r.get("pmid") else f"DOI {r.get('doi')}"
        pre = " (preprint)" if r.get("is_preprint") else ""
        lines.append(f"- {_clean(ap.get('one_line') or r.get('title'))} {pid}{pre}")
    lines += ["", "## Counts by domain and design", "", "| Domain | New | RCT | Meta-analysis | Guideline or statement | Observational | Other |",
              "|---|---|---|---|---|---|---|"]
    for d in config.DOMAINS:
        rs = [r for r in records if d in (r.get("domains") or [])]
        des = Counter(r.get("design") for r in rs)
        rct = des["rct"] + des["rct_secondary"]
        ma = des["ma"] + des["nma"] + des["ipd_ma"] + des["sr_no_ma"]
        gl = des["guideline"] + des["consensus_or_statement"]
        obs = des["registry_or_cohort"] + des["case_control"] + des["trial_emulation"]
        lines.append(f"| {d} {config.DOMAIN_NAMES[d]} | {len(rs)} | {rct} | {ma} | {gl} | {obs} | {len(rs) - rct - ma - gl - obs} |")
    new_q = [q for q in questions if q.get("created") == today.isoformat()]
    lines += ["", "## New candidate questions", ""]
    if not new_q:
        lines.append("None today.")
    for q in new_q:
        gates = "; ".join(f"{g} {'pass' if (q.get('gates') or {}).get(g, {}).get('pass') else 'fail'}" for g in register.GATES)
        lines.append(f"- {q['id']}: {_clean(q.get('title'))} ({gates})")
    lines.append("")
    return "\n".join(lines)


def records_csv(records):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "pmid", "doi", "title", "journal", "journal_tier", "entrez_date", "domains", "design", "tier",
                "is_preprint", "flags", "link"])
    for r in records:
        w.writerow([r["id"], r.get("pmid") or "", r.get("doi") or "", r.get("title") or "", r.get("journal") or "",
                    r.get("journal_tier") or "", (r.get("dates") or {}).get("entrez") or "", ";".join(r.get("domains") or []),
                    r.get("design") or "", r.get("tier") or "", "yes" if r.get("is_preprint") else "no",
                    ";".join(k for k, v in (r.get("flags") or {}).items() if v), link(r)])
    return buf.getvalue()


def write_daily(run, records, index, questions, today):
    y = f"{today.year:04d}"
    md = config.OUTPUTS / "daily" / y / f"{today.isoformat()}.md"
    config.atomic_write_text(md, digest(run, records, index, questions, today))
    config.atomic_write_text(config.OUTPUTS / "daily" / y / f"{today.isoformat()}_records.csv", records_csv(records))
    return md


# ---- weekly ----------------------------------------------------------------------------
_BIGRAM_STOP = set("a an the of in and or for with to on at by vs versus from after among patients patient study trial "
                   "analysis outcomes outcome results effect effects association role use using based case report "
                   "review systematic meta randomized randomised clinical acute".split())


def _bigrams(title):
    toks = [t for t in re.findall(r"[a-z0-9\-]+", (title or "").lower()) if t not in _BIGRAM_STOP and len(t) > 2]
    return {f"{a} {b}" for a, b in zip(toks, toks[1:])}


def weekly(index, questions, today):
    """Return (iso_week, markdown)."""
    wk = st.iso_week(today)
    monday = today - timedelta(days=today.weekday())
    week_start, week_end = monday - timedelta(days=7), monday - timedelta(days=1)
    rows = index.query("SELECT id, entrez, domains, tier, first_seen FROM rec WHERE entrez IS NOT NULL AND entrez >= ?",
                       ((week_start - timedelta(weeks=64)).isoformat(),))
    by_week = defaultdict(Counter)
    for rid, ent, doms, tier, fs in rows:
        try:
            e = date.fromisoformat(ent[:10])
        except ValueError:
            continue
        wn = (week_start - e).days // 7 if e < week_start else -1
        for d in (doms or "").split(","):
            if d:
                by_week[wn][d] += 1
    in_week = [r[0] for r in rows if week_start.isoformat() <= (r[1] or "")[:10] <= week_end.isoformat()]
    recs = store.get_records(in_week, index)
    tier_a = [r for r in recs.values() if r.get("tier") == "A"]
    lines = [f"# Weekly brief, {wk}", "", f"Covers records entered in PubMed or posted between {prose_date(week_start)} and "
             f"{prose_date(week_end)}, and register and trial changes in the same week. Rendered {prose_date(today)}.", ""]
    narrative = config.load_json(config.STATE / "weekly_narrative.json", {})
    if narrative.get("week") == wk and narrative.get("text"):
        lines += ["## Summary", "", narrative["text"].strip(), ""]
    lines += ["## Tier A papers and what they change", ""]
    if not tier_a:
        lines += ["No Tier A records this week.", ""]
    for r in sorted(tier_a, key=lambda x: x["id"]):
        ap = r.get("appraisal") or {}
        lines += [f"- {_clean(r.get('title'))}. {cite(r)}. {_clean(ap.get('why_it_matters'))}"]
    lines += ["", "## Movement by domain", "", "Records this week against the mean of the previous 12 weeks (week -1 is the reporting week).", "",
              "| Domain | This week | Previous 12-week mean | Ratio |", "|---|---|---|---|"]
    for d in config.DOMAINS:
        this = sum(1 for r in recs.values() if d in (r.get("domains") or []))
        prev = [by_week[w][d] for w in range(0, 12)]
        mean = sum(prev) / 12 if prev else 0
        ratio = f"{this / mean:.2f}" if mean else "n/a"
        lines.append(f"| {d} {config.DOMAIN_NAMES[d]} | {this} | {mean:.1f} | {ratio} |")
    lines += ["", "## Emerging topics", "",
              "Title bigrams and MeSH headings whose frequency per record in the last 12 weeks is more than twice their rate in the "
              "preceding 52 weeks, with at least five occurrences. MeSH indexing lags by several weeks, so MeSH signals understate the "
              "most recent weeks.", ""]
    lines += emerging_topics(index, week_end)
    changes = []
    if trials.CHANGES.exists():
        for l in trials.CHANGES.read_text(encoding="utf-8").splitlines():
            if l.strip():
                c = json.loads(l)
                if week_start.isoformat() <= c["date"] <= today.isoformat():
                    changes.append(c)
    lines += ["", "## Trial changes", ""]
    if not changes:
        lines.append("No registry changes detected this week.")
    by_kind = defaultdict(list)
    for c in changes:
        by_kind[c["change"]].append(c)
    for kind, cs in sorted(by_kind.items()):
        lines.append(f"### {kind.replace('_', ' ').capitalize()} ({len(cs)})")
        lines.append("")
        for c in cs[:40]:
            frm = f" from {c.get('from')} to {c.get('to')}" if kind != "new_registration" else ""
            lines.append(f"- {c['id']} {_clean(c.get('acronym') or '')} {_clean(c.get('title'))[:120]}{frm}")
        if len(cs) > 40:
            lines.append(f"- and {len(cs) - 40} more in data/trials/changes.jsonl")
        lines.append("")
    lines += ["## Next eight weeks", ""] + calendar_lines(today, weeks=8, min_enrolment=300) + [""]
    reg = [(q, h) for q in questions for h in q.get("status_history") or [] if week_start.isoformat() <= h["date"] <= today.isoformat()]
    lines += ["## Register changes", ""]
    if not reg:
        lines.append("No register changes this week.")
    for q, h in reg:
        lines.append(f"- {q['id']} {_clean(q.get('title'))}: {h['status'].replace('_', ' ')} on {prose_date(h['date'])} ({_clean(h['reason'])})")
    lines.append("")
    return wk, "\n".join(lines)


def emerging_topics(index, end, min_count=5):
    lo52 = (end - timedelta(weeks=64)).isoformat()
    mid = (end - timedelta(weeks=12)).isoformat()
    rows = index.query("SELECT id, entrez FROM rec WHERE entrez >= ? AND entrez <= ?", (lo52, end.isoformat()))
    ids_recent = [r[0] for r in rows if r[1] > mid]
    ids_prior = [r[0] for r in rows if r[1] <= mid]
    if len(ids_recent) < 50 or len(ids_prior) < 200:
        return ["Not enough records yet for a 12-week against 52-week comparison."]
    out = []
    for label, feat in (("Title bigrams", lambda r: _bigrams(r.get("title"))),
                        ("MeSH headings", lambda r: set(r.get("mesh") or []))):
        c_recent, c_prior = Counter(), Counter()
        for ids, c in ((ids_recent, c_recent), (ids_prior, c_prior)):
            for i in range(0, len(ids), 5000):
                for r in store.get_records(ids[i:i + 5000], index).values():
                    c.update(feat(r))
        n_r, n_p = len(ids_recent), len(ids_prior)
        hits = []
        for k, n in c_recent.items():
            if n < min_count:
                continue
            rate_r = n / n_r
            rate_p = c_prior[k] / n_p
            if rate_p == 0 or rate_r > 2 * rate_p:
                hits.append((rate_r / rate_p if rate_p else float("inf"), k, n, c_prior[k]))
        hits.sort(key=lambda x: (-x[2] if x[0] == float("inf") else -x[0], -x[2]))
        out.append(f"{label}:")
        out.append("")
        if not hits:
            out.append("- none met the threshold")
        for ratio, k, n, p in hits[:15]:
            rr = "new" if ratio == float("inf") else f"{ratio:.1f} times"
            out.append(f"- {k}: {n} in the last 12 weeks, {p} in the preceding 52 weeks ({rr})")
        out.append("")
    return out


# ---- calendar --------------------------------------------------------------------------
def calendar_lines(today, weeks=8, min_enrolment=300):
    out = []
    end = today + timedelta(weeks=weeks)
    ts = [t for t in trials.calendar(today, back_days=0, ahead_days=weeks * 7, min_enrolment=min_enrolment)]
    cong = config.load_json(config.CONFIG / "congresses.json", {"congresses": []}).get("congresses", [])
    upcoming = [c for c in cong if c.get("start") and today.isoformat() <= c["start"] <= end.isoformat()]
    if upcoming:
        out.append("Congresses:")
        out.append("")
        for c in upcoming:
            out.append(f"- {c['name']}, {prose_date(c['start'])} to {prose_date(c.get('end') or c['start'])}, {c.get('location', '')}. Programme: {c.get('programme_url', 'not yet published')}")
        out.append("")
    if ts:
        out.append(f"Randomised trials with at least {min_enrolment} participants whose primary completion date falls in the period (registry dates, often estimated):")
        out.append("")
        for t in ts:
            out.append(f"- {t['nct']} {_clean(t.get('acronym') or '')}: {_clean(t.get('title'))[:110]}; N {t.get('enrolment')}; primary completion {t.get('primary_completion')} ({(t.get('primary_completion_type') or 'type not stated').lower()}); {t.get('status', '').replace('_', ' ').lower()}")
    else:
        out.append("No large randomised trials are due to reach primary completion in the period.")
    return out


def write_calendar(today):
    lines = ["# Calendar", "", f"Updated {prose_date(today)}. Trial dates come from ClinicalTrials.gov and are often estimated by the sponsor. "
             "Congress dates and programme links come from official congress pages and carry their access date.", ""]
    cong = config.load_json(config.CONFIG / "congresses.json", {"congresses": []}).get("congresses", [])
    lines += ["## Congresses", ""]
    if not cong:
        lines.append("Congress dates have not yet been collected.")
    for c in sorted(cong, key=lambda c: c.get("start") or "9999"):
        if (c.get("end") or c.get("start") or "") < (today - timedelta(days=30)).isoformat():
            continue
        lines.append(f"- {c['name']}: {prose_date(c['start']) if c.get('start') else 'dates not announced'}"
                     f"{(' to ' + prose_date(c['end'])) if c.get('end') else ''}, {c.get('location', '')}. Source: {c.get('source_url', '')} (accessed {c.get('accessed', '')}).")
        for lb in c.get("late_breakers") or []:
            lines.append(f"  - Late-breaker: {_clean(lb.get('title'))}{(' (' + lb['nct'] + ')') if lb.get('nct') else ''}. {_clean(lb.get('synthesis_note', ''))}")
    ts = trials.calendar(today, back_days=365, ahead_days=3 * 365, min_enrolment=200)
    lines += ["", "## Trial readouts", "", "Randomised in-scope trials with at least 200 participants whose primary completion date falls between 12 months ago and 36 months ahead.", ""]
    by_q = defaultdict(list)
    for t in ts:
        pc = t.get("primary_completion") or ""
        y, m = int(pc[:4]), int(pc[5:7] or 1)
        by_q[f"{y} Q{(m - 1) // 3 + 1}"].append(t)
    for qk in sorted(by_q):
        lines += [f"### {qk}", "", "| NCT | Acronym | Title | N | Primary completion | Status | Domains |", "|---|---|---|---|---|---|---|"]
        for t in by_q[qk]:
            lines.append(f"| {t['nct']} | {_clean(t.get('acronym') or '')} | {_clean(t.get('title'))[:100]} | {t.get('enrolment') or ''} | "
                         f"{t.get('primary_completion')} ({(t.get('primary_completion_type') or '').lower()}) | {(t.get('status') or '').replace('_', ' ').lower()} | {', '.join(t.get('domains') or [])} |")
        lines.append("")
    config.atomic_write_text(config.OUTPUTS / "calendar.md", "\n".join(lines) + "\n")


# ---- README dashboard -----------------------------------------------------------------
def readme(index, questions, s, today, run=None):
    run = run or config.load_json(config.STATE / "last_run.json", {})
    lines = ["# Interventional Cardiology Evidence Watch", ""]
    now = config.london_now().strftime("%Y-%m-%d %H:%M")
    status = run.get("status", "not yet run")
    lines += ["## Status", "", f"- Last run: {run.get('finished_london', now)} (Europe/London), {run.get('kind', 'daily')}.",
              f"- Result: {status}{(', ' + run.get('status_reason')) if run.get('status_reason') else ''}."]
    b = s.get("baseline", {})
    if b.get("status") == "complete":
        lines.append(f"- Baseline: complete on {prose_date(b.get('completed_on'))}; {index.count()} records in the store.")
    else:
        lines.append(f"- Baseline: {b.get('status', 'not started')}; retrieval chunks pending {b.get('retrieval_pending', 'unknown')}; "
                     f"synthesis steps pending: {', '.join(b.get('synthesis_pending') or []) or 'none recorded'}.")
    lines.append(f"- Backlog awaiting appraisal: {len(appraise.load_backlog())}.")
    lines.append(f"- Records in the store: {index.count()} (Tier A {index.count('tier=?', ('A',))}, Tier B {index.count('tier=?', ('B',))}, "
                 f"Tier C {index.count('tier=?', ('C',))}, Tier D {index.count('tier=?', ('D',))}, untiered {index.count('tier IS NULL')}).")
    health = run.get("health") or s.get("source_health") or {}
    if health:
        lines += ["", "| Source | Health | Watermark |", "|---|---|---|"]
        for src, h in health.items():
            wms = sorted(v for k, v in s.get("watermarks", {}).items() if k.split(":")[0] == src)
            lines.append(f"| {src} | {'ok' if h == 'ok' else _clean(h)[:80]} | {wms[0] if wms else 'none'} |")
    warns = list(run.get("warnings") or [])
    if not config.contact_email():
        warns.append("CONTACT_EMAIL is not set in the environment, so NCBI, Crossref and OpenAlex requests carry no contact address.")
    unparsed = run.get("unparsed_decisions") or []
    for u in unparsed:
        warns.append(f"Owner decision not understood and not applied: '{_clean(u)}'.")
    if warns:
        lines += ["", "Warnings:", ""] + [f"- {_clean(w)}" for w in warns]
    r = register.ranked(questions, s.get("domain_weights"))
    lines += ["", "## Top ten priorities", ""]
    if not r:
        lines.append("The register has no question that passes all five gates yet.")
    for i, q in enumerate(r[:10], start=1):
        brief = f"register/briefs/{q['id']}.md"
        lk = f" ([brief]({brief}))" if (config.ROOT / brief).exists() else ""
        lines.append(f"{i}. {q['id']}: {_clean(q.get('title'))}, composite {register.composite(q, s.get('domain_weights'))}{lk}")
    lines += ["", "Full ranking and next actions: [PRIORITIES.md](PRIORITIES.md). Full register: [register/QUESTIONS.md](register/QUESTIONS.md).", ""]
    counts = Counter(q.get("status", "candidate") for q in questions)
    dcount = Counter(d for q in questions for d in q.get("domains") or [])
    lines += ["## Register", "", "By status: " + (", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(counts.items())) or "empty") + ".",
              "", "By domain: " + (", ".join(f"{d} {dcount[d]}" for d in config.DOMAINS if dcount[d]) or "empty") + ".", ""]
    since = (today - timedelta(days=7)).isoformat()
    rows = index.query("SELECT id FROM rec WHERE tier='A' AND (first_seen >= ? OR entrez >= ?)", (since, since))
    recent_a = [x for x in store.get_records([r[0] for r in rows], index).values() if not x.get("baseline") or ((x.get("dates") or {}).get("entrez") or "") >= since]
    lines += ["## Tier A in the past seven days", ""]
    if not recent_a:
        lines.append("None.")
    for x in sorted(recent_a, key=lambda x: (x.get("dates") or {}).get("entrez") or "", reverse=True)[:25]:
        lines.append(f"- [{_clean(x.get('title'))}]({link(x)}) ({x.get('journal')}{', preprint' if x.get('is_preprint') else ''})")
    lines += ["", "## Next eight weeks", ""] + calendar_lines(today, weeks=8, min_enrolment=500) + [""]
    lines += ["## Latest reports", ""]
    for kind in ("weekly", "monthly"):
        files = sorted((config.OUTPUTS / kind).glob("*.md")) if (config.OUTPUTS / kind).exists() else []
        lines.append(f"- {kind.capitalize()}: " + (f"[{files[-1].stem}](outputs/{kind}/{files[-1].name})" if files else "none yet"))
    dailies = sorted((config.OUTPUTS / "daily").rglob("*.md")) if (config.OUTPUTS / "daily").exists() else []
    lines.append("- Daily: " + (f"[{dailies[-1].stem}]({dailies[-1].relative_to(config.ROOT)})" if dailies else "none yet"))
    lines += ["- Domain landscapes: [outputs/landscape/](outputs/landscape/)", "- Calendar: [outputs/calendar.md](outputs/calendar.md)",
              "", "## How to steer it", "", "Write plain-language decisions in [context/decisions_by_owner.md](context/decisions_by_owner.md), one per line, "
              "for example `Q-014: in progress` or `Q-022: drop, outside my interests`. Edit [context/owner.md](context/owner.md) to change methods, data access or active projects. "
              "The operating specification is [CLAUDE.md](CLAUDE.md).", ""]
    config.atomic_write_text(config.ROOT / "README.md", "\n".join(lines))
