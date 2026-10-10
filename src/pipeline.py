"""Fetching, ingestion and the corrections sweep shared by daily and baseline runs."""
import json
from datetime import date, timedelta

from . import config, store, state as st, appraise, net
from .classify import classify, text_domains
from .dedupe import normalise_doi, is_preprint_match, title_tokens, first_author_surname
from .sources import pubmed, europepmc, medrxiv, crossref, ctgov

PREPRINT_PHRASES = [
    "percutaneous coronary", "coronary stent", "drug-eluting stent", "drug-coated balloon", "fractional flow reserve",
    "chronic total occlusion", "left main", "coronary bifurcation", "intravascular ultrasound", "optical coherence tomography",
    "cardiogenic shock", "Impella", "microaxial", "extracorporeal membrane oxygenation", "ECMO", "intra-aortic balloon",
    "mechanical circulatory support", "cardiac arrest", "TAVI", "TAVR", "transcatheter aortic", "aortic stenosis",
    "mitral regurgitation", "edge-to-edge", "tricuspid regurgitation", "STEMI", "NSTEMI", "acute coronary syndrome",
    "myocardial infarction", "unstable angina", "MINOCA", "coronary artery dissection", "no-reflow", "myocardial injury",
    "troponin", "clopidogrel", "ticagrelor", "prasugrel", "antiplatelet", "P2Y12", "dual antiplatelet",
    "left atrial appendage", "patent foramen ovale", "pulmonary embolism", "renal denervation", "interatrial shunt",
    "coronary sinus reducer",
]


def preprint_query(start, end):
    phrases = " OR ".join(f'TITLE_ABS:"{p}"' for p in PREPRINT_PHRASES)
    return f"(SRC:PPR) AND ({phrases}) AND (FIRST_IDATE:[{start.isoformat()} TO {end.isoformat()}])"


class Ingestor:
    """Classifies, deduplicates and merges records into the store."""

    def __init__(self, index, log):
        self.index = index
        self.log = log
        self._preprints = None

    def _load_preprints(self):
        if self._preprints is None:
            rows = self.index.query("SELECT id FROM rec WHERE is_preprint=1 AND (dup_of IS NULL)")
            recs = store.get_records([r[0] for r in rows], self.index) if rows else {}
            self._preprints = {rid: (title_tokens(r.get("title")), first_author_surname(r), r)
                               for rid, r in recs.items() if not r.get("published_as_id")}
        return self._preprints

    def ingest(self, records, domain=None, baseline=False):
        """Returns (n_new, n_updated, new_ids)."""
        keep, side_updates = [], {}
        for r in records:
            if domain:
                r["domains"] = sorted(set(r.get("domains") or []) | {domain})
            classify(r)
            if not r.get("domains"):
                continue  # out of scope for every domain
            if baseline:
                r["baseline"] = True
            nd = normalise_doi(r.get("doi"))
            if not r.get("pmid") and nd:
                existing = self.index.id_for_doi(nd)
                if existing and existing != r["id"]:
                    # Already held under its PMID: record the extra source only.
                    side_updates.setdefault(existing, {})["extra_source"] = r["sources"][0]
                    continue
            if r.get("pmid") and nd:
                existing = self.index.id_for_doi(nd)
                if existing and existing != r["id"] and existing.startswith("doi:"):
                    side_updates.setdefault(existing, {}).update({"flags": {"duplicate_of": r["id"]}})
                    self.log.append(f"linked {existing} to PubMed record {r['id']} by DOI")
            keep.append(r)
        # preprint linkage
        pp = None
        for r in keep:
            if r.get("is_preprint"):
                pub = r.get("published_as")
                if pub:
                    target = self.index.id_for_doi(pub)
                    if target:
                        r["published_as_id"] = target
                        side_updates.setdefault(target, {})["preprint_of"] = r["id"]
            elif r.get("pmid"):
                pp = pp if pp is not None else self._load_preprints()
                toks, sur = title_tokens(r.get("title")), first_author_surname(r)
                for pid, (ptoks, psur, prec) in pp.items():
                    if psur and psur == sur and is_preprint_match(prec, r):
                        r["preprint_of"] = pid
                        side_updates.setdefault(pid, {})["published_as_id"] = r["id"]
                        self.log.append(f"linked preprint {pid} to {r['id']} by title similarity and first author")
                        break
        n_new, n_upd = store.merge_records(keep, self.index)
        if side_updates:
            ups = {}
            current = store.get_records(list(side_updates), self.index)
            for rid, u in side_updates.items():
                if rid not in current:
                    continue
                up = {}
                if "extra_source" in u:
                    up["sources"] = sorted(set(current[rid].get("sources") or []) | {u["extra_source"]})
                for k in ("flags", "preprint_of", "published_as_id"):
                    if k in u:
                        up[k] = u[k]
                if up:
                    ups[rid] = up
            store.update_records(ups, self.index)
        self.index.commit()
        return n_new, n_upd, [r["id"] for r in keep]


