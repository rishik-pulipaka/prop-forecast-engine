"""End-to-end forecast: game logs in, projection + probabilities out."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .distribution import Distribution, build_distribution
from .minutes import project_minutes
from .rates import Rates, prepare_games


@dataclass
class Forecast:
    player: str
    stat: str
    mean: float
    sd: float
    projected_minutes: float
    rate_per_minute: float
    n_games: int
    effective_n: float
    distribution: Distribution

    def prob_over(self, line: float) -> float:
        return self.distribution.prob_over(line)

    def prob_under(self, line: float) -> float:
        return self.distribution.prob_under(line)


def forecast(player: str, stat: str, current_season_log: pd.DataFrame,
             previous_season_log: pd.DataFrame | None = None) -> Forecast:
    """Build a forecast from raw PlayerGameLog frames (either season may
    be the frame the client returned; previous may be None/empty)."""
    games = prepare_games(current_season_log, previous_season_log)
    if len(games) == 0:
        raise ValueError(f"no usable games for {player}")
    rates = Rates(games)
    minutes = project_minutes(rates)
    rate = rates.rate_per_minute(stat)
    variance = rates.per_minute_variance(stat)
    dist = build_distribution(rate * minutes, variance, minutes,
                              rates.effective_n)
    return Forecast(
        player=player,
        stat=stat.upper(),
        mean=dist.mean,
        sd=dist.sd,
        projected_minutes=minutes,
        rate_per_minute=rate,
        n_games=rates.n_games,
        effective_n=rates.effective_n,
        distribution=dist,
    )
