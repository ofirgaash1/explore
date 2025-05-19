from __future__ import annotations
from pathlib import Path
import json
import threading
from dataclasses import dataclass, field
from typing import List

from .file_service import FileService, FileRecord


@dataclass(slots=True)
class TranscriptIndex:
    ids:  List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)   # raw, full-episode string


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
            idx.ids.append(rec.id)
            idx.text.append(_episode_to_string(data))
        return idx


# helper converts Kaldi-style or plain list JSON to a single string
def _episode_to_string(data: dict | list) -> str:
    """
    Return the full raw transcript as one space-separated string.

    Accepted input shapes
    ---------------------
    1. {'text': "…"}                         ← fastest path
    2. {'segments': [{'text': …}, …]}        (Kaldi / Whisper JSON)
    3. [{'start': …, 'text': …}, …]          (plain list)

    Raises ValueError if none of the patterns match.
    """
    # --- 1️⃣  fastest: pre-baked full text ---------------------------------
    if isinstance(data, dict) and isinstance(data.get("text"), str):
        return data["text"]

    # --- 2️⃣  Kaldi / Whisper style ----------------------------------------
    if isinstance(data, dict) and "segments" in data:
        segs = data["segments"]
    # --- 3️⃣  plain list ----------------------------------------------------
    elif isinstance(data, list):
        segs = data
    else:
        raise ValueError("Unrecognised transcript JSON structure")

    return " ".join(seg["text"] for seg in segs)