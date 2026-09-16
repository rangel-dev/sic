"""
Segmentado Engine – Grade (múltiplas abas "LISTA_NN") → Pricebook XML Segmentado.

Gera um Pricebook XML enxuto (override de preço) para uma única lista/campanha
segmentada, a partir da coluna "POR SEGMENTADO" encontrada em abas específicas
da grade de ativação — totalmente independente do Pricebook DE/POR completo
gerado pelo GeradorEngine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Optional

import openpyxl
from lxml import etree

from src.core.excel_reader import dominant_brand
from src.core.gerador_engine import PRICEBOOK_DEFS, PRICEBOOK_NS, SKU_PATTERN

# "Loja" reaproveita os 3 parents já conhecidos do GeradorEngine — sem tabela nova.
LOJA_PARENT_IDS: dict[str, str] = {
    "natura": PRICEBOOK_DEFS["natura"]["por"]["id"],
    "avon":   PRICEBOOK_DEFS["avon"]["por"]["id"],
    "ml":     PRICEBOOK_DEFS["ml"]["por"]["id"],
}

# IDs das pricebooks default (DE e POR de todas as marcas). Um pricebook
# segmentado NUNCA pode usar um desses IDs — importar sobrescreveria a
# pricebook principal em produção.
RESERVED_PRICEBOOK_IDS: frozenset[str] = frozenset(
    defs[key]["id"] for defs in PRICEBOOK_DEFS.values() for key in ("de", "por")
)

BRAND_PREFIX: dict[str, str] = {"natura": "NATBRA-", "avon": "AVNBRA-"}

HEADER_TARGETS: tuple[str, ...] = ("POR SEGMENTADO", "POR ORIGEM")
_HEADER_SCAN_ROWS = 15

_WS_RE = re.compile(r"\s+")
_WS_US_RE = re.compile(r"[\s_]+")  # BRD-011: usado só no fallback de _find_header_row


@dataclass
class SegmentedSku:
    product_id: str
    price: float


@dataclass
class ListaCandidate:
    sheet_name: str
    lp_label: Optional[str]
    periodo_sugerido: Optional[tuple[date, date]]
    total_skus_informado: Optional[int]
    rows: list[SegmentedSku]
    rows_scanned: int
    matched_header: str
    nat_count: int = 0
    avn_count: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def display_label(self) -> str:
        return self.lp_label or self.sheet_name


@dataclass
class SegmentScanResult:
    candidates: list[ListaCandidate] = field(default_factory=list)
    detected_brand: Optional[str] = None
    brand_mismatch: bool = False
    error: Optional[str] = None


_EMPTY_STATS = {"scanned": 0, "nat": 0, "avn": 0, "foreign": 0, "no_price": 0, "dup": 0}


class SegmentadoEngine:
    # ── Normalização de cabeçalho ────────────────────────────────────────
    @staticmethod
    def _normalize(cell) -> str:
        """upper + strip + colapsa espaços internos múltiplos — necessário
        pois a grade real tem cabeçalhos como 'POR  SEGMENTADO' (2+ espaços)."""
        if cell is None:
            return ""
        return _WS_RE.sub(" ", str(cell).strip().upper())

    # ── Parsing de preço (NÃO reaproveita excel_reader.parse_price, que
    # trunca propositalmente na vírgula decimal para manter paridade com o
    # JS legado de DE/POR — "POR SEGMENTADO" é uma coluna nova, sem esse
    # legado, então precisa preservar os centavos corretamente) ──────────
    @staticmethod
    def _parse_price_cell(val) -> Optional[float]:
        if val is None or isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).replace("R$", "").replace("\xa0", "").strip()
        if not s:
            return None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # ── Detecção de aba candidata ─────────────────────────────────────────
    @staticmethod
    def _loose(s: str) -> str:
        """BRD-011: versão 'frouxa' p/ fallback — remove todo espaço/underscore.
        Nunca substitui `_normalize`; só é chamada quando a busca exata (título
        com espaço, como hoje) não encontrar nada."""
        return _WS_US_RE.sub("", s)

    @classmethod
    def _find_header_row(cls, rows: list[tuple]) -> Optional[tuple[int, dict[str, int], str]]:
        for i, row in enumerate(rows[:_HEADER_SCAN_ROWS]):
            header_map: dict[str, int] = {}
            for j, cell in enumerate(row):
                norm = cls._normalize(cell)
                if not norm:
                    continue
                if norm not in header_map:
                    header_map[norm] = j
            matched = next((t for t in HEADER_TARGETS if t in header_map), None)
            if matched is None:
                # BRD-011: fallback aditivo, só roda se a busca exata acima
                # não achou nada — tolera título sem espaço/underscore.
                loose_targets = {cls._loose(t) for t in HEADER_TARGETS}
                matched = next(
                    (key for key in header_map if cls._loose(key) in loose_targets),
                    None,
                )
            if matched is not None:
                return i, header_map, matched
        return None

    @staticmethod
    def _pick_product_id_column(rows: list[tuple], header_row_idx: int) -> Optional[int]:
        """Não confia no rótulo do cabeçalho (a coluna 'SKU' pode conter só o
        número, enquanto 'COD SALES FORCE' tem o NATBRA-/AVNBRA- completo) —
        escolhe a coluna com mais valores batendo o padrão de SKU."""
        sample = rows[header_row_idx + 1: header_row_idx + 51]
        counts: dict[int, int] = {}
        for row in sample:
            for j, cell in enumerate(row):
                if cell is None:
                    continue
                if SKU_PATTERN.match(str(cell).strip()):
                    counts[j] = counts.get(j, 0) + 1
        if not counts:
            return None
        return max(counts, key=lambda col: counts[col])

    @staticmethod
    def _extract_periodo(rows: list[tuple]) -> Optional[tuple[date, date]]:
        if len(rows) < 1 or len(rows[0]) < 3:
            return None
        start, end = rows[0][1], rows[0][2]
        if isinstance(start, date) and isinstance(end, date):
            start_d = start.date() if isinstance(start, datetime) else start
            end_d = end.date() if isinstance(end, datetime) else end
            if end_d < start_d:
                return None
            return start_d, end_d
        return None

    @classmethod
    def _extract_lp_label(cls, rows: list[tuple]) -> Optional[str]:
        if len(rows) < 2 or len(rows[1]) < 2:
            return None
        label_cell, value_cell = rows[1][0], rows[1][1]
        if cls._normalize(label_cell).startswith("LP") and value_cell:
            return str(value_cell).strip()
        return None

    @classmethod
    def _extract_total_informado(cls, rows: list[tuple]) -> Optional[int]:
        if len(rows) < 3 or len(rows[2]) < 2:
            return None
        label_cell, value_cell = rows[2][0], rows[2][1]
        label_norm = cls._normalize(label_cell)
        # BRD-011: segunda condição é fallback aditivo (título sem espaço).
        if ((label_norm == "TOTAL SKUS" or cls._loose(label_norm) == "TOTALSKUS")
                and isinstance(value_cell, (int, float))
                and not isinstance(value_cell, bool)):
            return int(value_cell)
        return None

    @classmethod
    def _extract_rows(
        cls,
        rows: list[tuple],
        header_row_idx: int,
        product_id_col: int,
        price_col: int,
        expected_prefix: Optional[str],
    ) -> tuple[list[SegmentedSku], dict[str, int]]:
        """Retorna os SKUs com preço segmentado válido (deduplicados — a
        última ocorrência vence, como no GeradorEngine) e contadores para
        diagnóstico."""
        by_sku: dict[str, SegmentedSku] = {}
        stats = dict(_EMPTY_STATS)
        empty_streak = 0

        for row in rows[header_row_idx + 1:]:
            raw_sku = row[product_id_col] if product_id_col < len(row) else None
            sku = str(raw_sku).strip().upper() if raw_sku is not None else ""
            if not sku:
                empty_streak += 1
                if empty_streak >= 50:
                    break
                continue
            empty_streak = 0
            if not SKU_PATTERN.match(sku):
                continue

            stats["scanned"] += 1
            if sku.startswith("NATBRA-"):
                stats["nat"] += 1
            elif sku.startswith("AVNBRA-"):
                stats["avn"] += 1

            # Filtro de contaminação cruzada (mesma regra do GeradorEngine)
            if expected_prefix and not sku.startswith(expected_prefix):
                stats["foreign"] += 1
                continue

            price_val = row[price_col] if price_col < len(row) else None
            price = cls._parse_price_cell(price_val)
            if price is None or price <= 0:
                stats["no_price"] += 1
                continue

            if sku in by_sku:
                stats["dup"] += 1
            by_sku[sku] = SegmentedSku(product_id=sku, price=price)

        return list(by_sku.values()), stats

    @classmethod
    def _scan_sheet(cls, ws, sheet_name: str, expected_brand: str) -> Optional[ListaCandidate]:
        # Só lê o cabeçalho primeiro — a grade real tem ~55 abas e a maioria
        # não é candidata; ler tudo de todas seria desperdício.
        head = list(ws.iter_rows(max_row=_HEADER_SCAN_ROWS, values_only=True))
        found = cls._find_header_row(head)
        if found is None:
            return None
        header_row_idx, header_map, matched_header = found
        price_col = header_map.get(matched_header)
        if price_col is None:
            return None

        rows = list(ws.iter_rows(max_row=10000, values_only=True))
        warnings: list[str] = []
        expected_prefix = BRAND_PREFIX.get(expected_brand)

        product_id_col = cls._pick_product_id_column(rows, header_row_idx)
        if product_id_col is None:
            seg_rows: list[SegmentedSku] = []
            stats = dict(_EMPTY_STATS)
            warnings.append("Aba sem SKUs — nenhuma linha com NATBRA-/AVNBRA- encontrada.")
        else:
            seg_rows, stats = cls._extract_rows(
                rows, header_row_idx, product_id_col, price_col, expected_prefix
            )

        total_informado = cls._extract_total_informado(rows)
        if total_informado is not None and total_informado != stats["scanned"]:
            warnings.append(
                f"Total informado na aba ({total_informado}) difere do total de linhas "
                f"de SKU identificadas ({stats['scanned']})."
            )
        if stats["foreign"]:
            warnings.append(
                f"{stats['foreign']} SKU(s) de outra marca ignorado(s) "
                f"(marca selecionada: {expected_brand.capitalize()})."
            )
        if stats["no_price"]:
            hint = ""
            if stats["no_price"] == stats["scanned"] - stats["foreign"]:
                hint = " Se a coluna for fórmula, abra e salve a planilha no Excel antes de importar."
            warnings.append(
                f"{stats['no_price']} SKU(s) sem preço {matched_header} válido serão ignorados.{hint}"
            )
        if stats["dup"]:
            warnings.append(
                f"{stats['dup']} SKU(s) repetido(s) na aba — prevalece a última ocorrência."
            )

        return ListaCandidate(
            sheet_name=sheet_name,
            lp_label=cls._extract_lp_label(rows),
            periodo_sugerido=cls._extract_periodo(rows),
            total_skus_informado=total_informado,
            rows=seg_rows,
            rows_scanned=stats["scanned"],
            matched_header=matched_header,
            nat_count=stats["nat"],
            avn_count=stats["avn"],
            warnings=warnings,
        )

    # ── Entry point público ───────────────────────────────────────────────
    @classmethod
    def scan_workbook(
        cls,
        path: str,
        expected_brand: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> SegmentScanResult:
        progress = progress_callback or (lambda p, m: None)
        candidates: list[ListaCandidate] = []

        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            return SegmentScanResult(error=f"Não foi possível abrir o arquivo: {exc}")

        try:
            sheet_names = wb.sheetnames
            total = len(sheet_names) or 1
            for i, sheet_name in enumerate(sheet_names):
                progress(int(i / total * 100), f"Verificando aba '{sheet_name}'…")
                ws = wb[sheet_name]
                # Abas ocultas são listas desativadas — mesma regra do SyncEngine.
                if getattr(ws, "sheet_state", "visible") != "visible":
                    continue
                try:
                    candidate = cls._scan_sheet(ws, sheet_name, expected_brand)
                except Exception:
                    candidate = None
                if candidate is not None:
                    candidates.append(candidate)
        finally:
            wb.close()

        progress(100, "Varredura concluída.")

        nat_count = sum(c.nat_count for c in candidates)
        avn_count = sum(c.avn_count for c in candidates)
        detected_brand = dominant_brand(nat_count, avn_count) if (nat_count or avn_count) else None
        brand_mismatch = detected_brand is not None and detected_brand != expected_brand

        error = None
        if not candidates:
            targets = " ou ".join(f"'{t}'" for t in HEADER_TARGETS)
            error = f"Nenhuma aba com coluna {targets} encontrada nesta grade."

        return SegmentScanResult(
            candidates=candidates,
            detected_brand=detected_brand,
            brand_mismatch=brand_mismatch,
            error=error,
        )

    # ── Janela online-from / online-to (BRT → UTC, sem DST) ─────────────────
    @staticmethod
    def compute_online_window(dt_start: datetime, dt_end: datetime) -> tuple[str, str]:
        """Converte hora local (Brasília, UTC-3 fixo, sem horário de verão)
        para UTC. Segundos/microssegundos são zerados — o seletor da UI só
        produz granularidade de minuto."""
        utc_start = dt_start.replace(second=0, microsecond=0) + timedelta(hours=3)
        utc_end = dt_end.replace(second=0, microsecond=0) + timedelta(hours=3)
        online_from = utc_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        online_to = utc_end.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return online_from, online_to

    # ── Geração do XML ──────────────────────────────────────────────────────
    @staticmethod
    def build_xml(
        pricebook_id: str,
        parent_id: str,
        online_from: str,
        online_to: str,
        skus: list[SegmentedSku],
        display_name: Optional[str] = None,
    ) -> bytes:
        NS = PRICEBOOK_NS
        root = etree.Element("pricebooks", xmlns=NS)
        pb_el = etree.SubElement(root, "pricebook")

        header = etree.SubElement(pb_el, f"{{{NS}}}header")
        header.set("pricebook-id", pricebook_id)

        curr = etree.SubElement(header, f"{{{NS}}}currency")
        curr.text = "BRL"

        if display_name:
            disp = etree.SubElement(header, f"{{{NS}}}display-name")
            disp.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
            disp.text = display_name

        online_flag = etree.SubElement(header, f"{{{NS}}}online-flag")
        online_flag.text = "true"

        online_from_el = etree.SubElement(header, f"{{{NS}}}online-from")
        online_from_el.text = online_from

        online_to_el = etree.SubElement(header, f"{{{NS}}}online-to")
        online_to_el.text = online_to

        parent_el = etree.SubElement(header, f"{{{NS}}}parent")
        parent_el.text = parent_id

        tables = etree.SubElement(pb_el, f"{{{NS}}}price-tables")
        for sku in skus:
            pt = etree.SubElement(tables, f"{{{NS}}}price-table")
            pt.set("product-id", sku.product_id)
            amt = etree.SubElement(pt, f"{{{NS}}}amount")
            amt.set("quantity", "1")
            amt.text = f"{sku.price:.2f}"

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
