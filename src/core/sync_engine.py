"""
Sync Engine – Merchandising Sync: store-list assignments + product attributes.
Migrated from sync.js.  Implements the 'Golden Rule' and 10-minute freshness check.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import openpyxl
from lxml import etree

CATALOG_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"
SKU_PATTERN = re.compile(r"^(NAT|AVN)BRA-", re.IGNORECASE)
MIN_FILE_AGE_SECONDS = 600  # 10-minute golden rule


@dataclass
class SyncResult:
    xml_content: Optional[bytes] = None
    stats: dict = field(default_factory=dict)
    brand: str = "unknown"
    catalog_id: str = ""
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class SyncEngine:
    def __init__(self, progress_callback: Optional[Callable] = None):
        self._progress = progress_callback or (lambda p, msg: None)

    # ── Entry point ───────────────────────────────────────────────────────
    def run(
        self,
        excel_paths: list[str],
        catalog_xml_paths: list[str],
    ) -> SyncResult:
        result = SyncResult()

        try:
            # File-age safety check
            self._progress(5, "Validando antiguidade dos XMLs…")
            for path in catalog_xml_paths:
                warning = self._check_file_age(path)
                if warning:
                    result.warnings.append(warning)

            # Parse Excel: lists + visibility
            self._progress(15, "Lendo planilhas Excel…")
            excel_lists, visibility_map, seal_map, brand = self._parse_excel_files(excel_paths)
            result.brand = brand

            if not excel_lists and not visibility_map:
                result.error = "Nenhum dado encontrado nas planilhas."
                return result

            # Parse current catalog XMLs
            self._progress(40, "Analisando Catálogos atuais…")
            current_state, catalog_id = self._parse_catalogs(catalog_xml_paths)
            result.catalog_id = catalog_id

            # Calculate delta
            self._progress(65, "Calculando Delta…")
            delta = self._calculate_delta(excel_lists, visibility_map, seal_map, current_state, brand)

            # Generate XML
            self._progress(80, "Gerando XML Catálogo Delta…")
            result.xml_content = self._generate_catalog_xml(delta, catalog_id)

            result.stats = {
                "additions":   sum(len(v) for v in delta["add"].values()),
                "removals":    sum(len(v) for v in delta["remove"].values()),
                "attr_updates": len(delta["attributes"]),
                "lists_processed": len(excel_lists),
            }
            self._progress(100, "Sync concluído!")

        except Exception as exc:
            result.error = str(exc)

        return result

    # ── File age check ────────────────────────────────────────────────────
    def _check_file_age(self, path: str) -> Optional[str]:
        try:
            age = time.time() - os.path.getmtime(path)
            if age < MIN_FILE_AGE_SECONDS:
                minutes = int(age / 60)
                return (
                    f"{Path(path).name}: arquivo tem apenas {minutes}m "
                    f"(regra: ≥ 10 min). Pode estar incompleto."
                )
        except OSError:
            pass
        return None

    # ── Excel parsing ─────────────────────────────────────────────────────
    def _parse_excel_files(
        self, paths: list[str]
    ) -> tuple[dict[str, set[str]], dict[str, bool], dict[str, str | None], str]:
        excel_lists: dict[str, set[str]] = {}
        visibility: dict[str, bool] = {}
        seals: dict[str, str | None] = {}
        nat = avn = 0

        for path in paths:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

            # Grade sheet → visibility + seals
            for name in wb.sheetnames:
                n = name.upper()
                if "GRADE" in n or "ATIVA" in n:
                    v_map, s_map, file_nat, file_avn = self._parse_grade(wb[name])
                    visibility.update(v_map)
                    seals.update(s_map)
                    nat += file_nat
                    avn += file_avn
                    break

            # Lista sheets
            for name in wb.sheetnames:
                if re.match(r"(?i)lista[-_]\d+", name):
                    skus = self._parse_lista(wb[name])
                    key  = name.upper().replace("-", "_")
                    excel_lists.setdefault(key, set()).update(skus)
                    for s in skus:
                        if s.startswith("NATBRA-"):
                            nat += 1
                        elif s.startswith("AVNBRA-"):
                            avn += 1

            wb.close()

        brand = "avon" if avn > nat else "natura"
        return excel_lists, visibility, seals, brand

    def _parse_grade(
        self, ws
    ) -> tuple[dict[str, bool], dict[str, str | None], int, int]:
        rows = list(ws.iter_rows(max_row=600, values_only=True))
        sku_col = vis_col = selo_col = None
        sku_start = None
        nat = avn = 0

        for i, row in enumerate(rows[:60]):
            for j, cell in enumerate(row):
                if cell is None:
                    continue
                v = str(cell).strip()
                vu = v.upper()
                if "VISIBLE" in vu or "VISIBILIDADE" in vu:
                    vis_col = j
                elif vu in ("SELO", "FLAG", "MARKETING", "BADGE"):
                    selo_col = j
                if sku_col is None and SKU_PATTERN.match(v):
                    sku_col = j
                    sku_start = i

        visibility: dict[str, bool] = {}
        seals: dict[str, str | None] = {}
        if sku_col is None:
            return visibility, seals, nat, avn

        empty = 0
        for row in rows[sku_start:]:
            raw = row[sku_col] if sku_col < len(row) else None
            if not raw or not SKU_PATTERN.match(str(raw).strip()):
                empty += 1
                if empty >= 50:
                    break
                continue
            empty = 0
            sku = str(raw).strip().upper()
            if sku.startswith("NATBRA-"):
                nat += 1
            else:
                avn += 1

            vis_raw = row[vis_col] if vis_col is not None and vis_col < len(row) else None
            visibility[sku] = str(vis_raw).strip().upper() in ("SIM", "S", "1", "TRUE", "X", "✓") if vis_raw else True

            seal_raw = row[selo_col] if selo_col is not None and selo_col < len(row) else None
            seals[sku] = str(seal_raw).strip() if seal_raw else None

        return visibility, seals, nat, avn

    def _parse_lista(self, ws) -> set[str]:
        skus: set[str] = set()
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell and SKU_PATTERN.match(str(cell).strip()):
                    skus.add(str(cell).strip().upper())
        return skus

    # ── Catalog parsing ───────────────────────────────────────────────────
    def _parse_catalogs(
        self, paths: list[str]
    ) -> tuple[dict, str]:
        """Returns current state dict and primary catalog_id."""
        state: dict = {
            "assignments": {},   # category_id -> set of product-ids
            "online": {},        # product-id -> bool
            "searchable": {},    # product-id -> bool
        }
        catalog_id = ""

        for path in paths:
            try:
                parser = etree.XMLParser(resolve_entities=False, no_network=True)
                tree = etree.parse(path, parser=parser)
            except etree.XMLSyntaxError as exc:
                raise ValueError(f"XML inválido ({Path(path).name}): {exc}") from exc

            ns = {"c": CATALOG_NS}
            root = tree.getroot()
            if not catalog_id:
                catalog_id = root.get("catalog-id", "")

            for ca in root.findall("c:category-assignment", ns):
                cat_id = ca.get("category-id", "").upper()
                pid    = ca.get("product-id",  "").upper()
                state["assignments"].setdefault(cat_id, set()).add(pid)

            for prod_el in root.findall(".//c:product", ns):
                pid = prod_el.get("product-id", "").upper()
                online_el = prod_el.find("c:online-flag", ns)
                srch_el   = prod_el.find("c:searchable-flag", ns)
                if online_el is not None:
                    state["online"][pid] = (online_el.text or "").lower() == "true"
                if srch_el is not None:
                    state["searchable"][pid] = (srch_el.text or "").lower() == "true"

        return state, catalog_id

    # ── Delta calculation ─────────────────────────────────────────────────
    def _calculate_delta(
        self,
        excel_lists: dict[str, set[str]],
        visibility: dict[str, bool],
        seals: dict[str, str | None],
        current: dict,
        brand: str,
    ) -> dict:
        delta: dict = {"add": {}, "remove": {}, "attributes": {}}

        current_assignments: dict[str, set[str]] = current.get("assignments", {})

        for list_key, excel_skus in excel_lists.items():
            sf_skus = current_assignments.get(list_key, set())

            to_add    = excel_skus - sf_skus
            to_remove = sf_skus - excel_skus

            if to_add:
                delta["add"][list_key] = to_add
            if to_remove:
                delta["remove"][list_key] = to_remove

        # Attribute updates (online-flag, searchable-flag)
        all_excel_skus = set().union(*excel_lists.values()) if excel_lists else set()
        for sku in all_excel_skus:
            vis = visibility.get(sku, True)
            sf_online     = current["online"].get(sku)
            sf_searchable = current["searchable"].get(sku)

            attrs: dict = {}
            if sf_online is None or sf_online != vis:
                attrs["online-flag"] = "true" if vis else "false"
            if sf_searchable is None or sf_searchable != vis:
                attrs["searchable-flag"] = "true" if vis else "false"

            seal = seals.get(sku)
            if seal:
                attrs["natg_preferencialProductSlot"] = json.dumps(
                    {"Name": seal, "Color": "#edf0ff", "Border": "radius"}
                )

            if attrs:
                delta["attributes"][sku] = attrs

        return delta

    # ── XML generation ────────────────────────────────────────────────────
    def _generate_catalog_xml(self, delta: dict, catalog_id: str) -> bytes:
        root = etree.Element("catalog", xmlns=CATALOG_NS)
        root.set("catalog-id", catalog_id or "storefront-catalog")

        # Removals (mode="delete")
        for cat_id, skus in delta.get("remove", {}).items():
            for sku in sorted(skus):
                ca = etree.SubElement(root, "category-assignment")
                ca.set("category-id", cat_id)
                ca.set("product-id",  sku)
                ca.set("mode",        "delete")

        # Additions
        for cat_id, skus in delta.get("add", {}).items():
            for sku in sorted(skus):
                ca = etree.SubElement(root, "category-assignment")
                ca.set("category-id", cat_id)
                ca.set("product-id",  sku)

        # Attribute updates
        for sku, attrs in delta.get("attributes", {}).items():
            prod_el = etree.SubElement(root, "product")
            prod_el.set("product-id", sku)

            if "online-flag" in attrs:
                el = etree.SubElement(prod_el, "online-flag")
                el.text = attrs["online-flag"]

            if "searchable-flag" in attrs:
                el = etree.SubElement(prod_el, "searchable-flag")
                el.text = attrs["searchable-flag"]

            custom_attrs = {k: v for k, v in attrs.items()
                            if k not in ("online-flag", "searchable-flag")}
            if custom_attrs:
                cas_el = etree.SubElement(prod_el, "custom-attributes")
                for attr_id, val in custom_attrs.items():
                    ca_el = etree.SubElement(cas_el, "custom-attribute")
                    ca_el.set("attribute-id", attr_id)
                    ca_el.text = val

        return etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", pretty_print=True
        )
