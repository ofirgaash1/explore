from __future__ import annotations
from pathlib import Path
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import os
import gzip
import orjson
from tqdm.auto import tqdm

from .file_service import FileService, FileRecord


@dataclass(slots=True)
class TranscriptIndex:
    ids:  List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)   # raw, full-episode string
    seg_offsets: List[List[int]]       = field(default_factory=list)   
    seg_times:   List[List[float]]     = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert index to a dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TranscriptIndex:
        """Create index from a dictionary."""
        return cls(
            ids=data["ids"],
            text=data["text"],
            seg_offsets=data["seg_offsets"],
            seg_times=data["seg_times"]
        )


# ­­­­­­­­­­­­­­­­­­­­­­­­­­­­-------------------------------------------------- #
class IndexManager:
    """Global, read-only index."""
    def __init__(self, file_svc: Optional[FileService] = None, index_path: Optional[Path] = None) -> None:
        self._file_svc = file_svc
        self._index_path = Path(index_path) if index_path else None
        self._index = None
        
        if index_path and Path(index_path).exists():
            self._index = self._load_index()
        elif file_svc:
            self._index = self._build()
        else:
            raise ValueError("Either file_svc or index_path must be provided")

    def get(self) -> TranscriptIndex:
        return self._index

    def save_index(self, path: str | Path) -> None:
        """Save the index to a gzipped JSON file."""
        path = Path(path)
        data = self._index.to_dict()
        with gzip.open(path, 'wb') as f:
            f.write(orjson.dumps(data))

    def _load_index(self) -> TranscriptIndex:
        """Load index from a gzipped JSON file."""
        if not self._index_path or not self._index_path.exists():
            raise ValueError(f"Index file not found: {self._index_path}")
        
        with gzip.open(self._index_path, 'rb') as f:
            data = orjson.loads(f.read())
        return TranscriptIndex.from_dict(data)

    def _load_and_convert(self, rec_idx: int, rec: FileRecord) -> Tuple[int, str, dict, float, float]:
        """Load and convert a single record, with timing."""
        t0 = time.perf_counter()
        
        # Time JSON read
        t_read = time.perf_counter()
        data = rec.read_json()
        read_ms = (time.perf_counter() - t_read) * 1000
        
        # Time string conversion
        t_conv = time.perf_counter()
        full, offs, tms = _episode_to_string_and_meta(data)
        conv_ms = (time.perf_counter() - t_conv) * 1000
        
        return rec_idx, rec.id, {"full": full, "offs": offs, "tms": tms}, read_ms, conv_ms

    def _build(self) -> TranscriptIndex:
        idx = TranscriptIndex()
        log = logging.getLogger("index")
        records = list(enumerate(self._file_svc.records()))
        total_files = len(records)
        
        # Use CPU count for thread pool size, but cap at 16 to avoid too many threads
        n_threads = min(16, os.cpu_count() or 4)
        log.info(f"Building index with {n_threads} threads for {total_files} files")
        
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            # Submit all jobs
            futures = [
                executor.submit(self._load_and_convert, rec_idx, rec)
                for rec_idx, rec in records
            ]
            
            # Process results in order as they complete
            with tqdm(total=total_files, desc="Building index", unit="file") as pbar:
                for future in futures:
                    t_append = time.perf_counter()
                    rec_idx, rec_id, data, read_ms, conv_ms = future.result()
                    
                    # Thread-safe append operations
                    idx.ids.append(rec_id)
                    idx.text.append(data["full"])
                    idx.seg_offsets.append(data["offs"])
                    idx.seg_times.append(data["tms"])
                    
                    append_ms = (time.perf_counter() - t_append) * 1000
                    total_ms = read_ms + conv_ms + append_ms
                    
                    #log.info(f"[{rec_idx}] Built {rec_id}: {len(data['offs'])} segments | "
                    #        f"read={read_ms:.1f}ms conv={conv_ms:.1f}ms append={append_ms:.1f}ms "
                    #        f"total={total_ms:.1f}ms")
                    pbar.update(1)
        
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
        cursor += len(part) + 1      # +1 for the space we'll add below
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