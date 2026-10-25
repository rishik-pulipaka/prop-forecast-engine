"""In-house team pace derivation.

docs/DATA_PIPELINE.md: the LeagueDashTeamStats (pace) endpoint never
answered from this sandbox, so pace is DERIVED from game logs we can pull,
never fetched. A team's possessions in a game are estimated with the
standard formula:

    POSS = FGA + 0.44 * FTA - OREB + TOV

summed over every player on the team in that game. Pace here is possessions
per game (regulation games are 48 minutes, so this is effectively
possessions per 48; overtime games inflate it slightly — noted, accepted
for v1).

This module is the foundation for v2 matchup adjustments; the v1 rates
engine does not consume pace yet.
"""

from __future__ import annotations

import pandas as pd

FTA_POSSESSION_FACTOR = 0.44


def possessions(fga: float, fta: float, oreb: float, tov: float) -> float:
    """Estimated possessions from team totals for one game."""
    return fga + FTA_POSSESSION_FACTOR * fta - oreb + tov


def _team_abbrev(row: pd.Series) -> str | None:
    """Team abbrev from a game-log row: explicit column, else MATCHUP."""
    for col in ("TEAM_ABBREVIATION", "Team_ABBREVIATION"):
        if col in row and isinstance(row[col], str) and row[col]:
            return row[col]
    matchup = row.get("MATCHUP")
    if isinstance(matchup, str) and matchup:
        # "CLE vs. BKN" (home) or "CLE @ PHI" (away): player's team is first.
        return matchup.split()[0]
    return None


def team_game_possessions(player_rows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-game rows into per-team, per-game possessions.

    Input: rows with Game_ID (or GAME_ID), FGA, FTA, OREB, TOV and either a
    team column or MATCHUP. Output columns: game_id, team, possessions.
    """
    df = player_rows.copy()
    game_col = "Game_ID" if "Game_ID" in df.columns else "GAME_ID"
    df["_team"] = df.apply(_team_abbrev, axis=1)
    df = df[df["_team"].notna()]
    grouped = (
        df.groupby([game_col, "_team"])[["FGA", "FTA", "OREB", "TOV"]]
        .sum()
        .reset_index()
    )
    grouped["possessions"] = possessions(
        grouped["FGA"], grouped["FTA"], grouped["OREB"], grouped["TOV"])
    return grouped.rename(columns={game_col: "game_id", "_team": "team"})[
        ["game_id", "team", "possessions"]
    ]


def team_pace(player_rows: pd.DataFrame) -> pd.Series:
    """Mean possessions per game per team, from player-game rows."""
    per_game = team_game_possessions(player_rows)
    return per_game.groupby("team")["possessions"].mean()
