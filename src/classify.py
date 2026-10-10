"""Rule-based classification: design, domains (text rules), tags, journal
tier and the Tier D pre-screen.

PubMed records get their domains from the domain queries that retrieved them;
the text rules here classify records from other sources (preprints, Crossref
online-first items) and act as a secondary check.
"""
import re

from . import config

def _rx(*terms):
    return re.compile("|".join(terms), re.I)


# ---- design -----------------------------------------------------------------
NOTICE_PT = {"Retraction of Publication", "Published Erratum", "Expression of Concern",
             "Retraction Notice", "Correction"}
EDITORIAL_PT = {"Editorial", "Comment", "Letter", "News", "Newspaper Article", "Interview",
                "Biography", "Portrait", "Historical Article", "Lecture", "Video-Audio Media"}
SECONDARY_RX = _rx(r"post[- ]hoc", r"secondary analys", r"sub-?analys", r"sub-?stud", r"pre-?specified",
                   r"insights? from", r"results? from the", r"analysis (of|from) the", r"subgroup",
                   r"\bfrom the [A-Z0-9-]+ (randomi[sz]ed )?trial", r"ancillary", r"exploratory analys")
RANDOMISED_RX = _rx(r"randomi[sz]ed (controlled |clinical |multicent\w+ |pragmatic |open-label |double-blind |non-?inferiority |noninferiority )*trial",
                    r"were randomly (assigned|allocated)", r"randomly assigned", r"randomly allocated",
                    r"underwent randomi[sz]ation", r"were randomi[sz]ed\b", r"randomi[sz]ed (1:1|2:1|in a)")
META_RX = _rx(r"meta-?analys", r"metaanalys")
NMA_RX = _rx(r"network meta-?analys", r"bayesian network")
IPD_RX = _rx(r"individual[- ](patient|participant)[- ]data", r"patient-level (meta|pooled)", r"\bIPD\b",
             r"reconstructed individual")
SR_RX = _rx(r"systematic review", r"systematic literature review")
EMULATION_RX = _rx(r"target trial", r"trial emulation", r"emulat\w+ (a |of a )?(target )?trial")
MODEL_RX = _rx(r"markov", r"decision[- ]analytic", r"microsimulation", r"decision model", r"cost-?utility")
COST_RX = _rx(r"cost-?effectiveness", r"\bQALY", r"economic evaluation")
CASE_CONTROL_RX = _rx(r"case-?control")
COHORT_RX = _rx(r"registry", r"registries", r"cohort", r"retrospective", r"prospective", r"nationwide",
                r"population-based", r"propensity", r"observational", r"claims data", r"database",
                r"real-world", r"biobank")
CASE_REPORT_RX = _rx(r"\bcase report\b", r"^a case of\b", r"\ba rare case\b", r"\bcase series\b")
GUIDELINE_RX = _rx(r"\bguideline", r"\bguidance\b")
CONSENSUS_RX = _rx(r"consensus", r"scientific statement", r"position (statement|paper)", r"expert opinion",
                   r"clinical (expert )?statement", r"joint statement", r"\bstatement from\b")
REVIEW_RX = _rx(r"state[- ]of[- ]the[- ]art review", r"\breview\b", r"\boverview\b")


