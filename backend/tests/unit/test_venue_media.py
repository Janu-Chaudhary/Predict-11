"""Venue photos: curated-entry parsing, licence gate, crops, and the optional API fields."""

from __future__ import annotations

import io
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from p11.analytics import venue_media
from p11.analytics.home_schemas import HomeMatch, HomeTeam, HomeVenue
from p11.analytics.seasons_schemas import VenueRef
from p11.analytics.venue_media import ImageCredit, media_for
from p11.analytics.venues import VenueSummary
from p11.ingest.venue_media import (
    cover_crop,
    download_url,
    is_free_license,
    parse_entries,
    strip_html,
    to_webp,
    web_paths,
)

CREDIT = ImageCredit(
    author="Jane Doe",
    license="CC BY-SA 4.0",
    license_url="https://creativecommons.org/licenses/by-sa/4.0",
    file_page="https://commons.wikimedia.org/wiki/File:Ground.jpg",
)
MEDIA = {
    171: {
        "image_url": "/venues/171-1600.webp",
        "thumb_url": "/venues/171-640.webp",
        "image_credit": CREDIT,
    }
}


def _entry(**kw: object) -> dict[str, object]:
    e: dict[str, object] = {
        "venue_id": 171,
        "venue_name": "Narendra Modi Stadium",
        "file": "Ground.jpg",
        "file_page": "https://commons.wikimedia.org/wiki/File:Ground.jpg",
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Ground.jpg",
        "author": '<a href="//commons.wikimedia.org/wiki/User:Jane">Jane &amp; Doe</a>',
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0",
    }
    e.update(kw)
    return e


# --------------------------------------------------------------------------- ingest helpers
def test_strip_html_keeps_visible_text() -> None:
    assert strip_html('<span class="x"><a href="y">Ana  B</a></span>\n') == "Ana B"
    assert strip_html("Jane &amp; Doe") == "Jane & Doe"


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("CC BY-SA 4.0", True),
        ("CC BY 2.0", True),
        ("CC0", True),
        ("Public domain", True),
        ("CC BY-NC 2.0", False),
        ("CC BY-ND 4.0", False),
        ("All rights reserved", False),
        ("Fair use", False),
    ],
)
def test_licence_gate(name: str, ok: bool) -> None:
    assert is_free_license(name) is ok


def test_parse_entries_strips_author_and_rejects_non_free() -> None:
    (e,) = parse_entries({"venues": [_entry(focus=[0.3, 0.6])]})
    assert e.author == "Jane & Doe" and e.focus == (0.3, 0.6)
    with pytest.raises(ValueError, match="not a free licence"):
        parse_entries({"venues": [_entry(license="CC BY-NC 2.0")]})


def test_web_paths_and_download_url() -> None:
    assert web_paths(171) == ("/venues/171-1600.webp", "/venues/171-640.webp")
    (e,) = parse_entries({"venues": [_entry(file="File:Eden Gardens (1).jpg")]})
    assert download_url(e) == (
        "https://commons.wikimedia.org/wiki/Special:FilePath/Eden_Gardens_%281%29.jpg?width=2400"
    )


def test_cover_crop_follows_the_focus_point() -> None:
    im = Image.new("RGB", (400, 400), (0, 0, 255))
    im.paste((255, 0, 0), (0, 0, 400, 100))  # red band at the top
    top = cover_crop(im, (160, 60), (0.5, 0.0))
    assert top.size == (160, 60) and top.getpixel((80, 5)) == (255, 0, 0)
    mid = cover_crop(im, (160, 60), (0.5, 0.5))
    assert mid.getpixel((80, 30)) == (0, 0, 255)
    wide = cover_crop(Image.new("RGB", (1000, 200)), (640, 400))
    assert wide.size == (640, 400)


def test_to_webp_outputs_both_sizes() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (2000, 1300), (30, 140, 60)).save(buf, "JPEG")
    for size in ((1600, 600), (640, 400)):
        with Image.open(io.BytesIO(to_webp(buf.getvalue(), size, (0.5, 0.5)))) as out:
            assert (out.format, out.size) == ("WEBP", size)


# --------------------------------------------------------------------------- API fields
def test_image_fields_are_optional_and_additive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(venue_media, "media_map", lambda conn=None: MEDIA)
    assert media_for(None) == {} and media_for(999) == {}
    ref = VenueRef(id=171, name="Narendra Modi Stadium", **media_for(171))
    dumped = ref.model_dump()
    assert dumped["image_url"] == "/venues/171-1600.webp"
    assert dumped["image_credit"]["license"] == "CC BY-SA 4.0"
    bare = HomeVenue(id=1, name="X").model_dump()
    assert bare["image_url"] is None and bare["thumb_url"] is None and bare["image_credit"] is None
    s = VenueSummary(
        id=171,
        name="N",
        city=None,
        matches=1,
        matches_recent=1,
        first_season=2026,
        last_season=2026,
        par_recent=None,
        par_all_time=None,
        chase_win_pct_recent=None,
        **MEDIA[171],
    )
    assert s.thumb_url == "/venues/171-640.webp"


def test_home_match_endpoint_returns_venue_photo(monkeypatch: pytest.MonkeyPatch) -> None:
    from p11.api.app import app
    from p11.api.routers import home as router

    @contextmanager
    def no_db():  # type: ignore[no-untyped-def]
        yield None

    t = HomeTeam(id=1, name="Gujarat Titans", short_code="GT")
    match = HomeMatch(
        id=7,
        date="2026-05-31",
        season=2026,
        title="Final",
        stage="Final",
        match_number=None,
        venue=HomeVenue(id=171, name="Narendra Modi Stadium", city="Ahmedabad", **MEDIA[171]),
        team1=t,
        team2=t,
        winner_id=1,
        result="GT won",
        scores=[],
    )
    monkeypatch.setattr(router, "_conn", no_db)
    monkeypatch.setattr(router.svc, "get_match", lambda conn, mid: match)
    r = TestClient(app).get("/api/v1/home/match/7")
    assert r.status_code == 200
    v = r.json()["venue"]
    assert v["image_url"] == "/venues/171-1600.webp"
    assert v["image_credit"]["file_page"].startswith("https://commons.wikimedia.org/")
