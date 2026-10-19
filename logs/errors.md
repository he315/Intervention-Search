# Errors log

Notes for the next run. Each entry: date, what failed, what to try first.

- 2026-10-14 09:55: crossref fetch failed: HTTP 400 for https://api.crossref.org/journals/0195-668X/works?filter=from-created-date%3A2026-10-07%2Cuntil-created-date%3A2026-10-14%2Ctype%3Ajournal-article&rows=500&cursor=%2A&select=DOI%2Ctitle%2Ctype%2Cpublished-online%2Cpublished-print%2Ccreated%2Ccontainer-title%2CISSN%2Cauthor%2Cabstract%2Crelation%2Csubtype: {"status":"failed","message-type":"validation-failure","message":[{"type":"select-not-available","value":"subtype","message":"Select 'subtype' specified but there is no such select for this route. Val. Watermark not advanced.
- 2026-10-19: monthly maintenance core-journal completeness was 0.791 (14 of 67 indexed in-scope Crossref items missing from the store). Investigate which journals and whether the cause is PubMed indexing lag, the 3-day overlap or query scope; revise queries and log figures in config/queries/CHANGELOG.md. Baseline synthesis (landscapes, citation benchmark, register, briefs, guideline extracts) is still not done; backlog 10,935 records. Monthly narrative not written, so `monthly` was not run.