def classify_design(rec):
    pts = set(rec.get("pub_types") or [])
    title = rec.get("title") or ""
    abstract = rec.get("abstract") or ""
    text = title + " " + abstract[:3000]
    if pts & NOTICE_PT or re.match(r"^(erratum|correction|retraction|expression of concern)\b", title, re.I):
        return "editorial_letter_comment"
    if pts & EDITORIAL_PT and not ({"Randomized Controlled Trial", "Meta-Analysis"} & pts):
        return "editorial_letter_comment"
    if "Case Reports" in pts or CASE_REPORT_RX.search(title):
        return "case_report"
    if {"Practice Guideline", "Guideline"} & pts or (GUIDELINE_RX.search(title) and not META_RX.search(title)
                                                      and re.search(r"\b(ESC|ACC|AHA|NICE|SCAI|EAPCI|EACTS|society|association|college)\b", title + abstract[:400], re.I)):
        return "guideline"
    if {"Consensus Development Conference", "Consensus Development Conference, NIH", "Consensus Statement"} & pts or CONSENSUS_RX.search(title):
        return "consensus_or_statement"
    is_meta = "Meta-Analysis" in pts or "Network Meta-Analysis" in pts or META_RX.search(title) or META_RX.search(abstract[:600])
    if is_meta:
        if "Network Meta-Analysis" in pts or NMA_RX.search(text):
            return "nma"
        if IPD_RX.search(text):
            return "ipd_ma"
        return "ma"
    if "Systematic Review" in pts or SR_RX.search(title):
        return "sr_no_ma"
    if EMULATION_RX.search(text):
        return "trial_emulation"
    if MODEL_RX.search(text):
        return "decision_model"
    is_rct = bool({"Randomized Controlled Trial", "Pragmatic Clinical Trial", "Equivalence Trial",
                   "Clinical Trial, Phase III"} & pts) or bool(RANDOMISED_RX.search(text))
    if is_rct and not COST_RX.search(title):
        return "rct_secondary" if SECONDARY_RX.search(title) else "rct"
    if is_rct and COST_RX.search(title):
        return "rct_secondary"
    if COST_RX.search(text):
        return "decision_model"
    if CASE_CONTROL_RX.search(text):
        return "case_control"
    if "Observational Study" in pts or COHORT_RX.search(text):
        return "registry_or_cohort"
    if "Review" in pts or "Systematic Review" in pts or REVIEW_RX.search(title):
        return "narrative_review"
    return "other"


