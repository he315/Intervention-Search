# Adversarial review: Q-023

All identifiers below were retrieved from the local store in this session; titles, journals and dates are as stored. Dates are published dates unless stated. Numbers are as reported in the stored abstracts.

## Existing syntheses or analyses

- 38596853, European Heart Journal, 14 June 2024: "Invasive vs. conservative management of older patients with non-ST-elevation acute coronary syndrome: individual patient data meta-analysis". One-stage IPD, six RCTs, 1479 participants (736 invasive, 743 conservative), literature search to 11 September 2023, PROSPERO CRD42023379819. Primary endpoint all-cause death or MI at 1 year: HR 0.87 (95% CI 0.63-1.22); MI HR 0.62 (0.44-0.87). Overlap: this is the same design in a target journal. It predates the NEJM SENIOR-RITA publication (39225274, 7 November 2024), is censored at 1 year, and the abstract does not report a frailty-by-treatment interaction, RMST, time-varying hazard or competing-risk analysis.
- 39698149, European Heart Journal Open, 1 November 2024: older women, subset of the same six-trial IPD, 717 women, 1-year follow-up. Primary endpoint HR 0.77 (95% CI 0.52-1.13). Overlap: sex-specific effect modification is already taken; the question's frailty angle is not.
- 40549394, JAMA Internal Medicine, 1 August 2025: aggregate-data meta-analysis, patients 70 or older with ACS, search to October 2024, primary endpoint all-cause death (RR 1.05; 95% CI 0.98-1.11), recurrent MI RR 0.78 (0.67-0.91), major bleeding RR 1.60 (1.01-2.53). Includes the recent long-term trials. Overlap: answers the average-effect question with current trial data; JAMA Internal Medicine is neither target nor general tier under section 4.
- 40654250 (JAHA, 15 July 2025; 7 RCTs, 2997 patients, weighted mean follow-up 47.1 months), 41165642 (JACC: Advances, 1 December 2025; 8 RCTs, 3275 patients), 39494560 (JAHA, 5 November 2024), 40231483 (Catheterization and Cardiovascular Interventions, 1 July 2025; 7 RCTs, 2997 patients), 40135822 (J Am Geriatr Soc, 1 July 2025): further aggregate meta-analyses of the same trials, none in a target or general journal. They show the average-effect question is saturated.
- 40966585, European Heart Journal Quality of Care and Clinical Outcomes, 6 January 2026: meta-analysis of invasive procedures by frailty across cardiovascular conditions; for frail NSTEMI patients it reports HR 1.13 (95% CI 0.64-2.01) for mortality, an aggregate approach with two or three trials.
- Single-trial frailty and time-varying analyses already published: 42012832 (JAMA Network Open, 1 April 2026; SENIOR-RITA, Fried frailty in 469 of 1446 with data; HR 1.21, 95% CI 0.88-1.67 in frail patients; significant continuous-frailty interaction with a signal of harm at the highest frailty); 38446482 (JAMA Network Open, 4 March 2024; MOSCA-FRAIL extended follow-up, early harm shifting to late benefit, landmark HR 0.58, 0.33-0.99); 39922692 (Heart, 28 July 2025; MOSCA-FRAIL reinfarction with death as competing risk, biphasic mortality); 36877502 (JAMA Internal Medicine, 1 May 2023; MOSCA-FRAIL primary); 37968019 (JACC, 21 November 2023; After Eighty, median 5.3 years, IRR 0.76, 0.63-0.93). Overlap: each trial has already shown the frailty and time-varying signals in isolation; what is missing is the pooled, harmonised, adequately powered test.
- No registry, trial-emulation or biobank analysis in a target or general journal addressing frailty modification of invasive strategy was found in the store beyond the above. 32861307 (Lancet, 29 August 2020, SENIOR-NSTEMI cohort) predates the trials. I did not find an IPD update including SENIOR-RITA in a PubMed search (edat June 2024 to October 2026, ten hits, none an IPD update), but the store is only partly appraised and the search was not exhaustive.

## Ongoing trials

None found that would answer the question first. From data/trials/current.jsonl.gz:

