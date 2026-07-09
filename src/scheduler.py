from collections import defaultdict

from src.config import SLOTS_PER_DAY
from src.models import Player


def _sort_for_assignment(players: list[Player]) -> list[Player]:
    return sorted(
        players,
        key=lambda p: (len(p.slot_indices), -p.speedups, p.pseudo.lower()),
    )


def assign_slots(players: list[Player]) -> dict[int, Player]:
    schedule: dict[int, Player] = {}
    assigned_pseudos: set[str] = set()

    for player in _sort_for_assignment(players):
        if player.pseudo in assigned_pseudos:
            continue
        for slot in sorted(player.slot_indices):
            if slot not in schedule:
                schedule[slot] = player
                player.assigned_slot = slot
                assigned_pseudos.add(player.pseudo)
                break

    for slot in range(SLOTS_PER_DAY):
        if slot in schedule:
            continue

        candidates = [
            p
            for p in players
            if slot in p.slot_indices and p.pseudo not in assigned_pseudos
        ]
        if not candidates:
            continue

        best = max(candidates, key=lambda p: (p.speedups, p.pseudo.lower()))
        schedule[slot] = best
        best.assigned_slot = slot
        assigned_pseudos.add(best.pseudo)

    _apply_speedup_replacements(players, schedule, assigned_pseudos)
    return schedule


def _apply_speedup_replacements(
    players: list[Player],
    schedule: dict[int, Player],
    assigned_pseudos: set[str],
) -> None:
    by_availability: dict[frozenset[int], list[Player]] = defaultdict(list)
    for player in players:
        by_availability[player.availability_key].append(player)

    for group in by_availability.values():
        unassigned = [p for p in group if not p.is_assigned]
        assigned = [p for p in group if p.is_assigned]

        if not unassigned or not assigned:
            continue

        unassigned.sort(key=lambda p: (-p.speedups, p.pseudo.lower()))

        for candidate in unassigned:
            replaceable = [p for p in assigned if p.speedups < candidate.speedups]
            if not replaceable:
                continue

            victim = min(replaceable, key=lambda p: (p.speedups, p.pseudo.lower()))
            slot = victim.assigned_slot
            if slot is None:
                continue

            schedule[slot] = candidate
            candidate.assigned_slot = slot
            assigned_pseudos.add(candidate.pseudo)

            victim.assigned_slot = None
            assigned_pseudos.discard(victim.pseudo)
            assigned.remove(victim)
            assigned.append(candidate)


def get_unassigned(players: list[Player]) -> list[Player]:
    return [p for p in players if not p.is_assigned]
