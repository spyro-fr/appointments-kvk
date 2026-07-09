from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.config import SLOTS_PER_DAY
from src.models import Player
from src.time_slots import generate_slot_labels, slot_index_to_label


def ensure_template(template_path: Path) -> None:
    if template_path.exists():
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Planning"

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    ws["A1"] = "Horaire"
    ws["B1"] = "Pseudo"
    for cell in ("A1", "B1"):
        ws[cell].font = header_font
        ws[cell].fill = header_fill
        ws[cell].alignment = Alignment(horizontal="center")

    for i, label in enumerate(generate_slot_labels(), start=2):
        ws.cell(row=i, column=1, value=label)

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 25
    wb.save(template_path)


def write_schedule(
    schedule: dict[int, Player],
    template_path: Path,
    output_path: Path,
) -> None:
    ensure_template(template_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(template_path)
    ws = wb.active

    for slot in range(SLOTS_PER_DAY):
        row = slot + 2
        ws.cell(row=row, column=1, value=slot_index_to_label(slot))

        player = schedule.get(slot)
        ws.cell(row=row, column=2, value=player.pseudo if player else "")

    wb.save(output_path)
