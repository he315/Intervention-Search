"""Paths, constants and small JSON helpers shared by every module.

All paths are relative to the repository root so the pipeline runs the same
way in a scheduled cloud session and on a laptop.
"""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
LONDON = ZoneInfo("Europe/London")

DOMAINS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
DOMAIN_NAMES = {
    "D1": "Coronary intervention",
    "D2": "Cardiogenic shock, cardiac arrest and MCS",
    "D3": "Aortic valve intervention",
    "D4": "Mitral intervention",
    "D5": "Tricuspid intervention",
    "D6": "Acute coronary syndromes",
    "D7": "Type 2 MI and myocardial injury",
    "D8": "Antithrombotic therapy around interventions",
    "D9": "Adjacent interventions",
}
DESIGNS = [
    "rct", "rct_secondary", "ipd_ma", "ma", "nma", "sr_no_ma", "trial_emulation",
    "registry_or_cohort", "case_control", "decision_model", "guideline",
    "consensus_or_statement", "narrative_review", "case_report",
    "editorial_letter_comment", "other",
]
TIERS = ["A", "B", "C", "D"]

CONFIG = ROOT / "config"
DATA = ROOT / "data"
RECORDS = DATA / "records"
TRIALS = DATA / "trials"
TRENDS = DATA / "trends"
CITATIONS = DATA / "citations"
GUIDELINES = DATA / "guidelines"
STATE = ROOT / "state"
REGISTER = ROOT / "register"
OUTPUTS = ROOT / "outputs"
LOGS = ROOT / "logs"
CACHE = ROOT / ".cache"
CONTEXT = ROOT / "context"


def utc_now():
    return datetime.now(timezone.utc)


def london_now():
    return datetime.now(LONDON)


def london_today():
    """The Europe/London calendar date of the run, used to name outputs."""
    return london_now().date()


def iso_date(d):
    return d.strftime("%Y-%m-%d")


def days_ago(n, base=None):
    base = base or london_today()
    return base - timedelta(days=n)


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def atomic_write_text(path, text):
    """Write to a temporary file in the same directory, then rename.

    A crash mid-write leaves the previous version intact rather than a
    truncated file, which matters because JSONL partitions are the source of
    truth.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def save_json(path, obj):
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def contact_email():
    return os.environ.get("CONTACT_EMAIL", "").strip()


def journals():
    return load_json(CONFIG / "journals.json", {"journals": []})


def queries():
    out = {}
    for d in DOMAINS:
        p = CONFIG / "queries" / f"{d}.txt"
        if p.exists():
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                     if ln.strip() and not ln.lstrip().startswith("#")]
            out[d] = " ".join(ln.strip() for ln in lines)
    return out