# ---- domains (text rules) -----------------------------------------------------
DOMAIN_RULES = {
    "D1": [_rx(r"percutaneous coronary", r"coronary angioplasty", r"drug[- ]eluting stent", r"drug[- ]coated balloon",
               r"(paclitaxel|sirolimus)[- ]coated balloon", r"coronary stent", r"bioresorbable scaffold", r"bioadaptor",
               r"intravascular lithotripsy", r"coronary atherectomy", r"fractional flow reserve", r"wave-free ratio",
               r"quantitative flow ratio", r"chronic total occlusion", r"left main (coronary|stenting|disease|PCI)",
               r"coronary bifurcation", r"bifurcation (lesion|stenting)", r"in-stent restenosis",
               r"high-risk PCI", r"complex PCI", r"periprocedural myocardial", r"\bPCI\b.{0,60}(coronary|stent|CABG|angina|infarct)",
               r"(coronary|stent|CABG|angina|infarct).{0,60}\bPCI\b", r"intravascular (ultrasound|imaging).{0,40}coronary",
               r"coronary.{0,40}(optical coherence tomography|intravascular ultrasound)")],
    "D2": [_rx(r"cardiogenic shock", r"\bimpella\b", r"micro-?axial flow pump", r"intra-?aortic balloon",
               r"mechanical circulatory support", r"\bVA-?ECMO\b", r"veno-?arterial (extracorporeal|ECMO)",
               r"extracorporeal cardiopulmonary resuscitation", r"\bECPR\b", r"left ventricular unloading",
               r"\bLV unloading\b", r"right ventricular assist", r"\bRVAD\b", r"shock team", r"SCAI (shock )?stag",
               r"extracorporeal (life support|membrane oxygenation).{0,80}(cardiac|cardiogenic|heart|myocardial|arrest)",
               r"cardiac arrest.{0,80}(coronary angiography|percutaneous coronary|extracorporeal)")],
    "D3": [_rx(r"\bTAVI\b", r"\bTAVR\b", r"transcatheter aortic", r"valve-in-valve", r"aortic stenosis.{0,80}(replacement|intervention|surgery)",
               r"aortic valve replacement", r"leaflet thrombosis", r"hypo-?attenuated leaflet", r"cerebral embolic protection",
               r"bicuspid.{0,60}(transcatheter|TAVI|TAVR)")],
    "D4": [_rx(r"mitral.{0,80}(transcatheter|edge-to-edge|TEER|MitraClip|PASCAL|repair|replacement|annuloplasty)",
               r"(transcatheter|edge-to-edge|TEER).{0,40}mitral", r"\bMitraClip\b", r"\bTMVR\b",
               r"acute mitral regurgitation", r"papillary muscle rupture")],
    "D5": [_rx(r"tricuspid.{0,80}(transcatheter|edge-to-edge|TEER|TriClip|replacement|repair|intervention|EVOQUE)",
               r"(transcatheter|edge-to-edge|T-TEER).{0,40}tricuspid", r"\bTriClip\b", r"\bTTVR\b", r"caval valve",
               r"lead-(related|induced) tricuspid")],
    "D6": [_rx(r"\bSTEMI\b", r"\bNSTEMI\b", r"\bNSTE-?ACS\b", r"ST-?(segment )?elevation myocardial", r"non-ST-?(segment )?elevation",
               r"acute coronary syndrome", r"unstable angina", r"\bMINOCA\b", r"myocardial infarction with non-?obstructive",
               r"spontaneous coronary artery dissection", r"no-?reflow", r"infarct size",
               r"(acute )?myocardial infarction.{0,80}(reperfusion|revasculari|PCI|invasive|beta-?blocker|colchicine|secondary prevention|SGLT2|GLP-1|semaglutide|statin|PCSK9)")],
    "D7": [_rx(r"type (2|II) myocardial infarction", r"type 2 MI\b", r"secondary myocardial infarction", r"demand isch(a)?emia",
               r"supply[- ]demand (mismatch|isch)", r"myocardial injury", r"perioperative myocardial (infarction|injury)",
               r"myocardial injury after non-?cardiac surgery", r"\bMINS\b.{0,40}surgery", r"universal definition of myocardial infarction")],
    "D8": [_rx(r"(clopidogrel|prasugrel|ticagrelor|cangrelor|P2Y12|dual antiplatelet|\bDAPT\b|antiplatelet|aspirin|glycoprotein IIb|tirofiban|eptifibatide|bivalirudin|heparin|anticoagula|triple therapy|factor XIa?|abelacimab|asundexian|milvexian|de-?escalation|high bleeding risk).{0,120}(PCI|percutaneous coronary|stent|acute coronary|myocardial infarction|STEMI|NSTEMI|TAVI|TAVR|transcatheter|edge-to-edge|appendage|coronary artery disease|chronic coronary)",
               r"(PCI|percutaneous coronary|stent|acute coronary|myocardial infarction|STEMI|TAVI|TAVR|transcatheter|appendage).{0,120}(clopidogrel|prasugrel|ticagrelor|cangrelor|P2Y12|dual antiplatelet|\bDAPT\b|antiplatelet|anticoagula|triple therapy|bivalirudin|factor XIa?)",
               r"left ventricular thromb", r"\bLV thromb")],
    "D9": [_rx(r"left atrial appendage (closure|occlusion)", r"\bLAAO\b", r"\bLAAC\b", r"\bWatchman\b", r"Amulet occluder",
               r"patent foramen ovale.{0,60}(closure|occlu|device)", r"\bPFO closure", r"pulmonary embol\w+.{0,80}(catheter-directed|thrombectomy|catheter-based|ultrasound-facilitated|FlowTriever)",
               r"(catheter-directed|thrombectomy).{0,60}pulmonary embol", r"renal denervation", r"interatrial shunt", r"atrial shunt device",
               r"coronary sinus reducer")],
}
ANIMAL_RX = _rx(r"\b(mice|mouse|murine|rats?|porcine|swine|pigs?|canine|dogs?|rabbits?|sheep|ovine|zebrafish)\b")


def text_domains(rec):
    text = (rec.get("title") or "") + " " + (rec.get("abstract") or "")[:4000]
    return sorted(d for d, rules in DOMAIN_RULES.items() if any(r.search(text) for r in rules))


