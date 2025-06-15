from __future__ import annotations
import regex
import time
import logging
from dataclasses import dataclass
from typing import List, Callable

from .index import IndexManager, TranscriptIndex, segment_for_hit, Segment

logger = logging.getLogger(__name__)

@dataclass(slots=True, frozen=True)
class SearchHit:
    episode_idx: int
    char_offset: int


class SearchService:
    """Stateless, one-pass search over the current TranscriptIndex."""
    def __init__(self, index_mgr: IndexManager) -> None:
        self._index_mgr = index_mgr
        # Log index statistics on initialization
        idx = self._index_mgr.get()
        total_chars = sum(len(text) for text in idx.text)
        logger.info(f"SearchService initialized with {len(idx.text)} texts, total size: {total_chars:,} characters")

    # ­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­ #
    def search(self, query: str, *, regex: bool = False) -> List[SearchHit]:
        start_time = time.perf_counter()
        idx = self._index_mgr.get()
        
        # Log search parameters
        logger.info(f"Starting search for query: '{query}' (regex={regex})")
        
        matcher = _make_matcher(query)
        matcher_time = time.perf_counter() - start_time
        logger.info(f"Matcher compilation took {matcher_time*1000:.2f}ms")

        hits: List[SearchHit] = []
        total_chars = 0

        text_start = time.perf_counter()

        for epi, text in enumerate(idx.text):
            text_hits = [SearchHit(epi, pos) for pos in matcher(text)]
            hits.extend(text_hits)

            total_chars += len(text)
            
        text_time = time.perf_counter() - text_start
                    
        total_time = time.perf_counter() - start_time
        logger.info(f"Search completed in {total_time*1000:.2f}ms. "
                   f"Found {len(hits)} hits in {len(idx.text)} texts "
                   f"({total_chars:,} total characters)")
        return hits

    def segment(self, hit: SearchHit) -> Segment:
        """Return the segment that contains this hit."""
        idx = self._index_mgr.get()
        return segment_for_hit(idx, hit.episode_idx, hit.char_offset)

# ------------------------------------------------------------------ #
def _make_matcher(pat: str) -> Callable[[str], List[int]]:
    """Return function that yields every match offset in s using regex.
    For single words, adds word boundary matching."""
    # Check if pattern is a single word (no spaces or special regex chars)
    if regex.match(r'^[\w-]+$', pat):
        pat = r'\b' + regex.escape(pat) + r'\b'
    else:
        pat = regex.escape(pat)
    
    rx = regex.compile(pat)
    logger.debug(f"Compiled regex pattern: {pat}")

    def _inner(s: str) -> List[int]:
        return [m.start() for m in rx.finditer(s)]
    return _inner
