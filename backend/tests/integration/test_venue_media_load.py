"""``p11 media venues`` loader against a throwaway database and tmp files (no network)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import Engine, text

from p11.analytics import venue_media
from p11.ingest.venue_media import load_venue_media

pytestmark = pytest.mark.integration


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2400, 1350), (40, 150, 70)).save(buf, "JPEG")
    return buf.getvalue()


def _curated(tmp: Path, vid: int, *, license: str = "CC BY-SA 4.0", src: str = "a.jpg") -> Path:
    p = tmp / "venue_images.json"
    p.write_text(
        json.dumps(
            {
                "venues": [
                    {
                        "venue_id": vid,
                        "venue_name": "Test Ground",
                        "file": "Test ground.jpg",
                        "file_page": "https://commons.wikimedia.org/wiki/File:Test_ground.jpg",
                        "source_url": f"https://upload.wikimedia.org/x/{src}",
                        "author": "<b>Jane</b> Doe",
                        "license": license,
                        "license_url": "https://creativecommons.org/licenses/by-sa/4.0",
                    },
                    {
                        "venue_id": 987654,  # not in the venue table
                        "venue_name": "Nowhere",
                        "file": "N.jpg",
                        "file_page": "https://commons.wikimedia.org/wiki/File:N.jpg",
                        "source_url": "https://upload.wikimedia.org/x/n.jpg",
                        "author": "N",
                        "license": "CC0",
                    },
                ]
            }
        )
    )
    return p


def test_loader_writes_crops_and_rows(db: Engine, tmp_path: Path) -> None:
    with db.begin() as c:
        vid = c.execute(
            text("INSERT INTO venue (name, city) VALUES ('Test Ground', 'X') RETURNING id")
        ).scalar_one()
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return _jpeg()

    out, cache = tmp_path / "public", tmp_path / "cache"
    kw = {"out_dir": out, "cache_dir": cache, "fetch": fetch, "gap_s": 0.0}
    with db.begin() as c:
        rep = load_venue_media(c, curated=_curated(tmp_path, vid), **kw)  # type: ignore[arg-type]
    assert rep["written"] == [vid] and rep["unknown_venues"] == [987654]
    assert rep["changes"]["inserted"] == 1 and len(calls) == 1
    for name, size in ((f"{vid}-1600.webp", (1600, 600)), (f"{vid}-640.webp", (640, 400))):
        with Image.open(out / name) as im:
            assert (im.format, im.size) == ("WEBP", size)
    with db.connect() as c:
        row = c.execute(text("SELECT * FROM venue_media WHERE venue_id = :v"), {"v": vid}).one()
        assert row.image_path == f"/venues/{vid}-1600.webp"
        assert row.thumb_path == f"/venues/{vid}-640.webp"
        assert row.author == "Jane Doe" and row.license == "CC BY-SA 4.0"
        venue_media.clear_cache()
        assert venue_media.media_for(vid, c)["thumb_url"] == f"/venues/{vid}-640.webp"
    venue_media.clear_cache()

    # same source + files on disk -> skipped, nothing re-downloaded or changed
    with db.begin() as c:
        rep = load_venue_media(c, curated=_curated(tmp_path, vid), **kw)  # type: ignore[arg-type]
    assert rep["skipped"] == [vid] and rep["changes"]["updated"] == 0 and len(calls) == 1

    # a new source file is fetched and the row updated
    with db.begin() as c:
        rep = load_venue_media(c, curated=_curated(tmp_path, vid, src="b.jpg"), **kw)  # type: ignore[arg-type]
    assert rep["written"] == [vid] and rep["changes"]["updated"] == 1 and len(calls) == 2


def test_loader_rejects_non_free_licences(db: Engine, tmp_path: Path) -> None:
    with db.begin() as c, pytest.raises(ValueError, match="not a free licence"):
        load_venue_media(
            c,
            curated=_curated(tmp_path, 1, license="CC BY-NC-SA 2.0"),
            out_dir=tmp_path,
            cache_dir=tmp_path,
            fetch=lambda u: b"",
        )
