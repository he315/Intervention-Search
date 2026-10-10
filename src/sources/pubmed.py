"""PubMed through NCBI E-utilities: the primary source.

Surveillance windows use esearch with datetype=edat (the date a record
entered PubMed) so late-indexed and back-dated records are caught. esearch
returns at most 10,000 identifiers per query, so windows are split by date
until each holds fewer than 9,000. efetch is called by POST with 200
identifiers per request.
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from .. import net, config
from ..dedupe import normalise_doi

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SPLIT_LIMIT = 9000
FETCH_BATCH = 200

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

REGISTRY_PATTERNS = {
    "NCT": re.compile(r"\bNCT\d{8}\b"),
    "ISRCTN": re.compile(r"\bISRCTN\s?\d{8}\b"),
    "ChiCTR": re.compile(r"\bChiCTR[-\w]{6,20}\b"),
    "EudraCT": re.compile(r"\b(?:EudraCT[^0-9]{0,12})?(20\d{2}-\d{6}-\d{2})\b"),
    "CTIS": re.compile(r"\b(20\d{2}-5\d{5}-\d{2}-\d{2})\b"),
}


def _base_params():
    p = {"db": "pubmed", "tool": "ic_evidence_watch"}
    email = config.contact_email()
    if email:
        p["email"] = email
    key = os.environ.get("NCBI_API_KEY")
    if key:
        p["api_key"] = key
    return p


def _fmt(d):
    return d.strftime("%Y/%m/%d")


def search(term, mindate=None, maxdate=None, datetype="edat", retmax=0):
    """Run esearch; returns (count, idlist, warnings)."""
    params = _base_params()
    params.update({"term": term, "retmode": "json", "retmax": retmax})
    if mindate or maxdate:
        params.update({"datetype": datetype, "mindate": _fmt(mindate or date(1800, 1, 1)),
                       "maxdate": _fmt(maxdate or date(3000, 1, 1))})
    text = net.request(f"{EUTILS}/esearch.fcgi", data=params)
    return parse_esearch(text)


def parse_esearch(text):
    d = json.loads(text)
    if "esearchresult" not in d:
        raise net.HttpError("esearch", 200, text[:300], "unexpected esearch response")
    r = d["esearchresult"]
    if "ERROR" in r:
        raise net.HttpError("esearch", 200, str(r["ERROR"]), "esearch error")
    warnings = []
    for k in ("warninglist", "errorlist"):
        w = r.get(k) or {}
        for kk, vv in w.items():
            if vv:
                warnings.append(f"{k}.{kk}: {vv}")
    return int(r.get("count", 0)), list(r.get("idlist", [])), warnings


def count(term, mindate=None, maxdate=None, datetype="edat"):
    n, _, warn = search(term, mindate, maxdate, datetype, retmax=0)
    return n, warn


def ids_in_window(term, mindate, maxdate, datetype="edat"):
    """All PMIDs for a term in [mindate, maxdate], splitting large windows."""
    n, ids, _ = search(term, mindate, maxdate, datetype, retmax=SPLIT_LIMIT)
    if n < SPLIT_LIMIT:
        return ids
    if mindate >= maxdate:
        # A single day above the limit cannot be split by date; page within it.
        out = list(ids)
        while len(out) < n:
            params = _base_params()
            params.update({"term": term, "retmode": "json", "retmax": SPLIT_LIMIT, "retstart": len(out),
                           "datetype": datetype, "mindate": _fmt(mindate), "maxdate": _fmt(maxdate)})
            _, more, _ = parse_esearch(net.request(f"{EUTILS}/esearch.fcgi", data=params))
            if not more:
                break
            out.extend(more)
        return out
    mid = mindate + (maxdate - mindate) // 2
    left = ids_in_window(term, mindate, mid, datetype)
    right = ids_in_window(term, mid + timedelta(days=1), maxdate, datetype)
    return list(dict.fromkeys(left + right))


def fetch(pmids):
    """Fetch and parse records for the given PMIDs, 200 per POST."""
    out = []
    pmids = [str(p) for p in pmids]
    for i in range(0, len(pmids), FETCH_BATCH):
        batch = pmids[i:i + FETCH_BATCH]
        params = _base_params()
        params.update({"retmode": "xml", "id": ",".join(batch)})
        xml_text = net.request(f"{EUTILS}/efetch.fcgi", data=params, timeout=120)
        out.extend(parse_xml(xml_text))
    return out


def _text(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _date_from(el):
    if el is None:
        return None
    y = el.findtext("Year")
    if not y:
        md = el.findtext("MedlineDate") or ""
        m = re.match(r"(\d{4})", md)
        return f"{m.group(1)}-01-01" if m else None
    mo = el.findtext("Month") or "1"
    mo = MONTHS.get(mo[:3].lower(), None) if not mo.isdigit() else int(mo)
    dy = el.findtext("Day") or "1"
    try:
        return date(int(y), int(mo or 1), int(dy)).isoformat()
    except ValueError:
        return f"{int(y):04d}-01-01"


def _country(aff):
    if not aff:
        return None
    s = re.sub(r"\S+@\S+", "", aff).strip().rstrip(".").strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return None
    last = re.sub(r"\d+", "", parts[-1]).strip(" .;")
    return last or None


def extract_registry_ids(text):
    found = set()
    for name, pat in REGISTRY_PATTERNS.items():
        for m in pat.finditer(text or ""):
            val = m.group(1) if m.groups() else m.group(0)
            val = val.replace(" ", "")
            if name in ("EudraCT", "CTIS"):
                val = f"{name}:{val}"
            found.add(val)
    return found


CC_FLAGS = {
    "RetractionIn": "retracted",
    "ErratumIn": "erratum",
    "ExpressionOfConcernIn": "expression_of_concern",
    "UpdateIn": "updated",
}
CC_NOTICES = {"RetractionOf", "ErratumFor", "ExpressionOfConcernFor", "UpdateOf"}


def parse_xml(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for art in root.findall("PubmedArticle"):
        rec = parse_article(art)
        if rec:
            out.append(rec)
    return out


def parse_article(art):
    mc = art.find("MedlineCitation")
    a = mc.find("Article")
    pmid = mc.findtext("PMID")
    title = _text(a.find("ArticleTitle")) or _text(a.find("VernacularTitle"))
    parts = []
    for at in a.findall("Abstract/AbstractText"):
        label = at.get("Label")
        txt = _text(at)
        if txt:
            parts.append(f"{label}: {txt}" if label else txt)
    abstract = "\n".join(parts)
    authors = []
    countries = []
    for au in a.findall("AuthorList/Author"):
        if au.findtext("CollectiveName"):
            authors.append(au.findtext("CollectiveName").strip())
        else:
            ln = au.findtext("LastName") or ""
            ini = au.findtext("Initials") or ""
            if ln:
                authors.append(f"{ln} {ini}".strip())
        countries.append(_country(au.findtext("AffiliationInfo/Affiliation")))
    ids = {i.get("IdType"): (i.text or "").strip() for i in art.findall("PubmedData/ArticleIdList/ArticleId")}
    doi = normalise_doi(ids.get("doi"))
    if not doi:
        for el in a.findall("ELocationID"):
            if el.get("EIdType") == "doi":
                doi = normalise_doi(el.text)
    hist = {d.get("PubStatus"): _date_from(d) for d in art.findall("PubmedData/History/PubMedPubDate")}
    epub = None
    for ad in a.findall("ArticleDate"):
        if ad.get("DateType") == "Electronic":
            epub = _date_from(ad)
    journal = a.find("Journal")
    issns = sorted({(i.text or "").strip() for i in journal.findall("ISSN") if i.text}
                   | {(mc.findtext("MedlineJournalInfo/ISSNLinking") or "").strip()} - {""})
    pub_types = [_text(p) for p in a.findall("PublicationTypeList/PublicationType")]
    mesh = [_text(m.find("DescriptorName")) for m in mc.findall("MeshHeadingList/MeshHeading")]
    keywords = [_text(k) for k in mc.findall("KeywordList/Keyword") if _text(k)]
    registry = set()
    for db in mc.findall("Article/DataBankList/DataBank"):
        for acc in db.findall("AccessionNumberList/AccessionNumber"):
            if acc.text and acc.text.strip().upper().startswith(("NCT", "ISRCTN", "CHICTR")):
                registry.add(acc.text.strip())
    registry |= extract_registry_ids(abstract)
    flags = {}
    corrects = []
    for cc in mc.findall("CommentsCorrectionsList/CommentsCorrections"):
        rt = cc.get("RefType")
        if rt in CC_FLAGS:
            flags[CC_FLAGS[rt]] = cc.findtext("PMID") or True
        elif rt in CC_NOTICES and cc.findtext("PMID"):
            corrects.append({"type": rt, "pmid": cc.findtext("PMID")})
    if "Retracted Publication" in pub_types:
        flags.setdefault("retracted", True)
    lang = [l.text for l in a.findall("Language") if l.text]
    rec = {
        "id": str(pmid),
        "pmid": str(pmid),
        "doi": doi,
        "pmcid": ids.get("pmc") or None,
        "sources": ["pubmed"],
        "title": title,
        "abstract": abstract,
        "authors": (authors[:10] + ([authors[-1]] if len(authors) > 10 else [])),
        "n_authors": len(authors),
        "first_author_country": countries[0] if countries else None,
        "last_author_country": countries[-1] if countries else None,
        "journal": _text(journal.find("Title")),
        "journal_abbrev": mc.findtext("MedlineJournalInfo/MedlineTA") or journal.findtext("ISOAbbreviation"),
        "issns": issns,
        "pub_types": pub_types,
        "mesh": mesh,
        "keywords": keywords,
        "language": lang,
        "registry_ids": sorted(registry),
        "dates": {"entrez": hist.get("entrez") or hist.get("pubmed"),
                  "published": _date_from(journal.find("JournalIssue/PubDate")),
                  "epub": epub},
        "is_preprint": False,
        "flags": flags,
    }
    if corrects:
        rec["corrects"] = corrects
    return rec
