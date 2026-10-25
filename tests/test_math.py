"""Pure-math tests: pace derivation and distribution probabilities."""

import math
import unittest

import pandas as pd

from src.data.pace import possessions, team_game_possessions, team_pace
from src.engine.distribution import build_distribution, normal_cdf


class TestPossessions(unittest.TestCase):
    def test_formula(self):
        # 80 FGA + 0.44*20 FTA - 10 OREB + 12 TOV = 90.8
        self.assertAlmostEqual(possessions(80, 20, 10, 12), 90.8, places=6)

    def test_team_aggregation_from_player_rows(self):
        rows = pd.DataFrame([
            {"GAME_ID": 1, "MATCHUP": "CLE vs. BKN", "FGA": 40, "FTA": 10,
             "OREB": 5, "TOV": 6},
            {"GAME_ID": 1, "MATCHUP": "CLE vs. BKN", "FGA": 40, "FTA": 10,
             "OREB": 5, "TOV": 6},
            {"GAME_ID": 1, "MATCHUP": "BKN @ CLE", "FGA": 45, "FTA": 10,
             "OREB": 8, "TOV": 7},
            {"GAME_ID": 1, "MATCHUP": "BKN @ CLE", "FGA": 40, "FTA": 10,
             "OREB": 6, "TOV": 7},
        ])
        per_game = team_game_possessions(rows)
        cle = per_game[per_game["team"] == "CLE"].iloc[0]["possessions"]
        bkn = per_game[per_game["team"] == "BKN"].iloc[0]["possessions"]
        self.assertAlmostEqual(cle, possessions(80, 20, 10, 12))
        self.assertAlmostEqual(bkn, possessions(85, 20, 14, 14))

    def test_team_pace_averages_games(self):
        rows = pd.DataFrame([
            {"GAME_ID": 1, "MATCHUP": "CLE vs. BKN", "FGA": 80, "FTA": 0,
             "OREB": 0, "TOV": 0},
            {"GAME_ID": 2, "MATCHUP": "CLE @ NYK", "FGA": 100, "FTA": 0,
             "OREB": 0, "TOV": 0},
        ])
        pace = team_pace(rows)
        self.assertAlmostEqual(pace["CLE"], 90.0)


class TestDistribution(unittest.TestCase):
    def test_normal_cdf_reference_values(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5)
        self.assertAlmostEqual(normal_cdf(1.96), 0.975, places=3)
        self.assertAlmostEqual(normal_cdf(-1.0), 1 - normal_cdf(1.0))

    def test_line_at_mean_is_a_coin_flip(self):
        dist = build_distribution(mean=20.0, per_minute_variance=2.0,
                                  projected_minutes=30.0, effective_n=30.0)
        self.assertAlmostEqual(dist.prob_over(20.0), 0.5, places=6)
        self.assertAlmostEqual(dist.prob_under(20.0), 0.5, places=6)

    def test_far_lines_approach_zero_and_one(self):
        # mean 20, sd ~5.8: line 5 is ~2.6 sd below, line 40 ~3.4 sd above.
        dist = build_distribution(mean=20.0, per_minute_variance=1.0,
                                  projected_minutes=30.0, effective_n=30.0)
        self.assertGreater(dist.prob_over(5.0), 0.99)
        self.assertLess(dist.prob_over(40.0), 0.01)

    def test_sd_floor_prevents_fake_certainty(self):
        # Near-zero empirical variance must not yield sd ~ 0.
        dist = build_distribution(mean=25.0, per_minute_variance=0.0,
                                  projected_minutes=35.0, effective_n=50.0)
        self.assertGreaterEqual(dist.sd, 0.45 * math.sqrt(25.0))
        self.assertLess(dist.prob_over(20.5), 0.999)

    def test_small_sample_widens_sd(self):
        big = build_distribution(20.0, 2.0, 30.0, effective_n=100.0)
        small = build_distribution(20.0, 2.0, 30.0, effective_n=4.0)
        self.assertGreater(small.sd, big.sd)


class TestCalibrationBuckets(unittest.TestCase):
    def test_report_math(self):
        from src.settle import calibration_report
        rows = [
            {"prob_over": "0.9", "went_over": "1", "actual": "30"},
            {"prob_over": "0.85", "went_over": "1", "actual": "28"},
            {"prob_over": "0.1", "went_over": "0", "actual": "10"},
            {"prob_over": "0.5", "went_over": "", "actual": ""},  # unsettled
        ]
        report = calibration_report(rows)
        self.assertIn("Settled projections: 3", report)


if __name__ == "__main__":
    unittest.main()
