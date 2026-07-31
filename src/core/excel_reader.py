"""
Excel Reader Utilities – shared helpers for Excel parsing across engines.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import openpyxl

_PRICE_RE = re.compile(r'^[+-]?\d+(?:\.\d+)?')


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


def parse_price(val) -> Optional[float]:
    """Parses a price cell the same way the legacy JS parseFloat() did:
    strips 'R$', then matches only the leading numeric run — truncates at a
    decimal COMMA on purpose (e.g. "R$ 45,90" -> 45.0, not 45.90). This is
    intentional legacy-parity behavior, not a bug; do not "fix" the regex.
    Returns None for empty/non-numeric input.
    """
    if val is None:
        return None
    v_str = str(val).replace("R$", "").strip()
    m = _PRICE_RE.match(v_str)
    if m:
        return float(m.group(0))
    return None
