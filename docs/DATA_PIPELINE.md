# Data Pipeline — Feasibility Spike (Phase 1)

Date: 2026-10-24/25 (America/Los_Angeles)
Question: can this sandbox reliably feed the engine with (i) per-player game
logs with minutes, (ii) team pace, and (iii) nightly box scores for settling?

## Environment setup (reproduce after any VM replacement)

System pip packages do not survive VM replacement, so the project uses a
project-local venv:

```bash
cd ~/workspace/projects/prop-forecast-engine
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # nba_api, pandas, requests
```

Verified working: Python 3.12.3, nba_api 1.12.0, pandas 3.1.0, requests 2.34.2.

## What was tested (actual results, not assumptions)

All traffic from this sandbox egresses through a proxy: DNS resolves public
hosts to 198.18.x.x addresses (stats.nba.com -> 198.18.36.255).

| # | Call | Result |
|---|------|--------|
| 1 | `requests.get https://stats.nba.com/stats/` | ReadTimeout at 15s (that path returns nothing useful anyway) |
| 2 | nba_api `PlayerGameLog` — James Harden, 2026-27 | **SUCCESS** — 2 games x 27 cols, saved to `data/harden_gamelog_2026-27.csv`. Rows cross-check exactly against verified box scores: Oct 22 @ PHI (33 MIN, 16 PTS, 5 AST, 6 TOV) and Oct 24 vs BKN (33 MIN, 12 PTS, 7 AST) |
| 3 | nba_api `LeagueDashTeamStats` (Advanced/pace), default headers | **FAIL** — ProxyError: proxy remote end closed connection |
| 4 | Same pace call, custom browser headers + 3 retries w/ backoff | **FAIL** — hung past 6 minutes, killed; single-attempt rerun: ReadTimeout at 25s |
| 5 | nba_api `LeagueGameLog` (all players, 2026-10-24), custom headers | **FAIL** — ReadTimeout at 25s |
| 6 | `cdn.nba.com` liveData boxscore + scoreboard JSON | **403** in <1.5s — CDN blocks this egress IP outright |
| 7 | basketball-reference box score page (202610240CLE) | **404** with a 94 KB body, no box-score table present — unverified/blocked from this sandbox |

So the NBA stats API is **not hard-blocked** (call #2 returned real, current
data), but it is **unreliable under repeated calls from this sandbox**: 1 of 5
endpoint calls succeeded. Failures are proxy disconnects and read timeouts,
consistent with stats.nba.com's known aggressive throttling of datacenter IPs
compounded by the sandbox proxy. Custom headers and retries (one full round)
did not fix it.

## Chosen design

**Primary source: NBA stats API via nba_api** — the only source proven to
return real data from here — used in the most request-frugal way possible:

- **Batch endpoints only.** `LeagueGameLog` (all players, date-ranged) is ONE
  call per night for settling AND the raw material for per-player logs.
  Per-player `PlayerGameLog` calls (proven working) are for targeted refresh,
  never a nightly loop over the player pool.
- **Slow pacing + disk cache.** Seconds-to-tens-of-seconds between calls,
  generous timeouts, every response cached to `data/` so no call is ever
  repeated for the same data. A failed call is retried on a minutes-scale
  budget (e.g. by the next scheduled run), not hammered in a tight loop.
- **(i) Per-player game logs with minutes: YES** — proven (see sample below).
- **(ii) Team pace: DERIVE, don't fetch.** `LeagueDashTeamStats` failed every
  attempt. Possessions per team-game are computable from the game logs we can
  pull (FGA + 0.44*FTA - OREB + TOV), so pace is a derived stat in-house. No
  dependency on the endpoint that doesn't work.
- **(iii) Nightly settling: `LeagueGameLog` by date** is the designed path
  (same endpoint family as the proven game-log call; needs the slow-pacing
  treatment). **Backup: Sportradar public box-score pages**, which the parent
  workflow already reads successfully via browser search/fetch (verified
  repeatedly on 2026-10-24 for live and final lines).

**Fallbacks evaluated:**
- *Kaggle datasets* — good for **historical backtest data only** (static
  dumps, not nightly-fresh). Download needs a free Kaggle account; not
  required for the live pipeline, note for the backtest phase.
- *basketball-reference* — could in principle supply all three needs, but
  **unverified from this sandbox** (test returned 404/no table) and it rate
  limits scrapers hard. Not chosen.
- *cdn.nba.com JSON* — cleanest format of all, but **403 from this egress**.
  Revisit only if egress changes.

## Sample data actually pulled

`data/harden_gamelog_2026-27.csv` (gitignored) — shape **(2, 27)**:

Columns: `SEASON_ID, Player_ID, Game_ID, GAME_DATE, MATCHUP, WL, MIN, FGM,
FGA, FG_PCT, FG3M, FG3A, FG3_PCT, FTM, FTA, FT_PCT, OREB, DREB, REB, AST,
STL, BLK, TOV, PF, PTS, PLUS_MINUS, VIDEO_AVAILABLE`

That covers every prop market we model (PTS/REB/AST, threes, steals, blocks,
turnovers) plus MIN — the single most important input — per game.

## Known quirks / rules for builders

1. stats.nba.com throttles datacenter IPs: expect timeouts and proxy drops.
   Design for it (cache everything, pace calls, retry across runs) instead
   of treating a timeout as "no data."
2. A timeout is not a block and a block is not a timeout: cdn.nba.com's
   instant 403 is a real block; stats.nba.com eventually answers.
3. The static player index (`nba_api.stats.static.players`) is bundled with
   the library and works offline — Harden = player id 201935.
4. Spike scripts live in `tests/spike_api.py`, `tests/spike_api2b.py`,
   `tests/spike_fallbacks.py` — rerun them after any VM replacement to
   re-verify egress before trusting the pipeline.
5. Sandbox DNS is proxied (198.18.x.x) — never conclude a host is down from
   `dig`/`nslookup`; judge by actual HTTPS responses.

## Blockers needing Rishik

None for this phase. (Later, optional: a free Kaggle account if we want
Kaggle's historical dumps for backtesting, and the free Odds API key for
line comparison — both already known asks, neither blocks the pipeline.)
