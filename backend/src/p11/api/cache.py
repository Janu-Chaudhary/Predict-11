"""HTTP cache helpers shared by the routers.

``BUILD_ID`` changes every time the API process starts (each deploy, and each ``--reload`` after
a code change), so weak ETags = data fingerprint + BUILD_ID. Without it, a browser holding a
response from older code gets ``304 Not Modified`` and keeps the old shape (e.g. new fields
missing) until the *data* changes.
"""

from __future__ import annotations

import os
import time

BUILD_ID = f"{time.time_ns():x}"[-8:] + f"{os.getpid():x}"


def weak_etag(fingerprint: str, prefix: str = "") -> str:
    return f'W/"{prefix}{fingerprint}-{BUILD_ID}"'
