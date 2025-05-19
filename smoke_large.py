#!/usr/bin/env python3
"""
Smoke-test the Explore search stack on a real corpus.

* Builds the TranscriptIndex
* Runs three hand-picked literal queries
* Runs three regex queries
* Times every query
* Samples 100 random words that appear in the corpus and
  checks that each full-text search finds ≥ 1 hit

Run:  python scripts/smoke_large.py
"""

from __future__ import annotations
import json, random, re, time
from collections import Counter
from pathlib import Path
from typing import Iterable

from app.services.file_service import FileService
from app.services.index import IndexManager
from app.services.search import SearchService

# ---------- CONFIG --------------------------------------------------------- #
JSON_DIR       = Path.home() / "data" / "json"      # ~/data/json
HAND_QUERIES   = ["שלום", "מתושלח", "אם"]           # literal
REGEX_QUERIES  = [r"\b[Aa]udio\b", r"(בית|בית־ספר)", r"^שלום"]   # regex
BATCH_SIZE     = 100                                # random words to test
WORD_RE        = re.compile(r"\w{4,}", re.UNICODE)  # ≥4-char “words”

# ---------- helpers -------------------------------------------------------- #
def time_call(fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, time.perf_counter() - t0


def harvest_random_words(index_texts: Iterable[str], k: int) -> list[str]:
    """Return k random *distinct* words that exist ≥2 times in corpus."""
    freq = Counter()
    for txt in index_texts:
        freq.update(WORD_RE.findall(txt))
    # keep reasonably frequent words to avoid zero-hit surprises
    common = [w for w, c in freq.items() if c >= 2]
    if len(common) < k:           # unlikely on 700 episodes
        common = list(freq)
    return random.sample(common, k)


def preview_hit(idx_mgr, hit, span=50) -> str:
    txt = idx_mgr.get().text[hit.episode_idx]
    start = max(0, hit.char_offset - 10)
    return txt[start : hit.char_offset + span]


# ---------- main ----------------------------------------------------------- #
def main() -> None:
    print("🔧  Building index …")
    fs   = FileService(JSON_DIR)
    idxm = IndexManager(fs)
    _, build_sec = time_call(idxm.rebuild_async, block=True)
    epi_cnt = len(idxm.get().ids)
    print(f"✅  {epi_cnt:,} episodes indexed in {build_sec:.1f} s")

    svc = SearchService(idxm)

    # --------------------------------------------------------------------- #
    print("\n=== Hand-picked literal queries ===")
    for q in HAND_QUERIES:
        hits, sec = time_call(svc.search, q, regex=False)
        print(f"q={q!r:<8}  hits={len(hits):4}  {sec*1000:6.1f} ms")
        if hits:
            print("  ↳", preview_hit(idxm, random.choice(hits)))

    # --------------------------------------------------------------------- #
    print("\n=== Hand-picked REGEX queries ===")
    for q in REGEX_QUERIES:
        hits, sec = time_call(svc.search, q, regex=True)
        print(f"rx={q!r:<18} hits={len(hits):4}  {sec*1000:6.1f} ms")
        if hits:
            print("  ↳", preview_hit(idxm, random.choice(hits)))

    # --------------------------------------------------------------------- #
    print(f"\n=== Batch test on {BATCH_SIZE} random words ===")
    rnd_words = harvest_random_words(idxm.get().text, BATCH_SIZE)
    failures = 0
    total_sec = 0.0
    for w in rnd_words:
        hits, sec = time_call(svc.search, w, regex=False)
        total_sec += sec
        if not hits:
            failures += 1
    avg_ms = (total_sec / BATCH_SIZE) * 1000
    print(f"avg per-search time: {avg_ms:.1f} ms  |  zero-hit words: {failures}")

    print("\n🎉  Smoke-test finished.")


if __name__ == "__main__":
    main()
