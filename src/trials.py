"""ClinicalTrials.gov (and ISRCTN) snapshots, change detection and the readout calendar.

data/trials/current.jsonl.gz holds the latest state of every in-scope trial.
Daily runs refresh trials updated in the window; weekly runs write a dated
snapshot and diff it against the previous one into data/trials/changes.jsonl.
"""
import gzip
import json
from datetime import date, timedelta

from . import config
from .sources import ctgov, isrctn

CURRENT = config.TRIALS / "current.jsonl.gz"
CHANGES = config.TRIALS / "changes.jsonl"
EXTRA = config.TRIALS / "extra.jsonl"

TERMS = {
    "D1": '"percutaneous coronary intervention" OR "coronary stent" OR "drug-eluting stent" OR "drug-coated balloon" OR "drug coated balloon" OR "fractional flow reserve" OR "coronary lithotripsy" OR "intravascular lithotripsy" OR "chronic total occlusion" OR "left main coronary" OR "coronary bifurcation" OR "coronary atherectomy" OR "intravascular ultrasound" OR "coronary revascularization"',
    "D2": '"cardiogenic shock" OR Impella OR "microaxial flow pump" OR "intra-aortic balloon" OR "venoarterial extracorporeal" OR "VA-ECMO" OR "mechanical circulatory support" OR "extracorporeal cardiopulmonary resuscitation" OR ("cardiac arrest" AND ("coronary angiography" OR extracorporeal))',
    "D3": 'TAVI OR TAVR OR "transcatheter aortic" OR "aortic stenosis" OR "aortic valve replacement"',
    "D4": 'MitraClip OR "mitral regurgitation" OR "transcatheter mitral" OR ("edge-to-edge" AND mitral)',
    "D5": '"tricuspid regurgitation" OR TriClip OR "transcatheter tricuspid"',
    "D6": '"acute coronary syndrome" OR "myocardial infarction" OR STEMI OR NSTEMI OR "unstable angina" OR MINOCA OR "spontaneous coronary artery dissection"',
    "D7": '"type 2 myocardial infarction" OR "myocardial injury" OR "perioperative myocardial infarction"',
    "D8": '(clopidogrel OR ticagrelor OR prasugrel OR cangrelor OR "dual antiplatelet" OR P2Y12 OR antiplatelet OR bivalirudin OR "factor XI" OR anticoagulation) AND ("percutaneous coronary" OR PCI OR stent OR "acute coronary syndrome" OR "myocardial infarction" OR TAVI OR TAVR OR transcatheter)',
    "D9": '"left atrial appendage" OR "patent foramen ovale" OR "renal denervation" OR "interatrial shunt" OR "coronary sinus reducer" OR ("pulmonary embolism" AND (catheter OR thrombectomy))',
}
ISRCTN_CONDITIONS = {
    "D1": ["coronary artery disease", "angina"], "D2": ["cardiogenic shock", "cardiac arrest"],
    "D3": ["aortic stenosis"], "D4": ["mitral regurgitation"], "D5": ["tricuspid regurgitation"],
    "D6": ["myocardial infarction", "acute coronary syndrome"], "D7": ["myocardial injury"],
    "D8": ["acute coronary syndrome"], "D9": ["pulmonary embolism", "patent foramen ovale"],
}
TRACKED = ("status", "primary_completion", "completion", "has_results", "enrolment")


def read_jsonl_gz(path):
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def write_jsonl_gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r.get("nct") or r.get("isrctn") or "")
    tmp = path.with_name(".tmp_" + path.name)
    with open(tmp, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode("utf-8"))
    tmp.replace(path)


def key(t):
    return t.get("nct") or t.get("isrctn")


def full_snapshot(domains=None, since="2010-01-01", include_isrctn=True):
    """Fetch every in-scope interventional study registered since `since`."""
    by_key = {}
    for d, term in TERMS.items():
        if domains and d not in domains:
            continue
        for s in ctgov.search(term, since=since):
            t = ctgov.parse_study(s)
            if not t.get("nct"):
                continue
            prev = by_key.get(t["nct"])
            t["domains"] = sorted(set((prev or {}).get("domains", [])) | {d})
            t["source"] = "ctgov"
            by_key[t["nct"]] = t
        if include_isrctn:
            for cond in ISRCTN_CONDITIONS.get(d, []):
                try:
                    for t in isrctn.search(cond):
                        if t.get("isrctn"):
                            prev = by_key.get(t["isrctn"])
                            t["domains"] = sorted(set((prev or {}).get("domains", [])) | {d})
                            by_key[t["isrctn"]] = t
                except Exception:
                    pass
    return by_key


