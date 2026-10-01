"""Probe 03: Open-Meteo archive + forecast for Wankhede Stadium (no key)."""
import json, requests
from pathlib import Path

S = Path(__file__).parent / "samples"
LAT, LON = 18.9389, 72.8258  # Wankhede Stadium, Mumbai
HOURLY = "temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover,surface_pressure"
UA = {"User-Agent": "predict11-spike/0.1 (personal research)"}
DATE = "2026-04-12"  # RCB v MI at Wankhede, 7:30pm IST

calls = {
    "archive": ("https://archive-api.open-meteo.com/v1/archive",
                dict(latitude=LAT, longitude=LON, start_date=DATE, end_date=DATE, hourly=HOURLY, timezone="Asia/Kolkata")),
    "historical_forecast": ("https://historical-forecast-api.open-meteo.com/v1/forecast",
                            dict(latitude=LAT, longitude=LON, start_date=DATE, end_date=DATE, hourly=HOURLY, timezone="Asia/Kolkata")),
    "forecast": ("https://api.open-meteo.com/v1/forecast",
                 dict(latitude=LAT, longitude=LON, hourly=HOURLY, forecast_days=3, timezone="Asia/Kolkata")),
}
for name, (url, params) in calls.items():
    r = requests.get(url, params=params, headers=UA, timeout=30)
    print(f"{name}: HTTP {r.status_code} {r.url[:120]}...")
    j = r.json()
    (S / f"openmeteo_{name}.json").write_text(json.dumps(j, indent=1))
    if r.status_code != 200:
        print("  error:", j); continue
    h = j["hourly"]
    print("  units:", j.get("hourly_units"))
    print("  grid lat/lon/elev:", j.get("latitude"), j.get("longitude"), j.get("elevation"))
    for i, t in enumerate(h["time"]):
        if t[11:13] in ("18", "19", "20", "21", "22", "23"):
            dp = h["dew_point_2m"][i]; tt = h["temperature_2m"][i]
            print(f"  {t} T={tt} RH={h['relative_humidity_2m'][i]} Td={dp} spread={None if dp is None else round(tt-dp,1)} "
                  f"pr={h['precipitation'][i]} ws={h['wind_speed_10m'][i]} cc={h['cloud_cover'][i]}")
        if name == "forecast" and i > 47:
            break
    print("  rate-limit headers:", {k: v for k, v in r.headers.items() if "limit" in k.lower()})
