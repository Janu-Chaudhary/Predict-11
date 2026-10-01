"""How a player is shown: full display name and photo URL, plus the name index used by search.

- ``display_name``: the ``player_alias`` row with ``source='display'`` (see
  ``p11.registry.display_names``), falling back to the Cricsheet name.
- ``image_url``: the locally cached 256 px WebP (``/players/<id>-256.webp``, written by
  ``p11 media cache`` and served by the web app from /public) when cached, else the resolved
  remote headshot URL, else None.

Both change independently of the ``match`` table, so they use a short TTL cache rather than the
match-fingerprint cache in ``players_data``.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from sqlalchemy import Connection, text

from .players_models import PlayerRef

TTL_S = 60.0


@dataclass(frozen=True, slots=True)
class Identity:
    name: str
    display_name: str
    image_url: str | None


@dataclass(frozen=True, slots=True)
class NameEntry:
    player_id: str
    name: str  # as stored
    norm: str  # lower-case, dots/hyphens/apostrophes -> spaces, single-spaced
    compact: str  # norm without spaces ("suryakumar yadav" -> "suryakumaryadav")
    primary: bool  # Cricsheet name / display name, not a register alias (which can be noisy)


_lock = threading.Lock()
_cache: dict[tuple[str, str], tuple[float, object]] = {}


def _ttl_cached[T](conn: Connection, name: str, build: Callable[[Connection], T]) -> T:
    key = (str(conn.engine.url), name)
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < TTL_S:
        return hit[1]  # type: ignore[return-value]
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < TTL_S:
            return hit[1]  # type: ignore[return-value]
        value = build(conn)
        _cache[key] = (time.monotonic(), value)
        return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()


_NORM_RE = re.compile(r"[.\-'’`]+")


def normalize(s: str) -> str:
    return " ".join(_NORM_RE.sub(" ", s.lower()).split())


# --------------------------------------------------------------------------- identity
def _build_identities(conn: Connection) -> dict[str, tuple[str | None, str | None]]:
    rows = conn.execute(
        text(
            """
            SELECT p.id, d.name, coalesce(m.local_path, m.image_url)
            FROM player p
            LEFT JOIN LATERAL (
              SELECT a.name FROM player_alias a
              WHERE a.player_id = p.id AND a.source = 'display' ORDER BY a.name LIMIT 1
            ) d ON true
            LEFT JOIN player_media_resolved m ON m.player_id = p.id
            WHERE d.name IS NOT NULL OR m.player_id IS NOT NULL
            """
        )
    )
    return {r[0]: (r[1], r[2]) for r in rows}


def _identities(conn: Connection) -> dict[str, tuple[str | None, str | None]]:
    return _ttl_cached(conn, "identities", _build_identities)


def identity(conn: Connection, pid: str, name: str) -> Identity:
    disp, img = _identities(conn).get(pid, (None, None))
    return Identity(name=name, display_name=disp or name, image_url=img)


def player_refs(conn: Connection, ids: Iterable[str]) -> dict[str, PlayerRef]:
    """id -> PlayerRef (Cricsheet name + display name + photo) for known players."""
    ids = list(set(ids))
    if not ids:
        return {}
    names = dict(
        conn.execute(text("SELECT id, name FROM player WHERE id = ANY(:ids)"), {"ids": ids}).all()
    )
    out = {}
    for pid, name in names.items():
        ident = identity(conn, pid, name)
        out[pid] = PlayerRef(
            id=pid, name=name, display_name=ident.display_name, image_url=ident.image_url
        )
    return out


def ref_or_id(refs: dict[str, PlayerRef], pid: str) -> PlayerRef:
    return refs.get(pid) or PlayerRef(id=pid, name=pid)


# --------------------------------------------------------------------------- search index
def _build_name_index(conn: Connection) -> list[NameEntry]:
    rows = conn.execute(
        text(
            """
            SELECT pid, name, primary_ FROM (
              SELECT id AS pid, name, true AS primary_, 1 AS rk FROM player
              UNION ALL SELECT id, unique_name, true, 2 FROM player
              UNION ALL SELECT player_id, name, source IN ('display', 'display_alt'),
                CASE source WHEN 'display' THEN 0 WHEN 'display_alt' THEN 3 ELSE 4 END
              FROM player_alias
            ) x ORDER BY rk  -- on equal quality the first spelling (display name) is reported
            """
        )
    )
    best: dict[tuple[str, str], NameEntry] = {}
    for pid, name, primary in rows:
        n = normalize(name)
        if n and (pid, n) not in best:
            best[(pid, n)] = NameEntry(pid, name, n, n.replace(" ", ""), bool(primary))
    return list(best.values())


def name_index(conn: Connection) -> list[NameEntry]:
    return _ttl_cached(conn, "name_index", _build_name_index)


def match_quality(entry: NameEntry, q: str, tokens: list[str]) -> int | None:
    """Lower is better; None = no match. Tiers: exact full name, every query token prefixes a
    word, substring; within a tier, Cricsheet/display names beat register aliases. A one-word
    exact hit ("Sharma") is only a word-prefix hit: it says nothing about which Sharma."""
    qc = q.replace(" ", "")
    words = entry.norm.split()
    if (entry.norm == q or entry.compact == qc) and len(words) > 1:
        tier = 0
    elif all(any(w.startswith(t) for w in words) for t in tokens) or entry.compact.startswith(qc):
        tier = 1
    elif all(t in entry.norm for t in tokens) or qc in entry.compact:
        tier = 2
    else:
        return None
    return tier * 2 + (0 if entry.primary else 1)
