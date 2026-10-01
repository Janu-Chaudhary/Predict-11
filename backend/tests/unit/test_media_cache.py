"""Player photo cache: square crop + WebP encode (pure, no network)."""

from __future__ import annotations

import io

from PIL import Image

from p11.ingest.media_cache import local_paths, square_top, to_webp


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), (200, 30, 30, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_square_top_keeps_the_top_of_portraits() -> None:
    im = Image.new("RGB", (100, 160), (0, 0, 255))
    im.paste((255, 0, 0), (0, 0, 100, 10))  # the "head" at the very top
    sq = square_top(im)
    assert sq.size == (100, 100) and sq.getpixel((50, 0)) == (255, 0, 0)
    assert square_top(Image.new("RGB", (160, 100))).size == (100, 100)


def test_to_webp_resizes_and_shrinks() -> None:
    src = _png(1000, 1200)
    for size in (256, 96):
        out = to_webp(src, size)
        with Image.open(io.BytesIO(out)) as im:
            assert (im.format, im.size) == ("WEBP", (size, size))
        assert len(out) < len(src)


def test_local_paths_are_web_relative() -> None:
    assert local_paths("ba607b88") == {
        256: "/players/ba607b88-256.webp",
        96: "/players/ba607b88-96.webp",
    }
