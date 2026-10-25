"""Minutes projection.

Formula (v1 — deliberately simple, fully documented):

    recent  = decay-weighted mean MIN over the last RECENT_WINDOW games,
              with a SHORT half-life (4 games) so the window tracks form
    overall = decay-weighted mean MIN over the full sample (half-life 12)
    proj    = 0.65 * recent + 0.35 * overall, clamped to [8, 40]

The recent/overall blend IS the starter/role adjustment in v1: a player
whose role grew (bench -> starter, or a teammate's injury freed minutes)
shows recent >> overall and the projection follows the recent window at
65% weight; a player losing his spot is pulled down the same way. True
rotation modeling (lineup data, coach tendencies) is a v2 concern.

Known limitations, accepted for v1: DNP rows are excluded upstream, but
injury-exit games (played 9 minutes, left hurt) stay in the sample and
drag the projection; nothing here knows about tonight's injury report.
"""

from __future__ import annotations

from .rates import Rates

RECENT_WINDOW = 5
RECENT_HALF_LIFE = 4.0
RECENT_WEIGHT = 0.65
MIN_PROJECTION = 8.0
MAX_PROJECTION = 40.0


def project_minutes(rates: Rates) -> float:
    recent = rates.weighted_minutes(last_n=RECENT_WINDOW,
                                    half_life=RECENT_HALF_LIFE)
    overall = rates.weighted_minutes()
    proj = RECENT_WEIGHT * recent + (1.0 - RECENT_WEIGHT) * overall
    return float(min(MAX_PROJECTION, max(MIN_PROJECTION, proj)))
