"""Integrity check run before every commit (CLAUDE.md section 12).

Every PMID, DOI and NCT identifier in any markdown output must exist in
data/records or data/trials. The check also flags em or en dashes and
leftover placeholder text in outputs, which the writing standard forbids.
Exit status 1 means at least one problem; the problems are printed.
"""
import re
import sys

from . import config, store, trials

PMID_RX = re.compile(r"\bPMIDs?:?\s*((?:\d{6,9}(?:\s*(?:,|;|and)\s*)?)+)", re.I)
PMID_URL_RX = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})")
DOI_RX = re.compile(r"\b(10\.\d{4,9}/[^\s\)\]\>\"'|,;]+)")
NCT_RX = re.compile(r"\bNCT\d{8}\b")
ISRCTN_RX = re.compile(r"\bISRCTN\d{8}\b")
PLACEHOLDER_RX = re.compile(r"\b(TODO|TBD|PLACEHOLDER|lorem ipsum|XXX)\b|\[\[|\{\{")
DASHES = ("—", "–")

SCAN_DIRS = ["outputs", "register"]
SCAN_FILES = ["README.md", "PRIORITIES.md"]


def markdown_files():
    files = [config.ROOT / f for f in SCAN_FILES if (config.ROOT / f).exists()]
    for d in SCAN_DIRS:
        p = config.ROOT / d
        if p.exists():
            files += sorted(p.rglob("*.md"))
    return files


def extract(text):
    pmids = set(PMID_URL_RX.findall(text))
    for m in PMID_RX.finditer(text):
        pmids |= set(re.findall(r"\d{6,9}", m.group(1)))
    dois = {d.rstrip(".").lower() for d in DOI_RX.findall(text)}
    ncts = set(NCT_RX.findall(text)) | set(ISRCTN_RX.findall(text))
    return pmids, dois, ncts


def check(index=None):
    index = index or store.Index()
    if index.count() == 0:
        index.rebuild()
    trial_ids = trials.all_trial_ids()
    problems = []
    for f in markdown_files():
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(config.ROOT)
        pmids, dois, ncts = extract(text)
        for p in sorted(pmids):
            if not index.has_pmid(p):
                problems.append(f"{rel}: PMID {p} is not in data/records")
        for d in sorted(dois):
            if not index.has_doi(d):
                problems.append(f"{rel}: DOI {d} is not in data/records")
        for n in sorted(ncts):
            if n not in trial_ids:
                problems.append(f"{rel}: {n} is not in data/trials")
        for ch in DASHES:
            if ch in text:
                problems.append(f"{rel}: contains a {'em' if ch == DASHES[0] else 'en'} dash")
        m = PLACEHOLDER_RX.search(text)
        if m:
            problems.append(f"{rel}: placeholder text '{m.group(0)}'")
    return problems


def main():
    problems = check()
    for p in problems:
        print(p)
    print(f"verify: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
