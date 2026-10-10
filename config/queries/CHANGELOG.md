# Domain query changelog

Every change to a domain query is recorded here with its validation figures. Validation follows CLAUDE.md section 4.1: recall against config/seeds.json, precision on a random sample of 100 records per domain from the last 12 months, and core-journal completeness against Crossref (run after the baseline and at every monthly maintenance).

Two precision figures are reported. Domain precision counts a record as in scope only if it belongs to the domain whose query retrieved it. System precision counts a record as in scope if it belongs to any of D1 to D9, because records carry several domain labels and a D6 record retrieved by the D1 query is not noise for the system. The 70% target is applied to system precision; domain precision is reported so that cross-domain leakage stays visible. This choice is logged in logs/decisions.md.

## Version 2, 10 October 2026 (current)

Precision samples: 100 PMIDs per domain drawn at random (fixed seed 20261010 plus domain number) from records entered in PubMed between 10 October 2025 and 10 October 2026 by the version 1 query, judged by reading title, journal and abstract by three independent reviewer agents who did not see the queries. Labels are stored in data/validation/2026-10-10/. Version 2 figures are computed on the subset of each version 1 sample that version 2 still retrieves, which is valid because version 2 is narrower than version 1 in every domain except D6, where the added title term can only add records.

| Domain | Seeds retrieved | Kept of sample | Domain precision v1 | Domain precision v2 | System precision v1 | System precision v2 | Records per 12 months v1 | v2 |
|---|---|---|---|---|---|---|---|---|
| D1 | 12/12 | 90/100 | 48.0% | 51.1% | 70.0% | 74.4% | 7,004 | 6,390 |
| D2 | 5/5 | 63/100 | 45.0% | 68.3% | 54.0% | 77.8% | 4,081 | 2,705 |
| D3 | 7/7 | 100/100 | 82.0% | 82.0% | 84.0% | 84.0% | 3,121 | 3,089 |
| D4 | 3/3 | 94/100 | 77.0% | 81.9% | 81.0% | 86.2% | 1,149 | 1,113 |
| D5 | 3/3 | 94/100 | 72.0% | 75.5% | 79.0% | 83.0% | 825 | 792 |
| D6 | 6/6 | 90/99 | 57.6% | 63.3% | 68.7% | 75.6% | 6,336 | 6,839 |
| D7 | 21/21 | 49/99 | 32.3% | 59.2% | 47.5% | 77.6% | 1,140 | 671 |
| D8 | 8/8 | 58/100 | 47.0% | 74.1% | 64.0% | 87.9% | 2,596 | 1,603 |
| D9 | 4/4 | 98/100 | 77.0% | 78.6% | 83.0% | 84.7% | 1,614 | 1,550 |

Seed recall is 100% in every domain (69 seeds: 49 named trials, the Fourth Universal Definition of Myocardial Infarction published in three journals, and a D7 recall set of 20 type 2 MI and myocardial injury cohort studies).

System recall of version 2 against version 1: of the 630 sample records judged in scope for the system, 620 (98.4%) are retrieved by at least one version 2 query. The ten not retrieved are listed below with the trade-off accepted.

- 41895254 (mixed vasodilatory shock in a cardiac intensive care unit), 41301798 (heparin-induced thrombocytopenia on ECMO, a narrative review spanning respiratory and cardiac ECMO), 42536004 (stuck mitral prosthesis case): lost when D2 was restricted to cardiogenic shock in the title or with a shock-management term, and ECMO to cardiac contexts. Restoring them would readmit respiratory ECMO and the incidental mentions of cardiogenic shock that made up most of the D2 noise (system precision 54%).
- 41314711 (transcatheter tricuspid valve replacement in congenital heart disease): congenital work is out of scope under CLAUDE.md section 3, so the exclusion is intended.
- 42395633 (nutritional index and mortality after acute myocardial infarction) was lost from D7 but is retrieved by D6 after the D6 addition below; 41872950 (TENS for ischaemia-reperfusion injury) is lost through the basic-science title exclusion.
- 42266552 (dual pathway inhibition in chronic coronary disease, an observational registry), 42051368 (prosthetic valve thrombus case), 41404104 (intramyocardial haematoma case), 42755031 (left atrial appendage thrombus thrombectomy case): lost when D8 required the intervention or ACS context in the title or as a major MeSH heading. These are marginal and the change raised D8 system precision from 64% to 88%.

Changes from version 1:

- All domains: added a title exclusion for animal and in vitro work (rat, mice, murine, canine, rabbit, cardiomyocyte, porcine or ovine model and similar) and for paediatric and congenital work, because most new records are not yet MeSH-indexed and the MeSH animal filter alone missed them.
- D1: the generic clause "PCI in title or abstract plus a coronary word" was restricted to PCI in the title; CTO now requires a coronary term; non-coronary balloon and stent sites (urethra, femoropopliteal, carotid, intracranial and similar) and basic-science title terms are excluded.
- D2: cardiogenic shock now requires a title mention, a major MeSH heading, or a co-mention of a shock-management term; ECMO requires a cardiac context (venoarterial, cardiogenic, cardiac arrest, ECPR, unloading); heart-assist devices require a temporary or shock context; durable LVAD, transplant, total artificial heart, respiratory and venovenous ECMO, trauma, poisoning and cannula engineering are excluded by title.
- D6: basic-science title exclusions (ischaemia-reperfusion injury, exosomes, extracellular vesicles, bioinformatics, ferroptosis and similar); added "acute myocardial infarction" in the title so that clinical studies of MI patients without a management keyword are retrieved.
- D7: "myocardial injury" now requires the title, or troponin plus a classification term (99th percentile, Universal Definition, type 2, acute or chronic myocardial injury, noncardiac surgery); added troponin in the title with myocardial injury or infarction; excluded cardioprotection experiments, biosensor work, ablation, myocarditis, poisoning and transplant titles. An exclusion on "cardiac surgery" in the title was tried and removed because PubMed matches it inside "non-cardiac surgery" and it dropped a seed.
- D8: the intervention context now requires coronary stent or PCI terms, ACS or MI in the title or as a major MeSH heading, or TAVI or TEER terms; left atrial appendage records require an antithrombotic title term or device-related thrombus; neurovascular, carotid, venous thromboembolism and peripheral titles are excluded.
- D9: "PFO" requires a stroke, shunt or migraine context (it collided with perfluoro-n-octane in eye surgery); thrombectomy requires pulmonary embolism and excludes stroke and deep vein titles.
- D3, D4, D5: only the common animal and paediatric exclusions.

Version 1 is kept in config/queries/v1/ for reference.

## Version 1, 10 October 2026

Built from the starting concepts in CLAUDE.md section 4. Seed recall 100% in every domain; precision figures as in the version 1 columns above.
