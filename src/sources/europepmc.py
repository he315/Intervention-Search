"""Europe PMC REST API: preprints, citation counts and open-access full text."""
import json
import re

from .. import net
from ..dedupe import normalise_doi

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def search(query, result_type="core", page_size=1000, max_pages=50):
    """Yield results for a query, following cursorMark pagination."""
    cursor = "*"
    for _ in range(max_pages):
        text = net.request(f"{BASE}/search", params={
            "query": query, "format": "json", "resultType": result_type,
            "pageSize": page_size, "cursorMark": cursor})
        d = json.loads(text)
        results = (d.get("resultList") or {}).get("result") or []
        for r in results:
            yield r
        nxt = d.get("nextCursorMark")
        if not results or not nxt or nxt == cursor:
            return
        cursor = nxt


def parse_preprint(r):
    """Convert a Europe PMC preprint result into a store record."""
    doi = normalise_doi(r.get("doi"))
    ppr = r.get("id")
    publisher = ((r.get("bookOrReportDetails") or {}).get("publisher")) or ""
    authors = []
    for a in ((r.get("authorList") or {}).get("author") or []):
        if a.get("lastName"):
            authors.append(f"{a['lastName']} {a.get('initials', '')}".strip())
        elif a.get("collectiveName"):
            authors.append(a["collectiveName"])
    if not authors and r.get("authorString"):
        authors = [s.strip() for s in r["authorString"].rstrip(".").split(",") if s.strip()]
    abstract = re.sub(r"<[^>]+>", " ", r.get("abstractText") or "")
    abstract = re.sub(r"\s+", " ", abstract).strip()
    published_as = None
    for cc in ((r.get("commentCorrectionList") or {}).get("commentCorrection") or []):
        if (cc.get("type") or "").lower().startswith("published") and cc.get("id"):
            published_as = cc.get("id")
    rec = {
        "id": ("doi:" + doi) if doi else ("ppr:" + ppr),
        "pmid": None,
        "doi": doi,
        "pmcid": None,
        "preprint_id": ppr,
        "sources": ["europepmc"],
        "title": re.sub(r"\s+", " ", r.get("title") or "").strip().rstrip("."),
        "abstract": abstract,
        "authors": authors[:10] + ([authors[-1]] if len(authors) > 10 else []),
        "n_authors": len(authors),
        "journal": f"{publisher} (preprint)" if publisher else "Preprint",
        "pub_types": ["Preprint"],
        "mesh": [],
        "keywords": [],
        "registry_ids": [],
        "dates": {"entrez": r.get("firstIndexDate") or r.get("firstPublicationDate"),
                  "published": r.get("firstPublicationDate"), "epub": None},
        "is_preprint": True,
        "flags": {},
    }
    if published_as:
        rec["published_as"] = published_as
    return rec


def citation_counts(pmids):
    """Return {pmid: citedByCount} for PMIDs, querying in batches of 100."""
    out = {}
    pmids = [str(p) for p in pmids]
    for i in range(0, len(pmids), 100):
        batch = pmids[i:i + 100]
        q = "(" + " OR ".join(f"EXT_ID:{p}" for p in batch) + ") AND SRC:MED"
        for r in search(q, result_type="lite", page_size=1000, max_pages=1):
            if r.get("source") == "MED" and r.get("id"):
                out[r["id"]] = int(r.get("citedByCount") or 0)
    return out


def full_text_xml(pmcid):
    return net.request(f"{BASE}/{pmcid}/fullTextXML", timeout=120)
