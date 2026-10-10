"""Single entry point: python -m src.run <command>.

Commands run non-interactively and each finishes within about eight minutes
(long jobs take --minutes and resume from state/state.json).

The daily cycle has two halves because appraisal is done by the session:
    python -m src.run daily          fetch, classify, corrections, trials, queue and export a batch
    (session appraises state/appraisal_batch.jsonl into state/appraisal_results.jsonl)
    python -m src.run daily-finish   import appraisals, write the digest, README, run log and verify
"""
import argparse
import json
import sys
import time
import traceback
from datetime import date, timedelta

from . import config, store, state as st, appraise, register, owner, outputs, trials, verify_citations, net
from . import pipeline, baseline as baseline_mod, trends, validate
from .sources import pubmed, europepmc, openalex


def _index(rebuild=True):
    idx = store.Index()
    if rebuild:
        idx.rebuild()
    return idx


def _log_decision(text):
    p = config.LOGS / "decisions.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"- {config.iso_date(config.london_today())}: {text}\n")


def _log_error(text):
    p = config.LOGS / "errors.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("# Errors log\n\nNotes for the next run. Each entry: date, what failed, what to try first.\n\n", encoding="utf-8")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"- {config.london_now().strftime('%Y-%m-%d %H:%M')}: {text}\n")


def apply_owner_decisions(s, today):
    questions = register.load()
    todo, bad = owner.pending(s)
    for d in todo:
        if d["kind"] == "add_tag":
            s["extra_tags"] = sorted(set(s.get("extra_tags") or []) | {d["tag"]})
            msg = f"owner decision applied: added tag '{d['tag']}'"
        elif d["kind"] == "weight":
            s.setdefault("domain_weights", {})[d["domain"]] = d["factor"]
            msg = f"owner decision applied: weight {d['factor']} for {d['domain']}"
        else:
            msg = register.apply_owner_decision(questions, d, today.isoformat())
        _log_decision(msg)
        s.setdefault("owner_decisions_applied", []).append(d["key"])
    if todo:
        register.save(questions)
    return [d["text"] for d in todo], bad


