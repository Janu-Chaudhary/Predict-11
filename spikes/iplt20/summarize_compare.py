"""Run compare.py on normalized/*.json and print a compact per-match table. usage: summarize_compare.py"""
import json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).parent
files = sorted(str(p) for p in (HERE / "normalized").glob("*.json"))
out = subprocess.run([sys.executable, str(HERE.parent / "compare" / "compare.py"), *files],
                     capture_output=True, text=True, cwd=HERE.parents[1]).stdout
body, summ = out.rsplit("\nSUMMARY", 1)
dec, i, body = json.JSONDecoder(), 0, body.strip()
while i < len(body):
    r, i = dec.raw_decode(body, i)
    while i < len(body) and body[i].isspace():
        i += 1
    src = json.load(open(HERE / "normalized" / f"{r['cs']}.json"))
    unres = r["resolve"].get("unresolved", 0) + r["resolve"].get("ambiguous", 0)
    unres_played = [p["name"] for p in src["players"] if p["status"] != "sub"]
    print(f"{r['cs']} toss={r['toss_ok']} xi={r['xi_ok']} miss={r['xi_missing']} extra={r['xi_extra']} "
          f"innings={[('SO' if x['super_over'] else '') + str(x['inn']) + ('ok' if x['ok'] else 'BAD') for x in r['innings']]} "
          f"pm={r['player_mismatches']} bm={r['ball_mismatches']} resolve={r['resolve']}")
    for x in r["innings"]:
        if not x["ok"]:
            print("    ", x)
print("SUMMARY" + summ)
