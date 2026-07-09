from dataclasses import dataclass, field
from typing import List


@dataclass
class Player:
    pseudo: str
    speedups: int
    # optional fields from CSV
    alliance_trigram: str = ""
    player_id: str = ""
    # slot_indices_per_day: list of frozenset[int], length NUM_DAYS
    slot_indices: List[frozenset] = field(default_factory=list)
    # For per-day assignment we'll store assigned_slot_per_day as dict day->row index
    assigned_slot_per_day: dict = field(default_factory=dict)

    def availability_for_day(self, day: int) -> frozenset:
        if 0 <= day < len(self.slot_indices):
            return self.slot_indices[day]
        return frozenset()

    @property
    def availability_key(self) -> tuple:
        # Useful for grouping: tuple of frozensets
        return tuple(self.slot_indices)

    def is_assigned_for_day(self, day: int) -> bool:
        return day in self.assigned_slot_per_day and self.assigned_slot_per_day[day] is not None

    def assign_for_day(self, day: int, row_index: int) -> None:
        self.assigned_slot_per_day[day] = row_index

    def unassign_for_day(self, day: int) -> None:
        if day in self.assigned_slot_per_day:
            self.assigned_slot_per_day[day] = None