# ---- daily -------------------------------------------------------------------------------
def cmd_daily(args):
    t0 = time.monotonic()
    today = config.london_today()
    s = st.load()
    run = {"kind": "daily", "date": today.isoformat(), "started_london": config.london_now().strftime("%Y-%m-%d %H:%M"),
           "warnings": [], "sources": {}, "status": "OK"}
    idx = _index()
    run["health"] = pipeline.health_check()
    s["source_health"] = run["health"]
    applied, bad = apply_owner_decisions(s, today)
    run["owner_decisions_applied"], run["unparsed_decisions"] = applied, bad
    log = []
    ing = pipeline.Ingestor(idx, log)
    new_ids = []
    ok = run["health"]
    if ok.get("pubmed") == "ok":
        for d in config.DOMAINS:
            try:
                res = pipeline.fetch_pubmed_domain(s, ing, d, today)
                new_ids += res.pop("ids")
                run["sources"][f"pubmed:{d}"] = res
                st.set_watermark(s, "pubmed", d, today)
            except Exception as e:
                run["warnings"].append(f"PubMed {d} fetch failed: {e}")
                _log_error(f"PubMed {d} fetch failed: {e}. Watermark not advanced.")
        try:
            res = pipeline.fetch_corrections(s, ing, today)
            run["correction_alerts"] = res.pop("alerts")
            run["sources"]["pubmed:corrections"] = res
            st.set_watermark(s, "pubmed", "corrections", today)
        except Exception as e:
            run["warnings"].append(f"Corrections sweep failed: {e}")
    for name, fn, key in (("europepmc", pipeline.fetch_preprints, ("europepmc", "preprints")),
                          ("medrxiv", pipeline.fetch_medrxiv, ("medrxiv", None)),
                          ("crossref", pipeline.fetch_crossref, ("crossref", None))):
        if ok.get(name) != "ok":
            continue
        try:
            res = fn(s, ing, today)
            new_ids += res.pop("ids")
            run["sources"][name] = res
            st.set_watermark(s, key[0], key[1], today)
        except Exception as e:
            run["warnings"].append(f"{name} fetch failed: {e}")
            _log_error(f"{name} fetch failed: {e}. Watermark not advanced.")
    if ok.get("ctgov") == "ok":
        try:
            start = st.window_start(s, "ctgov", None)
            run["sources"]["ctgov"] = trials.delta_update(start, today)
            st.set_watermark(s, "ctgov", None, today)
        except Exception as e:
            run["warnings"].append(f"ClinicalTrials.gov update failed: {e}")
    failed = [k for k, v in ok.items() if v != "ok"]
    if failed:
        run["status"] = "DEGRADED"
        run["status_reason"] = "source failure: " + ", ".join(failed)
    new_ids = sorted(set(new_ids))
    recs = store.get_records(new_ids, idx)
    todays = [r for r in recs.values() if r.get("first_seen") == today.isoformat()
              and (not r.get("baseline") or ((r.get("dates") or {}).get("entrez") or "") >= (today - timedelta(days=7)).isoformat())]
    run["new_record_ids"] = sorted(r["id"] for r in todays)
    # anomaly checks
    n_pub = sum(v.get("new", 0) for k, v in run["sources"].items() if k.startswith("pubmed:D"))
    if today.weekday() < 5 and ok.get("pubmed") == "ok" and n_pub == 0:
        run["warnings"].append("Zero new PubMed records on a weekday; query self-check recommended.")
    hist = [json.loads(l) for l in (config.LOGS / "runs.jsonl").read_text().splitlines() if l.strip()] if (config.LOGS / "runs.jsonl").exists() else []
    recent = sorted(h.get("n_new", 0) for h in hist[-28:] if h.get("kind") == "daily")
    if recent:
        med = recent[len(recent) // 2]
        if med and len(todays) > 3 * med:
            run["warnings"].append(f"New-record count {len(todays)} is above three times the 28-run median ({med}); query self-check recommended.")
    # register scoop candidates and appraisal queue
    questions = register.load()
    cands = register.scoop_candidates(questions, todays)
    config.save_json(config.STATE / "register_candidates.json", cands)
    appraise.queue(todays)
    n_batch = appraise.export_batch(idx, limit=args.limit, candidates=cands)
    run["batch"] = n_batch
    run["backlog_after_export"] = len(appraise.load_backlog())
    run["seconds_fetch"] = round(time.monotonic() - t0, 1)
    st.save(s)
    config.save_json(config.STATE / "last_daily.json", run)
    print(json.dumps({k: run[k] for k in ("status", "health", "batch", "backlog_after_export", "warnings")}, indent=1))
    print(f"New records today: {len(todays)}. Appraise the {n_batch} records in state/appraisal_batch.jsonl, write "
          "state/appraisal_results.jsonl, then run: python -m src.run daily-finish")
    return 0


def cmd_daily_finish(args):
    today = config.london_today()
    s = st.load()
    idx = _index()
    run = config.load_json(config.STATE / "last_daily.json", {})
    if run.get("date") != today.isoformat():
        print("No fetch phase recorded for today; run python -m src.run daily first.")
        return 1
    applied, errors = (0, [])
    if appraise.RESULTS.exists():
        applied, errors = appraise.import_results(idx)
        for e in errors:
            print("appraisal rejected:", e)
        if errors:
            run.setdefault("warnings", []).append(f"{len(errors)} appraisal entries were rejected by validation and stay in the backlog.")
    run["appraisals_applied"] = applied
    recs = list(store.get_records(run.get("new_record_ids") or [], idx).values())
    questions = register.load()
    # link records to questions from appraisal results
    for r in recs:
        for qid in r.get("question_ids") or []:
            for q in questions:
                if q["id"] == qid:
                    q.setdefault("audit", []).append({"date": today.isoformat(), "change": f"linked record {r['id']}"})
    if any(r.get("question_ids") for r in recs):
        register.save(questions)
    n_a = sum(1 for r in recs if r.get("tier") == "A")
    run["n_new"] = len(recs)
    run["tier_counts"] = {t: sum(1 for r in recs if r.get("tier") == t) for t in config.TIERS}
    run["tier_counts"]["untiered"] = sum(1 for r in recs if not r.get("tier"))
    run["finished_london"] = config.london_now().strftime("%Y-%m-%d %H:%M")
    outputs.write_daily(run, recs, idx, questions, today)
    s["last_runs"]["daily"] = today.isoformat()
    st.save(s)
    config.save_json(config.STATE / "last_run.json", run)
    outputs.readme(idx, questions, s, today, run)
    problems = verify_citations.check(idx)
    run["verify_problems"] = len(problems)
    for p in problems:
        print("verify:", p)
    with open(config.LOGS / "runs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "daily", "date": today.isoformat(), "started": run.get("started_london"),
                             "finished": run["finished_london"], "status": run.get("status"), "health": run.get("health"),
                             "sources": run.get("sources"), "n_new": len(recs), "tiers": run["tier_counts"],
                             "warnings": run.get("warnings"), "verify_problems": len(problems)}) + "\n")
    print(f"daily-finish: {len(recs)} new records, Tier A {n_a}, appraisals applied {applied}, verify problems {len(problems)}")
    return 1 if problems else 0


