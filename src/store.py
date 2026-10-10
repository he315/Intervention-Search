"""Record store: JSONL partitions by entrez month, plus a rebuildable index.

The JSONL partitions under data/records are the source of truth. Every write
goes through merge_records(), which merges by id and writes each touched
partition atomically. Partitions older than 12 months may be gzipped; every
reader handles both forms. The SQLite index in .cache/ is rebuilt from JSONL
at the start of each run and is never committed.
"""
import gzip
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from . import config
from .dedupe import normalise_doi

# Fields set by appraisal or later processing that a re-fetch must not erase.
PRESERVE = ("tier", "tier_method", "appraisal", "question_ids", "first_seen",
            "citations", "notes", "appraised_on")


def partition_key(record):
    d = (record.get("dates") or {}).get("entrez") or record.get("first_seen") or ""
    if len(d) >= 7:
        return d[:7]
    return "undated"


def partition_path(key, gz=False):
    year = key[:4] if key != "undated" else "undated"
    p = config.RECORDS / year / f"{key}.jsonl"
    return p.with_suffix(".jsonl.gz") if gz else p


def _existing_partition_file(key):
    plain, gzp = partition_path(key), partition_path(key, gz=True)
    if gzp.exists():
        return gzp
    if plain.exists():
        return plain
    return None


