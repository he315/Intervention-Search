# Adversarial review: Q-035 (time-varying effects of LAAO versus OAC by reconstructed IPD)

All identifiers below were read in the local store (data/records, data/trials/current.jsonl.gz) in this session. Dates are the stored published dates. The store is a PubMed-derived record set; no external search was needed because it already holds the relevant 2026 literature.

## Existing syntheses or analyses

- 42646743, JAMA Cardiology, 26 August 2026: "Catheter-Based Left Atrial Appendage Closure vs Oral Anticoagulation in Patients With Atrial Fibrillation: A Systematic Review and Meta-Analysis". Eight trials, 7434 patients, weighted mean follow-up 37.9 months, pooled as incidence rate ratios. Stroke IRR 1.08 (95% CI 0.82-1.41), major bleeding IRR 0.96 (95% CI 0.81-1.14), ischaemic stroke IRR 1.34 (95% CI 1.01-1.77), nonprocedural major bleeding IRR 0.73 (95% CI 0.58-0.92); periprocedural events reported. Same population, comparator and most outcomes, in a target journal within the last two months. It is aggregate-level and does not model time-varying hazards.
- 42843498, American Journal of Cardiology, 7 October 2026: reconstructed IPD meta-analysis, six trials, 7004 patients, restricted mean survival time differences at 3 years for composite efficacy, major bleeding, non-procedure-related bleeding and death. The method is the one proposed here, in a lower-tier journal.
- 42669174, Journal of Cardiovascular Electrophysiology, 1 September 2026: six RCTs, 7004 patients, reconstructed time-to-event analyses of stroke and bleeding plus trial sequential analysis. Reports similar cumulative incidence over follow-up. Partial overlap with the time-varying aim.
- 40549033, Clinical Research in Cardiology, 1 June 2026 (epub 23 June 2025): network and reconstructed IPD meta-analysis, twelve studies. Older evidence base.
- 42501028, JACC: Clinical Electrophysiology, 6 July 2026: seven RCTs, 7353 patients, 294 stroke or systemic embolism events, RR 1.10 (95% CI 0.82-1.48); includes an annualised rate-difference analysis by CHA2DS2-VASc and a post-ablation subgroup.
- 42308650 (JACC: Advances, 1 July 2026), 42777587 (JACC: Advances, 23 September 2026, network meta-analysis, 11 RCTs) and a further dozen or so pairwise meta-analyses in 2026 (for example 42592966, 42898218, 42817893, 42860016, 42855979, 42815712) cover the same trials with aggregate data.
- 41886189, Journal of Interventional Cardiac Electrophysiology, 26 March 2026: Medicare target trial emulation, 3692 LAAO versus 11,076 DOAC patients, stroke, TIA or systemic thromboembolism HR 1.38 (95% CI 0.98-1.95). Not a target journal and observational.

The evidence base has changed materially: the two largest comparisons to date are now published, so the pooled sample has roughly doubled from the pre-2026 position.

## Ongoing trials

- NCT04394546 CHAMPION-AF: 3000 randomised (1499 device, 1501 NOAC), now reported in the New England Journal of Medicine (41910347, 4 June 2026). Primary efficacy at 3 years noninferior (difference 0.9 percentage points, 95% CI -0.8 to 2.6); non-procedure-related bleeding HR 0.55 (95% CI 0.45 to 0.67). The registry still lists primary completion December 2027 and status active, not recruiting, so the longer follow-up continues.
- NCT03463317 CLOSURE-AF: 912 randomised, reported in the New England Journal of Medicine (41849741, 2 April 2026). Not noninferior; difference in restricted mean survival time -0.36 years (95% CI -0.70 to -0.01), P = 0.44 for noninferiority.
- NCT03795298 OPTION: 1600, completed, primary completion 24 July 2024, results posted.
- NCT04226547 CATALYST: 2650 planned, active not recruiting, primary completion January 2029 in the registry (April 2031 completion). Design paper 41638386 (American Heart Journal, 1 June 2026).
- NCT03642509 Occlusion-AF: 750, recruiting, registry primary completion 1 January 2026 (completion 1 October 2030), so the primary date has probably slipped.
- NCT04298723 CLEARANCE (530, post intracranial haemorrhage, 2029-06) and NCT05353140 (LAAO versus NOAC with PCI, 1386, 2028-09) are population-specific and would add heterogeneity rather than answer the question.

CATALYST and Occlusion-AF are the planned update triggers. CATALYST is unlikely to report within 24 months on the registry date (January 2029 is roughly 27 months away); Occlusion-AF may.

## Editor objections

- The headline comparison has been published in JAMA Cardiology in August 2026 and the reconstructed IPD approach in the American Journal of Cardiology in October 2026. A target-journal editor would see a third pooled analysis of the same six to eight trials within months.
- Reconstructed IPD from Kaplan-Meier curves adds little to patient-level data for the two NEJM trials, which already report time-to-event estimates. The CHAMPION-AF and CLOSURE-AF publications will have curves and restricted mean survival time outputs.
- Landmark analyses at 30 days and 1 year rest on events whose reconstruction is least accurate (early periprocedural events, small numbers at risk in the tail). Ischaemic and haemorrhagic stroke curves are rarely published for every trial.
- Trial heterogeneity (device type, comparator VKA versus NOAC, population: contraindicated to OAC, post-ablation, high bleeding risk, OAC-eligible) is a larger driver of differences than time-varying effects, and reconstructed data cannot adjust for it.
- Time-varying hazard ratios from open-label trials with non-proportional hazards can arise from crossover and early procedural harm, which the authors could not separate from a true late device benefit.

## Design objections

- Reconstructed IPD can answer shape-of-hazard questions only for outcomes with published curves and numbers at risk. Sharing of true IPD (Boston Scientific, Abbott, trial groups) would be the credible design, and the timing of CHAMPION-AF and CATALYST makes a consortium route realistic.
- One-stage random effects on reconstructed data across six to eight trials is under-powered to estimate effect modification; the proposed time-varying model would have wide intervals after year 3.
- Pre-registration on PROSPERO does not prevent the answer arriving first: 42843498 and 42669174 already report reconstructed analyses and restricted mean survival time results.
- G5 (not incremental) is at risk: the pooled analysis repeats a recent meta-analysis of the same trials with a different statistical layer.

## Verdict

partly scooped

The core comparison (LAAO versus OAC, stroke, bleeding, death) is now covered by a JAMA Cardiology meta-analysis (42646743), two reconstructed IPD analyses (42843498, 42669174) and two NEJM trials (41849741, 41910347), so a repeat reconstructed analysis would not pass G5 as written. A narrower angle survives: true patient-level or landmark data pooled by consortium from CHAMPION-AF, OPTION, CLOSURE-AF, CATALYST and Occlusion-AF for time-varying and heterogeneous effects, with ischaemic stroke emphasised, which no published analysis has tested. Without IPD access the question should be parked. Suggested changes: G3 should be recorded as failed on the current design (a target-journal meta-analysis, 42646743, appeared in the last 24 months and the pooled evidence has changed by roughly 3912 patients through the two NEJM trials, against 7434 in the pooled analysis); G5 should be marked as failing for the reconstructed-IPD design and passing only for a consortium IPD design; novelty should fall from the current level to 2 (reconstructed IPD analyses already published), and equipoise should be reduced by one point to reflect that the efficacy comparison is largely settled for OAC-eligible patients by CHAMPION-AF while the ischaemic stroke signal in meta-analyses remains contested.
