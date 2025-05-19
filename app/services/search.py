from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Callable

from .index import IndexManager, TranscriptIndex, segment_for_hit, Segment


@dataclass(slots=True, frozen=True)
class SearchHit:
    episode_idx: int
    char_offset: int


class SearchService:
    """Stateless, one-pass search over the current TranscriptIndex."""
    def __init__(self, index_mgr: IndexManager) -> None:
        self._index_mgr = index_mgr

    # ­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­ #
    def search(self, query: str, *, regex: bool = False) -> List[SearchHit]:
        idx = self._index_mgr.get()
        matcher = _make_matcher(query, regex)

        hits: List[SearchHit] = []
        for epi, text in enumerate(idx.text):
            for pos in matcher(text):
                hits.append(SearchHit(epi, pos))
        return hits

    def segment(self, hit: SearchHit) -> Segment:
        """Return the segment that contains this hit."""
        idx = self._index_mgr.get()
        return segment_for_hit(idx, hit.episode_idx, hit.char_offset)

# ------------------------------------------------------------------ #
def _make_matcher(pat: str, regex: bool) -> Callable[[str], List[int]]:
    """Return function that yields every match offset in s."""
    if not regex:
        def _inner(s: str) -> List[int]:
            off, res = 0, []
            while True:
                off = s.find(pat, off)
                if off == -1:
                    return res
                res.append(off)
                off += 1
        return _inner
    else:
        rx = re.compile(pat)

        def _inner(s: str) -> List[int]:
            return [m.start() for m in rx.finditer(s)]
        return _inner
