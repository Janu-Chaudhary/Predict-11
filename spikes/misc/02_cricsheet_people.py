"""Probe 02: people.csv / names.csv coverage for IPL 2026 players + 2026 tie/super-over check."""
import json, zipfile
import pandas as pd
from pathlib import Path

S = Path(__file__).parent / "samples"
people = pd.read_csv(S / "people.csv", dtype=str)
names = pd.read_csv(S / "names.csv", dtype=str)
print("people.csv rows/cols:", people.shape, list(people.columns))
print("names.csv rows/cols:", names.shape, list(names.columns))

ids, appeared = set(), set()
tie = None
with zipfile.ZipFile(S / "ipl_json.zip") as z:
    for n in z.namelist():
        if not n.endswith(".json"):
            continue
        m = json.loads(z.read(n))
        if str(m["info"]["season"]) != "2026":
            continue
        reg = m["info"]["registry"]["people"]
        for team, pl in m["info"]["players"].items():
            for p in pl:
                ids.add(reg[p])
        if m["info"]["outcome"].get("result") == "tie":
            tie = m
print("unique IPL 2026 players (in players lists):", len(ids))
sub = people[people["identifier"].isin(ids)]
print("found in people.csv:", len(sub))
for c in [c for c in people.columns if c.startswith("key_")]:
    print(f"  {c}: {sub[c].notna().sum()}/{len(sub)}  (all people: {people[c].notna().sum()}/{len(people)})")
print("sample rows:\n", sub.head(5).to_string())
if tie:
    print("2026 tie:", tie["info"]["teams"], tie["info"]["outcome"])
    print("innings:", [(i["team"], i.get("super_over"), len(i["overs"])) for i in tie["innings"]])
