from __future__ import annotations
from pathlib import Path
import json
import threading
from dataclasses import dataclass, field
from typing import List
from bisect import bisect_right

from .file_service import FileService, FileRecord


@dataclass(slots=True)
class TranscriptIndex:
    ids:  List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)   # raw, full-episode string
    seg_offsets: List[List[int]]       = field(default_factory=list)   
    seg_times:   List[List[float]]     = field(default_factory=list)


# ­­­­­­­­­­­­­­­­­­­­­­­­­­­­-------------------------------------------------- #
class IndexManager:
    """Global, read-only index with zero-downtime rebuilds."""
    def __init__(self, file_svc: FileService) -> None:
        self._file_svc = file_svc
        self._index: TranscriptIndex | None = None
        self._lock = threading.RLock()

    # ---------------------------------------------- #
    def get(self) -> TranscriptIndex:
        if self._index is None:
            self.rebuild_async(block=True)
        return self._index

    # ---------------------------------------------- #
    def rebuild_async(self, *, block: bool = False) -> None:
        """Start a background rebuild (or foreground if block=True)."""
        def _job():
            new_index = self._build()
            with self._lock:
                self._index = new_index         # atomic swap
        th = threading.Thread(target=_job, daemon=True)
        th.start()
        if block:
            th.join()

    # ---------------------------------------------- #
    def _build(self) -> TranscriptIndex:
        idx = TranscriptIndex()
        for rec in self._file_svc.records():
            with rec.json_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            full, offs, tms = _episode_to_string_and_meta(data)

            idx.ids.append(rec.id)
            idx.text.append(full)
            idx.seg_offsets.append(offs)
            idx.seg_times.append(tms)
        return idx

# helper converts Kaldi-style or plain list JSON to a single string
def _episode_to_string_and_meta(data: dict | list) -> tuple[str, list[int], list[float]]:
    """
    Returns:
        full_text,  offsets[],  start_times[]
    Offsets are char positions *within* full_text where each segment begins.
    """
    # # 1️⃣ fast path
    # if isinstance(data, dict) and isinstance(data.get("text"), str):
    #     full_text = data["text"]

    # 2️⃣ segments list extraction
    if isinstance(data, dict) and "segments" in data:
        segs = data["segments"]
    elif isinstance(data, list):
        segs = data
    else:
        raise ValueError("Unrecognised transcript JSON structure")

    offsets, times, parts = [], [], []
    cursor = 0
    for seg in segs:
        offsets.append(cursor)
        times.append(float(seg["start"]))
        part = seg["text"]
        parts.append(part)
        cursor += len(part) + 1      # +1 for the space we’ll add below
    full_text = " ".join(parts)
    return full_text, offsets, times


# ------------------------------------------------------------------ #
@dataclass(slots=True, frozen=True)
class Segment:
    episode_idx: int
    seg_idx: int
    text: str
    start_sec: float


def segment_for_hit(index: TranscriptIndex, episode_idx: int,
                    char_offset: int) -> Segment:
    """O(log n) lookup of segment containing `char_offset`."""
    offs = index.seg_offsets[episode_idx]
    i = bisect_right(offs, char_offset) - 1
    start_off = offs[i]
    end_off = offs[i + 1] if i + 1 < len(offs) else len(index.text[episode_idx])

    return Segment(
        episode_idx=episode_idx,
        seg_idx=i,
        text=index.text[episode_idx][start_off:end_off].strip(),
        start_sec=index.seg_times[episode_idx][i],
    )

def segment_by_idx(index: TranscriptIndex, episode_idx: int,
                   seg_idx: int) -> Segment:
    offs = index.seg_offsets[episode_idx]
    if seg_idx < 0 or seg_idx >= len(offs):
        raise IndexError("segment index out of bounds")
    start_off = offs[seg_idx]
    end_off = offs[seg_idx + 1] if seg_idx + 1 < len(offs) else len(index.text[episode_idx])
    return Segment(
        episode_idx=episode_idx,
        seg_idx=seg_idx,
        text=index.text[episode_idx][start_off:end_off].strip(),
        start_sec=index.seg_times[episode_idx][seg_idx],
    )