"""
RelatorioMenuEngine — match de menus Natura/Avon (origem) × CB (Minha Loja).

Menu na origem = categoria com online-flag=true e showInMenu=true.
Cada menu da origem é classificado contra o catálogo CB:
  OK            → existe no CB (mesmo category-id) e está online.
  AUSENTE_CB    → não existe no CB.
  OFFLINE_CB    → existe no CB, mas com online-flag=false.

Namespace: http://www.demandware.com/xml/impex/catalog/2006-10-31
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd
from lxml import etree

NS = {"dw": "http://www.demandware.com/xml/impex/catalog/2006-10-31"}

STATUS_OK         = "OK"
STATUS_AUSENTE_CB = "Ausente no CB"
STATUS_OFFLINE_CB = "Offline no CB"

BRANDS = ("Natura", "Avon")

COLUMNS = ["Marca", "ID", "Nome", "Nivel", "Pai", "Status_CB", "Resultado"]


@dataclass
class RelatorioMenuResult:
    df_report: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=COLUMNS))
    stats: dict = field(default_factory=dict)
    source_files: dict = field(default_factory=dict)
    error: Optional[str] = None


class RelatorioMenuEngine:
    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self._cb = progress_callback or (lambda pct, msg: None)

    def run(self, natura_path: str, avon_path: str, cb_path: str) -> RelatorioMenuResult:
        try:
            self._cb(5, "Lendo catálogo Natura…")
            df_natura = parse_catalog(natura_path)

            self._cb(30, "Lendo catálogo Avon…")
            df_avon = parse_catalog(avon_path)

            self._cb(55, "Lendo catálogo CB…")
            df_cb = parse_catalog(cb_path)

            self._cb(80, "Cruzando menus com o CB…")
            cb_online = dict(zip(df_cb["category_id"], df_cb["online_flag"]))
            frames = [
                self._match(df, brand, cb_online)
                for brand, df in (("Natura", df_natura), ("Avon", df_avon))
            ]
            df_report = pd.concat(frames, ignore_index=True)

            self._cb(100, "Concluído.")
            return RelatorioMenuResult(
                df_report=df_report,
                stats=compute_stats(df_report),
                source_files={"Natura": natura_path, "Avon": avon_path, "CB": cb_path},
            )
        except Exception as exc:
            import traceback
            return RelatorioMenuResult(
                error=f"Erro ao gerar o relatório:\n{exc}\n\n{traceback.format_exc()}"
            )

    @staticmethod
    def _match(df_origin: pd.DataFrame, brand: str, cb_online: dict) -> pd.DataFrame:
        if df_origin.empty:
            return pd.DataFrame(columns=COLUMNS)

        names = dict(zip(df_origin["category_id"], df_origin["display_name"]))
        menus = df_origin[
            (df_origin["online_flag"] == True) & (df_origin["show_in_menu"] == True)
        ].drop_duplicates(subset="category_id", keep="first")

        rows = []
        for _, r in menus.iterrows():
            cat_id = r["category_id"]
            parent = r["parent"]
            is_top = not parent or parent == "root"

            if cat_id not in cb_online:
                status_cb, resultado = "—", STATUS_AUSENTE_CB
            elif cb_online[cat_id]:
                status_cb, resultado = "Online", STATUS_OK
            else:
                status_cb, resultado = "Offline", STATUS_OFFLINE_CB

            rows.append({
                "Marca":     brand,
                "ID":        cat_id,
                "Nome":      r["display_name"],
                "Nivel":     "Menu" if is_top else "Submenu",
                "Pai":       "—" if is_top else names.get(parent, parent),
                "Status_CB": status_cb,
                "Resultado": resultado,
            })
        return pd.DataFrame(rows, columns=COLUMNS)


def parse_catalog(path: str) -> pd.DataFrame:
    root = etree.parse(path).getroot()
    records = []
    for cat in root.findall(".//dw:category", NS):
        cat_id = cat.get("category-id", "")
        if not cat_id:
            continue

        name_el = cat.find("dw:display-name", NS)
        display_name = name_el.text.strip() if name_el is not None and name_el.text else cat_id

        online_el = cat.find("dw:online-flag", NS)
        online_flag = online_el is not None and (online_el.text or "").strip().lower() == "true"

        parent_el = cat.find("dw:parent", NS)
        parent = (parent_el.text or "").strip() if parent_el is not None else ""

        records.append({
            "category_id":  cat_id,
            "display_name": display_name,
            "parent":       parent,
            "online_flag":  online_flag,
            "show_in_menu": _get_custom_bool(cat, "showInMenu"),
        })
    return pd.DataFrame(
        records,
        columns=["category_id", "display_name", "parent", "online_flag", "show_in_menu"],
    )


def _get_custom_bool(cat_el, attr_id: str) -> Optional[bool]:
    for attr in cat_el.findall(".//dw:custom-attribute", NS):
        if attr.get("attribute-id") == attr_id:
            return (attr.text or "").strip().lower() == "true"
    return None


def compute_stats(df: pd.DataFrame) -> dict:
    by_brand = {}
    for brand in BRANDS:
        sub = df[df["Marca"] == brand]
        counts = sub["Resultado"].value_counts()
        by_brand[brand] = {
            "total":   len(sub),
            "ok":      int(counts.get(STATUS_OK, 0)),
            "ausente": int(counts.get(STATUS_AUSENTE_CB, 0)),
            "offline": int(counts.get(STATUS_OFFLINE_CB, 0)),
        }
    totals = {k: sum(b[k] for b in by_brand.values()) for k in ("total", "ok", "ausente", "offline")}
    return {"by_brand": by_brand, **totals}
