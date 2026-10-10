"""ClinicalTrials.gov API v2: interventional studies in scope."""
import json

from .. import net

BASE = "https://clinicaltrials.gov/api/v2"
FIELDS = ("NCTId,BriefTitle,OfficialTitle,Acronym,OverallStatus,Phase,DesignInfo,EnrollmentInfo,"
          "PrimaryOutcome,PrimaryCompletionDate,CompletionDate,HasResults,LeadSponsorName,"
          "LocationCountry,StudyFirstSubmitDate,StudyType,Condition,InterventionName,LastUpdatePostDate")
STATUSES_NOT_WITHDRAWN = ("NOT_YET_RECRUITING,RECRUITING,ENROLLING_BY_INVITATION,ACTIVE_NOT_RECRUITING,"
                          "SUSPENDED,TERMINATED,COMPLETED,UNKNOWN")


def search(term, since="2010-01-01", page_size=1000, max_pages=100, extra_filter=None):
    """Yield raw study objects for an Essie query term."""
    adv = f"AREA[StudyType]INTERVENTIONAL AND AREA[StudyFirstSubmitDate]RANGE[{since},MAX]"
    if extra_filter:
        adv += " AND " + extra_filter
    token = None
    for _ in range(max_pages):
        params = {"query.term": term, "filter.advanced": adv, "filter.overallStatus": STATUSES_NOT_WITHDRAWN,
                  "pageSize": page_size, "fields": FIELDS, "countTotal": "true"}
        if token:
            params["pageToken"] = token
        d = json.loads(net.request(f"{BASE}/studies", params=params, timeout=120))
        for s in d.get("studies") or []:
            yield s
        token = d.get("nextPageToken")
        if not token:
            return


def get_study(nct):
    d = json.loads(net.request(f"{BASE}/studies/{nct}", params={"fields": FIELDS}))
    return parse_study(d)


def parse_study(s):
    p = s.get("protocolSection") or {}
    ident = p.get("identificationModule") or {}
    status = p.get("statusModule") or {}
    design = p.get("designModule") or {}
    dinfo = design.get("designInfo") or {}
    enrol = design.get("enrollmentInfo") or {}
    outcomes = (p.get("outcomesModule") or {}).get("primaryOutcomes") or []
    sponsor = ((p.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}).get("name")
    locs = (p.get("contactsLocationsModule") or {}).get("locations") or []
    countries = sorted({l.get("country") for l in locs if l.get("country")})
    pc = status.get("primaryCompletionDateStruct") or {}
    cc = status.get("completionDateStruct") or {}
    return {
        "nct": ident.get("nctId"),
        "acronym": ident.get("acronym"),
        "title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "status": status.get("overallStatus"),
        "phases": design.get("phases") or [],
        "allocation": dinfo.get("allocation"),
        "intervention_model": dinfo.get("interventionModel"),
        "masking": (dinfo.get("maskingInfo") or {}).get("masking"),
        "enrolment": enrol.get("count"),
        "enrolment_type": enrol.get("type"),
        "primary_outcomes": [{"measure": o.get("measure"), "time_frame": o.get("timeFrame")} for o in outcomes][:5],
        "primary_completion": pc.get("date"),
        "primary_completion_type": pc.get("type"),
        "completion": cc.get("date"),
        "has_results": bool(s.get("hasResults")),
        "sponsor": sponsor,
        "countries": countries,
        "conditions": (p.get("conditionsModule") or {}).get("conditions") or [],
        "interventions": [i.get("name") for i in ((p.get("armsInterventionsModule") or {}).get("interventions") or [])][:10],
        "first_submitted": status.get("studyFirstSubmitDate"),
        "last_update": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
    }
