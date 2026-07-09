import csv
from pathlib import Path

from src.config import COL_AVAILABILITY, COL_PSEUDO, COL_SPEEDUPS
from src.models import Player
from src.time_slots import parse_availability


def _parse_speedups(value: str) -> int:
    if not value or not value.strip():
        return 0
    digits = "".join(c for c in value if c.isdigit())
    return int(digits) if digits else 0


def load_players(csv_path: Path) -> list[Player]:
    players: list[Player] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)

        for row in reader:
            if len(row) <= COL_AVAILABILITY:
                continue

            pseudo = row[COL_PSEUDO].strip()
            if not pseudo:
                continue

            speedups = _parse_speedups(row[COL_SPEEDUPS])
            slots = parse_availability(row[COL_AVAILABILITY])

            if not slots:
                continue

            players.append(
                Player(
                    pseudo=pseudo,
                    speedups=speedups,
                    slot_indices=slots,
                )
            )

    return players
