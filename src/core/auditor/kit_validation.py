"""
Validação de composição de Kits para o Auditor (BRD-007).

Cruza os bundled-products dos XMLs de Catálogo (Salesforce) contra a planilha
do BO (COD_VENDA_PAI / FILHO / QUANTIDADE), reportando divergências de
composição e de quantidade.

A regra de comparação é portada, sem alterações, do antigo módulo
Cadastro → Validação de Kits (cadastro_engine.py). A diferença é estrutural:
em vez de rodar numa tela isolada, é chamada pelo AuditorEngine quando a
planilha do BO é anexada (upload opcional). As linhas retornadas já seguem o
schema de erro do Auditor ({sku, brand, detail}) para fluir pelo dashboard,
tabela e exportações existentes.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"


def _so_numeros(val) -> str:
    """Mantém apenas a parte numérica de um SKU (portado do CadastroEngine)."""
    if val is None:
        return ""
    return re.sub(r"\D", "", str(val).strip())


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
    """{pai_num: [{num, qty}]} lido da planilha do BO."""
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
            bo_mapa.setdefault(pai_num, []).append({"num": filho_num, "qty": qty})
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


def validate_kits(bo_path: str, cat_paths: list[str]) -> list[dict]:
    """
    Cruza os bundles dos catálogos contra a planilha do BO.

    Retorna linhas no schema do Auditor: {sku, brand, detail}. Cada divergência
    (kit ausente no BO, filho ausente de um lado, quantidade divergente) vira
    uma linha — mesma granularidade da tela antiga de Validação de Kits.
    """
    bo_mapa  = _read_bo_excel(bo_path)
    products = _read_kits_from_xml(cat_paths)

    rows: list[dict] = []
    for prod in products:
        pid_num   = prod["pid_num"]
        brand     = _brand_from_pid(prod["raw_pid"])
        sku       = (prod["raw_pid"] or pid_num).upper()
        filhos_sf = prod["filhos"]

        filhos_bo = bo_mapa.get(pid_num)
        if filhos_bo is None:
            rows.append({"sku": sku, "brand": brand,
                         "detail": "Kit ausente no BO: não consta na planilha do BO."})
            continue

        # SF → BO
        for f_sf in filhos_sf:
            match = next((f for f in filhos_bo if f["num"] == f_sf["num"]), None)
            if match is None:
                rows.append({"sku": sku, "brand": brand,
                             "detail": f"Filho {f_sf['num']} está no SF mas NÃO no BO."})
            elif match["qty"] != f_sf["qty"]:
                rows.append({"sku": sku, "brand": brand,
                             "detail": (f"Filho {f_sf['num']} com Qtd errada: "
                                        f"SF={f_sf['qty']} / BO={match['qty']}.")})

        # BO → SF (reverse check)
        sf_nums = {f["num"] for f in filhos_sf}
        for f_bo in filhos_bo:
            if f_bo["num"] not in sf_nums:
                rows.append({"sku": sku, "brand": brand,
                             "detail": f"Filho {f_bo['num']} está no BO mas falta no Salesforce."})

    return rows
