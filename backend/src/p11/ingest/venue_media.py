"""Ground photos for venue pages: freely licensed Wikimedia Commons images, cached as WebP.

Input is the hand-curated ``data/raw/media/venue_images.json`` (one chosen Commons file per
canonical venue, with its attribution). Only CC BY / CC BY-SA / CC0 / public-domain files are
accepted; anything else is rejected at load time. For each entry the loader

1. downloads a 2400 px rendition of the Commons original once (kept under
   ``data/archive/commons/``; ``Special:FilePath?width=`` serves the original when it is smaller),
2. writes ``web/public/venues/<venue_id>-1600.webp`` (1600x600 cover crop) and
   ``<venue_id>-640.webp`` (640x400 card crop), both cropped around the entry's ``focus``
   point (fractions of width/height, default centre),
3. upserts ``venue_media`` with the web paths and the attribution (author, licence, licence URL,
   Commons file page) the licences require wherever the photo is shown.

Polite: sequential requests with a descriptive User-Agent, a gap between downloads and
retries with backoff. Run ``p11 media venues [--force]``.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps
from sqlalchemy import Connection, text

from p11.core.settings import REPO_ROOT, get_settings
from p11.core.upsert import upsert

CURATED = REPO_ROOT / "data" / "raw" / "media" / "venue_images.json"
OUT_DIR = REPO_ROOT / "web" / "public" / "venues"
WEB_PREFIX = "/venues"
COVER = (1600, 600)
CARD = (640, 400)
DOWNLOAD_WIDTH = 2400
WEBP_QUALITY = 78
USER_AGENT = "Predict11/0.1 (+https://github.com/Janu-Chaudhary/Predict-11)"
REQUEST_GAP_S = 1.0
RETRIES = 3

_FREE = re.compile(r"^(cc0\b|cc by(-sa)? \d|public domain\b|pd\b)", re.I)


@dataclass(frozen=True)
class Entry:
    venue_id: int
    venue_name: str
    file: str
    file_page: str
    source_url: str
    author: str
    license: str
    license_url: str | None
    focus: tuple[float, float] = (0.5, 0.5)


@dataclass
class Report:
    entries: int = 0
    written: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    errors: dict[int, str] = field(default_factory=dict)
    unknown_venues: list[int] = field(default_factory=list)
    changes: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return vars(self)


# --------------------------------------------------------------------------- pure helpers
def strip_html(s: str) -> str:
    """Commons ``Artist`` metadata is HTML (links, spans); keep the visible text only."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def is_free_license(name: str) -> bool:
    return bool(_FREE.match(name.strip()))


def web_paths(venue_id: int) -> tuple[str, str]:
    return (
        f"{WEB_PREFIX}/{venue_id}-{COVER[0]}.webp",
        f"{WEB_PREFIX}/{venue_id}-{CARD[0]}.webp",
    )


def parse_entries(raw: dict[str, Any]) -> list[Entry]:
    out = []
    for e in raw["venues"]:
        lic = e["license"].strip()
        if not is_free_license(lic):
            raise ValueError(f"venue {e['venue_id']}: licence {lic!r} is not a free licence")
        fx, fy = e.get("focus", (0.5, 0.5))
        out.append(
            Entry(
                venue_id=int(e["venue_id"]),
                venue_name=e["venue_name"],
                file=e["file"],
                file_page=e["file_page"],
                source_url=e["source_url"],
                author=strip_html(e["author"]) or "Unknown author",
                license=lic,
                license_url=e.get("license_url") or None,
                focus=(float(fx), float(fy)),
            )
        )
    return out


