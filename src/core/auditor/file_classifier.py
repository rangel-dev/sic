"""
Classificador de arquivos para a entrada unificada do Auditor (Tarefa 1).

Detecta automaticamente se um arquivo solto/selecionado é Pricebook,
Catálogo, Grade de Ativação ou planilha do Kit BO, e qual(is) marca(s) ele
pertence — reaproveitando os mesmos sinais já usados em `BrandDetector` e
`excel_reader`, incluindo a checagem de país (BRD — incidente Chile) de
`BrandDetector.check_catalog_file`/`check_pricebook_file`. Não altera a
lógica de negócio do motor de auditoria (`auditor_engine.py`,
`kit_validation.py`) — é usado só para alimentar a UI de entrada.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import openpyxl
import pandas as pd

from src.core.brand_detector import BrandDetector, BrazilIdCheck
from src.core.excel_reader import find_grade_sheet_name

Category = Literal["pricebook", "catalog", "grade", "kit_bo", "unknown"]

# Metadados de exibição por categoria, na ordem em que aparecem no checklist.
CATEGORY_META: dict[str, dict] = {
    "pricebook": {"label": "Pricebook",          "icon": "📄", "singleton": True},
    "catalog":   {"label": "Catálogo",           "icon": "📚", "singleton": False},
    "grade":     {"label": "Grade de Ativação",  "icon": "📊", "singleton": False},
    "kit_bo":    {"label": "Kit BO",             "icon": "📦", "singleton": True},
}

# Assinatura estrita do Kit BO: precisa ter pelo menos uma destas colunas no
# cabeçalho (skiprows=3, mesma leitura de kit_validation._read_bo_excel) —
# sem fallback posicional (ao contrário de kit_validation._find_col, que
# sempre cai num índice quando não acha, o que geraria falso-positivo aqui).
_BO_COLUMN_MARKERS = ("COD_VENDA_PAI", "MATERIAL_PAI")


@dataclass(frozen=True)
class ClassifiedFile:
    path: str
    category: Category
    brands: set[str] = field(default_factory=set)
    reason: str = ""  # motivo legível quando category == "unknown"


def _country_reason(check: BrazilIdCheck) -> str:
    if check.country_hint:
        local = f'parece pertencer a {check.country_hint}'
    else:
        local = 'não tem marcador de Brasil ("-br"/"brazil")'
    return f'ID "{check.raw_id}" não corresponde a uma loja Brasil ({local}).'


def _classify_xml(path: str) -> ClassifiedFile:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.read(1024)
    except Exception:
        return ClassifiedFile(path, "unknown", reason="Não foi possível ler o arquivo XML.")

    if re.search(r'catalog-id=["\']', header):
        check = BrandDetector.check_catalog_file(path)
        if check.ok:
            return ClassifiedFile(path, "catalog", brands={check.brand})
        return ClassifiedFile(path, "unknown", reason=_country_reason(check))

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return ClassifiedFile(path, "unknown", reason="Não foi possível ler o arquivo XML.")

    if re.search(r'pricebook-id=["\']', content):
        checks = BrandDetector.check_pricebook_file(path)
        bad = next((c for c in checks if not c.ok), None)
        if bad is not None:
            return ClassifiedFile(path, "unknown", reason=_country_reason(bad))
        brands = {c.brand for c in checks if c.brand}
        return ClassifiedFile(path, "pricebook", brands=brands)

    return ClassifiedFile(path, "unknown", reason="XML não contém catalog-id nem pricebook-id.")


def _looks_like_kit_bo(path: str) -> bool:
    """Cabeçalho (linha 4, skiprows=3) precisa conter literalmente
    COD_VENDA_PAI ou MATERIAL_PAI — leitura só do cabeçalho (nrows=0)."""
    try:
        df = pd.read_excel(path, sheet_name=0, dtype=str, skiprows=3, nrows=0)
    except Exception:
        return False
    cols = [str(c).upper() for c in df.columns]
    return any(marker in col for col in cols for marker in _BO_COLUMN_MARKERS)


def _classify_excel(path: str) -> ClassifiedFile:
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return ClassifiedFile(path, "unknown", reason="Não foi possível ler o arquivo Excel.")

    try:
        if find_grade_sheet_name(wb) is not None:
            brands = BrandDetector.detect_single(path)
            return ClassifiedFile(path, "grade", brands=brands)
    finally:
        wb.close()

    if _looks_like_kit_bo(path):
        return ClassifiedFile(path, "kit_bo")

    return ClassifiedFile(
        path, "unknown",
        reason='Excel sem aba "GRADE DE ATIVAÇÃO" nem colunas do Kit BO (COD_VENDA_PAI/MATERIAL_PAI).'
    )


def classify_file(path: str) -> ClassifiedFile:
    """Classifica um único arquivo em Pricebook / Catálogo / Grade / Kit BO,
    ou 'unknown' com o motivo em `reason` (arquivo de tipo errado, país
    incorreto, Excel sem assinatura reconhecida etc.)."""
    ext = Path(path).suffix.lower()
    if ext == ".xml":
        return _classify_xml(path)
    if ext in (".xlsx", ".xlsm", ".xls"):
        return _classify_excel(path)
    return ClassifiedFile(path, "unknown", reason=f'Extensão "{ext or "?"}" não suportada.')


@dataclass(frozen=True)
class ReadinessState:
    """Espelho somente-leitura das checagens de `AuditorView._run()`
    (view_auditor.py) — usado só para alimentar o checklist ao vivo.
    `_run()` mantém suas próprias checagens intactas; esta função nunca
    substitui a validação real, só a reflete."""
    kit_only: bool
    pb_ok: bool
    cat_ok: bool
    cat_count: int
    grade_required: bool
    grade_ok: bool
    overall_ready: bool


def compute_readiness(
    pb_path: Optional[str],
    cat_paths: list[str],
    grade_paths: list[str],
    bo_path: Optional[str],
) -> ReadinessState:
    kit_only = bool(bo_path) and not pb_path
    pb_ok = kit_only or bool(pb_path)
    cat_count = len(cat_paths)
    cat_ok = cat_count > 0 and (kit_only or cat_count == 3)
    grade_required = bool(bo_path)
    grade_ok = (not grade_required) or bool(grade_paths)
    return ReadinessState(
        kit_only=kit_only,
        pb_ok=pb_ok,
        cat_ok=cat_ok,
        cat_count=cat_count,
        grade_required=grade_required,
        grade_ok=grade_ok,
        overall_ready=pb_ok and cat_ok and grade_ok,
    )
