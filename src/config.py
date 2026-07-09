from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"

# Colonnes CSV (index 0-based)
COL_PSEUDO = 1
COL_SPEEDUPS = 7
COL_AVAILABILITY = 8

DEFAULT_TEMPLATE = TEMPLATES_DIR / "planning_template.xlsx"
DEFAULT_OUTPUT = OUTPUT_DIR / "planning.xlsx"

SLOTS_PER_DAY = 48
