"""Raw payload archive: every source payload is kept gzipped under data/archive/<source>/,
content-addressed by sha256, so parsers can be fixed and replayed without re-fetching."""

from __future__ import annotations

import gzip
from pathlib import Path


def archive_payload(root: Path, source: str, name: str, sha256: str, data: bytes) -> Path:
    stem = Path(name).stem
    path = root / source / f"{stem}-{sha256[:16]}{Path(name).suffix}.gz"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        with gzip.GzipFile(tmp, "wb", mtime=0) as f:  # mtime=0: byte-identical re-archives
            f.write(data)
        tmp.replace(path)
    return path


def read_archived(path: Path) -> bytes:
    with gzip.open(path, "rb") as f:
        return f.read()
