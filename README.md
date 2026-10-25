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

- v1 engine (rates + minutes + distributions + self-grading): Oct 28, 2026
- Full build (ML layer, usage redistribution, entry optimizer, backtest,
  dashboard): Nov 2, 2026
- Live calibration verdict: Dec 5, 2026

## Layout

- `src/` — engine code
- `data/` — local data cache (not committed)
- `tests/` — tests
- `docs/` — design decision log and build plan
