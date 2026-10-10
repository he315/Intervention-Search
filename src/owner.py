"""Parse and apply the owner's plain-language decisions.

context/decisions_by_owner.md is read every run and never written by the
system. Each decision line is applied once; its text is remembered in
state.json so it is not re-applied. Lines that cannot be parsed are shown on
the dashboard rather than guessed at.
"""
import hashlib
import re

from . import config

STATUS_WORDS = {
    "in progress": "in_progress",
    "priority": "priority",
    "shortlist": "shortlisted",
    "shortlisted": "shortlisted",
    "park": "parked",
    "parked": "parked",
    "drop": "parked",
    "dropped": "parked",
    "reject": "parked",
    "answered": "answered",
    "scooped": "scooped",
    "candidate": "candidate",
}


def decision_lines():
    p = config.CONTEXT / "decisions_by_owner.md"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.lower().startswith(("one decision per line", "examples")):
            continue
        out.append(s.lstrip("-* ").strip())
    return out


def parse(line):
    """Return a decision dict, or None if the line is not understood."""
    m = re.match(r"^(Q-\d{3,})\s*[:\-]\s*(.+)$", line, re.I)
    if m:
        qid, rest = m.group(1).upper(), m.group(2).strip()
        mm = re.match(r"merge (with|into)\s+(Q-\d{3,})", rest, re.I)
        if mm:
            return {"kind": "merge", "qid": qid, "into": mm.group(2).upper(), "text": line}
        low = rest.lower()
        for word, status in STATUS_WORDS.items():
            if low.startswith(word):
                reason = rest[len(word):].strip(" ,.;:") or "owner decision"
                return {"kind": "status", "qid": qid, "status": status, "reason": reason, "text": line}
        return None
    m = re.match(r"^add tag\s*:\s*(.+)$", line, re.I)
    if m:
        return {"kind": "add_tag", "tag": m.group(1).strip(), "text": line}
    m = re.match(r"^(lower|raise) weight\s*:\s*(D[1-9])$", line, re.I)
    if m:
        return {"kind": "weight", "domain": m.group(2).upper(), "factor": 0.8 if m.group(1).lower() == "lower" else 1.2,
                "text": line}
    return None


def line_key(line):
    return hashlib.sha1(line.encode("utf-8")).hexdigest()[:12]


def pending(state):
    """Return (decisions_to_apply, unparsed_lines)."""
    applied = set(state.get("owner_decisions_applied") or [])
    todo, bad = [], []
    for ln in decision_lines():
        k = line_key(ln)
        if k in applied:
            continue
        d = parse(ln)
        if d is None:
            bad.append(ln)
        else:
            d["key"] = k
            todo.append(d)
    return todo, bad