- NCT03052036 (SENIOR-RITA), 1518 enrolled, primary completion 2024-03-31, already reported (39225274).
- NCT02900001 (DEAR-OLD), 696, primary completion 2019-10-30, status UNKNOWN, no stored publication.
- NCT03208153 (MOSCA-FRAIL), 167, completed, reported.
- NCT03289728 (EVAOLD), 588, terminated, primary completion 2025-07-28; imaging-guided versus routine angiography, so a different comparison. Its design paper is 39447717.
- NCT01777503 (Elderly ACS II), 1457, completed 2017; NCT03772743 (FIRE), 1445, active, multivessel complete revascularisation in older MI patients, a different comparison.

The trial base is therefore essentially fixed, which supports G3 on the trial side and also limits what a pooled analysis can add.

## Editor objections

- The headline answer is already in print many times. Eight or more aggregate meta-analyses and one EHJ IPD analysis agree on no mortality difference, fewer recurrent MI and revascularisations, and a bleeding signal. A target journal will ask what a further pooling adds beyond subgroup precision.
- The trial pool is small. Without SENIOR-RITA individual data, the analysis rests on 1479 participants; with it, the aggregate total is about 2997 across seven trials (40654250). Most frail patients come from one trial (469 in SENIOR-RITA, 167 in MOSCA-FRAIL), so a frailty-by-treatment interaction rests largely on single-trial data that are already published.
- Frailty is measured differently (Fried criteria in SENIOR-RITA, Clinical Frailty Scale in MOSCA-FRAIL, other measures or none in older trials). Harmonisation is the central weakness and may leave the interaction uninterpretable.
- It is a secondary, exploratory interaction analysis; the editor will treat positive findings as hypothesis-generating.
- Novelty is limited by the existing EHJ IPD group, which holds the data and has a registered protocol; a competing group may be unable to obtain the trial data.

## Design objections

- IPD access is the rate-limiting step: SENIOR-RITA (ISRCTN11343602), After Eighty (NCT01255540), MOSCA-FRAIL (NCT03208153) and the older trials all need data-sharing agreements, and the existing EHJ IPD collaboration may have pre-empted them.
- Time-varying hazard and RMST analyses are credible only with long, complete follow-up for all trials; follow-up ranges from 1 year to 5.3 years, so late-period estimates come from two or three trials.
- Competing-risk handling is sensible given high non-cardiac mortality (93 deaths against 32 first reinfarctions in MOSCA-FRAIL, 39922692), but event counts for frail subgroups will be small and confidence intervals wide.
- Two-stage versus one-stage with continuous frailty requires a consistent frailty scale; a trial-level fallback (aggregate interaction) has too few trials to be informative.
- The design could credibly answer the narrower question of whether harm in the first year, benefit later and a frailty gradient are consistent across trials. It cannot settle the decision for frail patients; that would need a new trial.

## Verdict

survives with a narrower angle

Reason: the average-effect question is fully answered by 38596853 and 40549394 and the further aggregate meta-analyses, and the single-trial frailty and time-varying signals are already published (42012832, 38446482, 39922692), so the original framing is largely scooped and should not be promoted as a general update. What remains unanswered is a harmonised IPD analysis that includes SENIOR-RITA and long-term After Eighty and MOSCA-FRAIL data, testing the frailty gradient and early-harm-to-late-benefit pattern with competing-risk and RMST methods; the existing IPD (1479 participants, 1-year censoring, search to September 2023) did not include SENIOR-RITA, whose 1518 patients roughly double the pool, and the abstract reports no such analyses. No ongoing trial will pre-empt this, but data access, frailty harmonisation and a likely competing IPD team are material risks.

Suggested changes: G3 should be recorded as passing only for the narrower IPD frailty and time-varying angle, with a note that 38596853 (14 June 2024) is in a target journal and the pooled sample would grow from 1479 to roughly 2997 (1479 plus 1518, before any overlap adjustment and subject to IPD availability); it fails for any average-effect framing. G5 should be marked at risk, passing only if the pre-specified frailty interaction and time-varying analyses are the primary objective rather than a repeat pooling. Novelty should fall by one point or more (suggest 4 to 2 or 3 depending on the current score), and equipoise should fall by one point for the average effect but remain unchanged for frail patients specifically, where the SENIOR-RITA signal of possible harm at the highest frailty and the MOSCA-FRAIL early harm leave genuine uncertainty.
