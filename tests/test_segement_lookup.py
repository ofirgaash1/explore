import json
from pathlib import Path

from app.services.file_service import FileService
from app.services.index import IndexManager, segment_for_hit
from app.services.search import SearchHit

def test_segment_lookup(tmp_path: Path):
    tr_dir = tmp_path / "json"
    tr_dir.mkdir()
    # two segments, known starts: 0s and 5s
    sample = {"segments": [
        {"start": 0.0, "text": "שלום עולם"},
        {"start": 5.0, "text": "מה שלומך"},
    ]}
    (tr_dir / "s.json").write_text(json.dumps(sample), "utf-8")

    fs   = FileService(tr_dir)
    idxm = IndexManager(fs)
    idxm.rebuild_async(block=True)
    idx  = idxm.get()

    # hit on second segment ("מה")
    full_txt = idx.text[0]
    char = full_txt.find("מה")
    seg = segment_for_hit(idx, 0, char)

    assert seg.seg_idx == 1
    assert seg.text == "מה שלומך"
    assert abs(seg.start_sec - 5.0) < 1e-6