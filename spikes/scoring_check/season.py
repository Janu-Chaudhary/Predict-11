"""Season totals per player under rule variants, for comparing with published season
fantasy-point totals. Usage: season.py <season> <before_date> name=ROLE ...
Prints per-match breakdown and totals for HIGHEST/STACK milestone variants."""
import json, sys
from dataclasses import replace
from common import _z, score
from p11.scoring import Role, T20_2026, T20_2025, MilestoneMode, HaulMode

season, before = sys.argv[1], sys.argv[2]
want = {}
for a in sys.argv[3:]:
    n, r = a.rsplit("=", 1)
    want[n] = Role(r)

base = T20_2026 if season == "2026" else T20_2025
variants = {
    "default": base,
    "mstack": replace(base, milestone_mode=MilestoneMode.STACK_BELOW_CENTURY),
    "hstack": replace(base, haul_mode=HaulMode.STACK),
    "no_cb_catch": replace(base, caught_and_bowled_counts_as_catch=False),
}
tot = {v: {p: 0 for p in want} for v in variants}
cnt = {p: 0 for p in want}
for n in sorted(_z.namelist(), key=lambda n: json.loads(_z.read(n))["info"]["dates"][0] if n.endswith('.json') else ''):
    if not n.endswith(".json"):
        continue
    info = json.loads(_z.read(n))["info"]
    d = info["dates"][0]
    if not (d.startswith(season) and d < before):
        continue
    if not any(p in ps for ps in info["players"].values() for p in want):
        continue
    for v, rs in variants.items():
        m, s = score(n[:-5], want, rs)
        for p in want:
            if p in s.players:
                tot[v][p] += s[p].total
                if v == "default":
                    cnt[p] += 1
                    st = s[p].stats
                    print(f"{n[:-5]} {d} {p:22s} {s[p].total:4d}  r{st.runs}({st.balls_faced}) w{st.wickets} c{st.catches} "
                          + " ".join(f"{k}={x}" for k, x in s[p].items.items() if x))
for p in want:
    print(p, cnt[p], {v: tot[v][p] for v in variants})