# ---- periodic ------------------------------------------------------------------------------
def cmd_weekly(args):
    today = config.london_today()
    s = st.load()
    idx = _index()
    if not args.no_snapshot:
        try:
            snap = trials.full_snapshot()
            n = trials.write_snapshot(snap, today)
            print(f"trial snapshot: {len(snap)} studies, {n} changes")
        except Exception as e:
            print("trial snapshot failed:", e)
            _log_error(f"weekly trial snapshot failed: {e}")
    questions = register.load()
    wk, md = outputs.weekly(idx, questions, today)
    config.atomic_write_text(config.OUTPUTS / "weekly" / f"{wk}.md", md)
    register.render_priorities_md(questions, outputs.prose_date(today), s.get("domain_weights"))
    register.render_questions_md(questions, outputs.prose_date(today))
    outputs.write_calendar(today)
    s["last_runs"]["weekly"] = wk
    st.save(s)
    print(f"weekly report written: outputs/weekly/{wk}.md")
    return 0


def cmd_monthly(args):
    today = config.london_today()
    s = st.load()
    idx = _index()
    key = f"{today.year:04d}-{today.month:02d}"
    if args.maintenance:
        changed = store.gzip_old_partitions(12)
        print(f"gzipped {len(changed)} partitions")
        idx = _index()
        refresh_citations(idx, tier="A")
        rec = validate.recall()
        config.save_json(config.DATA / "validation" / f"recall_{today.isoformat()}.json", rec)
        print("recall:", {d: r["recall"] for d, r in rec.items()})
        comp = completeness(idx, today)
        config.save_json(config.DATA / "validation" / f"completeness_{today.isoformat()}.json", comp)
        print("completeness:", comp["summary"])
        trends.update(recount_recent_months=6, deadline=time.monotonic() + 6 * 60)
        return 0
    narrative = config.load_json(config.STATE / "monthly_narrative.json", {})
    if narrative.get("month") != key:
        print(f"state/monthly_narrative.json for {key} is missing; write it (see CLAUDE.md appendix) and re-run.")
        return 1
    md = monthly_report(idx, register.load(), s, today, narrative)
    config.atomic_write_text(config.OUTPUTS / "monthly" / f"{key}.md", md)
    s["last_runs"]["monthly"] = key
    if st.quarterly_due(s, today) is False and today.month in (1, 4, 7, 10) and args.quarterly_done:
        s["last_runs"]["quarterly"] = st.quarter_key(today)
    st.save(s)
    print(f"monthly report written: outputs/monthly/{key}.md")
    return 0


