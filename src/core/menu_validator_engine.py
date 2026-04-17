"""
MenuValidatorEngine — SIC v1.1.0
Compares category menus between Natura/Avon (origin) and CB (destination).

Rules:
  MISSING      → Category is online in origin but missing from CB entirely.
  INACTIVE_CB  → Category is online in origin but offline (or missing flag) in CB.
  MENU_HIDDEN  → Category should be in menu (showInMenu=true) in origin but hidden in CB.

Namespace: http://www.demandware.com/xml/impex/catalog/2006-10-31
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable
import pandas as pd
from lxml import etree


# Demandware XML namespace
NS = {"dw": "http://www.demandware.com/xml/impex/catalog/2006-10-31"}

# Alert codes — add new rules here in the future
ALERT_MISSING       = "MISSING"
ALERT_INACTIVE_CB   = "INACTIVE_CB"
ALERT_MENU_HIDDEN   = "MENU_HIDDEN"

ALERT_META = {
    ALERT_MISSING: {
        "icon": "⊖",
        "title": "Faltante no CB",
        "desc": "Categoria ativa na origem (Natura/Avon) mas ausente no catálogo CB.",
    },
    ALERT_INACTIVE_CB: {
        "icon": "⊗",
        "title": "Inativo no CB",
        "desc": "Categoria online na origem mas com online-flag=false no CB.",
    },
    ALERT_MENU_HIDDEN: {
        "icon": "⊙",
        "title": "Oculto no Menu",
        "desc": "Categoria visível no menu da origem mas oculta no menu do CB.",
    },
}


@dataclass
class MenuValidationResult:
    df_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    stats: dict = field(default_factory=dict)
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
class MenuValidatorEngine:
    """
    Modular engine for category menu validation.
    Each rule is a separate private method — add new rules by implementing
    _rule_<name> and registering it in _RULES.
    """

    # Registry of active rules — to add a new rule, just append its method here.
    _RULES = [
        "_rule_missing",
        "_rule_inactive_cb",
        "_rule_menu_hidden",
    ]

    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self._cb = progress_callback or (lambda pct, msg: None)

    # ── Public API ────────────────────────────────────────────────────────────
    def run(
        self,
        natura_path: str,
        avon_path: str,
        cb_path: str,
    ) -> MenuValidationResult:
        try:
            self._cb(5, "Lendo catálogo Natura…")
            df_natura = self._parse_catalog(natura_path, brand="Natura")

            self._cb(25, "Lendo catálogo Avon…")
            df_avon = self._parse_catalog(avon_path, brand="Avon")

            self._cb(45, "Lendo catálogo CB…")
            df_cb = self._parse_catalog(cb_path, brand="CB")

            self._cb(60, "Consolidando origens (Natura + Avon) — apenas menus visíveis…")
            # Origin = only categories that are ONLINE *and* VISIBLE IN MENU on ecommerce
            # This ensures we compare only what actually appears on the website navigation.
            df_origin = (
                pd.concat([df_natura, df_avon], ignore_index=True)
                .drop_duplicates(subset="category_id", keep="first")
            )
            df_origin_online = df_origin[
                (df_origin["online_flag"] == True) &
                (df_origin["show_in_menu"] == True)
            ].copy()

            self._cb(70, "Realizando merge…")
            df_merged = df_origin_online.merge(
                df_cb[["category_id", "display_name", "online_flag", "show_in_menu"]],
                on="category_id",
                how="left",
                suffixes=("_origin", "_cb"),
            )

            self._cb(80, "Aplicando regras de validação…")
            rows: list[dict] = []
            for rule_name in self._RULES:
                rule = getattr(self, rule_name)
                rows.extend(rule(df_merged))

            self._cb(92, "Montando relatório…")
            if rows:
                df_report = pd.DataFrame(rows, columns=[
                    "ID", "Nome", "Marca_Origem",
                    "Status_Origem", "Status_CB",
                    "Menu_Origem", "Menu_CB",
                    "Alerta",
                ])
            else:
                df_report = pd.DataFrame(columns=[
                    "ID", "Nome", "Marca_Origem",
                    "Status_Origem", "Status_CB",
                    "Menu_Origem", "Menu_CB",
                    "Alerta",
                ])

            stats = self._compute_stats(df_report)
            self._cb(100, "Concluído.")
            return MenuValidationResult(df_report=df_report, stats=stats)

        except Exception as exc:
            import traceback
            return MenuValidationResult(
                error=f"Erro durante a validação:\n{exc}\n\n{traceback.format_exc()}"
            )

    # ── XML Parser ────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_catalog(path: str, brand: str) -> pd.DataFrame:
        """
        Parses a Demandware catalog XML and extracts category attributes.
        Returns a DataFrame with normalized boolean columns.
        """
        tree = etree.parse(path)
        root = tree.getroot()

        records = []
        for cat in root.findall(".//dw:category", NS):
            cat_id = cat.get("category-id", "")
            if not cat_id:
                continue

            # display-name (first occurrence, any locale)
            name_el = cat.find("dw:display-name", NS)
            display_name = name_el.text.strip() if name_el is not None and name_el.text else cat_id

            # online-flag
            online_el = cat.find("dw:online-flag", NS)
            online_flag = (online_el.text or "").strip().lower() == "true" if online_el is not None else False

            # showInMenu (custom attribute)
            show_in_menu = MenuValidatorEngine._get_custom_attr(cat, "showInMenu")

            records.append({
                "category_id":  cat_id,
                "display_name": display_name,
                "brand":        brand,
                "online_flag":  online_flag,
                "show_in_menu": show_in_menu,
            })

        return pd.DataFrame(records)

    @staticmethod
    def _get_custom_attr(cat_el, attr_id: str) -> Optional[bool]:
        """Extracts a custom attribute boolean value from a <category> element."""
        for attr in cat_el.findall(".//dw:custom-attribute", NS):
            if attr.get("attribute-id") == attr_id:
                val = (attr.text or "").strip().lower()
                return val == "true"
        return None  # Attribute not present

    # ── Rules ─────────────────────────────────────────────────────────────────
    def _rule_missing(self, df: pd.DataFrame) -> list[dict]:
        """MISSING: Categories online in origin but not present in CB at all."""
        missing = df[df["online_flag_cb"].isna()]
        return [
            self._row(r, "Online", "—", r["show_in_menu_origin"], "—", ALERT_MISSING)
            for _, r in missing.iterrows()
        ]

    def _rule_inactive_cb(self, df: pd.DataFrame) -> list[dict]:
        """INACTIVE_CB: Online in origin, but offline in CB."""
        inactive = df[
            df["online_flag_cb"].notna() &
            (df["online_flag_cb"] == False)
        ]
        return [
            self._row(r, "Online", "Offline", r["show_in_menu_origin"], r.get("show_in_menu_cb"), ALERT_INACTIVE_CB)
            for _, r in inactive.iterrows()
        ]

    def _rule_menu_hidden(self, df: pd.DataFrame) -> list[dict]:
        """MENU_HIDDEN: showInMenu=True in origin but False or missing in CB."""
        hidden = df[
            df["online_flag_cb"].notna() &
            (df["online_flag_cb"] == True) &
            (df["show_in_menu_origin"] == True) &
            (df["show_in_menu_cb"] != True)
        ]
        return [
            self._row(r, "Online", "Online", True, r.get("show_in_menu_cb"), ALERT_MENU_HIDDEN)
            for _, r in hidden.iterrows()
        ]

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _bool_str(val) -> str:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "—"
        return "Sim" if val else "Não"

    def _row(self, r, status_origin: str, status_cb: str, menu_origin, menu_cb, alert: str) -> dict:
        return {
            "ID":           r["category_id"],
            "Nome":         r.get("display_name", r["category_id"]),
            "Marca_Origem": r.get("brand", ""),
            "Status_Origem": status_origin,
            "Status_CB":    status_cb,
            "Menu_Origem":  self._bool_str(menu_origin),
            "Menu_CB":      self._bool_str(menu_cb),
            "Alerta":       ALERT_META[alert]["title"],
        }

    @staticmethod
    def _compute_stats(df: pd.DataFrame) -> dict:
        if df.empty:
            return {"total": 0, "by_alert": {}}
        counts = df["Alerta"].value_counts().to_dict()
        return {
            "total": len(df),
            "by_alert": {
                ALERT_META[k]["title"]: counts.get(ALERT_META[k]["title"], 0)
                for k in ALERT_META
            },
        }
