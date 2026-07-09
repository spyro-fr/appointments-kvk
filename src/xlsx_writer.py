from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.config import SLOTS_PER_DAY, NUM_DAYS
from src.models import Player
from src.time_slots import generate_slot_labels


DAY_NAMES = ["Monday", "Tuesday", "Thursday"]


def ensure_template(template_path: Path) -> None:
    """Create a template with three side-by-side tables.

    Layout (columns):
      Table 0: cols 1-4 (Slot, Pseudo, Trigram, ID)
      Col 5: empty separator
      Table 1: cols 6-9
      Col10: empty separator
      Table 2: cols 11-14

    Row 1: day name header (merged across the 4 columns of each table)
    Row 2: column headers (Slot / Pseudo / Trigram / ID)
    Row 3+: slot labels and entries
    """
    if template_path.exists():
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    # create day headers (row 1) and column headers (row 2)
    for day_index in range(NUM_DAYS):
        base_col = 1 + day_index * 5
        # merge cells for day name across 4 columns
        ws.merge_cells(start_row=1, start_column=base_col, end_row=1, end_column=base_col + 3)
        day_cell = ws.cell(row=1, column=base_col, value=DAY_NAMES[day_index] if day_index < len(DAY_NAMES) else f"Day {day_index + 1}")
        day_cell.font = header_font
        day_cell.fill = header_fill
        day_cell.alignment = Alignment(horizontal="center", vertical="center")

        # column headers in row 2
        headers = ["Slot", "Pseudo", "Trigram", "ID"]
        for i, h in enumerate(headers):
            cell = ws.cell(row=2, column=base_col + i, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

    # create labels: first the previous-day 23:45, then the usual SLOTS_PER_DAY labels
    labels = ["23:45 (veille)"] + generate_slot_labels()
    for i, label in enumerate(labels, start=3):
        # write the slot label in each table's Slot column for visual alignment
        for day_index in range(NUM_DAYS):
            base_col = 1 + day_index * 5
            ws.cell(row=i, column=base_col, value=label)

    # set sensible column widths
    for day_index in range(NUM_DAYS):
        base_col = 1 + day_index * 5
        # slot
        ws.column_dimensions[ws.cell(row=2, column=base_col).column_letter].width = 16
        # pseudo
        ws.column_dimensions[ws.cell(row=2, column=base_col + 1).column_letter].width = 25
        # trigram
        ws.column_dimensions[ws.cell(row=2, column=base_col + 2).column_letter].width = 12
        # id
        ws.column_dimensions[ws.cell(row=2, column=base_col + 3).column_letter].width = 18

    wb.save(template_path)


def write_schedule_per_days(
    schedules: list[dict[int, Player]],
    template_path: Path,
    output_path: Path,
) -> None:
    """
    Write three tables side-by-side on a single worksheet.

    Each table has columns: Slot / Pseudo / Trigram / ID
    Tables are separated by one empty column.
    """
    ensure_template(template_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(template_path)
    ws = wb.worksheets[0]
    ws.title = "Schedule"

    # ensure only one sheet remains
    while len(wb.worksheets) > 1:
        wb.remove(wb.worksheets[-1])

    labels = ["23:45 (veille)"] + generate_slot_labels()
    # rewrite labels (defensive)
    for row_offset, label in enumerate(labels, start=3):
        for day_index in range(NUM_DAYS):
            base_col = 1 + day_index * 5
            ws.cell(row=row_offset, column=base_col, value=label)

    # for each day write Pseudo / Trigram / ID columns
    for day_index in range(NUM_DAYS):
        schedule = schedules[day_index]
        base_col = 1 + day_index * 5
        for row in range(len(labels)):
            row_num = row + 3
            player = schedule.get(row)
            if player:
                ws.cell(row=row_num, column=base_col + 1, value=player.pseudo)
                ws.cell(row=row_num, column=base_col + 2, value=player.alliance_trigram)
                ws.cell(row=row_num, column=base_col + 3, value=player.player_id)
            else:
                # ensure blanks if no player
                ws.cell(row=row_num, column=base_col + 1, value="")
                ws.cell(row=row_num, column=base_col + 2, value="")
                ws.cell(row=row_num, column=base_col + 3, value="")

    wb.save(output_path)
