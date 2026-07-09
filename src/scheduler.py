from collections import defaultdict
from typing import List

from src.config import SLOTS_PER_DAY, NUM_DAYS
from src.models import Player


def _sort_for_assignment(players: List[Player], day: int) -> List[Player]:
    # Only consider players who asked for an appointment for this day
    eligible = [p for p in players if hasattr(p, "wants_appointment") and len(p.wants_appointment) > day and p.wants_appointment[day]]
    if day == 0:
        # day 1: sort by resource points (higher preferred)
        return sorted(
            eligible,
            key=lambda p: (len(p.availability_for_day(day)), -p.resource_points, p.pseudo.lower()),
        )
    return sorted(
        eligible,
        key=lambda p: (len(p.availability_for_day(day)), -p.speedups, p.pseudo.lower()),
    )


def assign_slots(players: List[Player], day: int, slots_sequence: List[int]) -> dict[int, Player]:
    """
    Assign players to the requested slots for a given day.
    slots_sequence: list of slot indices (values 0..SLOTS_PER_DAY-1), length = rows in sheet (49)
    returns mapping row_index -> Player
    Each player can be assigned at most one row for the given day.
    """
    schedule: dict[int, Player] = {}
    assigned_pseudos: set[str] = set()

    # First pass: give each player (sorted by fewest options) a free slot from their availability
    for player in _sort_for_assignment(players, day):
        if player.pseudo in assigned_pseudos:
            continue
        available = sorted(player.availability_for_day(day))
        # find the earliest row in slots_sequence that corresponds to an available slot and is free
        assigned = False
        for row_idx, slot_idx in enumerate(slots_sequence):
            if row_idx in schedule:
                continue
            if slot_idx in available:
                schedule[row_idx] = player
                player.assign_for_day(day, row_idx)
                assigned_pseudos.add(player.pseudo)
                assigned = True
                break
        if assigned:
            continue

    # Second pass: fill remaining rows by selecting best candidate for each row (highest speedups)
    for row_idx, slot_idx in enumerate(slots_sequence):
        if row_idx in schedule:
            continue
        # candidates must be eligible (asked for appointment) and available for this slot
        candidates = [
            p
            for p in players
            if (not p.is_assigned_for_day(day))
            and (slot_idx in p.availability_for_day(day))
            and hasattr(p, "wants_appointment")
            and len(p.wants_appointment) > day
            and p.wants_appointment[day]
        ]
        if not candidates:
            continue
        if day == 0:
            best = max(candidates, key=lambda p: (p.resource_points, -ord(p.pseudo[0]) if p.pseudo else 0, p.pseudo.lower()))
            # above uses resource_points as primary; tie-break by pseudo lexicographically
            best = max(candidates, key=lambda p: (p.resource_points, p.pseudo.lower()))
        else:
            best = max(candidates, key=lambda p: (p.speedups, p.pseudo.lower()))
        schedule[row_idx] = best
        best.assign_for_day(day, row_idx)
        assigned_pseudos.add(best.pseudo)

    # Third: try local speedup-based replacements inside groups of identical availability for the day
    _apply_speedup_replacements(players, day, schedule, assigned_pseudos)
    return schedule


def _apply_speedup_replacements(players: List[Player], day: int, schedule: dict[int, Player], assigned_pseudos: set[str]) -> None:
    by_availability: dict[frozenset, List[Player]] = defaultdict(list)
    for player in players:
        by_availability[player.availability_for_day(day)].append(player)

    for group in by_availability.values():
        unassigned = [p for p in group if not p.is_assigned_for_day(day)]
        assigned = [p for p in group if p.is_assigned_for_day(day)]

        if not unassigned or not assigned:
            continue

        if day == 0:
            # use resource_points for replacements on day 1
            unassigned.sort(key=lambda p: (-p.resource_points, p.pseudo.lower()))
        else:
            unassigned.sort(key=lambda p: (-p.speedups, p.pseudo.lower()))

        for candidate in unassigned:
            if day == 0:
                replaceable = [p for p in assigned if p.resource_points < candidate.resource_points]
            else:
                replaceable = [p for p in assigned if p.speedups < candidate.speedups]
            if not replaceable:
                continue

            # choose victim with lowest metric (and then lexicographically)
            if day == 0:
                victim = min(replaceable, key=lambda p: (p.resource_points, p.pseudo.lower()))
            else:
                victim = min(replaceable, key=lambda p: (p.speedups, p.pseudo.lower()))
            # victim's row
            victim_row = victim.assigned_slot_per_day.get(day)
            if victim_row is None:
                continue

            # replace
            schedule[victim_row] = candidate
            candidate.assign_for_day(day, victim_row)
            assigned_pseudos.add(candidate.pseudo)

            victim.unassign_for_day(day)
            assigned_pseudos.discard(victim.pseudo)
            assigned.remove(victim)
            assigned.append(candidate)


def get_unassigned(players: List[Player], day: int) -> List[Player]:
    return [p for p in players if not p.is_assigned_for_day(day)]
