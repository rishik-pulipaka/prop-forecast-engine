"""Pure-math tests for the rates engine (stdlib unittest — runs anywhere,
also collectable by pytest)."""

import unittest

import pandas as pd

from src.engine.minutes import project_minutes
from src.engine.rates import (Rates, decay_weights, effective_sample_size,
                              prepare_games, stat_values)


def make_log(rows):
    """rows: list of (date_str, minutes, pts, reb, ast), any order."""
    return pd.DataFrame([
        {"GAME_DATE": d, "MIN": m, "PTS": p, "REB": r, "AST": a,
         "FG3M": 0, "STL": 0, "BLK": 0, "TOV": 0}
        for d, m, p, r, a in rows
    ])


class TestDecayWeights(unittest.TestCase):
    def test_first_weight_is_one_and_decays(self):
        w = decay_weights(5, half_life=12.0)
        self.assertAlmostEqual(w[0], 1.0)
        self.assertTrue(all(w[i] > w[i + 1] for i in range(4)))

    def test_half_life_point(self):
        w = decay_weights(13, half_life=12.0)
        self.assertAlmostEqual(w[12], 0.5, places=6)

    def test_empty(self):
        self.assertEqual(len(decay_weights(0)), 0)


class TestEffectiveSampleSize(unittest.TestCase):
    def test_uniform_weights_give_n(self):
        import numpy as np
        self.assertAlmostEqual(effective_sample_size(np.ones(10)), 10.0)

    def test_single_dominant_weight_gives_one(self):
        import numpy as np
        self.assertAlmostEqual(
            effective_sample_size(np.array([1.0, 0.0, 0.0])), 1.0)


class TestRates(unittest.TestCase):
    def test_constant_rate_recovered(self):
        # Exactly 1.0 PTS/min in every game -> rate must be 1.0.
        log = make_log([
            ("Oct 24, 2026", 30, 30, 5, 5),
            ("Oct 22, 2026", 20, 20, 5, 5),
            ("Oct 20, 2026", 36, 36, 5, 5),
        ])
        rates = Rates(prepare_games(log))
        self.assertAlmostEqual(rates.rate_per_minute("PTS"), 1.0, places=9)

    def test_recent_games_weigh_more(self):
        # Old games: 0.5/min. Newest game: 2.0/min. Weighted rate must sit
        # closer to the newest game's rate than the plain average would.
        log = make_log([
            ("Oct 24, 2026", 30, 60, 0, 0),   # 2.0/min (most recent)
            ("Oct 22, 2026", 30, 15, 0, 0),   # 0.5/min
            ("Oct 20, 2026", 30, 15, 0, 0),   # 0.5/min
        ])
        rates = Rates(prepare_games(log))
        plain = (60 + 15 + 15) / 90.0
        self.assertGreater(rates.rate_per_minute("PTS"), plain)

    def test_dnp_rows_excluded(self):
        log = make_log([
            ("Oct 24, 2026", 30, 30, 5, 5),
            ("Oct 22, 2026", 0, 0, 0, 0),     # DNP
        ])
        games = prepare_games(log)
        self.assertEqual(len(games), 1)

    def test_combo_stats(self):
        log = make_log([("Oct 24, 2026", 30, 10, 5, 3)])
        games = prepare_games(log)
        self.assertEqual(stat_values(games, "PRA")[0], 18.0)
        self.assertEqual(stat_values(games, "R+A")[0], 8.0)
        self.assertEqual(stat_values(games, "P+R")[0], 15.0)


class TestMinutesProjection(unittest.TestCase):
    def test_stable_minutes_project_to_same(self):
        log = make_log([(f"Oct {d}, 2026", 30, 10, 5, 5)
                        for d in (24, 22, 20, 18, 16)])
        rates = Rates(prepare_games(log))
        self.assertAlmostEqual(project_minutes(rates), 30.0, places=6)

    def test_role_growth_pulls_projection_up(self):
        # Recent games 36 min (new starter), older games 12 min (bench):
        # projection must land well above the plain mean of 18.
        rows = [("Oct 24, 2026", 36, 10, 5, 5),
                ("Oct 22, 2026", 36, 10, 5, 5),
                ("Oct 20, 2026", 36, 10, 5, 5)]
        rows += [(f"Oct {d}, 2026", 12, 4, 2, 2)
                 for d in (18, 16, 14, 12, 10, 8, 6)]
        rates = Rates(prepare_games(make_log(rows)))
        proj = project_minutes(rates)
        self.assertGreater(proj, 24.0)
        self.assertLessEqual(proj, 36.0)


if __name__ == "__main__":
    unittest.main()
