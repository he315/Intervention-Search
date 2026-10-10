import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Point every storage path at a temporary directory."""
    from src import config, store, appraise, register, state, trials
    root = tmp_path
    monkeypatch.setattr(config, "RECORDS", root / "data" / "records")
    monkeypatch.setattr(config, "TRIALS", root / "data" / "trials")
    monkeypatch.setattr(config, "STATE", root / "state")
    monkeypatch.setattr(config, "CACHE", root / ".cache")
    monkeypatch.setattr(config, "REGISTER", root / "register")
    monkeypatch.setattr(appraise, "BATCH", root / "state" / "appraisal_batch.jsonl")
    monkeypatch.setattr(appraise, "RESULTS", root / "state" / "appraisal_results.jsonl")
    monkeypatch.setattr(appraise, "BACKLOG", root / "state" / "backlog.jsonl")
    monkeypatch.setattr(register, "PATH", root / "register" / "questions.jsonl")
    monkeypatch.setattr(state, "PATH", root / "state" / "state.json")
    monkeypatch.setattr(trials, "CURRENT", root / "data" / "trials" / "current.jsonl.gz")
    monkeypatch.setattr(trials, "EXTRA", root / "data" / "trials" / "extra.jsonl")
    monkeypatch.setattr(trials, "CHANGES", root / "data" / "trials" / "changes.jsonl")
    return root
