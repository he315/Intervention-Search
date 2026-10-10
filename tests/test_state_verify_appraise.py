import json
from datetime import date
from pathlib import Path

from src import state as st, verify_citations, appraise, register, store, owner, config
from src.sources import pubmed

FX = Path(__file__).parent / "fixtures"


def test_watermark_window_and_cadence(tmp_repo):
    s = st.load()
    assert s["schema_version"] == 1
    s["baseline"]["start_date"] = "2026-10-10"
    assert st.window_start(s, "pubmed", "D1") == date(2026, 10, 7)
    st.set_watermark(s, "pubmed", "D1", date(2026, 10, 12))
    st.save(s)
    s2 = st.load()
    assert st.window_start(s2, "pubmed", "D1") == date(2026, 10, 9)
    assert st.weekly_due(s2, date(2026, 10, 12))
    s2["last_runs"]["weekly"] = st.iso_week(date(2026, 10, 12))
    assert not st.weekly_due(s2, date(2026, 10, 14))
    assert not st.monthly_due(s2, date(2026, 11, 1))   # first Monday of November 2026 is the 2nd
    assert st.monthly_due(s2, date(2026, 11, 2))
    assert st.first_monday(2026, 11) == date(2026, 11, 2)


def test_verify_detects_unknown_identifiers(tmp_repo, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_repo)
    idx = store.Index()
    idx.rebuild()
    store.merge_records(pubmed.parse_xml((FX / "pubmed_efetch.xml").read_text()), idx)
    (tmp_repo / "outputs").mkdir()
    (tmp_repo / "outputs" / "x.md").write_text(
        "Known PMID 40139890 and DOI 10.1016/j.jacc.2025.01.029. Unknown PMID 99999999 and NCT00000001.\n", encoding="utf-8")
    problems = verify_citations.check(idx)
    assert any("99999999" in p for p in problems)
    assert any("NCT00000001" in p for p in problems)
    assert not any("40139890" in p for p in problems)
    (tmp_repo / "outputs" / "x.md").write_text("A sentence with an em dash — here.\n", encoding="utf-8")
    assert any("em dash" in p for p in verify_citations.check(idx))


def test_verify_extracts_lists_of_pmids():
    pm, dois, ncts = verify_citations.extract("PMIDs 12345678, 23456789 and 34567890; see NCT01471522.")
    assert pm == {"12345678", "23456789", "34567890"} and ncts == {"NCT01471522"}


def test_appraisal_import_rejects_numbers_not_in_abstract(tmp_repo):
    idx = store.Index()
    idx.rebuild()
    recs = pubmed.parse_xml((FX / "pubmed_efetch.xml").read_text())
    store.merge_records(recs, idx)
    rec = [r for r in recs if r["pmid"] == "40139890"][0]
    appraise.queue([rec])
    good_numbers = [n for n in appraise._numbers(rec["abstract"]) if "." in n][:2]
    good = {"id": "40139890", "tier": "B", "appraisal": {
        "one_line": "x", "design_and_n": "Secondary analysis of an RCT", "primary_result_as_reported": " ".join(good_numbers),
        "main_limitation": "y", "why_it_matters": "z"}}
    bad = {"id": "34514494", "tier": "A", "appraisal": {
        "one_line": "x", "design_and_n": "RCT", "primary_result_as_reported": "HR 0.123456 (95% CI 0.1111 to 0.2222)",
        "main_limitation": "y", "why_it_matters": "z"}}
    appraise.RESULTS.parent.mkdir(parents=True, exist_ok=True)
    appraise.RESULTS.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n")
    n, errs = appraise.import_results(idx, appraise.RESULTS)
    assert n == 1
    assert any("0.123456" in e for e in errs)
    got = store.get_records(["40139890", "34514494"], idx)
    assert got["40139890"]["tier"] == "B" and got["40139890"]["tier_method"] == "model"
    assert not got["34514494"].get("tier")
    assert all(x["id"] != "40139890" for x in appraise.load_backlog())


def test_register_composite_gates_and_owner_decisions(tmp_repo):
    q = {"id": "Q-001", "title": "t", "domains": ["D2"], "status": "candidate",
         "gates": {g: {"pass": True, "note": ""} for g in register.GATES},
         "scores": {k: {"score": 5, "why": ""} for k in register.WEIGHTS}}
    assert register.composite(q) == 100.0
    q2 = dict(q, id="Q-002", scores={k: {"score": 3, "why": ""} for k in register.WEIGHTS})
    q3 = dict(q, id="Q-003", gates={**q["gates"], "G3": {"pass": False, "note": "trial due"}})
    assert [x["id"] for x in register.ranked([q, q2, q3])] == ["Q-001", "Q-002"]
    d = owner.parse("Q-002: drop, outside my interests")
    assert d == {"kind": "status", "qid": "Q-002", "status": "parked", "reason": "outside my interests",
                 "text": "Q-002: drop, outside my interests"}
    msg = register.apply_owner_decision([q, q2, q3], d, "2026-10-10")
    assert "parked" in msg and q2["status"] == "parked"
    assert owner.parse("Q-003: merge with Q-001")["into"] == "Q-001"
    assert owner.parse("lower weight: D9")["factor"] == 0.8
    assert owner.parse("something vague") is None
