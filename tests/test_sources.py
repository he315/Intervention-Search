"""Parsers tested against responses recorded from the live APIs on 10 October 2026."""
import json
from pathlib import Path

from src.sources import pubmed, europepmc, medrxiv, crossref, ctgov, openalex, isrctn

FX = Path(__file__).parent / "fixtures"


def test_pubmed_esearch_parse():
    n, ids, warn = pubmed.parse_esearch((FX / "pubmed_esearch.json").read_text())
    assert n == 10 and len(ids) == 10 and warn == []
    assert "40139890" in ids


def test_pubmed_efetch_parse_fields():
    recs = {r["pmid"]: r for r in pubmed.parse_xml((FX / "pubmed_efetch.xml").read_text())}
    assert set(recs) == {"40139890", "34514494", "41139239"}
    r = recs["40139890"]
    assert r["id"] == "40139890"
    assert r["doi"] == "10.1016/j.jacc.2025.01.029"
    assert r["pmcid"] == "PMC12284807"
    assert r["dates"]["entrez"] == "2025-03-26"
    assert "Randomized Controlled Trial" in r["pub_types"]
    assert "NCT01471522" in r["registry_ids"]
    assert r["abstract"].startswith("BACKGROUND:")
    assert "RESULTS:" in r["abstract"]
    assert r["authors"] and " " in r["authors"][0]
    assert "0735-1097" in r["issns"]


def test_pubmed_corrections_flags():
    recs = {r["pmid"]: r for r in pubmed.parse_xml((FX / "pubmed_efetch.xml").read_text())}
    retracted = recs["41139239"]
    assert retracted["flags"]["retracted"] == "42153594"
    assert "retracted" not in recs["34514494"]["flags"]


def test_registry_regex():
    ids = pubmed.extract_registry_ids("Registered at ClinicalTrials.gov NCT01471522 and ISRCTN 70913605.")
    assert ids == {"NCT01471522", "ISRCTN70913605"}


def test_europepmc_preprint_parse():
    d = json.loads((FX / "europepmc_preprints.json").read_text())
    recs = [europepmc.parse_preprint(r) for r in d["resultList"]["result"]]
    assert all(r["is_preprint"] for r in recs)
    assert recs[0]["id"] == "doi:10.64898/2026.10.06.757199"
    assert recs[0]["preprint_id"] == "PPR1336059"
    assert recs[0]["journal"].endswith("(preprint)")


def test_europepmc_citation_counts_shape():
    d = json.loads((FX / "europepmc_cites.json").read_text())
    got = {r["id"]: r["citedByCount"] for r in d["resultList"]["result"]}
    assert got == {"40139890": 9, "34514494": 14}


def test_medrxiv_parse_keeps_cardiovascular_only():
    d = json.loads((FX / "medrxiv_details.json").read_text())
    recs = medrxiv.parse_items(d["collection"])
    assert len(recs) == 3
    assert all(r["sources"] == ["medrxiv"] and r["is_preprint"] for r in recs)
    # medRxiv moved to the 10.64898 DOI prefix in 2026; older posts keep 10.1101.
    assert {r["id"].split("/")[0] for r in recs} == {"doi:10.1101", "doi:10.64898"}


def test_crossref_journal_match_and_item_parse():
    payload = json.loads((FX / "crossref_journals.json").read_text())
    hits = crossref.match_journal(payload, "European Heart Journal")
    assert len(hits) == 1 and hits[0]["issn"] == ["0195-668X", "1522-9645"]
    works = json.loads((FX / "crossref_works.json").read_text())["message"]["items"]
    r = crossref.parse_item(works[0], "European Heart Journal", "target")
    assert r["id"] == "doi:10.1093/eurheartj/ehag749"
    assert r["journal_tier"] == "target"
    assert r["dates"]["epub"] == "2026-10-05"


def test_ctgov_parse_study():
    d = json.loads((FX / "ctgov_studies.json").read_text())
    t = ctgov.parse_study(d["studies"][0])
    assert t["nct"] == "NCT07687017"
    assert t["acronym"] == "CRP-SHOCK"
    assert t["allocation"] == "RANDOMIZED"
    assert t["enrolment"] == 50
    assert t["primary_completion"] == "2027-09-30"
    assert t["primary_outcomes"][0]["measure"] == "CLIP score"


def test_openalex_budget_error_is_detected():
    err = openalex.parse_error((FX / "openalex_budget_exhausted.json").read_text())
    assert err and "budget" in err["message"].lower()


def test_isrctn_parse():
    trials = isrctn.parse((FX / "isrctn_query.xml").read_text())
    assert trials[0]["isrctn"] == "ISRCTN10183174"
    assert trials[0]["completion"] == "2027-06-01"