def monthly_report(idx, questions, s, today, narrative):
    key = f"{today.year:04d}-{today.month:02d}"
    pd = outputs.prose_date
    lines = [f"# Monthly research ideas report, {outputs.MONTH_NAMES[today.month - 1]} {today.year}", "",
             f"Rendered {pd(today)}.", ""]
    if narrative.get("summary"):
        lines += ["## Summary", "", narrative["summary"].strip(), ""]
    r = register.ranked(questions, s.get("domain_weights"))
    lines += ["## Top ten after re-scoring", ""]
    for i, q in enumerate(r[:10], start=1):
        lines.append(f"{i}. {q['id']}: {q.get('title')} (composite {register.composite(q, s.get('domain_weights'))}; brief: register/briefs/{q['id']}.md)")
    lines += ["", "## New ideas this month", ""]
    new = [q for q in questions if (q.get("created") or "")[:7] == key]
    lines += [f"- {q['id']}: {q.get('title')}" for q in new] or ["None."]
    lines += ["", "## Questions parked, scooped, answered or merged this month", ""]
    gone = [(q, h) for q in questions for h in q.get("status_history") or []
            if h["date"][:7] == key and h["status"] in register.INACTIVE]
    lines += [f"- {q['id']}: {q.get('title')}. {h['status'].capitalize()}: {h['reason']}" for q, h in gone] or ["None."]
    lines += ["", "## Trends by domain", ""]
    for d in config.DOMAINS:
        txt = (narrative.get("domain_narratives") or {}).get(d)
        if txt:
            lines += [f"### {d} {config.DOMAIN_NAMES[d]}", "", txt.strip(), ""]
    val = narrative.get("validation")
    if val:
        lines += ["## Validation of the domain queries", "", val.strip(), ""]
    return "\n".join(lines)


def refresh_citations(idx, tier="A", ids=None):
    if ids is None:
        rows = idx.query("SELECT id FROM rec WHERE tier=?", (tier,))
        ids = [r[0] for r in rows]
    recs = list(store.get_records(ids, idx).values())
    counts, source = openalex.citation_counts(recs)
    today = config.iso_date(config.london_today())
    store.update_records({rid: {"citations": {"count": n, "source": source, "date": today}} for rid, n in counts.items()}, idx)
    idx.commit()
    if source != "openalex":
        _log_decision(f"citation counts for {len(counts)} records came from Europe PMC because OpenAlex was unavailable without a key")
    return counts, source


def completeness(idx, today, days=90):
    """Core-journal completeness: Crossref items in target and general journals that PubMed has indexed must be in the store."""
    from .sources import crossref
    from .classify import text_domains
    start = today - timedelta(days=days)
    out = {"window": [start.isoformat(), today.isoformat()], "journals": {}, "missing": []}
    for j in config.journals().get("journals", []):
        if j["tier"] not in ("target", "general") or not j.get("issn"):
            continue
        items = crossref.works(j["issn"][0], start, today, date_field="online-pub", max_items=20000)
        parsed = [x for x in (crossref.parse_item(it, j["name"], j["tier"]) for it in items) if x]
        inscope = [x for x in parsed if text_domains(x)]
        dois = [x["doi"] for x in inscope]
        indexed = {}
        for i in range(0, len(dois), 100):
            batch = dois[i:i + 100]
            term = " OR ".join(f'"{d}"[aid]' for d in batch)
            _, ids, _ = pubmed.search(term, retmax=200)
            if ids:
                for r in pubmed.fetch(ids):
                    if r.get("doi"):
                        indexed[r["doi"]] = r
        miss = [x for x in inscope if x["doi"] in indexed and not idx.has_doi(x["doi"])]
        out["journals"][j["name"]] = {"crossref_items": len(parsed), "in_scope_by_text_rules": len(inscope),
                                      "indexed_in_pubmed": sum(1 for x in inscope if x["doi"] in indexed), "missing_from_store": len(miss)}
        for x in miss:
            r = indexed[x["doi"]]
            out["missing"].append({"journal": j["name"], "doi": x["doi"], "pmid": r["pmid"], "title": x["title"],
                                   "pub_types": r.get("pub_types")})
    tot_idx = sum(v["indexed_in_pubmed"] for v in out["journals"].values())
    tot_miss = sum(v["missing_from_store"] for v in out["journals"].values())
    out["summary"] = {"indexed_in_scope": tot_idx, "missing": tot_miss,
                      "completeness": round(1 - tot_miss / tot_idx, 3) if tot_idx else None}
    return out


