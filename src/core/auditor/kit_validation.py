"""
Validação de composição de Kits para o Auditor (BRD-007).

Cruza os bundled-products dos XMLs de Catálogo (Salesforce) contra a planilha
do BO (COD_VENDA_PAI / FILHO / QUANTIDADE), reportando divergências de
composição e de quantidade.

A regra de comparação é portada, sem alterações, do antigo módulo
Cadastro → Validação de Kits (cadastro_engine.py) — os números batem 1:1 com
aquela tela. A diferença é estrutural: roda dentro do Auditor quando a planilha
do BO é anexada (upload opcional). Além das linhas no schema de erro do Auditor
({sku, brand, detail}), devolve os dados ricos que a tela antiga exibia (KPIs
analisados/corretos/divergências e o XML de Correção) via `KitAuditData`.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import pandas as pd

_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"


@dataclass
class KitAuditData:
    """Resultado rico da validação de kits, para o painel dedicado no Auditor."""
    rows: list[dict] = field(default_factory=list)   # [{sku, pai, brand, status, detail}]
    stats: dict = field(default_factory=dict)         # {total, ok, erro}
    correction_xml: str = ""


def _so_numeros(val) -> str:
    """Mantém apenas a parte numérica de um SKU. Remove primeiro o artefato
    '.0' de célula numérica lida como float (ex.: '73667.0' → '73667'),
    senão o ponto sai e o '0' final infla o código ('736670')."""
    if val is None:
        return ""
    s = str(val).strip()
    s = re.sub(r"\.0+$", "", s)
    return re.sub(r"\D", "", s)


def _brand_from_pid(raw_pid: str) -> str:
    """Deriva a marca a partir do prefixo do product-id (AVNBRA- → Avon)."""
    return "Avon" if str(raw_pid).upper().startswith("AVNBRA-") else "Natura"


def _find_col(keys: list[str], candidates: list[str], fallback_idx: int) -> str:
    for c in candidates:
        for key in keys:
            if c in str(key).upper():
                return key
    return keys[fallback_idx] if fallback_idx < len(keys) else keys[0]


def _find_col_ci(keys: list[str], needle: str, fallback_idx: int) -> str:
    for key in keys:
        if needle.upper() in str(key).upper():
            return key
    return keys[fallback_idx] if fallback_idx < len(keys) else keys[0]


def _read_bo_excel(path: str) -> dict[str, list[dict]]:
    """{pai_num: [{id, num, qty}]} lido da planilha do BO."""
    df = pd.read_excel(path, sheet_name=0, dtype=str, skiprows=3)
    keys = list(df.columns)

    col_pai   = _find_col(keys, ["COD_VENDA_PAI", "MATERIAL_P"],   1)
    col_filho = _find_col(keys, ["COD_VENDA_FILHO", "MATERIAL_FI"], 5)
    col_qtd   = _find_col_ci(keys, "QUANTIDADE", 7)

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


def _read_kits_from_xml(paths: list[str]) -> list[dict]:
    """[{pid_num, raw_pid, filhos:[{num, qty}]}] só para produtos com bundle."""
    products: list[dict] = []
    for path in paths:
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        root = tree.getroot()

        ns = _NS if root.tag.startswith("{") else ""
        tag = lambda t: f"{{{ns}}}{t}" if ns else t  # noqa: E731

        for p in root.iter(tag("product")):
            raw_pid = p.get("product-id", "")
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
                products.append({"pid_num": _so_numeros(raw_pid),
                                 "raw_pid": raw_pid, "filhos": filhos})
    return products


def _build_correction_xml(kits: list[dict]) -> str:
    """Gera o XML de Correção (composição do BO) para os kits divergentes.
    Portado fielmente de cadastro_engine.CadastroEngine._build_correction_xml."""
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


def validate_kits(bo_path: str, cat_paths: list[str]) -> KitAuditData:
    """
    Cruza os bundles dos catálogos contra a planilha do BO.

    Retorna `KitAuditData` com:
      - rows: linhas de divergência {sku, pai, brand, status, detail}. `sku`
        (NATBRA- completo) e `brand` alimentam o dashboard genérico; `pai`
        (numérico) e `status` alimentam o painel dedicado de kits.
      - stats: {total kits analisados, ok, erro} — idêntico à tela antiga.
      - correction_xml: XML de correção dos kits divergentes (composição do BO).
    """
    bo_mapa  = _read_bo_excel(bo_path)
    products = _read_kits_from_xml(cat_paths)

    rows: list[dict] = []
    kits_para_corrigir: list[dict] = []
    stats = {"total": 0, "ok": 0, "erro": 0}

    for prod in products:
        stats["total"] += 1
        pid_num   = prod["pid_num"]
        brand     = _brand_from_pid(prod["raw_pid"])
        sku       = (prod["raw_pid"] or pid_num).upper()
        filhos_sf = prod["filhos"]

        filhos_bo = bo_mapa.get(pid_num)
        if filhos_bo is None:
            rows.append({"sku": sku, "pai": pid_num, "brand": brand,
                         "status": "Ausente no BO",
                         "detail": "Este kit não consta na planilha do BO."})
            stats["erro"] += 1
            continue

        erro_no_kit = False

        # SF → BO
        for f_sf in filhos_sf:
            match = next((f for f in filhos_bo if f["num"] == f_sf["num"]), None)
            if match is None:
                rows.append({"sku": sku, "pai": pid_num, "brand": brand,
                             "status": "Divergente",
                             "detail": f"Filho {f_sf['num']} está no SF mas NÃO no BO."})
                erro_no_kit = True
            elif match["qty"] != f_sf["qty"]:
                rows.append({"sku": sku, "pai": pid_num, "brand": brand,
                             "status": "Divergente",
                             "detail": (f"Filho {f_sf['num']} com Qtd errada: "
                                        f"SF={f_sf['qty']} / BO={match['qty']}")})
                erro_no_kit = True

        # BO → SF (reverse check)
        sf_nums = {f["num"] for f in filhos_sf}
        for f_bo in filhos_bo:
            if f_bo["num"] not in sf_nums:
                rows.append({"sku": sku, "pai": pid_num, "brand": brand,
                             "status": "Divergente",
                             "detail": f"Filho {f_bo['num']} está no BO mas falta no Salesforce."})
                erro_no_kit = True

        if erro_no_kit:
            stats["erro"] += 1
            kits_para_corrigir.append({"pid": "NATBRA-" + pid_num, "filhos": filhos_bo})
        else:
            stats["ok"] += 1

    correction_xml = _build_correction_xml(kits_para_corrigir)
    return KitAuditData(rows=rows, stats=stats, correction_xml=correction_xml)