def cover_crop(
    img: Image.Image, size: tuple[int, int], focus: tuple[float, float] = (0.5, 0.5)
) -> Image.Image:
    """Largest box of ``size``'s aspect ratio inside ``img``, centred on ``focus`` (clamped to
    the frame), resized to ``size``."""
    w, h = img.size
    tw, th = size
    if w / h > tw / th:  # wider than the target: full height, slide horizontally
        ch, cw = h, round(h * tw / th)
    else:
        cw, ch = w, round(w * th / tw)
    cx, cy = focus[0] * w, focus[1] * h
    x = int(min(max(cx - cw / 2, 0), w - cw))
    y = int(min(max(cy - ch / 2, 0), h - ch))
    return img.crop((x, y, x + cw, y + ch)).resize(size, Image.Resampling.LANCZOS)


def to_webp(data: bytes, size: tuple[int, int], focus: tuple[float, float]) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        rgb = ImageOps.exif_transpose(im).convert("RGB")
        out = cover_crop(rgb, size, focus)
        buf = io.BytesIO()
        out.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
        return buf.getvalue()


# --------------------------------------------------------------------------- network
def download_url(entry: Entry, width: int = DOWNLOAD_WIDTH) -> str:
    name = urllib.parse.quote(entry.file.removeprefix("File:").replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{name}?width={width}"


def http_fetch(client: httpx.Client, url: str) -> bytes:
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            r = client.get(url)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
            r.raise_for_status()
            return r.content
        except httpx.HTTPError as e:
            last = e
            time.sleep(5.0 * (attempt + 1))
    raise RuntimeError(f"{type(last).__name__}: {last}")


# --------------------------------------------------------------------------- load
def load_venue_media(
    conn: Connection,
    *,
    curated: Path = CURATED,
    out_dir: Path = OUT_DIR,
    cache_dir: Path | None = None,
    force: bool = False,
    fetch: Callable[[str], bytes] | None = None,
    gap_s: float = REQUEST_GAP_S,
) -> dict[str, Any]:
    entries = parse_entries(json.loads(curated.read_text()))
    cache_dir = cache_dir or get_settings().raw_archive_dir / "commons"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    known = {r[0] for r in conn.execute(text("SELECT id FROM venue"))}
    have = dict(conn.execute(text("SELECT venue_id, source_url FROM venue_media")).all())

    client: httpx.Client | None = None
    if fetch is None:
        client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=90.0, follow_redirects=True
        )

        def fetch(url: str) -> bytes:
            assert client is not None
            return http_fetch(client, url)

    rep = Report(entries=len(entries))
    rows = []
    try:
        for e in entries:
            if e.venue_id not in known:
                rep.unknown_venues.append(e.venue_id)
                continue
            cover_path, card_path = web_paths(e.venue_id)
            files = [out_dir / Path(p).name for p in (cover_path, card_path)]
            row = {
                "venue_id": e.venue_id,
                "image_path": cover_path,
                "thumb_path": card_path,
                "source_url": e.source_url,
                "file_page": e.file_page,
                "author": e.author,
                "license": e.license,
                "license_url": e.license_url,
            }
            if (
                not force
                and have.get(e.venue_id) == e.source_url
                and all(f.exists() for f in files)
            ):
                rep.skipped.append(e.venue_id)
                rows.append(row)  # attribution edits still reach the table
                continue
            try:
                key = hashlib.sha1(e.source_url.encode()).hexdigest()[:12]
                raw_file = cache_dir / f"{e.venue_id}-{key}.img"
                if raw_file.exists():  # keyed by source URL; --force only re-crops
                    data = raw_file.read_bytes()
                else:
                    data = fetch(download_url(e))
                    raw_file.write_bytes(data)
                    time.sleep(gap_s)
                for f, size in zip(files, (COVER, CARD), strict=True):
                    tmp = f.with_name(f".{f.name}.tmp")
                    tmp.write_bytes(to_webp(data, size, e.focus))
                    tmp.replace(f)
                rep.written.append(e.venue_id)
                rows.append(row)
            except Exception as err:  # one bad image must not stop the batch
                rep.errors[e.venue_id] = f"{type(err).__name__}: {err}"
    finally:
        if client is not None:
            client.close()
    rep.changes = vars(upsert(conn, "venue_media", rows, ["venue_id"]))
    return rep.as_dict()
