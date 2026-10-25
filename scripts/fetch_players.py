"""Fetch + cache game logs for a list of players (both seasons by default).

Usage:
    .venv/bin/python scripts/fetch_players.py "Tyrese Maxey" "Domantas Sabonis"

Cache-first via src.data.client: re-running is cheap, failures are
reported per player/season and never abort the batch.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.client import CachedNBAClient, DataUnavailable, resolve_player_id

SEASONS = ("2026-27", "2025-26")


def main(names: list[str]) -> int:
    client = CachedNBAClient()
    for name in names:
        try:
            pid = resolve_player_id(name)
        except DataUnavailable as exc:
            print(f"{name}: SKIP ({exc})")
            continue
        for season in SEASONS:
            try:
                res = client.player_game_log(pid, season)
                print(f"{name} [{season}]: {res.source}, "
                      f"{len(res.df)} games (fetched {res.fetched_on})")
            except DataUnavailable as exc:
                print(f"{name} [{season}]: FAILED ({exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
