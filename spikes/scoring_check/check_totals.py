"""Compare published cumulative season fantasy-point totals (khelnow.com IPL 2026
'Top 5 Dream11 fantasy picks' articles) with our scorer under rule variants.

Each case: (cricsheet name, role, cutoff date (exclusive), cutoff file to exclude or None,
source total, source tag). Source totals are the player's season total *before* the
match the article previews.
"""
import json
from dataclasses import replace
from functools import lru_cache

from common import _z, score
from p11.scoring import HaulMode, MilestoneMode, Role, T20_2025, T20_2026

B, W, A, BW = Role.BAT, Role.WK, Role.AR, Role.BOWL

# (name, role, before_date, source_total, cmp, source)
CASES = [
    # RCB v GT Final preview, published 2026-05-30 (before final 2026-05-31)
    ("Shubman Gill", B, "2026-05-31", 1522, "=", "khelnow rcb-vs-gt ...202605"),
    ("RM Patidar", B, "2026-05-31", 1066, "=", "khelnow rcb-vs-gt ...202605"),
    ("V Kohli", B, "2026-05-31", 1244, "=", "khelnow rcb-vs-gt ...202605"),
    ("B Sai Sudharsan", B, "2026-05-31", 1418, "=", "khelnow rcb-vs-gt ...202605"),
    ("K Rabada", BW, "2026-05-31", 1229, "=", "khelnow rcb-vs-gt ...202605"),
    # SRH v RR (Eliminator 2026-05-27), published 2026-05-27
    ("Abhishek Sharma", A, "2026-05-27", 1251, "=", "khelnow srh-vs-rr ...202605"),
    ("H Klaasen", W, "2026-05-27", 1238, "=", "khelnow srh-vs-rr ...202605"),
    ("Dhruv Jurel", W, "2026-05-27", 1060, "=", "khelnow srh-vs-rr ...202605"),
    # GT v RR Q2 (2026-05-29)
    ("B Sai Sudharsan", B, "2026-05-29", 1250, ">", "khelnow gt-vs-rr q2"),
    ("Shubman Gill", B, "2026-05-29", 1200, ">", "khelnow gt-vs-rr q2"),
    # KKR v DC match 70 (2026-05-24)
    ("SP Narine", A, "2026-05-24", 745, "=", "khelnow kkr-vs-dc m70"),
    ("KL Rahul", W, "2026-05-24", 1081, "=", "khelnow kkr-vs-dc m70"),
    # LSG v PBKS match 68 (2026-05-23)
    ("P Simran Singh", W, "2026-05-23", 929, "=", "khelnow lsg-vs-pbks m68"),
    ("C Connolly", A, "2026-05-23", 1000, ">", "khelnow lsg-vs-pbks m68"),
    # MI v RR match 69 (2026-05-24)
    ("V Suryavanshi", B, "2026-05-24", 1277, "=", "khelnow mi-vs-rr m69"),
    ("Dhruv Jurel", W, "2026-05-24", 972, "=", "khelnow mi-vs-rr m69"),
    ("RD Rickelton", W, "2026-05-24", 982, "=", "khelnow mi-vs-rr m69"),
    # CSK v SRH match 63 (2026-05-18)
    ("Abhishek Sharma", A, "2026-05-18", 1063, "=", "khelnow csk-vs-srh m63"),
    ("SV Samson", W, "2026-05-18", 954, "=", "khelnow csk-vs-srh m63"),
    ("TM Head", B, "2026-05-18", 757, "=", "khelnow csk-vs-srh m63"),
    # LSG v KKR match 38 (2026-04-26)
    ("MR Marsh", A, "2026-04-26", 418, "=", "khelnow lsg-vs-kkr m38"),
    ("RR Pant", W, "2026-04-26", 343, "=", "khelnow lsg-vs-kkr m38"),
    ("A Raghuvanshi", B, "2026-04-26", 403, "=", "khelnow lsg-vs-kkr m38"),
    # GT v PBKS match 46 (2026-05-03)
    ("Shubman Gill", B, "2026-05-03", 765, "=", "khelnow gt-vs-pbks m46"),
    ("P Simran Singh", W, "2026-05-03", 724, "=", "khelnow gt-vs-pbks m46"),
    ("Priyansh Arya", B, "2026-05-03", 613, "=", "khelnow gt-vs-pbks m46"),
    ("SS Iyer", B, "2026-05-03", 637, "=", "khelnow gt-vs-pbks m46"),
    # PBKS v RR match 40 (2026-04-28)
    ("P Simran Singh", W, "2026-04-28", 621, "=", "khelnow pbks-vs-rr m40"),
    ("YBK Jaiswal", B, "2026-04-28", 537, "=", "khelnow pbks-vs-rr m40"),
    ("Priyansh Arya", B, "2026-04-28", 544, "=", "khelnow pbks-vs-rr m40"),
    ("SS Iyer", B, "2026-04-28", 581, "=", "khelnow pbks-vs-rr m40"),
]
import sys, importlib
extra = importlib.import_module("cases_extra").CASES if __import__("os").path.exists(
    __import__("os").path.join(__import__("os").path.dirname(__file__), "cases_extra.py")) else []
CASES += extra

VARIANTS = {
    "default": {},
    "mstack": {"milestone_mode": MilestoneMode.STACK_BELOW_CENTURY},
    "hstack": {"haul_mode": HaulMode.STACK},
    "noCBcatch": {"caught_and_bowled_counts_as_catch": False},
    "noByeDot": {"dot_ball_counts_byes_legbyes": False},
    "superOver": {"count_super_over": True},
    "sub0": {"substitute_played": 0},
}

FILES = sorted(
    (json.loads(_z.read(n))["info"]["dates"][0], n[:-5])
    for n in _z.namelist() if n.endswith(".json")
)


@lru_cache(maxsize=None)
def scored(mid, variant, roles_key):
    d = dict(roles_key)
    date = next(dt for dt, m in FILES if m == mid)
    base = T20_2026 if date >= "2026" else T20_2025
    return score(mid, d, replace(base, **VARIANTS[variant]))[1]


def season_total(name, role, before, variant):
    season = before[:4]
    tot, n = 0, 0
    for dt, mid in FILES:
        if not (dt.startswith(season) and dt < before):
            continue
        info = json.loads(_z.read(f"{mid}.json"))["info"]
        if not any(name in ps for ps in info["players"].values()):
            continue
        if info.get("outcome", {}).get("result") == "no result":
            continue  # Dream11 awards nothing for abandoned / no-result matches
        s = scored(mid, variant, ((name, role),))
        tot += s[name].total
        n += 1
    return tot, n


if __name__ == "__main__":
    print(f"{'player':18s} {'before':10s} src   n " + " ".join(f"{v:>9s}" for v in VARIANTS))
    for name, role, before, src, cmp, tag in CASES:
        res = {v: season_total(name, role, before, v) for v in VARIANTS}
        n = res["default"][1]
        def ok(x):
            return x == src if cmp == "=" else x > src
        cells = " ".join(f"{res[v][0]:>8d}{'*' if ok(res[v][0]) else ' '}" for v in VARIANTS)
        print(f"{name:18s} {before} {cmp}{src:<5d}{n:2d} {cells}  {tag}")
