"""List 2025/2026 IPL candidate performances: 50-99 runs, 4+ wkts, caught&bowled."""
from common import _z, score

for n in sorted(_z.namelist()):
    if not n.endswith(".json"):
        continue
    mid = n[:-5]
    import json
    info = json.loads(_z.read(n))["info"]
    d = info["dates"][0]
    if d < "2025-03-22":
        continue
    m, s = score(mid)
    teams = " v ".join(info["teams"])
    for p, ps in s.players.items():
        st = ps.stats
        tags = []
        if 50 <= st.runs <= 99: tags.append(f"{st.runs}({st.balls_faced})")
        if st.wickets >= 3: tags.append(f"{st.wickets}w")
        if any(True for _ in []): pass
        if tags:
            print(mid, d, teams, "|", p, " ".join(tags))
    for inn in m["innings"]:
        for o in inn["overs"]:
            for dd in o["deliveries"]:
                for w in dd.get("wickets", []):
                    if w["kind"] == "caught and bowled":
                        print(mid, d, teams, "|", dd["bowler"], "C&B of", w["player_out"])
