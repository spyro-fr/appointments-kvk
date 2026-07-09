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

    schedule = assign_slots(players)
    write_schedule(schedule, args.template, args.output)

    assigned_count = sum(1 for p in players if p.is_assigned)
    unassigned = get_unassigned(players)

    print(f"Joueurs lus          : {len(players)}")
    print(f"Creneaux remplis     : {len(schedule)}/48")
    print(f"Joueurs affilies     : {assigned_count}")
    print(f"Joueurs non affilies : {len(unassigned)}")

    if unassigned:
        print("\nNon affilies :")
        for player in sorted(unassigned, key=lambda p: (-p.speedups, p.pseudo)):
            print(f"  - {player.pseudo} ({player.speedups} speedups)")

    print(f"\nFichier genere : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

