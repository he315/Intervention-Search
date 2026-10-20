# Preflight

2026-10-10: push-access test from the setup session.

2026-10-14: resume run. Repository state: previous attempt detected (CLAUDE.md present, baseline retrieval complete on main). Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov and medRxiv reachable (HTTP 200); OpenAlex returned 429 (keyless budget spent), so citation counts fall back to Europe PMC. Offline tests: 24 passed using /usr/bin/python3 (pytest is not importable under /usr/local/bin/python3).

2026-10-20: resume run. Previous attempt detected. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set in environment.
