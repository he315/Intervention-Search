"""Query validation (CLAUDE.md section 4.1): recall against seeds, precision
sampling, and core-journal completeness against Crossref."""
import random
from datetime import timedelta

from . import config
from .sources import pubmed


def seed_pmids_by_domain():
    seeds = config.load_json(config.CONFIG / "seeds.json", {"seeds": []})["seeds"]
    out = {}
    for s in seeds:
        if s.get("status") != "resolved":
            continue
        ids = [s["pmid"]] + list(s.get("also_published_as") or [])
        out.setdefault(s["domain"], []).append({"name": s["name"], "pmids": ids})
    return out


def recall(domains=None):
    """Return {domain: {"n": seeds, "hit": n_retrieved, "missed": [names]}}."""
    q = config.queries()
    res = {}
    for d, seeds in seed_pmids_by_domain().items():
        if domains and d not in domains:
            continue
        allids = sorted({p for s in seeds for p in s["pmids"]})
        term = f"({q[d]}) AND (" + " OR ".join(f"{p}[uid]" for p in allids) + ")"
        _, ids, _ = pubmed.search(term, retmax=len(allids) + 5)
        got = set(ids)
        missed = [s["name"] for s in seeds if not set(s["pmids"]) & got]
        res[d] = {"n": len(seeds), "hit": len(seeds) - len(missed), "missed": missed,
                  "recall": round((len(seeds) - len(missed)) / len(seeds), 3)}
    return res


def precision_sample(domain, n=100, seed=20261010):
    """Random sample of PMIDs from the last 12 months for a domain."""
    q = config.queries()[domain]
    today = config.london_today()
    ids = pubmed.ids_in_window(q, today - timedelta(days=365), today)
    rng = random.Random(seed + int(domain[1:]))
    return rng.sample(ids, min(n, len(ids)))
