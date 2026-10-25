# Design Decision Log

## 2026-10-25 — v1 engine design (built ahead of the Oct 28 milestone)

- **Data:** NBA stats API via nba_api only, cache-first (data/cache/,
  keyed by endpoint+params+date). Timeouts are treated as routine, never
  fatal; stale cache beats no answer, and is always flagged as stale.
  Team pace is derived in-house (POSS = FGA + 0.44*FTA - OREB + TOV);
  the vendor pace endpoint never answered from this network.
- **Rates:** recency-weighted per-minute rates, exponential decay with a
  12-game half-life, ratio of weighted sums (not mean of ratios).
  Current + previous season merged into one decay sequence — last season
  informs, recent games dominate; no separate early-season blending rule.
- **Minutes:** proj = 0.65 * recent + 0.35 * overall, where "recent" is a
  5-game window with a 4-game half-life. The blend is v1's role/starter
  adjustment. Clamped to [8, 40].
- **Distribution:** Normal, mean = rate x minutes, variance scales with
  minutes via an empirically estimated per-minute variance. Honesty
  guards: SD floor of 0.45*sqrt(mean) and small-sample SD inflation
  sqrt(1 + 4/effective_n). No fake 95% probabilities on thin samples.
- **Calibration:** every CLI projection made with a line is appended to
  data/calibration.csv BEFORE the game; src/settle.py fills actuals from
  post-game logs and reports quoted-vs-actual by probability bucket.
- **Known v1 limits (accepted, v2 territory):** no injury-report input
  (a star sitting tonight is invisible to the engine), no pace/matchup
  adjustment in the rates themselves, injury-exit games drag minutes.