def health_check():
    """One small live call per source. Returns {source: "ok" | error text}."""
    checks = {
        "pubmed": lambda: pubmed.count('"cardiogenic shock"[ti]', date.today() - timedelta(days=30), date.today()),
        "europepmc": lambda: net.request(f"{europepmc.BASE}/search", params={"query": "SRC:PPR AND TITLE:\"stent\"", "format": "json", "pageSize": 1}),
        "medrxiv": lambda: net.request(f"{medrxiv.BASE}/{(date.today() - timedelta(days=2)).isoformat()}/{date.today().isoformat()}/0"),
        "crossref": lambda: net.request(f"{crossref.BASE}/journals/0195-668X", params={}),
        "ctgov": lambda: net.request(f"{ctgov.BASE}/version"),
    }
    out = {}
    for name, fn in checks.items():
        try:
            fn()
            out[name] = "ok"
        except net.NetworkBlocked as e:
            out[name] = f"blocked: {e.reason}"
        except Exception as e:  # report and continue with the other sources
            out[name] = f"error: {str(e)[:200]}"
    return out


def fetch_pubmed_domain(s, ing, domain, today, baseline=False):
    q = config.queries()[domain]
    start = st.window_start(s, "pubmed", domain)
    ids = pubmed.ids_in_window(q, start, today)
    recs = pubmed.fetch(ids) if ids else []
    n_new, n_upd, kept = ing.ingest(recs, domain=domain, baseline=baseline)
    return {"window": [start.isoformat(), today.isoformat()], "retrieved": len(ids), "new": n_new, "updated": n_upd, "ids": kept}


def fetch_corrections(s, ing, today):
    """Retraction, erratum and concern notices in the window, applied to stored records."""
    start = st.window_start(s, "pubmed", "corrections")
    term = ('"Retraction of Publication"[pt] OR "Published Erratum"[pt] OR "Expression of Concern"[pt] '
            'OR "Retracted Publication"[pt]')
    ids = pubmed.ids_in_window(term, start, today)
    recs = pubmed.fetch(ids) if ids else []
    flags = {}
    for r in recs:
        for c in r.get("corrects") or []:
            kind = {"RetractionOf": "retracted", "ErratumFor": "erratum", "ExpressionOfConcernFor": "expression_of_concern",
                    "UpdateOf": "updated"}.get(c["type"])
            if kind:
                flags.setdefault(c["pmid"], {})[kind] = r["pmid"]
        if "Retracted Publication" in (r.get("pub_types") or []):
            flags.setdefault(r["pmid"], {})["retracted"] = True
    alerts, ups = [], {}
    held = store.get_records([p for p in flags if ing.index.has(p)], ing.index)
    for pmid, fl in flags.items():
        rec = held.get(pmid)
        if not rec:
            continue
        new = {k: v for k, v in fl.items() if not (rec.get("flags") or {}).get(k)}
        if not new:
            continue
        ups[pmid] = {"flags": new}
        if rec.get("tier") == "A" or rec.get("question_ids"):
            alerts.append({"pmid": pmid, "flags": new, "title": rec.get("title"), "tier": rec.get("tier"),
                           "questions": rec.get("question_ids") or []})
    if ups:
        store.update_records(ups, ing.index)
        ing.index.commit()
    return {"window": [start.isoformat(), today.isoformat()], "notices": len(recs), "flagged": len(ups), "alerts": alerts}


def fetch_preprints(s, ing, today):
    start = st.window_start(s, "europepmc", "preprints")
    q = preprint_query(start, today)
    recs = [europepmc.parse_preprint(r) for r in europepmc.search(q, result_type="core", page_size=500, max_pages=20)]
    n_new, n_upd, kept = ing.ingest(recs)
    return {"window": [start.isoformat(), today.isoformat()], "retrieved": len(recs), "new": n_new, "updated": n_upd, "ids": kept}


def fetch_medrxiv(s, ing, today):
    start = st.window_start(s, "medrxiv", None)
    items = medrxiv.fetch_window(start, today)
    recs = medrxiv.parse_items(items)
    n_new, n_upd, kept = ing.ingest(recs)
    return {"window": [start.isoformat(), today.isoformat()], "retrieved": len(recs), "new": n_new, "updated": n_upd, "ids": kept}


def fetch_crossref(s, ing, today):
    start = st.window_start(s, "crossref", None)
    js = config.journals().get("journals", [])
    total, kept_all, new_all = 0, [], 0
    for j in js:
        if not j.get("issn"):
            continue
        items = crossref.works(j["issn"][0], start, today)
        total += len(items)
        recs = [x for x in (crossref.parse_item(it, j["name"], j["tier"]) for it in items) if x]
        recs = [r for r in recs if text_domains(r)]
        n_new, _, kept = ing.ingest(recs)
        new_all += n_new
        kept_all += kept
    return {"window": [start.isoformat(), today.isoformat()], "retrieved": total, "new": new_all, "ids": kept_all}
