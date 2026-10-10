"""Research question register: storage, scoring, gates and rendering.

register/questions.jsonl is the source of truth. The composite score uses
the weights in CLAUDE.md section 9 (Impact 25, Novelty 20, Equipoise 15,
Design credibility 15, Timeliness 10, Citation potential 10, Feasibility 5)
and is scaled to 0-100.
"""
import json
import re

from . import config

PATH = config.REGISTER / "questions.jsonl"
WEIGHTS = {"impact": 25, "novelty": 20, "equipoise": 15, "design": 15,
           "timeliness": 10, "citation": 10, "feasibility": 5}
GATES = ["G1", "G2", "G3", "G4", "G5"]
GATE_NAMES = {"G1": "Consequence", "G2": "Equipoise", "G3": "Not about to be answered",
              "G4": "Credible design", "G5": "Not incremental"}
INACTIVE = {"parked", "scooped", "answered", "merged"}
STATUSES = ["candidate", "shortlisted", "priority", "in_progress", "parked", "scooped", "answered", "merged"]


def load():
    if not PATH.exists():
        return []
    out = []
    for ln in PATH.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def save(questions):
    questions = sorted(questions, key=lambda q: q["id"])
    for q in questions:
        q["composite"] = composite(q)
    text = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions)
    config.atomic_write_text(PATH, text)


def next_id(questions):
    nums = [int(q["id"].split("-")[1]) for q in questions if re.match(r"^Q-\d+$", q["id"])]
    return f"Q-{(max(nums) + 1) if nums else 1:03d}"


def composite(q, domain_weights=None):
    s = q.get("scores") or {}
    total = 0.0
    for k, w in WEIGHTS.items():
        v = (s.get(k) or {}).get("score")
        if not isinstance(v, (int, float)):
            return None
        total += w * float(v)
    value = total / 5.0
    if domain_weights:
        factors = [domain_weights.get(d, 1.0) for d in q.get("domains") or []]
        if factors and all(f != 1.0 for f in factors):
            value *= min(factors)
    return round(value, 1)


def gates_passed(q):
    g = q.get("gates") or {}
    return all((g.get(k) or {}).get("pass") is True for k in GATES)


def failing_gates(q):
    g = q.get("gates") or {}
    return [k for k in GATES if (g.get(k) or {}).get("pass") is not True]


def eligible_for_top(q):
    return (q.get("status") not in INACTIVE and gates_passed(q)
            and not q.get("subspecialty_only") and composite(q) is not None)


def ranked(questions, domain_weights=None):
    elig = [q for q in questions if eligible_for_top(q)]
    return sorted(elig, key=lambda q: (-(composite(q, domain_weights) or 0), q["id"]))


def set_status(q, status, reason, date):
    if status not in STATUSES:
        raise ValueError(f"unknown status {status}")
    q["status"] = status
    q.setdefault("status_history", []).append({"date": date, "status": status, "reason": reason})


def apply_owner_decision(questions, d, date):
    """Apply one parsed owner decision; returns a log line."""
    by_id = {q["id"]: q for q in questions}
    if d["kind"] in ("status", "merge"):
        q = by_id.get(d["qid"])
        if not q:
            return f"owner decision not applied: {d['qid']} is not in the register ({d['text']})"
        if d["kind"] == "merge":
            if d["into"] not in by_id:
                return f"owner decision not applied: {d['into']} is not in the register ({d['text']})"
            set_status(q, "merged", f"owner decision: merged into {d['into']}", date)
            q["merged_into"] = d["into"]
            return f"{d['qid']} merged into {d['into']} (owner decision)"
        set_status(q, d["status"], f"owner decision: {d['reason']}", date)
        return f"{d['qid']} set to {d['status']} (owner decision: {d['reason']})"
    return None


def keywords(q):
    kws = [k.lower() for k in (q.get("keywords") or []) if k]
    return kws


