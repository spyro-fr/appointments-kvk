import csv
from pathlib import Path

from src.config import COL_AVAILABILITIES, COL_PSEUDO, COL_SPEEDUPS
from src.models import Player
from src.time_slots import parse_availability


def _parse_speedups(value: str) -> int:
    if not value or not value.strip():
        return 0
    digits = "".join(c for c in value if c.isdigit())
    return int(digits) if digits else 0


def load_players(csv_path: Path) -> list[Player]:
    players: list[Player] = []

    def _parse_timestamp(ts_str: str):
        """Parse timestamp strings like '2026/07/06 10:39:23 PM UTC+3' into a datetime.
        Returns None on failure.
        """
        if not ts_str:
            return None
        s = ts_str.strip()
        if not s:
            return None
        # remove trailing timezone token if present (e.g., 'UTC+3')
        if "UTC" in s:
            s = s.rsplit(" ", 1)[0]
        from datetime import datetime

        for fmt in ("%Y/%m/%d %I:%M:%S %p", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return None

    # read all rows first (skip header)
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        raw_rows = list(reader)

    # deduplicate by pseudo (case-insensitive): keep the row with the most recent timestamp
    dedup: dict[str, tuple[list, object]] = {}
    for row in raw_rows:
        if len(row) <= COL_PSEUDO:
            continue
        pseudo_raw = row[COL_PSEUDO].strip()
        if not pseudo_raw:
            continue
        key = pseudo_raw.lower()
        ts = _parse_timestamp(row[0]) if len(row) > 0 else None
        existing = dedup.get(key)
        if existing is None:
            dedup[key] = (row, ts)
            continue
        _, existing_ts = existing
        # decide whether to replace existing entry with this row
        replace = False
        if ts is None and existing_ts is None:
            # neither has timestamp -> prefer the later row seen (replace)
            replace = True
        elif ts is None:
            replace = False
        elif existing_ts is None:
            replace = True
        else:
            # both have timestamps -> keep the most recent
            replace = ts >= existing_ts
        if replace:
            dedup[key] = (row, ts)

    # now build Player objects from deduplicated rows
    for row, _ in dedup.values():
        # require at least pseudo and speedups
        if len(row) <= COL_PSEUDO:
            continue

        pseudo = row[COL_PSEUDO].strip()
        if not pseudo:
            continue

        speedups = _parse_speedups(row[COL_SPEEDUPS]) if len(row) > COL_SPEEDUPS else 0

        # parse optional fields: alliance trigram (col 2) and player id (col 3)
        alliance = row[2].strip() if len(row) > 2 and row[2] is not None else ""
        player_id = row[3].strip() if len(row) > 3 and row[3] is not None else ""

        per_day_slots = []
        for col in COL_AVAILABILITIES:
            if len(row) > col:
                slots = parse_availability(row[col])
            else:
                slots = frozenset()
            per_day_slots.append(slots)

        # if player has no availability in any day, skip
        if not any(per_day_slots):
            continue

        players.append(
            Player(
                pseudo=pseudo,
                speedups=speedups,
                alliance_trigram=alliance,
                player_id=player_id,
                slot_indices=per_day_slots,
            )
        )

    return players
