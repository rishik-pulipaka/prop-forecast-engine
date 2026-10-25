"""Spike part 2: retry failed endpoints with custom headers + backoff (one round).

Tests:
  A. LeagueDashTeamStats Advanced (pace) 2026-27 — failed with ProxyError in part 1
  B. LeagueGameLog for 2026-10-24 — nightly player box scores (settling source)
"""
import time

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}


def with_retries(label, fn, attempts=3, base_delay=8):
    for i in range(1, attempts + 1):
        try:
            out = fn()
            print(f"{label}: OK on attempt {i}")
            return out
        except Exception as e:
            print(f"{label}: attempt {i} failed: {type(e).__name__}: {str(e)[:160]}")
            if i < attempts:
                time.sleep(base_delay * i)
    print(f"{label}: ALL ATTEMPTS FAILED")
    return None


print("=== A. Team pace with headers + retries ===")
from nba_api.stats.endpoints import leaguedashteamstats


def get_pace():
    s = leaguedashteamstats.LeagueDashTeamStats(
        season="2026-27",
        measure_type_detailed_defense="Advanced",
        headers=HEADERS,
        timeout=60,
    )
    return s.get_data_frames()[0]


df = with_retries("pace", get_pace)
if df is not None:
    print("shape:", df.shape)
    cols = [c for c in ("TEAM_NAME", "GP", "PACE", "OFF_RATING", "DEF_RATING") if c in df.columns]
    print(df[cols].head(5).to_string())
    df.to_csv("data/team_advanced_2026-27.csv", index=False)
    print("saved data/team_advanced_2026-27.csv")

time.sleep(5)

print("\n=== B. LeagueGameLog 2026-10-24 (settling source) ===")
from nba_api.stats.endpoints import leaguegamelog


def get_night():
    lg = leaguegamelog.LeagueGameLog(
        season="2026-27",
        player_or_team_abbreviation="P",
        date_from_nullable="10/24/2026",
        date_to_nullable="10/24/2026",
        headers=HEADERS,
        timeout=60,
    )
    return lg.get_data_frames()[0]


night = with_retries("nightly log", get_night)
if night is not None:
    print("shape:", night.shape)
    print("columns:", list(night.columns))
    print(night[["PLAYER_NAME", "MATCHUP", "MIN", "PTS", "REB", "AST"]].head(5).to_string())
    night.to_csv("data/gamelog_2026-10-24.csv", index=False)
    print("saved data/gamelog_2026-10-24.csv")
