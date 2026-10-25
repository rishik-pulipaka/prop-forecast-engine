"""Spike part 3: test fallback sources from the sandbox (single quick probes)."""
import json
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

print("--- A. cdn.nba.com boxscore JSON (CLE vs BKN, game 0022600105) ---", flush=True)
t0 = time.time()
try:
    r = requests.get(
        "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600105.json",
        headers=UA, timeout=20,
    )
    print(f"status={r.status_code} in {time.time()-t0:.1f}s bytes={len(r.content)}", flush=True)
    if r.status_code == 200:
        data = r.json()
        home = data["game"]["homeTeam"]
        p = home["players"][0]
        print("team:", home["teamName"], "| player keys:", sorted(p.keys())[:12], flush=True)
        print("statistics keys:", sorted(p["statistics"].keys()), flush=True)
        with open("data/cdn_boxscore_0022600105.json", "w") as f:
            json.dump(data, f)
        print("saved data/cdn_boxscore_0022600105.json", flush=True)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:160]}", flush=True)

time.sleep(3)

print("--- B. basketball-reference box score page (202610240CLE) ---", flush=True)
t0 = time.time()
try:
    r = requests.get(
        "https://www.basketball-reference.com/boxscores/202610240CLE.html",
        headers=UA, timeout=20,
    )
    body = r.text
    print(f"status={r.status_code} in {time.time()-t0:.1f}s bytes={len(body)}", flush=True)
    for marker in ("James Harden", "basic box score", "data-stat=\"mp\""):
        print(f"  contains {marker!r}:", marker in body, flush=True)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:160]}", flush=True)

time.sleep(3)

print("--- C. cdn.nba.com today's scoreboard ---", flush=True)
t0 = time.time()
try:
    r = requests.get(
        "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        headers=UA, timeout=20,
    )
    print(f"status={r.status_code} in {time.time()-t0:.1f}s bytes={len(r.content)}", flush=True)
    if r.status_code == 200:
        sb = r.json()["scoreboard"]
        print("gameDate:", sb.get("gameDate"), "| games:", len(sb.get("games", [])), flush=True)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:160]}", flush=True)
