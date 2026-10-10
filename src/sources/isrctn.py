"""ISRCTN registry. Its free-text search is unreliable, so queries use the
condition: field, which returned relevant trials when tested at build time."""
import xml.etree.ElementTree as ET

from .. import net

BASE = "https://www.isrctn.com/api/query/format/default"


def search(condition, limit=500):
    text = net.request(BASE, params={"q": f'condition:"{condition}"', "limit": limit}, timeout=120)
    return parse(text)


def _t(el, path):
    x = el.find(path)
    return (x.text or "").strip() if x is not None and x.text else None


def parse(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for ft in root.findall("{*}fullTrial"):
        tr = ft.find("{*}trial")
        if tr is None:
            continue
        num = _t(tr, "{*}isrctn")
        desc = tr.find("{*}trialDescription")
        design = tr.find("{*}trialDesign")
        parts = tr.find("{*}participants")
        enrol = _t(parts, "{*}targetEnrolment") if parts is not None else None
        out.append({
            "nct": None,
            "isrctn": f"ISRCTN{num}" if num else None,
            "acronym": _t(desc, "{*}acronym") if desc is not None else None,
            "title": _t(desc, "{*}title") if desc is not None else None,
            "official_title": _t(desc, "{*}scientificTitle") if desc is not None else None,
            "status": None,
            "allocation": _t(design, "{*}allocation") if design is not None else None,
            "enrolment": int(enrol) if enrol and enrol.isdigit() else None,
            "completion": (_t(design, "{*}overallEndDate") or "")[:10] or None,
            "recruitment_end": (_t(parts, "{*}recruitmentEnd") or "")[:10] if parts is not None else None,
            "conditions": [(_t(c, "{*}description") or "") for c in tr.findall("{*}conditions/{*}condition")],
            "sponsor": _t(ft, "{*}sponsor/{*}organisation"),
            "source": "isrctn",
        })
    return out
