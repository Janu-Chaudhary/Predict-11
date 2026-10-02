"""Archived iplt20 headshots for players with no current photo -> ``player_media``.

Input: data/raw/media/player_images_archive.json (list of {player_id, name, url, season, ...}),
built from the iplt20 BFF past-squad pages (``/api/bff/cms/teams/<slug>?tab=squad&season=Y``)
and verified to be transparent PNGs, not the SVG silhouette iplt20 serves when a season has
no photo. Keyed by our player_id already, so no name matching happens here.

Source name ``iplt20_archive``; ``player_media_resolved`` prefers the newest ``image_season``,
so a current-squad photo (bcci / iplt20_2025) always wins over an archive one. Run
``uv run python -m p11.ingest.media_archive`` then ``p11 media cache --all`` to download the
local WebPs (the iplt20 asset host is slow, 10-40 s per image).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from p11.core.settings import REPO_ROOT
from p11.core.upsert import upsert

SOURCE = "iplt20_archive"
DEFAULT_FILE = REPO_ROOT / "data" / "raw" / "media" / "player_images_archive.json"


def load_archive(conn: Connection, path: Path = DEFAULT_FILE) -> dict[str, Any]:
    entries = json.loads(path.read_text())
    known = {r[0] for r in conn.execute(text("SELECT id FROM player"))}
    rows, unknown = [], []
    for e in entries:
        if e.get("transparent") is False or e["player_id"] not in known:
            unknown.append(e["player_id"])
            continue
        rows.append(
            {
                "player_id": e["player_id"],
                "source": SOURCE,
                "image_url": e["url"],
                "image_season": int(e["season"]),
            }
        )
    changes = upsert(
        conn,
        "player_media",
        rows,
        ["player_id", "source"],
        delete_missing=(["source"], [(SOURCE,)]),
    )
    return {"file": str(path), "entries": len(entries), "loaded": len(rows),
            "skipped": unknown, "changes": str(changes)}  # fmt: skip


if __name__ == "__main__":
    from p11.core import db

    with db.engine().begin() as conn:
        print(json.dumps(load_archive(conn), indent=2))
