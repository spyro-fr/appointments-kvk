#!/usr/bin/env python3
import argparse
import io
import sys
from pathlib import Path

from src.config import DEFAULT_OUTPUT, DEFAULT_TEMPLATE
from src.csv_reader import load_players
from src.scheduler import assign_slots, get_unassigned
from src.xlsx_writer import write_schedule


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_csv = script_dir / "#1881 KvK Prep Week Sign Up.csv"

    parser = argparse.ArgumentParser(
        description="Convertit un CSV d'inscriptions en planning Excel."
    )
    parser.add_argument("csv", nargs="?", type=Path, default=default_csv)
    parser.add_argument("-t", "--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    args = parse_args()

    if not args.csv.exists():
        print(f"Erreur : fichier CSV introuvable : {args.csv}", file=sys.stderr)
        return 1

    players = load_players(args.csv)
    if not players:
        print("Aucun joueur avec des disponibilites valides trouve.", file=sys.stderr)
        return 1

    slots_seq = build_slots_sequence_for_day()

    schedules = []
    all_unassigned = {}
    total_assigned = 0

    for day in range(NUM_DAYS):
        # clear any previous per-day assignments
        for p in players:
            p.assigned_slot_per_day.pop(day, None)

        schedule = assign_slots(players, day, slots_seq)
        schedules.append(schedule)

        unassigned = get_unassigned(players, day)
        all_unassigned[day] = unassigned
        total_assigned += sum(1 for p in players if p.is_assigned_for_day(day))

    write_schedule_per_days(schedules, args.template, args.output)

    print(f"Joueurs lus          : {len(players)}")
    print(f"Total creneaux (par jour): {SLOTS_PER_DAY + 1}")
    print(f"Joueurs affilies (somme sur jours) : {total_assigned}")

    for day in range(NUM_DAYS):
        print(f"\nJour {day + 1} - Non affilies : {len(all_unassigned[day])}")
        if all_unassigned[day]:
            for player in sorted(all_unassigned[day], key=lambda p: (-p.speedups, p.pseudo)):
                print(f"  - {player.pseudo} ({player.speedups} speedups)")

    print(f"\nFichier genere : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

