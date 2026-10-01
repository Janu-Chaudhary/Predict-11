"""Probe 12: do the off-the-shelf libraries work today? (run with .venv-libs)"""
import time, traceback
print("--- python-espncricinfo 0.5.8 (legacy /matches/engine/match/<id>.json + core.espnuk.org + hsapi)")
try:
    from espncricinfo.match import Match
    t = time.time(); m = Match(1535465); print("OK", m.description, f"{time.time()-t:.1f}s")
except Exception as e:
    print("FAIL", type(e).__name__, str(e)[:300])
time.sleep(1.5)
print("--- cricdata 0.3.2 (curl_cffi impersonate=chrome SSR __NEXT_DATA__ + site.web.api.espn.com)")
try:
    from cricdata import CricinfoClient
    c = CricinfoClient()
    t = time.time(); sc = c.match_scorecard("ipl-2026-1510719", "royal-challengers-bengaluru-vs-gujarat-titans-final-1535465")
    print("scorecard OK", type(sc).__name__, list(sc.keys())[:6] if hasattr(sc, "keys") else "", f"{time.time()-t:.1f}s")
    time.sleep(1.5)
    t = time.time(); bbb = c.match_ball_by_ball("ipl-2026-1510719", "royal-challengers-bengaluru-vs-gujarat-titans-final-1535465")
    print("ball_by_ball OK innings:", [len(i) for i in bbb], f"{time.time()-t:.1f}s")
except Exception as e:
    print("FAIL", type(e).__name__, str(e)[:300]); traceback.print_exc(limit=2)
