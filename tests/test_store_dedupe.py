from pathlib import Path

from src import store, dedupe, classify
from src.pipeline import Ingestor
from src.sources import pubmed, crossref
import json

FX = Path(__file__).parent / "fixtures"


def _pubmed_records():
    return pubmed.parse_xml((FX / "pubmed_efetch.xml").read_text())


def test_normalise_doi():
    assert dedupe.normalise_doi("https://doi.org/10.1016/J.JACC.2025.01.029.") == "10.1016/j.jacc.2025.01.029"
    assert dedupe.normalise_doi("doi: 10.1093/eurheartj/ehab509") == "10.1093/eurheartj/ehab509"
    assert dedupe.normalise_doi("not a doi") is None


def test_record_id_order():
    assert dedupe.record_id(pmid="123", doi="10.1/x") == "123"
    assert dedupe.record_id(doi="10.1/X") == "doi:10.1/x"
    assert dedupe.record_id(preprint_id="PPR1") == "ppr:PPR1"


def test_preprint_title_match():
    a = {"title": "Ticagrelor monotherapy after PCI in high-risk patients", "authors": ["Smith J"]}
    b = {"title": "Ticagrelor Monotherapy After PCI in High-Risk Patients.", "authors": ["Smith JA"]}
    c = {"title": "Ticagrelor monotherapy after PCI in high-risk patients", "authors": ["Jones K"]}
    assert dedupe.is_preprint_match(a, b)
    assert not dedupe.is_preprint_match(a, c)


def test_merge_is_idempotent_and_preserves_appraisal(tmp_repo):
    idx = store.Index()
    idx.rebuild()
    recs = _pubmed_records()
    n_new, n_upd = store.merge_records([dict(r) for r in recs], idx)
    assert n_new == 3 and n_upd == 0
    store.update_records({"40139890": {"tier": "B", "appraisal": {"one_line": "x"}}}, idx)
    n_new, n_upd = store.merge_records([dict(r) for r in recs], idx)
    assert n_new == 0
    got = store.get_records(["40139890"], idx)["40139890"]
    assert got["tier"] == "B" and got["appraisal"]["one_line"] == "x"
    files = store.all_partition_files()
    assert all(f.name.endswith(".jsonl") for f in files)
    total = sum(len(store.read_partition(f)) for f in files)
    assert total == 3


def test_gzip_partition_round_trip(tmp_repo):
    idx = store.Index()
    idx.rebuild()
    store.merge_records([dict(r) for r in _pubmed_records()], idx)
    changed = store.gzip_old_partitions(months=12)
    assert changed  # the 2021 and 2025 partitions are more than 12 months old
    idx2 = store.Index()
    assert idx2.rebuild() == 3
    assert store.get_records(["34514494"], idx2)["34514494"]["pmid"] == "34514494"


def test_crossref_record_links_to_pubmed_record(tmp_repo):
    idx = store.Index()
    idx.rebuild()
    log = []
    ing = Ingestor(idx, log)
    cr = {"id": "doi:10.1016/j.jacc.2025.01.029", "pmid": None, "doi": "10.1016/j.jacc.2025.01.029",
          "sources": ["crossref"], "title": "Invasive vs Conservative Management of Patients With Chronic Total Occlusion",
          "abstract": "", "authors": [], "journal": "JACC", "pub_types": ["journal-article"], "dates": {"entrez": "2025-03-20"},
          "is_preprint": False, "flags": {}, "domains": ["D1"]}
    ing.ingest([cr])
    ing.ingest([dict(r) for r in _pubmed_records() if r["pmid"] == "40139890"], domain="D1")
    both = store.get_records(["doi:10.1016/j.jacc.2025.01.029", "40139890"], idx)
    assert both["doi:10.1016/j.jacc.2025.01.029"]["flags"]["duplicate_of"] == "40139890"
    assert "D1" in both["40139890"]["domains"]


def test_classify_design_and_prescreen():
    recs = {r["pmid"]: r for r in _pubmed_records()}
    r = classify.classify(dict(recs["40139890"], domains=["D1"]))
    assert r["design"] == "rct_secondary"  # "Results From the ISCHEMIA Trial"
    note = {"title": "Erratum: something", "abstract": "", "pub_types": ["Published Erratum"]}
    assert classify.classify_design(note) == "editorial_letter_comment"
    assert classify.prescreen_tier(dict(note, design="editorial_letter_comment")) == "D"
    ma = {"title": "Drug-coated balloons: a network meta-analysis", "abstract": "We pooled 20 trials.", "pub_types": []}
    assert classify.classify_design(ma) == "nma"


def test_text_domains():
    rec = {"title": "Microaxial flow pump in infarct-related cardiogenic shock", "abstract": ""}
    assert "D2" in classify.text_domains(rec)
    rec = {"title": "Retinal detachment surgery outcomes", "abstract": ""}
    assert classify.text_domains(rec) == []