def cmd_quarterly(args):
    today = config.london_today()
    s = st.load()
    if args.done:
        s["last_runs"]["quarterly"] = st.quarter_key(today)
        st.save(s)
        print(f"quarterly tasks recorded as done for {st.quarter_key(today)}")
        return 0
    print("Quarterly tasks (CLAUDE.md section 10): rewrite outputs/landscape/D1.md to D9.md, re-run the citation benchmark "
          "(python -m src.run benchmark), check for new or updated guidelines, then run python -m src.run quarterly --done.")
    return 0


# ---- baseline and helpers --------------------------------------------------------------------
def cmd_baseline(args):
    idx = _index()
    res = baseline_mod.run(idx, max_minutes=args.minutes, only=args.only)
    print(json.dumps(res, indent=1))
    return 0


def cmd_trends(args):
    res = trends.update(deadline=time.monotonic() + args.minutes * 60, recount_recent_months=args.recount)
    print(res)
    return 0


def cmd_verify(args):
    return verify_citations.main()


def cmd_status(args):
    s = st.load()
    today = config.london_today()
    idx = _index()
    print(json.dumps({
        "today": today.isoformat(),
        "records": idx.count(),
        "baseline": {k: v for k, v in s["baseline"].items() if k not in ("chunks", "chunk_results")},
        "baseline_chunks_pending": len(baseline_mod.pending(s, today)),
        "backlog": len(appraise.load_backlog()),
        "last_runs": s["last_runs"],
        "due": {"weekly": st.weekly_due(s, today), "monthly": st.monthly_due(s, today), "quarterly": st.quarterly_due(s, today)},
        "watermarks": s["watermarks"],
        "register": len(register.load()),
    }, indent=1))
    return 0


def cmd_render(args):
    today = config.london_today()
    s = st.load()
    idx = _index()
    questions = register.load()
    register.save(questions)
    register.render_questions_md(questions, outputs.prose_date(today))
    register.render_priorities_md(questions, outputs.prose_date(today), s.get("domain_weights"))
    outputs.write_calendar(today)
    outputs.readme(idx, questions, s, today)
    print("rendered register, priorities, calendar and README")
    return 0


def cmd_add_records(args):
    idx = _index()
    ing = pipeline.Ingestor(idx, [])
    recs = pubmed.fetch(args.pmids)
    for r in recs:
        r["sources"] = sorted(set(r["sources"]) | {"manual"})
    n_new, n_upd, kept = ing.ingest(recs)
    missing = sorted(set(args.pmids) - {r["pmid"] for r in recs})
    print(f"added {n_new}, updated {n_upd}; stored {len(kept)}; not stored (out of scope or not found): {sorted(set(args.pmids) - set(kept))}; not returned by PubMed: {missing}")
    return 0


def cmd_add_trials(args):
    added = trials.add_extra(args.ids)
    print("added:", added)
    return 0


def cmd_appraise_export(args):
    idx = _index()
    cands = config.load_json(config.STATE / "register_candidates.json", [])
    n = appraise.export_batch(idx, limit=args.limit, candidates=cands, only_priority=args.priority)
    print(f"exported {n} records to state/appraisal_batch.jsonl; backlog {len(appraise.load_backlog())}")
    return 0


def cmd_appraise_import(args):
    idx = _index()
    n, errs = appraise.import_results(idx, path=config.ROOT / args.path if args.path else appraise.RESULTS)
    for e in errs:
        print("rejected:", e)
    print(f"applied {n}; rejected {len(errs)}; backlog {len(appraise.load_backlog())}")
    return 1 if errs else 0


