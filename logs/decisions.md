# Decisions log

Judgement calls made by the system, newest last. Each line: date, decision, reason.

- 2026-10-10: Built in the setup conversation rather than a fresh cloud session, because that session could reach GitHub with push access and every source host. Reason: earlier build sessions could not push.
- 2026-10-10: CONTACT_EMAIL is not set in this environment, so requests carry a descriptive User-Agent without an email address. Reason: the owner's address is not sent to third-party services unless the owner adds CONTACT_EMAIL to the environment; the dashboard shows a warning.
- 2026-10-10: The HTTP helper is src/net.py rather than src/http.py. Reason: a module named http inside the package risks shadowing the standard library http package that urllib depends on.
- 2026-10-10: OpenAlex returned 429 "Insufficient budget" for keyless requests (the free budget is shared per IP address). Citation counts fall back to Europe PMC citedByCount until OPENALEX_API_KEY is set. The OpenAlex test fixture is the recorded error response, so the fallback path is what is tested.
- 2026-10-10: ISRCTN's free-text search returned irrelevant trials when tested (a voice-therapy trial for "cardiogenic shock"); the condition: field returned relevant ones, so ISRCTN is queried by condition only.
- 2026-10-10: Test fixtures were recorded from real responses on 10 October 2026. The medRxiv fixture keeps 5 of 30 items of a real page and the ISRCTN fixture keeps the first trial of a real response, to keep the repository small; their structure is unchanged.
- 2026-10-10: ISSNs were resolved through Crossref's journal search with exact normalised title matching. JSCAI needed a different search string ("Society for Cardiovascular Angiography Interventions") because the exact title did not rank in Crossref's results; the matched title is exact.
- 2026-10-10: POPular TAVI seed is cohort A (PMID 32865376, aspirin with or without clopidogrel), which matches the descriptor "antiplatelet therapy after TAVI"; cohort B is a separate report of the same trial.
- 2026-10-10: AQUATIC seed (PMID 40888725) was resolved through its registry number NCT04217447, whose ClinicalTrials.gov acronym is AQUATIC; the PubMed abstract does not name the acronym.
- 2026-10-10: The Fourth Universal Definition of MI seed counts any of its three simultaneous publications (Eur Heart J, JACC, Circulation).
- 2026-10-10: Precision target applied to system precision (in scope for any domain), with domain precision also reported. Reason: records carry several domain labels, so an ACS record retrieved by the coronary-intervention query is not noise for appraisal; both figures are in config/queries/CHANGELOG.md.
- 2026-10-10: Precision samples were judged by three reviewer agents that did not see the queries, reading title, journal and the first 700 characters of the abstract.
