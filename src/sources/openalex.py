"""OpenAlex citation counts, with a Europe PMC fallback.

Without OPENALEX_API_KEY the free budget is shared by every user on the same
IP address and is often exhausted; a 429 with a long retryAfter is treated as
'budget exhausted' and the caller falls back to Europe PMC citedByCount.
"""
import json
import os

from .. import net
from ..dedupe import normalise_doi
from . import europepmc

BASE = "https://api.openalex.org"


class BudgetExhausted(Exception):
    pass


def parse_error(text):
    try:
        d = json.loads(text)
    except ValueError:
        return None
    if isinstance(d, dict) and d.get("error"):
        return d
    return None


def counts_by_doi(dois):
    out = {}
    dois = [d for d in (normalise_doi(x) for x in dois) if d]
    key = os.environ.get("OPENALEX_API_KEY")
    for i in range(0, len(dois), 50):
        batch = dois[i:i + 50]
        params = {"filter": "doi:" + "|".join(batch), "select": "doi,cited_by_count", "per-page": 50}
        if key:
            params["api_key"] = key
        try:
            text = net.request(f"{BASE}/works", params=params, retries=1)
        except net.HttpError as e:
            err = parse_error(e.body)
            if e.status == 429:
                raise BudgetExhausted((err or {}).get("message") or "OpenAlex rate limit")
            raise
        for w in json.loads(text).get("results") or []:
            d = normalise_doi(w.get("doi"))
            if d:
                out[d] = int(w.get("cited_by_count") or 0)
    return out


def citation_counts(records):
    """Return ({id: count}, source_name). Tries OpenAlex, falls back to Europe PMC."""
    by_doi = {normalise_doi(r.get("doi")): r["id"] for r in records if r.get("doi")}
    try:
        c = counts_by_doi(list(by_doi))
        res = {by_doi[d]: n for d, n in c.items() if d in by_doi}
        missing = [r for r in records if r["id"] not in res and r.get("pmid")]
        if missing:
            for pmid, n in europepmc.citation_counts([r["pmid"] for r in missing]).items():
                res[pmid] = n
        return res, "openalex"
    except BudgetExhausted:
        pm = [r["pmid"] for r in records if r.get("pmid")]
        return europepmc.citation_counts(pm), "europepmc"
