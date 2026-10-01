"""Download each resolved player headshot once and keep small local WebP copies.

The official iplt20 hosts serve ~1 MB PNGs and are slow (7-31 s per image), so the web app
shows ``web/public/players/<player_id>-{256,96}.webp`` instead. ``player_media`` records which
URL the files were made from (``cached_url``) and their web paths; ``player_media_resolved``
exposes the local paths only while that URL is still the resolved one.

Polite: at most ``CONCURRENCY`` downloads in flight, retries with backoff, and images already
cached from the same URL are skipped. Run ``p11 media cache [--season 2026 | --all]``.
"""

from __future__ import annotations

import datetime as dt
import io
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from sqlalchemy import Connection, text

from p11.core.settings import REPO_ROOT, get_settings

OUT_DIR = REPO_ROOT / "web" / "public" / "players"
WEB_PREFIX = "/players"
SIZES = (256, 96)
CONCURRENCY = 2
RETRIES = 3
TIMEOUT_S = 90.0
WEBP_QUALITY = 80


@dataclass
class Job:
    player_id: str
    source: str
    url: str


@dataclass
class Result:
    job: Job
    ok: bool
    seconds: float = 0.0
    bytes_in: int = 0
    bytes_out: dict[int, int] = field(default_factory=dict)
    error: str | None = None


def local_paths(player_id: str) -> dict[int, str]:
    return {s: f"{WEB_PREFIX}/{player_id}-{s}.webp" for s in SIZES}


def square_top(img: Image.Image) -> Image.Image:
    """Square crop that keeps the face: top-aligned for portraits, centred for landscapes."""
    w, h = img.size
    if h > w:
        return img.crop((0, 0, w, w))
    if w > h:
        x = (w - h) // 2
        return img.crop((x, 0, x + h, h))
    return img


def to_webp(data: bytes, size: int) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        sq = square_top(im.convert(mode))
        sq = sq.resize((size, size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        sq.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
        return buf.getvalue()


def select_jobs(
    conn: Connection, seasons: list[int] | None, *, force: bool = False, out_dir: Path = OUT_DIR
) -> list[Job]:
    """Resolved headshots of players who appeared in ``seasons`` (None = everyone with media),
    minus those already cached from the same URL with files on disk."""
    where = ""
    params: dict[str, Any] = {}
    if seasons:
        where = """
          WHERE m.player_id IN (
            SELECT mp.player_id FROM match_player_resolved mp
            JOIN match x ON x.id = mp.match_id JOIN season s ON s.id = x.season_id
            WHERE s.year = ANY(:seasons)
              AND mp.role_in_match IN ('xi', 'impact_in', 'impact_out'))"""
        params["seasons"] = seasons
    rows = conn.execute(
        text(
            f"""
            SELECT m.player_id, m.image_source, m.image_url, pm.cached_url
            FROM player_media_resolved m
            JOIN player_media pm ON pm.player_id = m.player_id AND pm.source = m.image_source
            {where}
            ORDER BY m.player_id
            """
        ),
        params,
    ).all()
    jobs = []
    for pid, source, url, cached_url in rows:
        files_ok = all((out_dir / f"{pid}-{s}.webp").exists() for s in SIZES)
        if force or cached_url != url or not files_ok:
            jobs.append(Job(pid, source, url))
    return jobs


class PlaceholderImage(Exception):
    pass


def _fetch(client: httpx.Client, url: str) -> bytes:
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            r = client.get(url)
            r.raise_for_status()
            if "svg" in r.headers.get("content-type", ""):
                # the iplt20 host answers unknown players with a generic silhouette SVG
                raise PlaceholderImage("placeholder silhouette (no real photo)")
            return r.content
        except PlaceholderImage:
            raise
        except (httpx.HTTPError, httpx.StreamError) as e:
            last = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"{type(last).__name__}: {last}")


def _run_one(client: httpx.Client, job: Job, out_dir: Path) -> Result:
    t = time.perf_counter()
    try:
        data = _fetch(client, job.url)
        sizes: dict[int, int] = {}
        for s in SIZES:
            webp = to_webp(data, s)
            tmp = out_dir / f".{job.player_id}-{s}.webp.tmp"
            tmp.write_bytes(webp)
            tmp.replace(out_dir / f"{job.player_id}-{s}.webp")
            sizes[s] = len(webp)
        return Result(job, True, time.perf_counter() - t, len(data), sizes)
    except Exception as e:  # one bad image must not stop the batch
        return Result(job, False, time.perf_counter() - t, error=str(e)[:200])


def record(conn: Connection, results: Iterable[Result]) -> int:
    n = 0
    now = dt.datetime.now(dt.UTC)
    for r in results:
        if not r.ok:
            continue
        paths = local_paths(r.job.player_id)
        n += conn.execute(
            text(
                "UPDATE player_media SET cached_url = :u, local_path = :p, "
                "local_thumb_path = :t, cached_at = :now "
                "WHERE player_id = :pid AND source = :src AND image_url = :u"
            ),
            {"u": r.job.url, "p": paths[256], "t": paths[96], "now": now,
             "pid": r.job.player_id, "src": r.job.source},
        ).rowcount
    return n


def cache_media(
    conn: Connection,
    seasons: list[int] | None = None,
    *,
    force: bool = False,
    limit: int | None = None,
    out_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = select_jobs(conn, seasons, force=force, out_dir=out_dir)
    if limit is not None:
        jobs = jobs[:limit]
    t0 = time.perf_counter()
    headers = {"User-Agent": get_settings().http_user_agent}
    with (
        httpx.Client(headers=headers, timeout=TIMEOUT_S, follow_redirects=True) as client,
        ThreadPoolExecutor(max_workers=CONCURRENCY) as pool,
    ):
        results = list(pool.map(lambda j: _run_one(client, j, out_dir), jobs))
    updated = record(conn, results)
    ok = [r for r in results if r.ok]
    secs = sorted(r.seconds for r in ok)

    def kb(xs: list[int]) -> float | None:
        return round(sum(xs) / len(xs) / 1024, 1) if xs else None

    return {
        "jobs": len(jobs),
        "cached": len(ok),
        "failed": [f"{r.job.player_id}: {r.error}" for r in results if not r.ok],
        "rows_updated": updated,
        "wall_s": round(time.perf_counter() - t0, 1),
        "per_image_s": {
            "median": round(secs[len(secs) // 2], 1) if secs else None,
            "max": round(secs[-1], 1) if secs else None,
        },
        "avg_kb": {
            "original": kb([r.bytes_in for r in ok]),
            **{f"webp_{s}": kb([r.bytes_out[s] for r in ok]) for s in SIZES},
        },
    }
