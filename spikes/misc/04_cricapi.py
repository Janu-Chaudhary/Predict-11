"""Probe 04: CricketData.org (CricAPI) — what is reachable without a key."""
import requests
from pathlib import Path

S = Path(__file__).parent / "samples"
UA = {"User-Agent": "predict11-spike/0.1 (personal research)"}
B = "https://api.cricapi.com/v1/"
for ep, params in [("currentMatches", {}), ("currentMatches", {"apikey": ""}),
                   ("matches", {"apikey": "test"}), ("series", {"apikey": "test", "search": "IPL"}),
                   ("players", {"apikey": "test"}), ("match_scorecard", {"apikey": "test", "id": "x"}),
                   ("cricScore", {})]:
    try:
        r = requests.get(B + ep, params=params, headers=UA, timeout=20)
        print(f"{ep} {params}: HTTP {r.status_code} ct={r.headers.get('content-type')} body={r.text[:300]!r}")
    except Exception as e:
        print(ep, "ERR", e)
for url in ["https://cricketdata.org/", "https://cricketdata.org/how-to-use-cricket-data-api.aspx",
            "https://cricketdata.org/pricing.aspx", "https://cricketdata.org/member-test.aspx"]:
    try:
        r = requests.get(url, headers=UA, timeout=20)
        name = url.rstrip("/").split("/")[-1] or "home"
        (S / f"cricapi_{name}.html").write_text(r.text)
        print(url, r.status_code, len(r.text))
    except Exception as e:
        print(url, "ERR", e)
