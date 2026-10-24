# Adversarial review of Q-020

Sources: local store (data/records, data/trials/current.jsonl.gz), read on 24 October 2026. A PubMed esearch (tricuspid with pooled, IPD or heterogeneity terms plus trial names) returned 11 identifiers, none of which was a new risk-stratified pooled analysis. Every identifier below was read in the store with title, journal and date as stored. Web search was not used, so unindexed items and conference abstracts were not checked.

## Existing syntheses or analyses

- 40803660, International Journal of Cardiology, 15 December 2025: meta-analysis of three RCTs (1,050 patients) of TEER or TTVR versus medical therapy, with individual patient data reconstructed from Kaplan-Meier curves where necessary. Odds ratios for all-cause mortality 1.01 (95% CI 0.63-1.60), cardiovascular death and heart failure hospitalisation (OR 0.87; 0.61-1.25). Overlaps the reconstructed-IPD element of Q-020, but is a specialty-level journal and pre-dates TRIC-I-HF.
- 41467224, International Journal of Cardiology Heart and Vasculature, 1 December 2025: meta-analysis with reconstructed time-to-event data, 3 RCTs and 2 observational studies (n = 1,988), PROSPERO CRD420251002402. Major bleeding RR 3.21 (1.61-6.39).
- 42249500, Journal of Cardiothoracic Surgery, 5 June 2026: frequentist and Bayesian network meta-analysis of the same three RCTs (1,050 patients), star-shaped with no direct TEER versus TTVR comparison, with SUCRA values, NNT and NNH, including bleeding and pacemaker outcomes. This already delivers the Bayesian T-TEER/TTVR network as proposed.
- 41145332, Cardiovascular Revascularization Medicine, 1 June 2026 (3 RCTs, 1,264 patients); 40735794, Catheterization and Cardiovascular Interventions, 1 October 2025 (4 RCTs, 1,292 patients); 40824202 (same journal, 7 studies, 4,220 patients, mortality HR 0.79; 0.64-0.98); 42103202, American Journal of Cardiology, 15 July 2026 (13 studies, 6,732 patients, RCT-only mortality null). Trial-level duplicates of one another.
- 42350254, Cardiovascular Revascularization Medicine, 17 June 2026: TRI-SCORE and outcomes after T-TEER, five observational studies (n = 2,074). Partial overlap on risk stratification, observational only.
- 40878717, European Heart Journal, 5 May 2026: TRISCEND II by baseline TR severity, post hoc. Win ratio 1.64 (1.11-2.43) in severe and 2.20 (1.55-3.14) in massive or torrential TR. A single-trial HTE analysis in a target journal, which weakens the claim that HTE is unexplored.
- 42850060, Heart, 8 October 2026: exploratory analysis of baseline invasive haemodynamics and response in TRI-FR (no abstract stored).
- 41973411, JAMA, 12 May 2026: STS/ACC TVT Registry real-world TTVR outcomes (registry, not a synthesis).
- No target- or general-tier meta-analysis of the randomised trials was found in the store. All pooled analyses are in specialty or low-tier journals, and all pre-date the NEJM TRIC-I-HF report.

## Ongoing trials

- 42670975, NEJM, 8 October 2026 (NCT04634266, TRIC-I-HF): 360 randomised, win ratio 2.42 (1.76-3.33); death or HF hospitalisation to 3 years HR 0.40 (0.29-0.55). This is the "next readout" the question was timed to, and it has now reported. The registry record still lists it as active, not recruiting, with a stale primary completion date.
- NCT03904147 (TRILUMINATE Pivotal, n = 572, 40159089 Circulation 2025) and NCT04482062 (TRISCEND II, n = 864 registered, 400 in the randomised cohort in 39475399 NEJM 2025): reported. NCT04646811 (TRI-FR, n = 300, completed 2024-04-23): reported in part (41258847, 40387042).
- NCT04097145 (CLASP II TR, n = 1,270 estimated, medical therapy comparator, primary completion 2027-12-31). The one large pending device-versus-medical-therapy RCT; design paper 42855029 published 9 October 2026.
- NCT06458907 (TRICAV-II, TricValve bicaval, n = 780, primary completion 2028-11, optimal medical therapy comparator); NCT07433504 (China, clipping system versus GDMT, n = 132, 2027-12-31); NCT05628779 (TRACE-NL, n = 150, 2027-11-01, two TEER systems compared).
- Head-to-head TTVR trials against EVOQUE, all with major adverse events at 30 days as the first primary endpoint and primary completion 2029 or later: NCT07454980 (n = 680, 2029-12), NCT07516444 (n = 730, 2029-06), NCT07321899 (n = 1,186, 2031-09), NCT07528326 (n = 831, 2031-09), NCT07687485 (n = 700, 2029-09). These would feed a network but not within 1 to 2 years.
- Consequence: only CLASP II TR is a pivotal readout inside the stated horizon, and its primary completion is about 14 months away. Whether the "next pivotal readouts" exist for a 1 to 2 year timeline rests on that single trial.

