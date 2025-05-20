import json
from pathlib import Path
from app.services.file_service import FileService
from app.services.index import IndexManager
from app.services.search import SearchService



def test_full_text(tmp_path: Path):
    # ----- fixture data -------------------------------------------------- #
    tr_dir = tmp_path / "json"
    tr_dir.mkdir()
    (tr_dir / "a.json").write_text(json.dumps([{"start": 0.0, "text": "שלום עולם"}]), "utf-8")
    (tr_dir / "b.json").write_text(json.dumps([{"start": 5.0, "text": "עולם אחר"}]), "utf-8")

    # ----- wiring -------------------------------------------------------- #
    fs   = FileService(tr_dir)
    idxm = IndexManager(fs)
    idxm.rebuild_async(block=True)
    svc  = SearchService(idxm)

    hits = svc.search("עולם")
    assert {(h.episode_idx, h.char_offset) for h in hits} == {(0, 5), (1, 0)}



def test_nested_json(tmp_path: Path):
    # layout: tmp/json/ABC/full_transcript.json
    base = tmp_path / "json" / "ABC"
    base.mkdir(parents=True)
    (base / "full_transcript.json").write_text(json.dumps(
        [{"start": 0.0, "text": "שלום עולם"}]), encoding="utf-8")

    fs = FileService(tmp_path / "json")
    recs = fs.records()
    assert len(recs) == 1
    assert recs[0].id == "ABC"
    assert recs[0].json_path.name == "full_transcript.json"
