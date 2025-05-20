from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import List, NamedTuple

_JSON_SUFFIX = ".json"          # transcripts
_AUDIO_SUFFIX = ".opus"         # keep opus-only for now


class FileRecord(NamedTuple):
    id: str
    json_path: Path


@dataclass(slots=True)
class FileService:
    transcripts_dir: Path
    _records: List[FileRecord] = None
    _last_mtime: float = 0.0

    # --------------------------------------------------------------------- #
    def records(self) -> List[FileRecord]:
        """Return cached file list; rescan if directory mtime changed."""
        current_mtime = self.transcripts_dir.stat().st_mtime
        if self._records is None or current_mtime > self._last_mtime:
            self._records = self._scan()
            self._last_mtime = current_mtime
        return self._records

    # --------------------------------------------------------------------- #
    def _scan(self) -> list[FileRecord]:
        """Return one FileRecord per transcript JSON.

        * Supports both legacy flat files:   <id>.json
        * …and new nested files:            <id>/full_transcript.json
        """
        recs: list[FileRecord] = []
        for p in self.transcripts_dir.rglob(f"*{_JSON_SUFFIX}"):
            # nested layout → use directory name as the recording ID
            if p.name == "full_transcript.json":
                rec_id = p.parent.name
            else:                              # flat layout
                rec_id = p.stem
            recs.append(FileRecord(rec_id, p))

        # complain loudly if we picked up duplicates
        seen: set[str] = set()
        dups: set[str] = set()
        for r in recs:
            if r.id in seen:
                dups.add(r.id)
            seen.add(r.id)
        if dups:
            logging.warning("FileService: duplicate IDs detected: %s", ", ".join(sorted(dups)))

        recs.sort(key=lambda r: r.id)
        return recs