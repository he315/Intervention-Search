"""The comprehensive first search (CLAUDE.md section 8), run in resumable chunks.

Chunk kinds:
  evidence:Dx:YYYY  RCTs, secondary analyses, SR/MA, guidelines and statements; every
                    in-scope article in target- and general-tier journals; registry and
                    cohort studies in specialty-tier journals (D1 to D8 from 2016, D9 from
                    2019 and RCT, MA and guidelines only).
  recent:Dx         every record matching the domain query in the last 15 months, so the
                    weekly trend analysis (12 weeks against the preceding 52) works from
                    the first week.
  trials            the ClinicalTrials.gov and ISRCTN snapshot.
Each chunk is checkpointed in state/state.json when it finishes.
"""
import time
from datetime import date, timedelta

from . import config, state as st
from .pipeline import Ingestor
from .sources import pubmed
from . import trials as trials_mod

RCT_MA_GL = ('("Randomized Controlled Trial"[pt] OR "randomized"[tiab] OR "randomised"[tiab] OR "Meta-Analysis"[pt] '
             'OR "Systematic Review"[pt] OR "meta-analysis"[tiab] OR "systematic review"[tiab] OR "Practice Guideline"[pt] '
             'OR "Guideline"[pt] OR "Consensus Statement"[pt] OR "consensus"[ti] OR "scientific statement"[ti] '
             'OR "position statement"[ti] OR "position paper"[ti] OR "guideline"[ti] OR "guidelines"[ti])')
OBS = ('("Observational Study"[pt] OR "registry"[tiab] OR "registries"[tiab] OR "cohort"[tiab] OR "retrospective"[tiab] '
       'OR "prospective"[tiab] OR "nationwide"[tiab] OR "propensity"[tiab] OR "real-world"[tiab])')


def issn_clause(tiers):
    issns = [i for j in config.journals().get("journals", []) if j["tier"] in tiers for i in (j.get("issn_pubmed") or j.get("issn") or [])]
    return "(" + " OR ".join(f'"{i}"[is]' for i in issns) + ")"


def evidence_filter(domain):
    if domain == "D9":
        return RCT_MA_GL
    return f"({RCT_MA_GL} OR {issn_clause(('target', 'general'))} OR ({issn_clause(('specialty',))} AND {OBS}))"


def plan(today=None):
    today = today or config.london_today()
    chunks = ["trials"]
    for d in config.DOMAINS:
        first = 2019 if d == "D9" else 2016
        for y in range(first, today.year + 1):
            chunks.append(f"evidence:{d}:{y}")
    for d in config.DOMAINS:
        chunks.append(f"recent:{d}")
    return chunks


def pending(s, today=None):
    done = s["baseline"].get("chunks") or {}
    return [c for c in plan(today) if done.get(c) != "done"]


def run_chunk(chunk, s, index, log, today):
    ing = Ingestor(index, log)
    kind = chunk.split(":")[0]
    if kind == "trials":
        snap = trials_mod.full_snapshot()
        n_changes = trials_mod.write_snapshot(snap, today)
        return {"trials": len(snap), "changes": n_changes}
    if kind == "evidence":
        _, d, y = chunk.split(":")
        y = int(y)
        lo, hi = date(y, 1, 1), min(date(y, 12, 31), today)
        term = f"({config.queries()[d]}) AND {evidence_filter(d)}"
        ids = pubmed.ids_in_window(term, lo, hi)
        n_new = n_upd = 0
        for i in range(0, len(ids), 1000):
            recs = pubmed.fetch(ids[i:i + 1000])
            a, b, _ = ing.ingest(recs, domain=d, baseline=True)
            n_new += a
            n_upd += b
        return {"retrieved": len(ids), "new": n_new, "updated": n_upd}
    if kind == "recent":
        d = chunk.split(":")[1]
        lo = today - timedelta(days=460)
        ids = pubmed.ids_in_window(config.queries()[d], lo, today)
        n_new = n_upd = 0
        for i in range(0, len(ids), 1000):
            recs = pubmed.fetch(ids[i:i + 1000])
            a, b, _ = ing.ingest(recs, domain=d, baseline=True)
            n_new += a
            n_upd += b
        return {"retrieved": len(ids), "new": n_new, "updated": n_upd}
    raise ValueError(f"unknown chunk {chunk}")


def run(index, max_minutes=7.5, only=None, log=None):
    """Run pending chunks until the time budget is spent. Returns a summary."""
    s = st.load()
    today = config.london_today()
    if not s["baseline"].get("start_date"):
        s["baseline"]["start_date"] = today.isoformat()
        s["baseline"]["status"] = "in_progress"
    deadline = time.monotonic() + max_minutes * 60
    log = log if log is not None else []
    results = {}
    for chunk in pending(s, today):
        if only and not chunk.startswith(only):
            continue
        if time.monotonic() > deadline:
            break
        t0 = time.monotonic()
        res = run_chunk(chunk, s, index, log, today)
        res["seconds"] = round(time.monotonic() - t0, 1)
        s = st.load() if config.STATE.joinpath("state.json").exists() else s
        if not s["baseline"].get("start_date"):
            s["baseline"]["start_date"] = today.isoformat()
            s["baseline"]["status"] = "in_progress"
        s["baseline"].setdefault("chunks", {})[chunk] = "done"
        s["baseline"].setdefault("chunk_results", {})[chunk] = res
        st.save(s)
        results[chunk] = res
    s = st.load()
    s["baseline"]["retrieval_pending"] = len(pending(s, today))
    st.save(s)
    return {"ran": results, "pending": len(pending(s, today))}
