"""Single-match source points derived from two consecutive khelnow season totals with
exactly one (non-no-result) match in between, vs our per-match score."""
from check_totals import CASES, FILES, scored, season_total
import json
from common import _z

by = {}
for name, role, before, src, cmp, tag in CASES:
    if cmp == "=":
        by.setdefault((name, role), []).append((before, src, tag))
for (name, role), pts in by.items():
    pts.sort()
    for (b1, s1, t1), (b2, s2, t2) in zip(pts, pts[1:]):
        mids = []
        for dt, mid in FILES:
            if b1 <= dt < b2:
                info = json.loads(_z.read(f"{mid}.json"))["info"]
                if any(name in ps for ps in info["players"].values()) and \
                        info.get("outcome", {}).get("result") != "no result":
                    mids.append((dt, mid))
        ours = sum(scored(m, "default", ((name, role),))[name].total for _, m in mids)
        detail = ""
        if len(mids) == 1:
            ps = scored(mids[0][1], "default", ((name, role),))[name]
            st = ps.stats
            detail = (f"r{st.runs}({st.balls_faced}) {st.fours}x4 {st.sixes}x6 w{st.wickets} c{st.catches} | "
                      + " ".join(f"{k}={v}" for k, v in ps.items.items() if v))
        print(f"{name:16s} {[m for _, m in mids]} src={s2 - s1} ours={ours} {detail}")
