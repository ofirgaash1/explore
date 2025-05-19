import json
from pathlib import Path
from app.services.file_service import FileService
from app.services.index import IndexManager
from app.services.search import SearchService


def test_full_text(tmp_path: Path):
    # ----- fixture data -------------------------------------------------- #
    tr_dir = tmp_path / "json"
    tr_dir.mkdir()
    (tr_dir / "a.json").write_text(json.dumps([{"text": "שלום עולם"}]), "utf-8")
    (tr_dir / "b.json").write_text(json.dumps([{"text": "עולם אחר"}]), "utf-8")

    # ----- wiring -------------------------------------------------------- #
    fs   = FileService(tr_dir)
    idxm = IndexManager(fs)
    idxm.rebuild_async(block=True)
    svc  = SearchService(idxm)

    hits = svc.search("עולם")
    assert {(h.episode_idx, h.char_offset) for h in hits} == {(0, 5), (1, 0)}
