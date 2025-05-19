#!/usr/bin/env python3
"""
Smoke-test: build index over ~/data/json and run a couple of
sanity-check searches.
Run:  python scripts/smoke_large.py
"""

from pathlib import Path
import time, random, json

from app.services.file_service import FileService
from app.services.index import IndexManager
from app.services.search import SearchService

JSON_DIR = Path.home() / "data" / "json"      # ~/data/json
TEST_QUERIES = ["שלום", "היום", "ברוך"]       # pick 2–3 common Hebrew words


def main() -> None:
    print("🔍  Initialising services …")
    fs   = FileService(JSON_DIR)
    idxm = IndexManager(fs)

    t0 = time.perf_counter()
    idxm.rebuild_async(block=True)
    t1 = time.perf_counter()
    print(f"✅  Index built in {t1 - t0:.1f} s "
          f"({len(idxm.get().ids):,} episodes)")

    svc = SearchService(idxm)

    # ------------------------------------------------------------------ #
    for q in TEST_QUERIES:
        hits = svc.search(q)
        print(f"• query={q!r:<8}  hits={len(hits):,}")

        # validate a random hit ↴
        if hits:
            hit = random.choice(hits)
            epi_text = idxm.get().text[hit.episode_idx]
            snippet  = epi_text[hit.char_offset: hit.char_offset + 50]
            assert q in snippet, "Mismatch between hit offset and text!"
            print(f"  ↳ sample   id={idxm.get().ids[hit.episode_idx]}  "
                  f"offset={hit.char_offset}  preview={snippet!r}")

    print("🎉  All checks passed.")


if __name__ == "__main__":
    main()
