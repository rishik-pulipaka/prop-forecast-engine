"""Spike: test NBA stats API reachability from the sandbox.

Tries, in order:
  1. Raw HTTPS reachability of stats.nba.com (what IP does DNS give, does TLS work)
  2. nba_api PlayerGameLog for James Harden, season 2026-27
  3. nba_api LeagueDashTeamStats (advanced -> pace), season 2026-27
"""
import socket
import sys
import traceback

print("=== 1. DNS + raw reachability ===")
try:
    print("stats.nba.com ->", socket.gethostbyname("stats.nba.com"))
except Exception as e:
    print("DNS FAILED:", repr(e))

import requests

try:
    r = requests.get("https://stats.nba.com/stats/", timeout=15)
    print("GET https://stats.nba.com/stats/ ->", r.status_code, "len", len(r.content))
except Exception as e:
    print("HTTPS FAILED:", repr(e))

print("\n=== 2. PlayerGameLog: James Harden 2026-27 ===")
try:
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playergamelog

    matches = [p for p in players.get_players() if p["full_name"] == "James Harden"]
    print("player match:", matches)
    if matches:
        pid = matches[0]["id"]
        log = playergamelog.PlayerGameLog(player_id=pid, season="2026-27", timeout=30)
        df = log.get_data_frames()[0]
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.head(3).to_string())
        df.to_csv("data/harden_gamelog_2026-27.csv", index=False)
        print("saved data/harden_gamelog_2026-27.csv")
except Exception as e:
    print("FAILED:", repr(e))
    traceback.print_exc(limit=2)

print("\n=== 3. Team advanced stats (pace) 2026-27 ===")
try:
    from nba_api.stats.endpoints import leaguedashteamstats

    stats = leaguedashteamstats.LeagueDashTeamStats(
        season="2026-27", measure_type_detailed_defense="Advanced", timeout=30
    )
    df = stats.get_data_frames()[0]
    print("shape:", df.shape)
    cols = [c for c in df.columns if c in ("TEAM_NAME", "PACE", "OFF_RATING", "DEF_RATING", "GP")]
    print(df[cols].head(5).to_string())
    df.to_csv("data/team_advanced_2026-27.csv", index=False)
    print("saved data/team_advanced_2026-27.csv")
except Exception as e:
    print("FAILED:", repr(e))
    traceback.print_exc(limit=2)
