"""state/state.json: watermarks, checkpoints, last-run dates, schema version.

Watermarks advance per source and domain only for sources that succeeded,
and are written in the same commit as the data they cover.
"""
from datetime import date, timedelta

from . import config

PATH = config.STATE / "state.json"


def default_state():
    return {
        "schema_version": config.SCHEMA_VERSION,
        "baseline": {"start_date": None, "status": "not_started", "chunks": {}, "completed_on": None},
        "watermarks": {},
        "last_runs": {"daily": None, "weekly": None, "monthly": None, "quarterly": None},
        "source_health": {},
        "owner_decisions_applied": [],
        "domain_weights": {},
        "extra_tags": [],
    }


def load():
    s = config.load_json(PATH)
    if s is None:
        return default_state()
    base = default_state()
    for k, v in base.items():
        s.setdefault(k, v)
    for k, v in base["last_runs"].items():
        s["last_runs"].setdefault(k, v)
    return s


def save(s):
    config.save_json(PATH, s)


def watermark(s, source, domain=None):
    key = f"{source}:{domain}" if domain else source
    v = s["watermarks"].get(key)
    return date.fromisoformat(v) if v else None


def set_watermark(s, source, domain, d):
    key = f"{source}:{domain}" if domain else source
    s["watermarks"][key] = d.isoformat()


def window_start(s, source, domain=None, overlap_days=3, default_days=7):
    """Window starts at the stored watermark minus the overlap."""
    wm = watermark(s, source, domain)
    if wm is None:
        start = s["baseline"].get("start_date")
        wm = date.fromisoformat(start) if start else config.london_today() - timedelta(days=default_days)
    return wm - timedelta(days=overlap_days)


def iso_week(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def first_monday(year, month):
    d = date(year, month, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def weekly_due(s, today=None):
    today = today or config.london_today()
    last = s["last_runs"].get("weekly")
    # The weekly report for ISO week W is due on the first run on or after Monday of W.
    return last != iso_week(today)


def monthly_due(s, today=None):
    today = today or config.london_today()
    key = f"{today.year:04d}-{today.month:02d}"
    if s["last_runs"].get("monthly") == key:
        return False
    return today >= first_monday(today.year, today.month)


def quarterly_due(s, today=None):
    today = today or config.london_today()
    if today.month not in (1, 4, 7, 10):
        return False
    key = f"{today.year:04d}-Q{(today.month - 1) // 3 + 1}"
    return s["last_runs"].get("quarterly") != key and monthly_due(s, today)


def quarter_key(today):
    return f"{today.year:04d}-Q{(today.month - 1) // 3 + 1}"
