"""Model appraisal hand-off.

The Python pipeline cannot call a model, so appraisal is done by the session
itself: `appraise-export` writes a batch of records to
state/appraisal_batch.jsonl, the session reads them and writes one JSON line
per record to state/appraisal_results.jsonl, and `appraise-import` validates
and applies them. Validation rejects any Tier A or B appraisal whose primary
result contains a number that does not appear in the stored abstract, which
enforces 'never infer a number that is not in the source'.
"""
import json
import re

from . import config, store
from .classify import appraisal_priority

BATCH = config.STATE / "appraisal_batch.jsonl"
RESULTS = config.STATE / "appraisal_results.jsonl"
BACKLOG = config.STATE / "backlog.jsonl"
APPRAISAL_KEYS = ["one_line", "design_and_n", "primary_result_as_reported", "main_limitation", "why_it_matters"]
NO_RESULT_PHRASES = ("does not report", "gives no", "reports no", "no effect estimate", "not reported in the abstract",
                     "no numerical", "no quantitative")
_NUM = re.compile(r"(?<![A-Za-z])\d+(?:[.·]\d+)?")


def needs_appraisal(rec):
    return not rec.get("tier")


def load_backlog():
    if not BACKLOG.exists():
        return []
    return [json.loads(ln) for ln in BACKLOG.read_text(encoding="utf-8").splitlines() if ln.strip()]


def save_backlog(items):
    seen, out = set(), []
    for it in items:
        if it["id"] not in seen:
            seen.add(it["id"])
            out.append(it)
    out.sort(key=lambda x: (x.get("priority", [9]), x["id"]))
    config.atomic_write_text(BACKLOG, "".join(json.dumps(x) + "\n" for x in out))


def queue(records):
    """Add records that need appraisal to the backlog."""
    items = load_backlog()
    for r in records:
        if needs_appraisal(r):
            items.append({"id": r["id"], "priority": list(appraisal_priority(r))})
    save_backlog(items)
    return len(items)


def export_batch(index, limit=400, candidates=None, only_priority=None):
    """Write the next `limit` backlog records (most urgent first) to the batch file."""
    items = load_backlog()
    items.sort(key=lambda x: (x.get("priority", [9]), x["id"]))
    if only_priority is not None:
        items = [x for x in items if x.get("priority", [9])[0] <= only_priority]
    want = [x["id"] for x in items[:limit]]
    recs = store.get_records(want, index)
    cand_by_rec = {}
    for c in candidates or []:
        cand_by_rec.setdefault(c["record"], []).append(c)
    lines = []
    for rid in want:
        r = recs.get(rid)
        if not r or not needs_appraisal(r):
            continue
        lines.append(json.dumps({
            "id": r["id"], "title": r.get("title"), "journal": r.get("journal"), "journal_tier": r.get("journal_tier"),
            "design": r.get("design"), "pub_types": r.get("pub_types"), "date": (r.get("dates") or {}).get("entrez"),
            "is_preprint": r.get("is_preprint", False), "domains": r.get("domains"),
            "registry_ids": r.get("registry_ids"), "abstract": (r.get("abstract") or "")[:4000],
            "register_candidates": [c["qid"] for c in cand_by_rec.get(rid, [])],
        }, ensure_ascii=False))
    config.atomic_write_text(BATCH, "\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def _numbers(s):
    return {m.group(0).replace("·", ".") for m in _NUM.finditer(s or "")}


def _norm_abstract(a):
    return (a or "").replace("·", ".").replace(" ", " ")


def validate_result(res, rec):
    errs = []
    tier = res.get("tier")
    if tier not in config.TIERS:
        errs.append(f"{res.get('id')}: tier must be one of A, B, C, D")
        return errs
    if tier in ("A", "B"):
        ap = res.get("appraisal") or {}
        for k in APPRAISAL_KEYS:
            if not str(ap.get(k) or "").strip():
                errs.append(f"{res['id']}: Tier {tier} appraisal missing {k}")
        pr = str(ap.get("primary_result_as_reported") or "")
        if pr and not any(p in pr.lower() for p in NO_RESULT_PHRASES):
            abstract = _norm_abstract(rec.get("abstract"))
            abs_nums = _numbers(abstract)
            for n in _numbers(pr):
                if n in ("95",) or n in abs_nums:
                    continue
                # allow integer forms that appear inside the abstract text (for example 1,234 written as 1234)
                if n.replace(".", "") and n in abstract.replace(",", ""):
                    continue
                errs.append(f"{res['id']}: number {n} in primary_result_as_reported is not in the abstract")
        dn = str(ap.get("design_and_n") or "")
        abstract = _norm_abstract(rec.get("abstract")).replace(",", "")
        for n in _numbers(dn):
            if len(n) >= 3 and n not in abstract and n.replace(".", "") not in abstract:
                errs.append(f"{res['id']}: number {n} in design_and_n is not in the abstract")
    return errs


def import_results(index, path=RESULTS):
    """Validate and apply appraisal results. Returns (applied, errors)."""
    path = config.ROOT / path if not str(path).startswith("/") else path
    if not path.exists():
        return 0, [f"{path} does not exist"]
    results = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    recs = store.get_records([r["id"] for r in results], index)
    today = config.iso_date(config.london_today())
    updates, errors = {}, []
    for res in results:
        rec = recs.get(res.get("id"))
        if not rec:
            errors.append(f"{res.get('id')}: not in the store")
            continue
        errs = validate_result(res, rec)
        if errs:
            errors.extend(errs)
            continue
        up = {"tier": res["tier"], "tier_method": "model", "appraised_on": today}
        if res["tier"] in ("A", "B"):
            up["appraisal"] = {k: res["appraisal"][k] for k in APPRAISAL_KEYS}
        if res.get("question_ids"):
            up["question_ids"] = sorted(set(rec.get("question_ids") or []) | set(res["question_ids"]))
        if res.get("register_verdicts"):
            up["register_verdicts"] = res["register_verdicts"]
        updates[res["id"]] = up
    store.update_records(updates, index)
    index.commit()
    done = set(updates)
    save_backlog([x for x in load_backlog() if x["id"] not in done])
    return len(updates), errors
