"""
Excel Reader Utilities – shared helpers for Excel parsing across engines.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import openpyxl


def find_grade_sheet_name(wb: openpyxl.Workbook) -> Optional[str]:
    """Returns the name of the 'GRADE DE ATIVAÇÃO' sheet, or None if not found."""
    if "GRADE DE ATIVAÇÃO" in wb.sheetnames:
        return "GRADE DE ATIVAÇÃO"
    for name in wb.sheetnames:
        if "GRADE" in name.upper() and "ATIVA" in name.upper():
            return name
    return None


def assert_grade_visible(wb: openpyxl.Workbook, sheet_name: str, file_name: str) -> None:
    """Raises ValueError if the grade sheet is hidden (RN-10)."""
    if wb[sheet_name].sheet_state == "hidden":
        raise ValueError(f"A aba '{sheet_name}' está oculta no arquivo {file_name}")


def dominant_brand(nat_count: int, avn_count: int) -> str:
    """Returns 'natura' or 'avon' based on SKU counts. Ties go to 'natura'."""
    return "natura" if nat_count >= avn_count else "avon"
