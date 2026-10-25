"""Spike part 2b: single attempt per endpoint, unbuffered, short timeouts."""
import sys
import time

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

from nba_api.stats.endpoints import leaguedashteamstats, leaguegamelog

print("--- pace attempt ---", flush=True)
t0 = time.time()
try:
    s = leaguedashteamstats.LeagueDashTeamStats(
        season="2026-27", measure_type_detailed_defense="Advanced",
        headers=HEADERS, timeout=25,
    )
    df = s.get_data_frames()[0]
    print(f"PACE OK in {time.time()-t0:.1f}s shape={df.shape}", flush=True)
    cols = [c for c in ("TEAM_NAME", "GP", "PACE", "OFF_RATING", "DEF_RATING") if c in df.columns]
    print(df[cols].head(5).to_string(), flush=True)
    df.to_csv("data/team_advanced_2026-27.csv", index=False)
    print("saved data/team_advanced_2026-27.csv", flush=True)
except Exception as e:
    print(f"PACE FAILED in {time.time()-t0:.1f}s: {type(e).__name__}: {str(e)[:200]}", flush=True)

time.sleep(6)

print("--- nightly league log attempt ---", flush=True)
t0 = time.time()
try:
    lg = leaguegamelog.LeagueGameLog(
        season="2026-27", player_or_team_abbreviation="P",
        date_from_nullable="10/24/2026", date_to_nullable="10/24/2026",
        headers=HEADERS, timeout=25,
    )
    night = lg.get_data_frames()[0]
    print(f"NIGHT OK in {time.time()-t0:.1f}s shape={night.shape}", flush=True)
    print("columns:", list(night.columns), flush=True)
    print(night[["PLAYER_NAME", "MATCHUP", "MIN", "PTS", "REB", "AST"]].head(5).to_string(), flush=True)
    night.to_csv("data/gamelog_2026-10-24.csv", index=False)
    print("saved data/gamelog_2026-10-24.csv", flush=True)
except Exception as e:
    print(f"NIGHT FAILED in {time.time()-t0:.1f}s: {type(e).__name__}: {str(e)[:200]}", flush=True)
