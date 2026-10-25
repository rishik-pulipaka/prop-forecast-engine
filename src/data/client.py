"""Cached, retrying client for the NBA stats API (via nba_api).

Design rules (from docs/DATA_PIPELINE.md — read it before changing this):
- stats.nba.com throttles this sandbox's egress hard. Timeouts and proxy
  drops are ROUTINE, not fatal. Never let one kill a run if cached data
  exists.
- Every successful response is written to a disk cache under data/cache/,
  keyed by endpoint + params + fetch date, so the same data is never
  requested twice. A new day gets a new cache key (fresh logs), an old
  cache file is the fallback when today's fetch fails.
- Calls are paced (seconds between network calls) and retried with
  backoff. Batch endpoints are preferred; per-player PlayerGameLog is the
  proven-working endpoint and is what v1 uses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# Seconds to wait between live network calls in one process.
MIN_CALL_GAP_S = 2.0
# Per-attempt request timeout. Phase 1 saw ReadTimeouts at 25s; the API is
# slow, so be generous.
REQUEST_TIMEOUT_S = 60
# Retry plan for one logical fetch: attempts and the sleep before each retry.
MAX_ATTEMPTS = 3
RETRY_BACKOFF_S = (5.0, 15.0)


@dataclass
class FetchResult:
    """A DataFrame plus where it came from."""

    df: pd.DataFrame
    source: str  # "cache" | "live" | "stale-cache"
    fetched_on: str  # ISO date the underlying data was fetched


class DataUnavailable(Exception):
    """Raised when neither a live fetch nor any cache can supply data."""


class CachedNBAClient:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_call_at = 0.0

    # ---- cache plumbing -------------------------------------------------

    def _cache_path(self, key: str, on: date) -> Path:
        return self.cache_dir / f"{key}_{on.isoformat()}.csv"

    def _read_cache(self, path: Path) -> pd.DataFrame | None:
        try:
            return pd.read_csv(path)
        except Exception:
            return None

    def _latest_cache(self, key: str) -> tuple[pd.DataFrame, str] | None:
        """Most recent cached copy of `key`, any date, or None."""
        matches = sorted(self.cache_dir.glob(f"{key}_*.csv"))
        if not matches:
            return None
        path = matches[-1]
        df = self._read_cache(path)
        if df is None:
            return None
        fetched_on = path.stem.rsplit("_", 1)[-1]
        return df, fetched_on

    def _write_cache(self, key: str, on: date, df: pd.DataFrame) -> None:
        df.to_csv(self._cache_path(key, on), index=False)

    # ---- network ---------------------------------------------------------

    def _pace(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < MIN_CALL_GAP_S:
            time.sleep(MIN_CALL_GAP_S - elapsed)

    def _call_with_retries(self, fn, description: str) -> pd.DataFrame:
        last_exc: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                time.sleep(RETRY_BACKOFF_S[min(attempt - 1, len(RETRY_BACKOFF_S) - 1)])
            self._pace()
            try:
                result = fn()
                self._last_call_at = time.monotonic()
                return result
            except Exception as exc:  # timeouts/proxy drops expected; retry
                self._last_call_at = time.monotonic()
                last_exc = exc
                print(f"[client] {description}: attempt {attempt + 1} failed "
                      f"({type(exc).__name__}: {exc})")
        raise DataUnavailable(f"{description}: all {MAX_ATTEMPTS} attempts "
                              f"failed; last error: {last_exc}")

    # ---- public API --------------------------------------------------------

    def player_game_log(self, player_id: int, season: str,
                        today: date | None = None) -> FetchResult:
        """Game log for one player/season, e.g. season='2026-27'.

        Cache-first: today's cache wins; otherwise one paced, retried live
        call; if that fails, the most recent stale cache is returned with
        source='stale-cache' instead of raising.
        """
        from nba_api.stats.endpoints import playergamelog

        today = today or date.today()
        key = f"playergamelog_{player_id}_{season}"
        todays_path = self._cache_path(key, today)
        if todays_path.exists():
            df = self._read_cache(todays_path)
            if df is not None:
                return FetchResult(df, "cache", today.isoformat())

        def _fetch() -> pd.DataFrame:
            frames = playergamelog.PlayerGameLog(
                player_id=player_id, season=season,
                timeout=REQUEST_TIMEOUT_S,
            ).get_data_frames()
            if not frames:
                raise DataUnavailable("empty response")
            return frames[0]

        try:
            df = self._call_with_retries(
                _fetch, f"PlayerGameLog player={player_id} season={season}")
        except DataUnavailable:
            stale = self._latest_cache(key)
            if stale is not None:
                df, fetched_on = stale
                print(f"[client] live fetch failed for {key}; serving "
                      f"stale cache from {fetched_on}")
                return FetchResult(df, "stale-cache", fetched_on)
            raise
        self._write_cache(key, today, df)
        return FetchResult(df, "live", today.isoformat())


def resolve_player_id(full_name: str) -> int:
    """Player id from the bundled static index (works fully offline)."""
    from nba_api.stats.static import players as static_players

    matches = static_players.find_players_by_full_name(full_name)
    if not matches:
        raise DataUnavailable(f"no player named {full_name!r} in static index")
    active = [m for m in matches if m.get("is_active")]
    chosen = active[0] if active else matches[0]
    return int(chosen["id"])
