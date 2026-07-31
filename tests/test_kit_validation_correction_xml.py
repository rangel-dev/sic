"""BRD-007 fix — catalog-id correto por marca no XML de Correção de kits."""
from __future__ import annotations

from pathlib import Path

import openpyxl
from lxml import etree

from src.core.auditor.kit_validation import validate_kits

_CATALOG_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"


def _write_bo_excel(path: Path, pai: str, filho: str, cm_pai: str, cm_filho: str, qty: int) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(3):
        ws.append([])  # skiprows=3 na leitura
    ws.append([
        "IGNORAR", "MATERIAL_PAI", "COD_VENDA_PAI", "COL3", "COL4",
        "MATERIAL_FILHO", "COD_VENDA_FILHO", "COL7", "QUANTIDADE",
    ])
    ws.append(["", cm_pai, pai, "", "", cm_filho, filho, "", str(qty)])
    wb.save(path)


def _write_catalog_xml(path: Path, catalog_id: str, pai_pid: str, filho_pid: str, qty: int) -> None:
    root = etree.Element("catalog", nsmap={None: _CATALOG_NS})
    root.set("catalog-id", catalog_id)
    prod = etree.SubElement(root, f"{{{_CATALOG_NS}}}product")
    prod.set("product-id", pai_pid)
    bundled = etree.SubElement(prod, f"{{{_CATALOG_NS}}}bundled-products")
    bp = etree.SubElement(bundled, f"{{{_CATALOG_NS}}}bundled-product")
    bp.set("product-id", filho_pid)
    qel = etree.SubElement(bp, f"{{{_CATALOG_NS}}}quantity")
    qel.text = str(qty)
    Path(path).write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


def test_avon_correction_xml_usa_catalog_id_avon(tmp_path):
    """Kit Avon divergente -> XML de correção deve sair com o catalog-id real
    do catálogo Avon, não com o hardcode antigo de Natura."""
    bo_path = tmp_path / "bo.xlsx"
    # BO diz quantidade 1; catálogo publica quantidade 2 -> força divergência
    # (QTD_ERRADA), o que inclui o kit em kits_para_corrigir.
    _write_bo_excel(bo_path, pai="1001", filho="2001", cm_pai="", cm_filho="", qty=1)

    cat_path = tmp_path / "catalogo_avon.xml"
    _write_catalog_xml(
        cat_path, catalog_id="avon-br-storefront-catalog",
        pai_pid="AVNBRA-1001", filho_pid="AVNBRA-2001", qty=2,
    )

    result = validate_kits(str(bo_path), [str(cat_path)], grade=None)

    assert result.stats["erro"] >= 1
    assert set(result.correction_xmls.keys()) == {"Avon"}

    xml_avon = result.correction_xmls["Avon"]
    root = etree.fromstring(xml_avon.encode("utf-8"))
    assert root.get("catalog-id") == "avon-br-storefront-catalog"
    assert root.get("catalog-id") != "natura-br-storefront-catalog"

    prod_ids = [p.get("product-id") for p in root.findall(f"{{{_CATALOG_NS}}}product")]
    assert prod_ids == ["AVNBRA-1001"]


def test_natura_e_avon_geram_xmls_separados_com_catalog_id_proprio(tmp_path):
    """Com kits divergentes das duas marcas, cada uma sai num XML próprio,
    cada um com o catalog-id do catálogo de origem daquela marca."""
    bo_path = tmp_path / "bo.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(3):
        ws.append([])
    ws.append([
        "IGNORAR", "MATERIAL_PAI", "COD_VENDA_PAI", "COL3", "COL4",
        "MATERIAL_FILHO", "COD_VENDA_FILHO", "COL7", "QUANTIDADE",
    ])
    ws.append(["", "", "1001", "", "", "", "2001", "", "1"])  # Natura: BO qty=1
    ws.append(["", "", "3001", "", "", "", "4001", "", "1"])  # Avon: BO qty=1
    wb.save(bo_path)

    cat_nat = tmp_path / "catalogo_natura.xml"
    _write_catalog_xml(
        cat_nat, catalog_id="natura-br-storefront-catalog",
        pai_pid="NATBRA-1001", filho_pid="NATBRA-2001", qty=2,
    )
    cat_avn = tmp_path / "catalogo_avon.xml"
    _write_catalog_xml(
        cat_avn, catalog_id="avon-br-storefront-catalog",
        pai_pid="AVNBRA-3001", filho_pid="AVNBRA-4001", qty=2,
    )

    result = validate_kits(str(bo_path), [str(cat_nat), str(cat_avn)], grade=None)

    assert set(result.correction_xmls.keys()) == {"Natura", "Avon"}
    root_nat = etree.fromstring(result.correction_xmls["Natura"].encode("utf-8"))
    root_avn = etree.fromstring(result.correction_xmls["Avon"].encode("utf-8"))
    assert root_nat.get("catalog-id") == "natura-br-storefront-catalog"
    assert root_avn.get("catalog-id") == "avon-br-storefront-catalog"