## Editor objections

- The base is four RCTs with distinct populations, endpoints and comparators. A target-journal editor will see a fifth meta-analysis of the same trials, now with a positive headline trial already published in NEJM.
- Heterogeneity of treatment effect by baseline risk from four trials (about 1,600 patients with randomised follow-up) is underpowered for interaction tests, and subgroup claims are exploratory. Trial crossover in TRILUMINATE (61.5% in the control arm at 2 years, 40159089) and in TRIC-I-HF's crossover design complicates time-to-event comparison.
- The win ratio across trials uses different hierarchies (TRILUMINATE, TRISCEND II and TRIC-I-HF differ in components), so pooling is not straightforward without IPD.
- Reconstructed IPD cannot support risk-stratified modelling. Baseline risk scores (TRI-SCORE, EuroSCORE) are not on Kaplan-Meier curves, and subgroup curves are rarely published.
- Prior reconstructed-IPD and network analyses (40803660, 41467224, 42249500) reduce novelty of the method.
- Open-label designs with KCCQ-driven hierarchies invite performance bias, which the manuscript would have to address.

## Design objections

- True risk-stratified HTE needs patient-level data from the sponsors (Abbott, Edwards) and the DZHK and Tri.FR groups. A consortium IPD meta-analysis could do this credibly, but reconstructed IPD cannot, and the proposal as written leans on reconstruction.
- A Bayesian network across T-TEER and TTVR is star-shaped with medical therapy as the only common comparator (42249500), so the indirect comparison is confounded by population differences (TRISCEND II enrolled mostly severe-to-torrential TR with anatomic suitability for replacement). Transitivity is weak.
- PROSPERO registration before the next readout is feasible, and a pre-specified living update fits CLASP II TR, but the prior-art meta-analyses show the field will absorb that readout quickly.
- A better-powered question is available: IPD consortium analysis of effect modification by baseline risk, RV function, TR grade and age, using all four trials (and CLASP II TR when available), with a hierarchical composite and a time-to-event analysis harmonised across trials.

## Verdict

survives with a narrower angle

The trial-level and reconstructed-IPD synthesis of T-TEER and TTVR versus medical therapy is largely scooped by 40803660, 41467224 and 42249500, and the signature "next readout" (TRIC-I-HF, 42670975) has already appeared in NEJM, which also removes the equipoise for the headline composite question. A real gap remains for effect modification by baseline risk and TR severity, which has so far been studied only within single trials (for example 40878717), and no target-tier pooled analysis exists. That angle needs consortium patient-level data from TRILUMINATE, TRISCEND II, Tri.FR and TRIC-I-HF, with CLASP II TR as the timed update, and it should drop the reconstruction-only and star-network components. Suggested changes: G3 should be recorded as passing only for the narrowed IPD question, with a note that no RCT of the same comparison will report within 24 months other than CLASP II TR (about 14 months away, NCT04097145), and that three low-tier meta-analyses of the same trials exist in 2025 to 2026 but none in a target or general journal. G5 should be marked at risk, because the question as written is a repeat meta-analysis of the same four trials and passes only if patient-level data are obtained. Novelty should fall from its present score by at least one point, to 3 at most, for the reconstructed and network design, and about 3 or 4 for a consortium IPD design. Equipoise should be lowered by one point for the headline benefit question (TRIC-I-HF win ratio 2.42, 1.76-3.33) and kept for hard-outcome mortality and risk-stratified benefit, where pooled mortality remains null in RCT-only analyses (42103202).