# ---- tags ---------------------------------------------------------------------
TAG_RULES = {
    "sex": _rx(r"\bwomen\b", r"\bsex[- ](differences|specific|based|disparit)", r"\bgender\b", r"\bfemale patients\b"),
    "older_frailty": _rx(r"\bolder (adults|patients)\b", r"\belderly\b", r"octogenarian", r"nonagenarian", r"\bfrail"),
    "ethnicity": _rx(r"\bethnic", r"\bracial\b", r"\brace\b", r"\bBlack patients\b", r"\bHispanic\b", r"South Asian"),
    "ckd": _rx(r"chronic kidney disease", r"\bCKD\b", r"dialysis", r"end-stage renal", r"renal insufficiency"),
    "diabetes": _rx(r"diabet"),
    "cancer": _rx(r"\bcancer\b", r"oncolog", r"malignan"),
    "high_bleeding_risk": _rx(r"high bleeding risk", r"\bHBR\b"),
    "lmic": _rx(r"low- and middle-income", r"low-? and middle-? income", r"\bLMICs?\b", r"resource-limited"),
    "cost_effectiveness": COST_RX,
    "ai_ml": _rx(r"machine learning", r"deep learning", r"artificial intelligence", r"neural network", r"large language model"),
    "method_bayesian": _rx(r"\bbayesian\b"),
    "method_registry_rct": _rx(r"registry-based randomi[sz]ed", r"registry-based (clinical )?trial"),
}
DESIGN_TAGS = {"rct": "method_rct", "rct_secondary": "method_rct", "ipd_ma": "method_ipd_ma", "nma": "method_nma",
               "trial_emulation": "method_trial_emulation", "decision_model": "method_decision_model"}


def tags_for(rec):
    text = (rec.get("title") or "") + " " + (rec.get("abstract") or "")[:4000]
    tags = {t for t, rx in TAG_RULES.items() if rx.search(text)}
    if rec.get("design") in DESIGN_TAGS:
        tags.add(DESIGN_TAGS[rec["design"]])
    return sorted(tags)


# ---- journal tier ---------------------------------------------------------------
_TIER_CACHE = {}


def _issn_map():
    if "map" not in _TIER_CACHE:
        m = {}
        for j in config.journals().get("journals", []):
            for i in j.get("issn") or []:
                m[i.upper()] = (j["tier"], j["name"])
        _TIER_CACHE["map"] = m
    return _TIER_CACHE["map"]


def journal_tier(rec):
    if rec.get("is_preprint"):
        return "other"
    m = _issn_map()
    for i in rec.get("issns") or []:
        hit = m.get(i.upper())
        if hit:
            return hit[0]
    return "other"


# ---- pre-screen ---------------------------------------------------------------------
def prescreen_tier(rec):
    """Return 'D' when a record goes to Tier D without model appraisal, else None."""
    if rec.get("design") in ("case_report", "editorial_letter_comment"):
        return "D"
    if len((rec.get("abstract") or "").strip()) < 100:
        return "D"
    return None


APPRAISAL_DESIGNS = {"rct", "rct_secondary", "ipd_ma", "ma", "nma", "guideline", "consensus_or_statement", "trial_emulation"}


def appraisal_priority(rec):
    """Lower is more urgent. Used by the volume guard and the backlog."""
    jt = rec.get("journal_tier") or "other"
    jrank = {"target": 0, "general": 0, "specialty": 1}.get(jt, 2)
    drank = 0 if rec.get("design") in APPRAISAL_DESIGNS else 1
    return (min(jrank, drank) if (jrank < 2 or drank == 0) else 3, jrank, drank)


def classify(rec):
    """Fill design, tags, journal_tier, and the pre-screen tier in place."""
    rec["design"] = classify_design(rec)
    rec["journal_tier"] = rec.get("journal_tier") or journal_tier(rec)
    if rec.get("journal_tier") in (None, "other"):
        rec["journal_tier"] = journal_tier(rec)
    if not rec.get("domains"):
        rec["domains"] = text_domains(rec)
    rec["tags"] = sorted(set(rec.get("tags") or []) | set(tags_for(rec)))
    pre = prescreen_tier(rec)
    if pre and not rec.get("tier"):
        rec["tier"], rec["tier_method"] = pre, "rule"
    return rec
