"""medRxiv through the bioRxiv/medRxiv API, cardiovascular medicine category."""
import json
import re

from .. import net
from ..dedupe import normalise_doi

BASE = "https://api.biorxiv.org/details/medrxiv"
CATEGORY = "cardiovascular medicine"


def fetch_window(start, end, max_pages=200):
    """Return raw items posted in [start, end] (dates), all categories."""
    items = []
    cursor = 0
    for _ in range(max_pages):
        text = net.request(f"{BASE}/{start.isoformat()}/{end.isoformat()}/{cursor}", timeout=90)
        d = json.loads(text)
        coll = d.get("collection") or []
        items.extend(coll)
        msg = (d.get("messages") or [{}])[0]
        total = int(msg.get("total") or 0)
        cursor += len(coll)
        if not coll or cursor >= total:
            break
    return items


def parse_items(items):
    """Keep cardiovascular medicine items, latest version per DOI."""
    latest = {}
    for it in items:
        if (it.get("category") or "").strip().lower() != CATEGORY:
            continue
        doi = normalise_doi(it.get("doi"))
        if not doi:
            continue
        v = int(it.get("version") or 1)
        if doi not in latest or v > int(latest[doi].get("version") or 1):
            latest[doi] = it
    out = []
    for doi, it in latest.items():
        authors = [a.strip().replace(",", "") for a in (it.get("authors") or "").split(";") if a.strip()]
        published = it.get("published")
        rec = {
            "id": "doi:" + doi,
            "pmid": None,
            "doi": doi,
            "pmcid": None,
            "preprint_id": doi,
            "sources": ["medrxiv"],
            "title": re.sub(r"\s+", " ", it.get("title") or "").strip(),
            "abstract": re.sub(r"\s+", " ", it.get("abstract") or "").strip(),
            "authors": authors[:10] + ([authors[-1]] if len(authors) > 10 else []),
            "n_authors": len(authors),
            "journal": "medRxiv (preprint)",
            "pub_types": ["Preprint"],
            "mesh": [],
            "keywords": [],
            "registry_ids": [],
            "dates": {"entrez": it.get("date"), "published": it.get("date"), "epub": None},
            "is_preprint": True,
            "flags": {},
        }
        if published and published != "NA":
            rec["published_as"] = normalise_doi(published) or published
        out.append(rec)
    return out
