"""Crossref REST API: ISSN resolution and online-first items by journal."""
import json
import re
import unicodedata

from .. import net
from ..dedupe import normalise_doi

BASE = "https://api.crossref.org"


def _norm(title):
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    t = re.sub(r"^the\s+", "", t.strip())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def find_journal(title, rows=20, query=None):
    """Return the Crossref journal entries whose normalised title equals `title`.

    `query` lets the search string differ from the title being matched, for
    titles whose punctuation upsets Crossref's ranking.
    """
    text = net.request(f"{BASE}/journals", params={"query": query or title, "rows": rows})
    return match_journal(json.loads(text), title)


def match_journal(payload, title):
    want = _norm(title)
    out = []
    for it in (payload.get("message") or {}).get("items") or []:
        if _norm(it.get("title")) == want:
            out.append({"title": it.get("title"), "publisher": it.get("publisher"),
                        "issn": it.get("ISSN") or [], "issn_type": it.get("issn-type") or []})
    return out


def works(issn, from_date, until_date, date_field="created", max_items=5000):
    """Items for one ISSN created (or published online) within a window."""
    filt = f"from-{date_field}-date:{from_date.isoformat()},until-{date_field}-date:{until_date.isoformat()},type:journal-article"
    cursor = "*"
    items = []
    while len(items) < max_items:
        text = net.request(f"{BASE}/journals/{issn}/works", params={
            "filter": filt, "rows": 500, "cursor": cursor,
            "select": "DOI,title,type,published-online,published-print,created,container-title,ISSN,author,abstract,relation,subtype"})
        m = json.loads(text)["message"]
        batch = m.get("items") or []
        items.extend(batch)
        nxt = m.get("next-cursor")
        if not batch or not nxt or len(batch) < 500:
            break
        cursor = nxt
    return items


def _dp(obj):
    if not obj:
        return None
    parts = (obj.get("date-parts") or [[None]])[0]
    if not parts or parts[0] is None:
        return None
    y = parts[0]
    m = parts[1] if len(parts) > 1 else 1
    d = parts[2] if len(parts) > 2 else 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_item(it, journal_name=None, tier=None):
    doi = normalise_doi(it.get("DOI"))
    if not doi:
        return None
    title = " ".join(it.get("title") or []).strip()
    title = re.sub(r"<[^>]+>", "", title)
    abstract = re.sub(r"<[^>]+>", " ", it.get("abstract") or "")
    abstract = re.sub(r"\s+", " ", abstract).strip()
    authors = []
    for a in it.get("author") or []:
        fam = a.get("family")
        if fam:
            given = a.get("given") or ""
            ini = "".join(p[0] for p in re.split(r"[\s\-.]+", given) if p)
            authors.append(f"{fam} {ini}".strip())
        elif a.get("name"):
            authors.append(a["name"])
    created = (it.get("created") or {}).get("date-time", "")[:10] or None
    return {
        "id": "doi:" + doi,
        "pmid": None,
        "doi": doi,
        "pmcid": None,
        "sources": ["crossref"],
        "title": title,
        "abstract": abstract,
        "authors": authors[:10] + ([authors[-1]] if len(authors) > 10 else []),
        "n_authors": len(authors),
        "journal": journal_name or " ".join(it.get("container-title") or []),
        "issns": it.get("ISSN") or [],
        "journal_tier": tier,
        "pub_types": [it.get("type") or "journal-article"],
        "mesh": [],
        "keywords": [],
        "registry_ids": [],
        "dates": {"entrez": created, "published": _dp(it.get("published-print")),
                  "epub": _dp(it.get("published-online"))},
        "is_preprint": False,
        "flags": {},
    }
