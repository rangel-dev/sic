"""
Cadastro Engine — Kit Validation.
Crosses Salesforce XML against BO Excel to find kit component divergences.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd


_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"


@dataclass
class KitValidationResult:
    errors: list[dict] = field(default_factory=list)  # [{Pai, Status, Detalhe}]
    stats: dict = field(default_factory=dict)          # {total, ok, erro}
    correction_xml: str = ""
    error: Optional[str] = None


def _so_numeros(val) -> str:
    """Strip non-digit characters, leaving only the numeric part of a SKU."""
    if val is None:
        return ""
    return re.sub(r"\D", "", str(val).strip())


class CadastroEngine:
    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self._progress = progress_callback or (lambda p, m: None)

    def run(self, xml_path: str, excel_path: str) -> KitValidationResult:
        try:
            self._progress(5, "Lendo planilha Excel do BO…")
            bo_mapa = self._read_excel(excel_path)

            self._progress(35, "Lendo XML do Salesforce…")
            products = self._read_xml(xml_path)

            self._progress(60, "Validando kits…")
            result = self._validate(bo_mapa, products)

            self._progress(100, "Concluído.")
            return result

        except Exception as exc:  # noqa: BLE001
            return KitValidationResult(error=str(exc))

    # ── Excel ─────────────────────────────────────────────────────────────

    def _read_excel(self, path: str) -> dict[str, list[dict]]:
        df = pd.read_excel(path, sheet_name=0, dtype=str, skiprows=3)
        keys = list(df.columns)

        col_pai   = self._find_col(keys, ["COD_VENDA_PAI", "MATERIAL_P"],  fallback_idx=1)
        col_filho = self._find_col(keys, ["COD_VENDA_FILHO", "MATERIAL_FI"], fallback_idx=5)
        col_qtd   = self._find_col_ci(keys, "QUANTIDADE", fallback_idx=7)

        bo_mapa: dict[str, list[dict]] = {}
        for _, row in df.iterrows():
            pai_num   = _so_numeros(row.get(col_pai))
            filho_num = _so_numeros(row.get(col_filho))
            try:
                qty = round(float(row.get(col_qtd) or 0))
            except (ValueError, TypeError):
                qty = 0

            if pai_num and filho_num:
                bo_mapa.setdefault(pai_num, []).append(
                    {"id": "NATBRA-" + filho_num, "num": filho_num, "qty": qty}
                )
        return bo_mapa

    @staticmethod
    def _find_col(keys: list[str], candidates: list[str], fallback_idx: int) -> str:
        for c in candidates:
            for key in keys:
                if c in str(key).upper():
                    return key
        return keys[fallback_idx] if fallback_idx < len(keys) else keys[0]

    @staticmethod
    def _find_col_ci(keys: list[str], needle: str, fallback_idx: int) -> str:
        for key in keys:
            if needle.upper() in key.upper():
                return key
        return keys[fallback_idx] if fallback_idx < len(keys) else keys[0]

    # ── XML ───────────────────────────────────────────────────────────────

    def _read_xml(self, path: str) -> list[dict]:
        """Return list of {pid_num, filhos: [{num, qty}]} for kits only."""
        tree = ET.parse(path)
        root = tree.getroot()

        # Support both namespaced and plain XML
        ns = _NS if root.tag.startswith("{") else ""
        tag = lambda t: f"{{{ns}}}{t}" if ns else t  # noqa: E731

        products = []
        for p in root.iter(tag("product")):
            pid_num = _so_numeros(p.get("product-id", ""))
            bundled = p.find(tag("bundled-products"))
            if bundled is None:
                continue

            filhos: list[dict] = []
            for c in bundled.findall(tag("bundled-product")):
                cid_num = _so_numeros(c.get("product-id", ""))
                qty_el  = c.find(tag("quantity"))
                try:
                    c_qty = round(float(qty_el.text or 0)) if qty_el is not None else 0
                except (ValueError, TypeError):
                    c_qty = 0
                filhos.append({"num": cid_num, "qty": c_qty})

            if filhos:
                products.append({"pid_num": pid_num, "filhos": filhos})

        return products

    # ── Validation ────────────────────────────────────────────────────────

    def _validate(self, bo_mapa: dict, products: list[dict]) -> KitValidationResult:
        errors: list[dict] = []
        kits_para_corrigir: list[dict] = []
        stats = {"total": 0, "ok": 0, "erro": 0}

        total = len(products)
        for i, prod in enumerate(products):
            if i % max(1, total // 10) == 0:
                pct = 60 + int((i / max(1, total)) * 30)
                self._progress(pct, f"Validando kit {i + 1}/{total}…")

            pid_num  = prod["pid_num"]
            filhos_sf = prod["filhos"]
            stats["total"] += 1

            filhos_bo = bo_mapa.get(pid_num)
            if filhos_bo is None:
                errors.append({
                    "Pai": pid_num,
                    "Status": "Ausente no BO",
                    "Detalhe": "Este kit não consta na planilha do BO.",
                })
                stats["erro"] += 1
                continue

            erro_no_kit = False

            # SF → BO
            for f_sf in filhos_sf:
                match = next((f for f in filhos_bo if f["num"] == f_sf["num"]), None)
                if match is None:
                    errors.append({
                        "Pai": pid_num,
                        "Status": "Divergente",
                        "Detalhe": f"Filho {f_sf['num']} está no SF mas NÃO no BO.",
                    })
                    erro_no_kit = True
                elif match["qty"] != f_sf["qty"]:
                    errors.append({
                        "Pai": pid_num,
                        "Status": "Divergente",
                        "Detalhe": (
                            f"Filho {f_sf['num']} com Qtd errada: "
                            f"SF={f_sf['qty']} / BO={match['qty']}"
                        ),
                    })
                    erro_no_kit = True

            # BO → SF (reverse check)
            sf_nums = {f["num"] for f in filhos_sf}
            for f_bo in filhos_bo:
                if f_bo["num"] not in sf_nums:
                    errors.append({
                        "Pai": pid_num,
                        "Status": "Divergente",
                        "Detalhe": f"Filho {f_bo['num']} está no BO mas falta no Salesforce.",
                    })
                    erro_no_kit = True

            if erro_no_kit:
                stats["erro"] += 1
                kits_para_corrigir.append({"pid": "NATBRA-" + pid_num, "filhos": filhos_bo})
            else:
                stats["ok"] += 1

        correction_xml = self._build_correction_xml(kits_para_corrigir)
        return KitValidationResult(errors=errors, stats=stats, correction_xml=correction_xml)

    # ── Correction XML ────────────────────────────────────────────────────

    @staticmethod
    def _build_correction_xml(kits: list[dict]) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31"'
            ' catalog-id="natura-br-storefront-catalog">',
        ]
        for kit in kits:
            lines.append(f'  <product product-id="{kit["pid"]}">')
            lines.append("    <bundled-products>")
            for f in kit["filhos"]:
                lines.append(f'      <bundled-product product-id="{f["id"]}">')
                lines.append(f"        <quantity>{f['qty']}</quantity>")
                lines.append("      </bundled-product>")
            lines.append("    </bundled-products>")
            lines.append("  </product>")
        lines.append("</catalog>")
        return "\n".join(lines)
