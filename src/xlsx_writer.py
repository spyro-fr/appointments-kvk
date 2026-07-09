from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.config import SLOTS_PER_DAY, NUM_DAYS
from src.models import Player
from src.time_slots import generate_slot_labels, slot_index_to_label


def ensure_template(template_path: Path) -> None:
    if template_path.exists():
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Day 1"

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    ws["A1"] = "Horaire"
    ws["B1"] = "Pseudo"
    for cell in ("A1", "B1"):
        ws[cell].font = header_font
        ws[cell].fill = header_fill
        ws[cell].alignment = Alignment(horizontal="center")

    # create labels: first the previous-day 23:45, then the usual SLOTS_PER_DAY labels
    labels = ["23:45 (veille)"] + generate_slot_labels()

    for i, label in enumerate(labels, start=2):
        ws.cell(row=i, column=1, value=label)

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 25
    wb.save(template_path)


def write_schedule_per_days(
    schedules: list[dict[int, Player]],
    template_path: Path,
    output_path: Path,
) -> None:
    """
    schedules: list of per-day schedule dicts mapping row_index -> Player
    Each schedule dict corresponds to one day (NUM_DAYS long).
    Each schedule uses rows: 0..(SLOTS_PER_DAY) where row 0 is prev 23:45 and rows 1..SLOTS_PER_DAY are the normal slots.
    """
    ensure_template(template_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(template_path)
    # if template only has one sheet, duplicate it for other days
    base_ws = wb.worksheets[0]

    # ensure we have NUM_DAYS sheets
    while len(wb.worksheets) < NUM_DAYS:
        wb.copy_worksheet(base_ws)

    for day_index in range(NUM_DAYS):
        ws = wb.worksheets[day_index]
        ws.title = f"Day {day_index + 1}"

        # write labels explicitly (in case template differed)
        labels = ["23:45 (veille)"] + generate_slot_labels()
        for row_offset, label in enumerate(labels, start=2):
            ws.cell(row=row_offset, column=1, value=label)

        schedule = schedules[day_index]
        for row in range(len(labels)):
            row_num = row + 2
            player = schedule.get(row)
            ws.cell(row=row_num, column=2, value=player.pseudo if player else "")

    wb.save(output_path)
