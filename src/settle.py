"""Settle the calibration store against real box scores and report
calibration by confidence bucket.

Usage:
    .venv/bin/python -m src.settle

For every store row whose game date is in the past and whose `actual` is
still blank, this pulls the player's current-season game log through the
cached client (fresh cache key for today, so tonight's/today's games are
included once played), finds the game played on the projection date,
fills `actual` and `went_over`, and rewrites the store.

Then it reports calibration: rows are bucketed by quoted P(over); for
each bucket, the mean quoted probability vs the actual over-hit rate. A
calibrated model has those two numbers close in every bucket.

If fetching a log fails, that player's rows stay unsettled (never fatal)
and are reported as pending — retry on the next run.
"""

from __future__ import annotations

import sys
from datetime import date, datetime

import pandas as pd

from .data.client import CachedNBAClient, DataUnavailable
from .engine.rates import stat_values
from .store import read_store, write_store

CURRENT_SEASON = "2026-27"
BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def settle_rows(rows: list[dict], client: CachedNBAClient,
                today: date | None = None) -> tuple[int, int]:
    """Settle what can be settled. Returns (newly_settled, still_pending)."""
    today = today or date.today()
    logs: dict[int, pd.DataFrame | None] = {}
    settled = 0
    pending = 0
    for row in rows:
        if row.get("actual") not in (None, ""):
            continue
        game_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        if game_date >= today:
            pending += 1
            continue
        pid = int(row["player_id"])
        if pid not in logs:
            try:
                logs[pid] = client.player_game_log(pid, CURRENT_SEASON).df
            except DataUnavailable:
                logs[pid] = None
        log = logs[pid]
        if log is None or len(log) == 0:
            pending += 1
            continue
        log_dates = pd.to_datetime(log["GAME_DATE"]).dt.date
        match = log[log_dates == game_date]
        if len(match) == 0:
            # Player had no game that date (or log not updated yet).
            pending += 1
            continue
        actual = float(stat_values(match.iloc[[0]], row["stat"])[0])
        row["actual"] = f"{actual:g}"
        row["went_over"] = "1" if actual > float(row["line"]) else "0"
        settled += 1
    return settled, pending


def calibration_report(rows: list[dict]) -> str:
    settled = [r for r in rows if r.get("actual") not in (None, "")]
    if not settled:
        return "No settled projections yet — nothing to grade."
    lines = [f"Settled projections: {len(settled)}",
             f"{'quoted P(over)':>16} | {'n':>3} | {'mean quoted':>11} | "
             f"{'actual over rate':>16}"]
    for lo, hi in BUCKETS:
        bucket = [r for r in settled
                  if lo <= float(r["prob_over"]) < hi]
        if not bucket:
            continue
        mean_quoted = sum(float(r["prob_over"]) for r in bucket) / len(bucket)
        actual_rate = sum(int(r["went_over"]) for r in bucket) / len(bucket)
        lines.append(f"{lo:.1f}-{min(hi, 1.0):.1f} bucket   | "
                     f"{len(bucket):>3} | {mean_quoted:>11.2f} | "
                     f"{actual_rate:>16.2f}")
    overall_quoted = sum(float(r["prob_over"]) for r in settled) / len(settled)
    overall_actual = sum(int(r["went_over"]) for r in settled) / len(settled)
    lines.append(f"Overall: mean quoted {overall_quoted:.2f} vs actual over "
                 f"rate {overall_actual:.2f} "
                 f"(gap {abs(overall_quoted - overall_actual):.2f})")
    return "\n".join(lines)


def main() -> int:
    rows = read_store()
    if not rows:
        print("Calibration store is empty — make some projections first "
              "(src.cli with --line).")
        return 0
    client = CachedNBAClient()
    settled, pending = settle_rows(rows, client)
    write_store(rows)
    print(f"Newly settled: {settled}; still pending: {pending}")
    print(calibration_report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
