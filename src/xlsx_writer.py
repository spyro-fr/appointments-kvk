from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.config import SLOTS_PER_DAY, NUM_DAYS
from src.models import Player
from src.time_slots import generate_slot_labels


def ensure_template(template_path: Path) -> None:
    """Create a simple template with one sheet that has the time labels in column A
    and placeholder headers for ID/Alliance and Pseudo for NUM_DAYS to the right.
    """
    if template_path.exists():
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    # time header
    ws["A1"] = "Horaire"
    ws["A1"].font = header_font
    ws["A1"].fill = header_fill
    ws["A1"].alignment = Alignment(horizontal="center")

    # for each day, create two columns: ID / Alliance and Pseudo
    for day_index in range(NUM_DAYS):
        base_col = 2 + day_index * 2  # B, D, F ... (1-based)
        id_cell = ws.cell(row=1, column=base_col, value=f"Day {day_index + 1} - ID / Alliance")
        pseudo_cell = ws.cell(row=1, column=base_col + 1, value=f"Day {day_index + 1} - Pseudo")
        for cell in (id_cell, pseudo_cell):
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

    # create labels: first the previous-day 23:45, then the usual SLOTS_PER_DAY labels
    labels = ["23:45 (veille)"] + generate_slot_labels()
    for i, label in enumerate(labels, start=2):
        ws.cell(row=i, column=1, value=label)

    # set sensible column widths
    ws.column_dimensions["A"].width = 16
    for day_index in range(NUM_DAYS):
        col_letter_id = chr(ord("A") + (1 + day_index * 2))
        col_letter_pseudo = chr(ord("A") + (2 + day_index * 2))
        ws.column_dimensions[col_letter_id].width = 20
        ws.column_dimensions[col_letter_pseudo].width = 25

    wb.save(template_path)


def _format_id_alliance(player: Player) -> str:
    if not player:
        return ""
    parts = []
    if getattr(player, "player_id", None):
        parts.append(player.player_id)
    if getattr(player, "alliance_trigram", None):
        parts.append(player.alliance_trigram)
    return " / ".join(parts)


def write_schedule_per_days(
    schedules: list[dict[int, Player]],
    template_path: Path,
    output_path: Path,
) -> None:
    """
    Write all NUM_DAYS schedules on a single worksheet named 'Schedule'.
    Column A: time labels. For each day i (0-based) we use columns:
      base = 2 + i*2 -> ID / Alliance
      base+1 -> Pseudo

    schedules: list of per-day schedule dicts mapping row_index -> Player
    Each schedule dict corresponds to one day (NUM_DAYS long).
    Each schedule uses rows: 0..(SLOTS_PER_DAY) where row 0 is prev 23:45 and rows 1..SLOTS_PER_DAY are the normal slots.
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
    for row_offset, label in enumerate(labels, start=2):
        ws.cell(row=row_offset, column=1, value=label)

    # for each day write ID/Alliance and Pseudo columns
    for day_index in range(NUM_DAYS):
        schedule = schedules[day_index]
        base_col = 2 + day_index * 2
        for row in range(len(labels)):
            row_num = row + 2
            player = schedule.get(row)
            ws.cell(row=row_num, column=base_col, value=_format_id_alliance(player))
            ws.cell(row=row_num, column=base_col + 1, value=player.pseudo if player else "")

    wb.save(output_path)
