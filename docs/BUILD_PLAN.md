# Build Plan (started 2026-10-24)

## Milestones
- Wed Oct 28, 2026: v1 engine live — data pipeline, recency-weighted
  per-minute rates, minutes projection, stat distributions -> P(over/under),
  nightly settle + calibration log. Feeds the morning Pick6 build.
- Mon Nov 2, 2026: code-complete — gradient-boosting layer, usage
  redistribution for missing players, blowout-aware minutes, correlation-aware
  entry optimizer, historical backtest (2025-26 season), dashboard, GitHub
  packaging.
- Sat Dec 5, 2026: live calibration verdict after 5+ weeks of nightly
  self-grading.

## Ownership protocol (Rishik)
- Design decisions are presented to Rishik before each major component;
  decisions logged in docs/DECISIONS.md.
- Rishik hand-writes core modules (calibration grader, minutes model) with
  tutoring; reviews every push.
- Failure drills from the calibration log before interviews.

## Data sources (all free)
- NBA stats API via nba_api (game logs, pace, opponent stats)
- NBA official injury report
- The Odds API free tier (sportsbook lines) — key pending from Rishik
- Pick6 lines: app-only, no API anywhere; model benchmarks vs sportsbook lines

## Known risks
- stats.nba.com sometimes blocks datacenter IPs; fallbacks: cached Kaggle
  datasets, basketball-reference, Sportradar public pages.
