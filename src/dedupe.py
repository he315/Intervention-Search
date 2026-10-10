"""Identifier normalisation and preprint linkage.

Deduplication order: PMID, then DOI (lower-cased, resolver prefixes
stripped), then preprint identifier. Preprints link to their published
version through DOI relation fields where present, otherwise by normalised
title similarity (token Jaccard >= 0.9) plus a first-author surname match.
"""
import re
import unicodedata

_DOI_PREFIXES = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", re.I)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "of", "in", "and", "or", "for", "with", "to", "on", "at", "by", "vs", "versus", "from"}


def normalise_doi(doi):
    if not doi:
        return None
    d = _DOI_PREFIXES.sub("", str(doi).strip()).strip().lower()
    d = d.rstrip(".;,")
    return d if d.startswith("10.") else None


def record_id(pmid=None, doi=None, preprint_id=None):
    if pmid:
        return str(pmid)
    nd = normalise_doi(doi)
    if nd:
        return "doi:" + nd
    if preprint_id:
        return "ppr:" + str(preprint_id)
    raise ValueError("record has no PMID, DOI or preprint identifier")


def title_tokens(title):
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    return {w for w in _TOKEN.findall(t) if w not in _STOP}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def first_author_surname(record):
    authors = record.get("authors") or []
    if not authors:
        return ""
    first = authors[0]
    surname = first.split(" ")[0] if " " in first else first
    surname = unicodedata.normalize("NFKD", surname).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", surname)


def is_preprint_match(preprint, published, threshold=0.9):
    """True when a preprint and a journal record describe the same work."""
    sim = jaccard(title_tokens(preprint.get("title")), title_tokens(published.get("title")))
    if sim < threshold:
        return False
    a, b = first_author_surname(preprint), first_author_surname(published)
    return bool(a) and a == b
