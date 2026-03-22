# Predict-11 🏏

An IPL fantasy cricket assistant that helps you build the best Dream11 team. Predict-11 combines live match data, historical ball-by-ball stats, and an ML-based scoring engine to suggest optimal fantasy squads — all through a clean, browser-based interface.

---

## Features

- **AI Fantasy Team Predictor** — Generates a recommended Dream11 squad for any IPL matchup using historical batting and bowling performance data
- **Live Match Scores** — Fetches real-time match data from an external cricket API with a local JSON fallback
- **Head-to-Head Stats** — Analyse any batter vs. bowler matchup with ball-by-ball breakdowns, strike rate, average, boundary %, and dot ball %
- **Points Table** — Live IPL standings with smart caching that refreshes only when a new match result comes in
- **Squad Browser** — View full team rosters with player roles, credits, and foreign-player status
- **Match Schedule** — Browse upcoming and completed IPL 2025 fixtures

---

## Project Structure

```
Predict-11/
├── Backend/
│   ├── app.py                  # Flask API server
│   ├── team.py                 # Dream11Predictor ML engine
│   ├── fetch_points_table.py   # Points table scraper
│   ├── Teams/                  # IPL squad CSV files (one per team)
│   ├── Static/public/          # JSON data files (match schedules, etc.)
│   ├── team_logos/             # Team logo images
│   ├── flags/                  # Country flag images
│   ├── requirements.txt
│   └── Procfile
├── Frontend/
│   ├── index.html              # Home / match schedule
│   ├── fantasy_team.html       # Fantasy team predictor UI
│   ├── head_to_head.html       # Batter vs. bowler analysis
│   ├── match.html              # Live match view
│   ├── points_table.html       # IPL standings
│   ├── squads.html             # Team squads browser
│   ├── squads.json             # Squad data
│   ├── points_table.js         # Points table logic
│   └── config.js               # Environment config (dev / prod URLs)
├── render.yaml                 # Render deployment config
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-CORS |
| Data processing | Pandas, NumPy |
| Server | Gunicorn |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Deployment | Render |

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/Predict-11.git
cd Predict-11

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the backend server
cd Backend
gunicorn app:app
# or for development:
python app.py
```

The server will start at `http://localhost:5000`.

### Running the Frontend

Open any of the HTML files in the `Frontend/` directory directly in your browser, or serve them with a simple HTTP server:

```bash
cd Frontend
python -m http.server 8080
```

Then visit `http://localhost:8080`.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/test` | Health check |
| GET | `/api/ipl_matches` | IPL 2025 match schedule |
| GET | `/api/live-matches` | Live / recent match data |
| GET | `/api/fantasy_team` | Generate recommended Dream11 squad |
| GET | `/points_table` | IPL standings (cached, auto-refreshes on new results) |
| POST | `/analyze` | Head-to-head batter vs. bowler stats |
| GET | `/results/<filename>` | Retrieve a saved head-to-head analysis |
| GET | `/static/<filename>` | Serve static assets |

### Example: Head-to-head analysis

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"batter": "Virat Kohli", "bowler": "Jasprit Bumrah"}'
```

---

## How the Fantasy Predictor Works

The `Dream11Predictor` class in `team.py` scores each player using historical IPL ball-by-ball data:

1. Loads batting and bowling JSON datasets and squad CSVs for all 10 IPL teams
2. Calculates a composite performance score per player based on recent form metrics
3. Applies Dream11 squad constraints — role limits (WK, BAT, AR, BOWL), a 100-credit cap, and a max 7 players per team rule
4. Returns an optimal 11-player squad with a suggested captain and vice-captain

---

## Deployment

The backend is configured to deploy on [Render](https://render.com) using the included `render.yaml`:

```yaml
services:
  - type: web
    name: cricket-stats-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
```

Update the `apiBaseUrl` in `Frontend/config.js` to point to your deployed Render URL for production.

---

## Data Sources

- Live match data — [The Hindu LiveScore API](https://livescoreapi.thehindu.com)
- Points table — Sportskeeda IPL standings API
- Historical ball-by-ball data — ball-by-ball CSV (`deliveries.csv`) for head-to-head analysis
- Squad data — manually curated CSVs in `Backend/Teams/`

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a pull request

---
