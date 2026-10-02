"""Venue photo fields shared by every response that carries a venue (additive, optional).

``venue_media`` is tiny (one row per ground), so it is read whole and kept in-process for
``TTL_S`` seconds; a re-run of ``p11 media venues`` shows up within that window.
"""

from __future__ import annotations

import threading
import time

from pydantic import BaseModel
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from p11.core import db

TTL_S = 300.0


class ImageCredit(BaseModel):
    author: str
    license: str
    license_url: str | None = None
    file_page: str


class VenueImageFields(BaseModel):
    """Mixin: ground photo (Wikimedia Commons) as local WebP paths plus required credit."""

    image_url: str | None = None
    thumb_url: str | None = None
    image_credit: ImageCredit | None = None


Media = dict[str, object]

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[int, Media]]] = {}


def _read(conn: Connection) -> dict[int, Media]:
    rows = conn.execute(
        text(
            "SELECT venue_id, image_path, thumb_path, author, license, license_url, file_page "
            "FROM venue_media"
        )
    ).mappings()
    return {
        r["venue_id"]: {
            "image_url": r["image_path"],
            "thumb_url": r["thumb_path"],
            "image_credit": ImageCredit(
                author=r["author"],
                license=r["license"],
                license_url=r["license_url"],
                file_page=r["file_page"],
            ),
        }
        for r in rows
    }


def media_map(conn: Connection | None = None) -> dict[int, Media]:
    """{venue_id: image fields}; empty when the table is missing or unreachable."""
    key = str(conn.engine.url) if conn is not None else "default"
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < TTL_S:
            return hit[1]
    try:
        if conn is not None:
            with conn.begin_nested():  # a missing table must not abort the caller's tx
                value = _read(conn)
        else:
            with db.engine().connect() as c:
                value = _read(c)
    except DBAPIError:
        value = {}
    with _lock:
        _cache[key] = (now, value)
    return value


def media_for(venue_id: int | None, conn: Connection | None = None) -> Media:
    """Keyword arguments for a model using ``VenueImageFields`` ({} when there is no photo)."""
    if venue_id is None:
        return {}
    return media_map(conn).get(venue_id, {})


def clear_cache() -> None:
    with _lock:
        _cache.clear()
