from dataclasses import dataclass, field


@dataclass
class Player:
    pseudo: str
    speedups: int
    slot_indices: frozenset[int] = field(default_factory=frozenset)
    assigned_slot: int | None = None

    @property
    def availability_key(self) -> frozenset[int]:
        return self.slot_indices

    @property
    def is_assigned(self) -> bool:
        return self.assigned_slot is not None
