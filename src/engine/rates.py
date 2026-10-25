"""Recency-weighted per-minute rates from game logs.

Method
------
Games are ordered most-recent first and weighted with exponential decay:

    w_i = 0.5 ** (i / HALF_LIFE_GAMES)        i = 0 is the latest game

The per-minute rate for a stat is the ratio of weighted sums,

    rate = sum(w_i * stat_i) / sum(w_i * minutes_i)

NOT the average of per-game ratios, so a 3-minute garbage-time cameo can't
outweigh a 36-minute start. Current-season games come first in the merged
sample and last season's games continue the same decay sequence (they are
all older), which is how early-season small samples stay sane without a
separate blending rule: last season informs, recent games dominate.

Combos (PRA, R+A, P+R, ...) are computed per game first, then rated the
same way — for linear combos this equals summing the component rates.
Games where the player did not play (MIN == 0 / missing) are excluded.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HALF_LIFE_GAMES = 12.0

# Stats the engine can rate directly off a game-log column, and combos as
# sums of columns.
BASE_STATS = ("PTS", "REB", "AST", "FG3M", "STL", "BLK", "TOV")
COMBO_STATS = {
    "PRA": ("PTS", "REB", "AST"),
    "R+A": ("REB", "AST"),
    "P+R": ("PTS", "REB"),
    "P+A": ("PTS", "AST"),
}
SUPPORTED_STATS = BASE_STATS + tuple(COMBO_STATS)


def stat_values(df: pd.DataFrame, stat: str) -> np.ndarray:
    """Per-game values for a base or combo stat, in df's row order."""
    stat = stat.upper()
    if stat in COMBO_STATS:
        cols = COMBO_STATS[stat]
        return df[list(cols)].sum(axis=1).to_numpy(dtype=float)
    if stat in BASE_STATS:
        return df[stat].to_numpy(dtype=float)
    raise ValueError(f"unsupported stat {stat!r}; supported: {SUPPORTED_STATS}")


def decay_weights(n: int, half_life: float = HALF_LIFE_GAMES) -> np.ndarray:
    """Exponential decay weights for n games, most recent first."""
    if n <= 0:
        return np.array([])
    idx = np.arange(n, dtype=float)
    return 0.5 ** (idx / half_life)


def effective_sample_size(weights: np.ndarray) -> float:
    """Kish effective sample size: (sum w)^2 / sum(w^2)."""
    total = weights.sum()
    if total == 0:
        return 0.0
    return float(total * total / np.square(weights).sum())


def prepare_games(current: pd.DataFrame,
                  previous: pd.DataFrame | None = None) -> pd.DataFrame:
    """Merge current + previous season logs into one sample.

    Sorted most-recent first; DNP rows (MIN missing or 0) dropped.
    """
    frames = [f for f in (current, previous) if f is not None and len(f)]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.copy()
    df["_date"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("_date", ascending=False).reset_index(drop=True)
    df = df[df["MIN"].fillna(0) > 0]
    return df.reset_index(drop=True)


class Rates:
    """Weighted rates + per-minute variance for one player's game sample."""

    def __init__(self, games: pd.DataFrame, half_life: float = HALF_LIFE_GAMES):
        if games is None or len(games) == 0:
            raise ValueError("no games in sample")
        self.games = games.reset_index(drop=True)
        self.n_games = len(self.games)
        self.minutes = self.games["MIN"].to_numpy(dtype=float)
        self.weights = decay_weights(self.n_games, half_life)
        self.effective_n = effective_sample_size(self.weights)

    def rate_per_minute(self, stat: str) -> float:
        values = stat_values(self.games, stat)
        return float(np.sum(self.weights * values)
                     / np.sum(self.weights * self.minutes))

    def per_minute_variance(self, stat: str) -> float:
        """Variance parameter v such that Var(game stat) ~= v * minutes.

        Residual-based: e_i = stat_i - rate * minutes_i, and
        v = sum(w_i * e_i^2 / minutes_i) / sum(w_i).
        Counting stats are over-dispersed vs Poisson, so v is estimated
        empirically rather than assumed.
        """
        values = stat_values(self.games, stat)
        rate = self.rate_per_minute(stat)
        resid = values - rate * self.minutes
        v = np.sum(self.weights * resid ** 2 / self.minutes) / np.sum(self.weights)
        return float(v)

    def weighted_minutes(self, last_n: int | None = None,
                         half_life: float = HALF_LIFE_GAMES) -> float:
        """Decay-weighted mean minutes, optionally over the last n games
        (weights renormalized over the window)."""
        minutes = self.minutes if last_n is None else self.minutes[:last_n]
        weights = decay_weights(len(minutes), half_life)
        return float(np.sum(weights * minutes) / np.sum(weights))
