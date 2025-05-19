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
    def _scan(self) -> List[FileRecord]:
        recs: List[FileRecord] = []
        for p in self.transcripts_dir.rglob(f"*{_JSON_SUFFIX}"):
            rec_id = p.stem      # file name without suffix
            recs.append(FileRecord(rec_id, p))
        recs.sort(key=lambda r: r.id)
        return recs
