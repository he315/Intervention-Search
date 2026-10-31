# Preflight

2026-10-10: push-access test from the setup session.

2026-10-14: resume run. Repository state: previous attempt detected (CLAUDE.md present, baseline retrieval complete on main). Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov and medRxiv reachable (HTTP 200); OpenAlex returned 429 (keyless budget spent), so citation counts fall back to Europe PMC. Offline tests: 24 passed using /usr/bin/python3 (pytest is not importable under /usr/local/bin/python3).

2026-10-20: resume run. Previous attempt detected. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set in environment.

2026-10-21: resume run. Previous attempt detected. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). Work pushed to main as the task prompt directs.

2026-10-22: resume run. Previous attempt detected. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. Pushed to main as the task prompt directs.

2026-10-23: resume run. Previous attempt detected. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. Pushed to main as the task prompt directs.

2026-10-24: resume run. Previous attempt detected. Network: PubMed, Crossref, ClinicalTrials.gov, medRxiv reachable (200); Europe PMC 503 on first probe; OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. Pushed to main as the task prompt directs.

2026-10-25: resume run. Previous attempt detected. The 18 synthesis commits (landscapes, register, briefs) sat only on the claude/ branch; main fast-forwarded to include them. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. pytest not importable under the default python3 at first check.

2026-10-27: resume run. Previous attempt detected; main and the claude/ branch are at the same commit. Network: PubMed, Crossref, ClinicalTrials.gov, medRxiv reachable (200); Europe PMC 503; OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. Pushed to main as the task prompt directs.

2026-10-29: resume run. Previous attempt detected; on main at origin/main. Network: PubMed, Europe PMC, Crossref, ClinicalTrials.gov, medRxiv reachable (200); OpenAlex 429 (fallback to Europe PMC). CONTACT_EMAIL not set. Pushed to main as the task prompt directs.

2026-10-31: resume run. Previous attempt detected; on main at origin/main. Network: PubMed, Europe PMC, ClinicalTrials.gov, medRxiv reachable (200); Crossref 429 and OpenAlex 429 on the probe (rate limited, not blocked). CONTACT_EMAIL not set. pytest was missing and was installed.
