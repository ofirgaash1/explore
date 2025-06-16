import orjson
import gzip
from pathlib import Path
from app.services.file_service import FileService
from app.services.index import IndexManager
from app.services.search import SearchService



def test_full_text(tmp_path: Path):
    # ----- fixture data -------------------------------------------------- #
    tr_dir = tmp_path / "json"
    tr_dir.mkdir()
    with gzip.open(tr_dir / "a.json.gz", 'wb') as f:
        f.write(orjson.dumps([{"start": 0.0, "text": "שלום עולם"}]))
    with gzip.open(tr_dir / "b.json.gz", 'wb') as f:
        f.write(orjson.dumps([{"start": 5.0, "text": "עולם אחר"}]))

    # ----- wiring -------------------------------------------------------- #
    fs   = FileService(tr_dir)
    idxm = IndexManager(fs)
    svc  = SearchService(idxm)

    hits = svc.search("עולם")
    assert {(h.episode_idx, h.char_offset) for h in hits} == {(0, 5), (1, 0)}



def test_nested_json(tmp_path: Path):
    # layout: tmp/json/ABC/full_transcript.json.gz
    base = tmp_path / "json" / "ABC"
    base.mkdir(parents=True)
    with gzip.open(base / "full_transcript.json.gz", 'wb') as f:
        f.write(orjson.dumps([{"start": 0.0, "text": "שלום עולם"}]))

    fs = FileService(tmp_path / "json")
    recs = fs.records()
    assert len(recs) == 1
    assert recs[0].id == "ABC"
    assert recs[0].json_path.name == "full_transcript.json.gz"
