"""From a rate and projected minutes to a probability.

The game stat is modeled as Normal:

    mean = rate_per_minute * projected_minutes
    var  = per_minute_variance * projected_minutes   (variance scales with
                                                      playing time, as it
                                                      does for counting stats)

Two honesty adjustments, both documented here rather than hidden:
- SD floor: sd is never allowed below 0.45 * sqrt(mean). On a tiny sample
  the empirical variance can come out absurdly small and produce fake
  95% probabilities; the floor keeps the model humble.
- Small-sample inflation: sd is multiplied by sqrt(1 + 4 / effective_n).
  At effective_n = 20 that is ~1.10x; at 5 it is ~1.34x.

P(over line) uses the .5 in real lines as the continuity correction:
for an integer-valued stat, P(stat > 26.5) = P(stat >= 27), and the Normal
CDF evaluated at 26.5 is exactly that corrected value. For integer lines
(e.g. 27.0) P(over) + P(under) < 1 and the remainder is the push mass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SD_FLOOR_FRACTION = 0.45


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class Distribution:
    mean: float
    sd: float

    def prob_over(self, line: float) -> float:
        if self.sd <= 0:
            return 1.0 if self.mean > line else 0.0
        return 1.0 - normal_cdf((line - self.mean) / self.sd)

    def prob_under(self, line: float) -> float:
        if self.sd <= 0:
            return 1.0 if self.mean < line else 0.0
        return normal_cdf((line - self.mean) / self.sd)


def build_distribution(mean: float, per_minute_variance: float,
                       projected_minutes: float,
                       effective_n: float) -> Distribution:
    var = max(per_minute_variance, 0.0) * projected_minutes
    sd = math.sqrt(var)
    sd = max(sd, SD_FLOOR_FRACTION * math.sqrt(max(mean, 0.0)))
    if effective_n > 0:
        sd *= math.sqrt(1.0 + 4.0 / effective_n)
    return Distribution(mean=float(mean), sd=float(sd))
