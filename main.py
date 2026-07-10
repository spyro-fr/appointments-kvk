#!/usr/bin/env python3
import argparse
import io
import sys
from pathlib import Path

from src.config import *
from src.csv_reader import load_players
from src.scheduler import assign_slots, get_unassigned
from src.xlsx_writer import write_schedule_per_days


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


def build_slots_sequence_for_day() -> list[int]:
    return list(range(SLOTS_PER_DAY))


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

    # Ask user which algorithm to use (English prompt, enter 1 or 2)
    algo_choice = None
    while algo_choice not in ("1", "2"):
        try:
            algo_choice = input("Choose assignment algorithm: 1) Greedy  2) Weighted bipartite matching. Enter 1 or 2: ").strip()
        except EOFError:
            # default to greedy if input not available
            algo_choice = "1"
            break
    algorithm = "greedy" if algo_choice == "1" else "bipartite"

    schedules = []
    all_unassigned = {}
    total_assigned = 0

    for day in range(NUM_DAYS):
        # clear any previous per-day assignments
        for p in players:
            p.assigned_slot_per_day.pop(day, None)

        schedule = assign_slots(players, day, slots_seq, algorithm=algorithm)
        schedules.append(schedule)

        unassigned = get_unassigned(players, day)
        all_unassigned[day] = unassigned
        total_assigned += sum(1 for p in players if p.is_assigned_for_day(day))

    write_schedule_per_days(schedules, args.template, args.output)

    print(f"Players read          : {len(players)}")
    print(f"Total slots per day   : {SLOTS_PER_DAY + 1}")
    print(f"Total assigned (sum over days) : {total_assigned}")

    # total estimated resource points for day 1 (if any assignments)
    sum_points_day1 = 0
    if schedules and len(schedules) > 0:
        sum_points_day1 = sum(p.resource_points for p in schedules[0].values())
    # format with space as thousands separator (e.g., 1 234 567)
    formatted_points = f"{sum_points_day1:,}".replace(",", " ")
    print(f"Total estimated resource points (Day 1) : {formatted_points}")

    for day in range(NUM_DAYS):
        print(f"\nDay {day + 1} - Unassigned : {len(all_unassigned[day])}")
        if all_unassigned[day]:
            for player in sorted(all_unassigned[day], key=lambda p: (-p.speedups, p.pseudo)):
                print(f"  - {player.pseudo} ({player.speedups} speedup days)")

    print(f"\nGenerated file : {args.output}")

    # Try to open the generated Excel file for convenience
    try:
        if args.output.exists():
            if sys.platform == "win32":
                import os

                os.startfile(str(args.output))
            else:
                # fallback for non-windows platforms
                import subprocess

                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, str(args.output)])
    except Exception as e:
        print(f"Could not open output file: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