def scoop_candidates(questions, records):
    """Pair active questions with new records that may answer or scoop them."""
    out = []
    active = [q for q in questions if q.get("status") not in INACTIVE]
    for r in records:
        text = ((r.get("title") or "") + " " + (r.get("abstract") or "")).lower()
        rdom = set(r.get("domains") or [])
        regs = set(r.get("registry_ids") or [])
        for q in active:
            if not rdom & set(q.get("domains") or []):
                continue
            ncts = {c.get("nct") for c in q.get("competing") or [] if c.get("nct")}
            kws = keywords(q)
            hits = [k for k in kws if k in text]
            need = min(3, max(2, len(kws) // 2)) if kws else 99
            if (ncts & regs) or len(hits) >= need:
                if r.get("design") in ("rct", "rct_secondary", "ipd_ma", "ma", "nma", "guideline",
                                       "consensus_or_statement", "trial_emulation", "registry_or_cohort"):
                    out.append({"record": r["id"], "qid": q["id"], "hits": hits, "trial_overlap": sorted(ncts & regs)})
    return out


def _fmt_score(q):
    c = composite(q)
    return f"{c:.1f}" if c is not None else "unscored"


def render_questions_md(questions, today):
    lines = ["# Research question register", "",
             f"Rendered {today}. Source of truth: register/questions.jsonl. Composite is out of 100.", ""]
    counts = {}
    for q in questions:
        counts[q.get("status", "candidate")] = counts.get(q.get("status", "candidate"), 0) + 1
    lines.append("Status counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".")
    lines.append("")
    for status in STATUSES:
        group = [q for q in questions if q.get("status") == status]
        if not group:
            continue
        group.sort(key=lambda q: (-(composite(q) or 0), q["id"]))
        lines += [f"## {status.replace('_', ' ').capitalize()} ({len(group)})", "",
                  "| ID | Title | Domains | Composite | Gates | Design | Brief |",
                  "|---|---|---|---|---|---|---|"]
        for q in group:
            fails = failing_gates(q)
            gate = "all passed" if not fails else "failed " + ", ".join(fails)
            if q.get("subspecialty_only"):
                gate += "; subspecialty only"
            brief = f"[brief](briefs/{q['id']}.md)" if (config.REGISTER / "briefs" / f"{q['id']}.md").exists() else ""
            design = ((q.get("designs") or {}).get("primary") or "").replace("|", "/")
            lines.append(f"| {q['id']} | {q.get('title', '').replace('|', '/')} | {', '.join(q.get('domains') or [])} | "
                         f"{_fmt_score(q)} | {gate} | {design[:80]} | {brief} |")
        lines.append("")
    config.atomic_write_text(config.REGISTER / "QUESTIONS.md", "\n".join(lines) + "\n")


def render_priorities_md(questions, today, domain_weights=None):
    r = ranked(questions, domain_weights)
    lines = ["# Research priorities", "", f"Refreshed {today}. Ranked by composite score among questions that pass "
             "all five gates and are not limited to a subspecialty journal. Feasibility is reported for every "
             "question but carries 5% of the weight.", "", "## Top ten", ""]
    for i, q in enumerate(r[:10], start=1):
        acts = q.get("next_actions") or []
        lines += [f"### {i}. {q['id']}: {q.get('title', '')}", "",
                  f"Composite {_fmt_score(q)}. Status: {q.get('status', 'candidate').replace('_', ' ')}. "
                  f"Domains: {', '.join(q.get('domains') or [])}. Target journal: {q.get('target_journal', 'not set')}.", "",
                  f"Design: {(q.get('designs') or {}).get('primary', 'not set')}", "",
                  f"Why now: {q.get('why_now', 'not set')}", "",
                  f"Feasibility for the owner: {(q.get('scores') or {}).get('feasibility', {}).get('why', q.get('feasibility', 'not set'))}", ""]
        if acts:
            lines.append("Next three actions:")
            lines.append("")
            for j, a in enumerate(acts[:3], start=1):
                lines.append(f"{j}. {a}")
            lines.append("")
        if (config.REGISTER / "briefs" / f"{q['id']}.md").exists():
            lines += [f"Full brief: [register/briefs/{q['id']}.md](register/briefs/{q['id']}.md)", ""]
    lines += ["## Watch list (ranks 11 to 25)", ""]
    watch = r[10:25]
    if not watch:
        lines.append("No further questions currently pass every gate.")
    for i, q in enumerate(watch, start=11):
        lines.append(f"{i}. {q['id']}: {q.get('title', '')} (composite {_fmt_score(q)})")
    lines.append("")
    config.atomic_write_text(config.ROOT / "PRIORITIES.md", "\n".join(lines) + "\n")