def delta_update(start, today):
    """Refresh trials whose record was updated in [start, today]."""
    cur = {key(t): t for t in read_jsonl_gz(CURRENT)}
    changed = 0
    flt = f"AREA[LastUpdatePostDate]RANGE[{start.isoformat()},{today.isoformat()}]"
    for d, term in TERMS.items():
        for s in ctgov.search(term, since="2010-01-01", extra_filter=flt):
            t = ctgov.parse_study(s)
            t["source"] = "ctgov"
            prev = cur.get(t["nct"])
            t["domains"] = sorted(set((prev or {}).get("domains", [])) | {d})
            if prev != t:
                changed += 1
            cur[t["nct"]] = t
    old = {key(t): t for t in read_jsonl_gz(CURRENT)}
    changes = diff(old, cur, today)
    write_jsonl_gz(CURRENT, list(cur.values()))
    append_changes(changes)
    return {"updated": changed, "changes": len(changes)}


def diff(old, new, today):
    out = []
    for k, t in new.items():
        o = old.get(k)
        if o is None:
            if old:
                out.append({"date": today.isoformat(), "id": k, "change": "new_registration", "title": t.get("title"),
                            "acronym": t.get("acronym"), "domains": t.get("domains")})
            continue
        for f in TRACKED:
            if o.get(f) != t.get(f):
                out.append({"date": today.isoformat(), "id": k, "change": f, "from": o.get(f), "to": t.get(f),
                            "title": t.get("title"), "acronym": t.get("acronym"), "domains": t.get("domains")})
    return out


def append_changes(changes):
    if not changes:
        return
    CHANGES.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANGES, "a", encoding="utf-8") as fh:
        for c in changes:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def write_snapshot(by_key, today):
    old = {key(t): t for t in read_jsonl_gz(CURRENT)}
    changes = diff(old, by_key, today)
    write_jsonl_gz(CURRENT, list(by_key.values()))
    write_jsonl_gz(config.TRIALS / f"ctgov_{today.isoformat()}.jsonl.gz", list(by_key.values()))
    append_changes(changes)
    return len(changes)


def all_trial_ids():
    ids = {key(t) for t in read_jsonl_gz(CURRENT)}
    if EXTRA.exists():
        ids |= {json.loads(l).get("nct") or json.loads(l).get("isrctn") for l in EXTRA.read_text().splitlines() if l.strip()}
    return {i for i in ids if i}


def add_extra(ncts):
    """Fetch individual trials (for example ones cited in a brief) into extra.jsonl."""
    have = all_trial_ids()
    added = []
    with open(EXTRA, "a", encoding="utf-8") as fh:
        for n in ncts:
            if n in have:
                continue
            t = ctgov.get_study(n)
            if t.get("nct"):
                t["source"] = "ctgov_extra"
                fh.write(json.dumps(t, ensure_ascii=False) + "\n")
                added.append(n)
    return added


def get_trials(ids=None):
    rows = read_jsonl_gz(CURRENT)
    if EXTRA.exists():
        rows += [json.loads(l) for l in EXTRA.read_text().splitlines() if l.strip()]
    if ids is None:
        return rows
    ids = set(ids)
    return [t for t in rows if key(t) in ids]


def _d(s):
    if not s:
        return None
    try:
        if len(s) == 7:
            return date.fromisoformat(s + "-01")
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def calendar(today, back_days=365, ahead_days=3 * 365, min_enrolment=0, randomised_only=True):
    """Trials with primary completion between today-back and today+ahead."""
    out = []
    lo, hi = today - timedelta(days=back_days), today + timedelta(days=ahead_days)
    for t in read_jsonl_gz(CURRENT):
        if t.get("source") != "ctgov":
            continue
        if randomised_only and t.get("allocation") != "RANDOMIZED":
            continue
        if (t.get("enrolment") or 0) < min_enrolment:
            continue
        pc = _d(t.get("primary_completion"))
        if pc and lo <= pc <= hi and t.get("status") not in ("WITHDRAWN",):
            out.append(t)
    out.sort(key=lambda t: _d(t.get("primary_completion")))
    return out