def cmd_queue_baseline(args):
    """Queue baseline records for appraisal: rule tier C for the rest (CLAUDE.md 8.1)."""
    idx = _index()
    from .classify import appraisal_priority, APPRAISAL_DESIGNS
    rows = idx.query("SELECT id FROM rec WHERE tier IS NULL")
    ids = [r[0] for r in rows]
    queue, rule_c = [], {}
    for i in range(0, len(ids), 5000):
        for r in store.get_records(ids[i:i + 5000], idx).values():
            pr = appraisal_priority(r)
            model = (r.get("journal_tier") in ("target", "general") and r.get("design") not in ("narrative_review", "other")) \
                or (r.get("journal_tier") == "specialty" and r.get("design") in APPRAISAL_DESIGNS) \
                or (r.get("design") in ("rct", "ipd_ma", "nma", "guideline"))
            if model:
                queue.append(r)
            else:
                rule_c[r["id"]] = {"tier": "C", "tier_method": "rule"}
    store.update_records(rule_c, idx)
    idx.commit()
    n = appraise.queue(queue, baseline=True)
    print(f"queued {len(queue)} records for model appraisal (backlog now {n}); assigned rule tier C to {len(rule_c)}")
    return 0


def cmd_due(args):
    s = st.load()
    today = config.london_today()
    due = {"baseline_retrieval": len(baseline_mod.pending(s, today)) > 0,
           "baseline_synthesis": s["baseline"].get("status") != "complete",
           "weekly": st.weekly_due(s, today), "monthly": st.monthly_due(s, today), "quarterly": st.quarterly_due(s, today)}
    print(json.dumps(due))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m src.run")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("daily"); a.add_argument("--limit", type=int, default=400); a.set_defaults(fn=cmd_daily)
    a = sub.add_parser("daily-finish"); a.set_defaults(fn=cmd_daily_finish)
    a = sub.add_parser("weekly"); a.add_argument("--no-snapshot", action="store_true"); a.set_defaults(fn=cmd_weekly)
    a = sub.add_parser("monthly"); a.add_argument("--maintenance", action="store_true"); a.add_argument("--quarterly-done", action="store_true"); a.set_defaults(fn=cmd_monthly)
    a = sub.add_parser("quarterly"); a.add_argument("--done", action="store_true"); a.set_defaults(fn=cmd_quarterly)
    a = sub.add_parser("baseline"); a.add_argument("--minutes", type=float, default=7.5); a.add_argument("--only"); a.set_defaults(fn=cmd_baseline)
    a = sub.add_parser("trends"); a.add_argument("--minutes", type=float, default=7.5); a.add_argument("--recount", type=int, default=0); a.set_defaults(fn=cmd_trends)
    a = sub.add_parser("verify"); a.set_defaults(fn=cmd_verify)
    a = sub.add_parser("status"); a.set_defaults(fn=cmd_status)
    a = sub.add_parser("due"); a.set_defaults(fn=cmd_due)
    a = sub.add_parser("render"); a.set_defaults(fn=cmd_render)
    a = sub.add_parser("add-records"); a.add_argument("pmids", nargs="+"); a.set_defaults(fn=cmd_add_records)
    a = sub.add_parser("add-trials"); a.add_argument("ids", nargs="+"); a.set_defaults(fn=cmd_add_trials)
    a = sub.add_parser("appraise-export"); a.add_argument("--limit", type=int, default=400); a.add_argument("--priority", type=int); a.set_defaults(fn=cmd_appraise_export)
    a = sub.add_parser("appraise-import"); a.add_argument("path", nargs="?"); a.set_defaults(fn=cmd_appraise_import)
    a = sub.add_parser("queue-baseline"); a.set_defaults(fn=cmd_queue_baseline)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except net.NetworkBlocked as e:
        print(f"network blocked: {e.reason}. Add the host to the environment's allowed domains.")
        _log_error(f"{args.cmd}: network blocked: {e.reason}")
        return 2
    except Exception as e:
        traceback.print_exc()
        _log_error(f"{args.cmd} failed: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
