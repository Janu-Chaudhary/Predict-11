# Predict-11 — IPL Dream11 Fantasy XI Predictor

A from-scratch rebuild: a **trained ML model + constraint optimizer** that picks
an optimal Dream11 fantasy XI for an IPL fixture, validated by a **walk-forward
backtest** against real historical fantasy points.

This replaces the original heuristic project (hand-tuned weights, scraping trapped
in notebooks, no evaluation). Here the prediction is learned and measured.

```
Cricsheet YAML ─► DuckDB ─► Dream11 scoring (labels) ─► leak-safe features
                                                              │
                                          LightGBM regressor (predicted FP/player)
                                                              │
   temporal backtest vs baselines  ◄────────────┬───────────►  PuLP optimizer (XI + C/VC)
   (random / form / oracle)                      │                       │
                                                 ▼                       ▼
                                          FastAPI  ──────────────►  single-page UI
```

## Why this design

| Concern | Old project | This rebuild |
|---|---|---|
| Prediction | hand-tuned heuristic, never measured | LightGBM trained on 17 seasons, backtested |
| Data source | Selenium scraping + unquoted CSV (comma-in-venue bugs) | structured **Cricsheet YAML → DuckDB** |
| Ground truth | none | Dream11 points reconstructed from ball-by-ball |
| Leakage | n/a | features use only strictly-prior matches (`shift(1)`) |
| Selection | greedy with hardcoded fixture | **ILP** optimizer, exact C/VC modelling, real constraints |
| Evaluation | none | walk-forward backtest vs random / form / oracle |
| Architecture | 1 file, 4 concerns, dead code | layered package: `data / scoring / features / model / optimize / api` |

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .

# build everything: ingest -> labels+features -> train -> backtest
predict11 all

# predict an XI for a fixture
predict11 predict chennai-super-kings mumbai-indians

# run the web app  ->  http://127.0.0.1:8000
predict11 serve
```

(If not installing the package, prefix commands with `PYTHONPATH=src python -m predict11.cli`.)

## Pipeline stages

| Stage | Module | What it does |
|---|---|---|
| Ingest | `data/ingest.py` | 884 Cricsheet YAMLs → `matches`, `deliveries`, `playing_xi` (DuckDB) |
| Scoring | `scoring/fantasy_points.py` | Dream11 T20 rules → actual fantasy points per player per match (**labels**) |
| Features | `features/build.py` | leak-safe pre-match features (form, venue, opponent, consistency, role) |
| Model | `model/train.py` | LightGBM regressor, temporal split, MAE/RMSE/Spearman |
| Backtest | `model/backtest.py` | walk-forward XI selection vs baselines |
| Optimize | `optimize/select_xi.py` | PuLP ILP: best XI + captain/vice under Dream11 constraints |
| Serve | `api/` | FastAPI + single-page frontend |

## Current results (test seasons 2023–2025, 159 matches)

| Strategy | Mean realized XI points |
|---|---|
| Oracle (hindsight) | 921 |
| **Model** | **565** |
| Form heuristic (≈ old approach) | 562 |
| Random legal XI | 487 |

Model beats random 70% of matches and edges the form heuristic (57%); captain lands
in the match's actual top-3 scorers 25.8% of the time. Per-match fantasy scoring is
inherently high-variance, so the ML edge over recent form is real but modest — and
honestly reported rather than inflated.

## Data

Source: [Cricsheet](https://cricsheet.org/) ball-by-ball IPL data (YAML), already
under `data/raw/cricsheet_ipl/` (gitignored). Squad metadata (role, credits,
overseas) from the `data/raw/Teams/*.csv` files. See `predict11 ingest` to rebuild
the DuckDB from raw. No live scraping is required to run the project.

## Tests

```bash
pytest            # scoring rules, optimizer constraints, leak-safety, API contract
```

## Layout

```
src/predict11/{data,scoring,features,model,optimize,api}/   # one concern per package
frontend/index.html                                         # single-page UI
data/raw/{cricsheet_ipl,Teams}/                             # inputs (gitignored)
data/curated/predict11.duckdb                               # built artifact
models/lgbm_fp.txt                                          # trained model
tests/                                                      # unit + integration
```
