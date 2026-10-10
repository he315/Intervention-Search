"""Resolve journal ISSNs once through Crossref and store them in config/journals.json.

ISSNs are never typed from memory: each journal title is looked up in
Crossref's journal search and only an exact (normalised) title match is kept.
"""
from . import config
from .sources import crossref

TIERS = {
    "target": ["European Heart Journal", "Circulation", "Journal of the American College of Cardiology", "JAMA Cardiology"],
    "general": ["New England Journal of Medicine", "The Lancet", "JAMA", "BMJ", "Nature Medicine"],
    "specialty": ["EuroIntervention", "JACC: Cardiovascular Interventions", "Circulation: Cardiovascular Interventions",
                  "European Heart Journal: Acute Cardiovascular Care", "Intensive Care Medicine", "Resuscitation", "Heart",
                  "Catheterization and Cardiovascular Interventions",
                  "Journal of the Society for Cardiovascular Angiography & Interventions", "JACC: Heart Failure",
                  "European Journal of Heart Failure"],
}
# Alternative spellings tried when the canonical title has no exact match in Crossref.
ALIASES = {
    "European Heart Journal: Acute Cardiovascular Care": ["European Heart Journal. Acute Cardiovascular Care"],
    "JAMA": ["JAMA: The Journal of the American Medical Association", "Journal of the American Medical Association"],
    "BMJ": ["The BMJ", "BMJ (Clinical research ed.)"],
    "The Lancet": ["Lancet"],
    "Journal of the Society for Cardiovascular Angiography & Interventions":
        ["Journal of the Society for Cardiovascular Angiography and Interventions"],
}


# Search strings used when the exact title does not rank in Crossref's results.
SEARCH_STRINGS = {
    "Journal of the Society for Cardiovascular Angiography & Interventions":
        "Society for Cardiovascular Angiography Interventions",
}


def resolve():
    out, log = [], []
    for tier, names in TIERS.items():
        for name in names:
            hits = []
            for candidate in [name] + ALIASES.get(name, []):
                hits = crossref.find_journal(candidate)
                if hits:
                    break
            if not hits and name in SEARCH_STRINGS:
                hits = crossref.find_journal(name, query=SEARCH_STRINGS[name])
            if not hits:
                log.append(f"{name}: no exact Crossref title match; ISSN unresolved")
                out.append({"name": name, "tier": tier, "issn": [], "crossref_title": None, "status": "unresolved"})
                continue
            issns = sorted({i for h in hits for i in h["issn"]})
            out.append({"name": name, "tier": tier, "issn": issns, "crossref_title": hits[0]["title"],
                        "publisher": hits[0].get("publisher"), "status": "resolved"})
            log.append(f"{name}: {', '.join(issns)} (Crossref title '{hits[0]['title']}')")
    config.save_json(config.CONFIG / "journals.json", {
        "resolved_on": config.iso_date(config.london_today()), "method": "Crossref /journals exact title match",
        "journals": out})
    return log
