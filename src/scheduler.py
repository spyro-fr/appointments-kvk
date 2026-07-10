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


def assign_slots(players: List[Player], day: int, slots_sequence: List[int], algorithm: str = "greedy") -> dict[int, Player]:
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

    # If algorithm is bipartite matching, delegate to the specialized routine
    if algorithm == "bipartite":
        return _assign_slots_bipartite(players, day, slots_sequence)

    # Second pass (greedy): fill remaining rows by selecting best candidate for each row (highest speedups or resource)
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
            # choose by resource points
            best = max(candidates, key=lambda p: (p.resource_points, p.pseudo.lower()))
        else:
            best = max(candidates, key=lambda p: (p.speedups, p.pseudo.lower()))
        schedule[row_idx] = best
        best.assign_for_day(day, row_idx)
        assigned_pseudos.add(best.pseudo)

    # Third: try local replacements inside groups of identical availability for the day
    _apply_speedup_replacements(players, day, schedule, assigned_pseudos)
    return schedule


def _assign_slots_bipartite(players: List[Player], day: int, slots_sequence: List[int]) -> dict[int, Player]:
    """Assign slots using a maximum-weight bipartite matching (Hungarian algorithm).
    Left side: eligible players (asked for appointment). Right side: slot rows (indices in slots_sequence).
    Weight = resource_points for day 0, else speedups. Only allow edges where player is available for the slot.
    Returns mapping row_index -> Player.
    """
    # build eligible players list
    eligible = [p for p in players if hasattr(p, "wants_appointment") and len(p.wants_appointment) > day and p.wants_appointment[day]]
    n_players = len(eligible)
    n_slots = len(slots_sequence)
    if n_players == 0 or n_slots == 0:
        return {}

    # construct weight matrix players x slots
    NEG_INF = -10**9
    weights = [[NEG_INF] * n_slots for _ in range(n_players)]
    for i, p in enumerate(eligible):
        for j, slot_idx in enumerate(slots_sequence):
            if slot_idx in p.availability_for_day(day):
                weights[i][j] = p.resource_points if day == 0 else p.speedups

    # use Hungarian algorithm for max weight matching
    assign = _hungarian_max_weight(weights)

    schedule: dict[int, Player] = {}
    for i, j in enumerate(assign):
        if i < n_players and j is not None and j < n_slots:
            w = weights[i][j]
            if w <= NEG_INF // 2:
                continue
            # assign player i to row index j
            player = eligible[i]
            schedule[j] = player
            player.assign_for_day(day, j)
    return schedule


def _hungarian_max_weight(weights: List[List[int]]) -> List[int]:
    """Compute max-weight assignment for a rectangular weight matrix weights (n_rows x m_cols).
    Returns a list 'ans' of length n_rows where ans[i] is the assigned column index or None.
    Uses the Hungarian algorithm for minimization on transformed costs.
    """
    n = len(weights)
    m = max((len(row) for row in weights), default=0)
    if n == 0 or m == 0:
        return [None] * n

    # make square matrix of size sz = max(n,m) by padding with zeros
    sz = max(n, m)
    # treat very negative values as unavailable; compute max finite weight among available edges
    MIN_AVAILABLE = -10**8
    max_w = max((w for row in weights for w in row if w > MIN_AVAILABLE), default=0)

    # build cost matrix for minimization: cost = max_w - weight (for available), big cost for unavailable
    BIG = 10**9
    a = [[0] * sz for _ in range(sz)]
    for i in range(sz):
        for j in range(sz):
            if i < n and j < m and j < len(weights[i]):
                w = weights[i][j]
                if w <= MIN_AVAILABLE:
                    a[i][j] = BIG
                else:
                    a[i][j] = max_w - w
            else:
                a[i][j] = BIG

    # Hungarian algorithm (O(n^3)) for minimization
    INF = 10**12
    u = [0] * (sz + 1)
    v = [0] * (sz + 1)
    p = [0] * (sz + 1)
    way = [0] * (sz + 1)
    for i in range(1, sz + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (sz + 1)
        used = [False] * (sz + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = 0
            for j in range(1, sz + 1):
                if used[j]:
                    continue
                cur = a[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(0, sz + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    # p[j] - row assigned to column j
    ans = [None] * n
    for j in range(1, sz + 1):
        i = p[j]
        if i != 0 and i <= n and j <= m:
            ans[i - 1] = j - 1
    return ans


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
