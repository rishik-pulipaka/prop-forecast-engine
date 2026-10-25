# Prop Forecast Engine

A probabilistic forecasting engine for NBA player props. Instead of point
predictions ("projects 7.2 assists"), the engine produces a full probability
distribution for each player stat, so every prop line gets an honest
probability — and the engine grades its own calibration every night against
real box scores.

## What it does

- Pulls player game logs, team pace, and opponent data from free public sources
  (NBA stats API).
- Projects minutes from rotation patterns, then converts recency-weighted
  per-minute rates into stat distributions.
- Adjusts for pace, matchup, and usage redistribution when players sit.
- Outputs P(over) / P(under) for any prop line, with the projection and the
  model's confidence side by side.
- Settles every projection nightly and tracks calibration by confidence
  bucket: when it says 65%, reality should hit ~65%.

## Status

- **v1 engine: LIVE (Oct 25, 2026 — ahead of the Oct 28 milestone).**
  Cached data pipeline, recency-weighted rates, minutes projection,
  distributions -> P(over/under), CLI, and nightly settle + calibration
  grading all working end-to-end on real players.
- Full build (ML layer, usage redistribution, entry optimizer, backtest,
  dashboard): Nov 2, 2026
- Live calibration verdict: Dec 5, 2026

## Usage

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Fetch + cache game logs for tonight's players (cache-first, safe to rerun)
.venv/bin/python scripts/fetch_players.py "Tyrese Maxey" "Domantas Sabonis"

# Project a prop (appends to the calibration store when a line is given)
.venv/bin/python -m src.cli --player "Tyrese Maxey" --stat PTS --line 26.5

# Settle past projections against box scores + calibration report
.venv/bin/python -m src.settle

# Tests
.venv/bin/python -m unittest discover -s tests -t .
```

Stats supported: PTS, REB, AST, PRA, R+A, P+R, P+A, FG3M, STL, BLK, TOV.

## Layout

- `src/` — engine code
- `data/` — local data cache (not committed)
- `tests/` — tests
- `docs/` — design decision log and build plan
