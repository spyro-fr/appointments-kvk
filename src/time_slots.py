import re

from src.config import SLOTS_PER_DAY

_TIME_PATTERN = re.compile(r"(\d{1,2}):(\d{2})")


def generate_slot_labels() -> list[str]:
    labels: list[str] = []
    for hour in range(24):
        labels.append(f"{hour:02d}:15")
        labels.append(f"{hour:02d}:45")
    return labels


def time_to_slot_index(hour: int, minute: int) -> int | None:
    if minute == 15:
        return hour * 2
    if minute == 45:
        return hour * 2 + 1
    return None


def parse_availability(raw: str) -> frozenset[int]:
    if not raw or not raw.strip():
        return frozenset()

    indices: set[int] = set()
    for part in re.split(r"[;\s]+", raw.strip()):
        part = part.strip()
        if not part:
            continue

        match = _TIME_PATTERN.search(part)
        if not match:
            continue

        hour, minute = int(match.group(1)), int(match.group(2))
        if hour < 0 or hour > 23:
            continue

        index = time_to_slot_index(hour, minute)
        if index is not None and 0 <= index < SLOTS_PER_DAY:
            indices.add(index)

    return frozenset(indices)


def slot_index_to_label(index: int) -> str:
    labels = generate_slot_labels()
    if 0 <= index < len(labels):
        return labels[index]
    raise ValueError(f"Index de creneau invalide : {index}")
