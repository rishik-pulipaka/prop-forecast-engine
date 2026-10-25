"""Calibration store: every real projection the engine makes is logged
here BEFORE the game, then settled against the actual box score.

CSV at data/calibration.csv (gitignored — it is live local state, not
source). Columns:

    date          projection date = the game date (America/Los_Angeles)
    player, player_id, stat, line
    prob_over     the model's quoted P(stat > line) at projection time
    mean, sd      the distribution it came from
    proj_minutes, n_games, effective_n   model inputs, for honesty audits
    actual        filled by settle.py after the game (blank until then)
    went_over     1/0 once settled (blank until then)

Calibration question this answers: in the bucket where the model quoted
P(over) ~ 0.7, did the over actually land ~70% of the time?
"""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = PROJECT_ROOT / "data" / "calibration.csv"

FIELDS = [
    "date", "player", "player_id", "stat", "line", "prob_over",
    "mean", "sd", "proj_minutes", "n_games", "effective_n",
    "actual", "went_over",
]


def append_projection(row: dict, path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with open(path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDS})


def read_store(path: Path = STORE_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_store(rows: list[dict], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