def read_partition(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    out = []
    with opener(path, "rt", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def write_partition(path, records):
    path = Path(path)
    records = sorted(records, key=lambda r: r["id"])
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records)
    if path.suffix == ".gz":
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(".tmp_" + path.name)
        # mtime=0 keeps the gzip bytes stable so unchanged partitions do not churn in git.
        with open(tmp, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
                gz.write(text.encode("utf-8"))
        tmp.replace(path)
    else:
        config.atomic_write_text(path, text)


def all_partition_files():
    if not config.RECORDS.exists():
        return []
    files = list(config.RECORDS.glob("*/*.jsonl")) + list(config.RECORDS.glob("*/*.jsonl.gz"))
    return sorted(files)


def iter_records():
    for f in all_partition_files():
        for r in read_partition(f):
            yield r


def _merge_one(old, new):
    merged = dict(old)
    for k, v in new.items():
        if k in PRESERVE and old.get(k) not in (None, [], {}, ""):
            continue
        if k == "sources":
            merged["sources"] = sorted(set(old.get("sources", [])) | set(v or []))
        elif k == "domains":
            merged["domains"] = sorted(set(old.get("domains", [])) | set(v or []))
        elif k == "tags":
            merged["tags"] = sorted(set(old.get("tags", [])) | set(v or []))
        elif k == "flags":
            f = dict(old.get("flags") or {})
            for fk, fv in (v or {}).items():
                if fv:
                    f[fk] = fv
            merged["flags"] = f
        elif v in (None, [], {}, "") and old.get(k) not in (None, [], {}, ""):
            continue
        else:
            merged[k] = v
    return merged


def merge_records(records, index=None):
    """Merge records into their partitions. Returns (n_new, n_updated)."""
    by_part = defaultdict(list)
    for r in records:
        r.setdefault("schema_version", config.SCHEMA_VERSION)
        r.setdefault("first_seen", config.iso_date(config.london_today()))
        key = partition_key(r)
        if index is not None:
            loc = index.partition_of(r["id"])
            if loc:
                key = loc
        by_part[key].append(r)
    n_new = n_upd = 0
    for key, recs in by_part.items():
        path = _existing_partition_file(key) or partition_path(key)
        existing = {x["id"]: x for x in read_partition(path)} if path.exists() else {}
        for r in recs:
            if r["id"] in existing:
                merged = _merge_one(existing[r["id"]], r)
                if merged != existing[r["id"]]:
                    n_upd += 1
                existing[r["id"]] = merged
            else:
                existing[r["id"]] = r
                n_new += 1
        write_partition(path, list(existing.values()))
        if index is not None:
            for r in recs:
                index.upsert(existing[r["id"]], key)
    return n_new, n_upd


def update_records(updates, index):
    """Apply field updates {id: {field: value}} in place, bypassing PRESERVE.

    Used for appraisal results, flags and citation refreshes, where the new
    value is meant to replace the old one.
    """
    by_part = defaultdict(dict)
    missing = []
    for rid, fields in updates.items():
        key = index.partition_of(rid)
        if not key:
            missing.append(rid)
            continue
        by_part[key][rid] = fields
    for key, ups in by_part.items():
        path = _existing_partition_file(key)
        recs = {x["id"]: x for x in read_partition(path)}
        for rid, fields in ups.items():
            if rid in recs:
                rec = recs[rid]
                for k, v in fields.items():
                    if k == "flags":
                        f = dict(rec.get("flags") or {})
                        f.update(v)
                        rec["flags"] = f
                    else:
                        rec[k] = v
                index.upsert(rec, key)
        write_partition(path, list(recs.values()))
    return missing


def gzip_old_partitions(months=12):
    """Compress partitions older than `months` months. Returns files changed."""
    today = config.london_today()
    y, m = today.year, today.month - months
    while m <= 0:
        m += 12
        y -= 1
    cutoff = f"{y:04d}-{m:02d}"
    changed = []
    for f in all_partition_files():
        if f.suffix == ".jsonl" and f.stem < cutoff and f.stem != "undated":
            recs = read_partition(f)
            gzp = f.with_suffix(".jsonl.gz")
            write_partition(gzp, recs)
            f.unlink()
            changed.append(str(gzp))
    return changed


class Index:
    """SQLite index over the JSONL store for fast lookups during a run."""

    def __init__(self, path=None):
        path = Path(path or (config.CACHE / "index.sqlite"))
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(str(path))
        self.db.execute("PRAGMA journal_mode=OFF")
        self.db.execute("PRAGMA synchronous=OFF")

    def rebuild(self):
        self.db.execute("DROP TABLE IF EXISTS rec")
        self.db.execute(
            "CREATE TABLE rec (id TEXT PRIMARY KEY, pmid TEXT, doi TEXT, partition TEXT, entrez TEXT,"
            " first_seen TEXT, tier TEXT, design TEXT, journal_tier TEXT, domains TEXT, is_preprint INT,"
            " title TEXT, dup_of TEXT)")
        rows = []
        for f in all_partition_files():
            key = f.name.split(".")[0]
            for r in read_partition(f):
                rows.append(self._row(r, key))
        self.db.executemany("INSERT OR REPLACE INTO rec VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_doi ON rec(doi)")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_pmid ON rec(pmid)")
        self.db.commit()
        return len(rows)

    @staticmethod
    def _row(r, key):
        return (r["id"], r.get("pmid"), normalise_doi(r.get("doi")), key,
                (r.get("dates") or {}).get("entrez"), r.get("first_seen"), r.get("tier"),
                r.get("design"), r.get("journal_tier"), ",".join(r.get("domains") or []),
                1 if r.get("is_preprint") else 0, (r.get("title") or "")[:300],
                (r.get("flags") or {}).get("duplicate_of"))

    def upsert(self, r, key):
        self.db.execute("INSERT OR REPLACE INTO rec VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", self._row(r, key))

    def commit(self):
        self.db.commit()

    def partition_of(self, rid):
        row = self.db.execute("SELECT partition FROM rec WHERE id=?", (rid,)).fetchone()
        return row[0] if row else None

    def has(self, rid):
        return self.partition_of(rid) is not None

    def id_for_doi(self, doi):
        nd = normalise_doi(doi)
        if not nd:
            return None
        rows = self.db.execute("SELECT id FROM rec WHERE doi=? ORDER BY pmid IS NULL", (nd,)).fetchall()
        return rows[0][0] if rows else None

    def has_pmid(self, pmid):
        return self.db.execute("SELECT 1 FROM rec WHERE pmid=?", (str(pmid),)).fetchone() is not None

    def has_doi(self, doi):
        return self.id_for_doi(doi) is not None

    def count(self, where="1=1", args=()):
        return self.db.execute(f"SELECT COUNT(*) FROM rec WHERE {where}", args).fetchone()[0]

    def query(self, sql, args=()):
        return self.db.execute(sql, args).fetchall()


def get_records(ids, index):
    """Load full records for the given ids."""
    by_part = defaultdict(set)
    for rid in ids:
        key = index.partition_of(rid)
        if key:
            by_part[key].add(rid)
    out = {}
    for key, want in by_part.items():
        path = _existing_partition_file(key)
        for r in read_partition(path):
            if r["id"] in want:
                out[r["id"]] = r
    return out
