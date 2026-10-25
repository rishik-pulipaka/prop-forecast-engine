"""CLI: one player, one stat, one line -> projection + probabilities.

Usage:
    .venv/bin/python -m src.cli --player "Tyrese Maxey" --stat PTS --line 26.5

Options:
    --stat        PTS REB AST PRA R+A P+R P+A FG3M STL BLK TOV (default PTS)
    --line        the prop line to price (omit for a projection only)
    --season      current season string (default 2026-27)
    --prev-season previous season for sample depth (default 2025-26;
                  pass "none" to skip)
    --no-store    do not append this projection to the calibration store

A run with --line is a REAL projection: it is appended to
data/calibration.csv before the game so settle.py can grade it later.
Data comes from the cached client — live calls happen only on a cache
miss, and a failed fetch falls back to stale cache with a loud warning.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from .data.client import CachedNBAClient, DataUnavailable, resolve_player_id
from .engine.forecast import forecast
from .engine.rates import SUPPORTED_STATS
from .store import append_projection

CURRENT_SEASON = "2026-27"
PREVIOUS_SEASON = "2025-26"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prop-forecast", description=__doc__)
    parser.add_argument("--player", required=True)
    parser.add_argument("--stat", default="PTS", choices=SUPPORTED_STATS)
    parser.add_argument("--line", type=float, default=None)
    parser.add_argument("--season", default=CURRENT_SEASON)
    parser.add_argument("--prev-season", default=PREVIOUS_SEASON)
    parser.add_argument("--no-store", action="store_true")
    args = parser.parse_args(argv)

    client = CachedNBAClient()
    try:
        player_id = resolve_player_id(args.player)
        current = client.player_game_log(player_id, args.season)
        previous = None
        previous_source = None
        if args.prev_season.lower() != "none":
            try:
                prev_res = client.player_game_log(player_id, args.prev_season)
                previous, previous_source = prev_res.df, prev_res.source
            except DataUnavailable:
                print(f"[cli] WARNING: no {args.prev_season} log available for "
                      f"{args.player}; forecasting on current season only")
    except DataUnavailable as exc:
        print(f"ERROR: {exc}")
        return 2

    try:
        fc = forecast(args.player, args.stat, current.df, previous)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    today = date.today().isoformat()
    print(f"{args.player} — {args.stat} — {today}")
    print(f"  Projection (mean): {fc.mean:.1f}   sd {fc.sd:.1f}")
    if args.line is not None:
        p_over = fc.prob_over(args.line)
        p_under = fc.prob_under(args.line)
        print(f"  Line {args.line}:  P(over) {p_over:.2f}   "
              f"P(under) {p_under:.2f}")
        if args.line == int(args.line):
            print(f"  (integer line: push probability "
                  f"{max(0.0, 1.0 - p_over - p_under):.2f})")
    print(f"  Projected minutes: {fc.projected_minutes:.1f}")
    print(f"  Rate: {fc.rate_per_minute:.3f} {args.stat}/min (recency-weighted)")
    season_note = args.season + (f" + {args.prev_season}"
                                  if previous is not None else " only")
    print(f"  Sample: {fc.n_games} games ({season_note}), "
          f"effective n {fc.effective_n:.1f}")
    print(f"  Data source: current-season log = {current.source} "
          f"(fetched {current.fetched_on})"
          + (f"; prev-season log = {previous_source}" if previous is not None
             else ""))
    if current.source == "stale-cache":
        print("  WARNING: current-season data is STALE cache — the live "
              "fetch failed; treat this projection with suspicion.")

    if args.line is not None and not args.no_store:
        append_projection({
            "date": today,
            "player": args.player,
            "player_id": player_id,
            "stat": args.stat,
            "line": args.line,
            "prob_over": f"{fc.prob_over(args.line):.4f}",
            "mean": f"{fc.mean:.2f}",
            "sd": f"{fc.sd:.2f}",
            "proj_minutes": f"{fc.projected_minutes:.1f}",
            "n_games": fc.n_games,
            "effective_n": f"{fc.effective_n:.1f}",
        })
        print("  Logged to calibration store (data/calibration.csv).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
