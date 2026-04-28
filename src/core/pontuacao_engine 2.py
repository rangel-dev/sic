"""
Pontuação Engine — Auditor de Pontuação BR/BIO.
Crosses Grade de Ativação (.xlsm) against GCP report (.xlsx/.csv) to validate
whether each SKU has active pricing within a ±2-cycle window of the reference cycle.
Uses a 19-cycle-per-year calendar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd


@dataclass
class PontuacaoResult:
    relatorio: list[dict] = field(default_factory=list)
    carga: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)   # {total, ok, fora, erro}
    error: Optional[str] = None


def _offset_ciclo(base: int, off: int) -> int:
    """Advance or retract a cycle reference using the 19-cycles-per-year calendar."""
    ano, ciclo = divmod(base, 100)
    ciclo += off
    if ciclo <= 0:
        ano -= 1
        ciclo = 19 + ciclo
    elif ciclo > 19:
        ano += 1
        ciclo -= 19
    return ano * 100 + ciclo


def _limpar_sku(v) -> str:
    """Remove NATBRA-/AVNBRA- prefixes, the '.0' artifact from pandas
    float-to-string conversion, non-digits and leading zeros."""
    if v is None:
        return ""
    s = str(v).strip()
    # pandas dtype=str converts numeric Excel cells via str(float) → "12345.0".
    # Drop a trailing ".0..." anywhere at the end (covers "12345.0",
    # "NATBRA-095046.0", "12345.00", etc.) before stripping non-digits,
    # otherwise the dot is removed and the SKU gets inflated 10×.
    s = re.sub(r"\.0+$", "", s)
    s = re.sub(r"(?i)NATBRA-|AVNBRA-", "", s)
    s = re.sub(r"\D", "", s)
    s = re.sub(r"^0+", "", s)
    return s


def _find_col(
    columns: list[str],
    needles: list[str],
    exclude: Optional[list[str]] = None,
) -> Optional[str]:
    """Return the first column whose name contains any of the needles
    (case-insensitive) and does NOT contain any term in `exclude`."""
    exclude = [e.upper() for e in (exclude or [])]
    for needle in needles:
        for col in columns:
            up = str(col).upper()
            if needle.upper() in up and not any(e in up for e in exclude):
                return col
    return None


class PontuacaoEngine:
    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self._progress = progress_callback or (lambda p, m: None)

    def run(self, ciclo_ref: int, grade_path: str, gcp_path: str) -> PontuacaoResult:
        try:
            self._progress(5, "Calculando janela de validade…")
            l_inf = _offset_ciclo(ciclo_ref, -2)
            l_sup = _offset_ciclo(ciclo_ref, +2)

            self._progress(15, "Lendo relatório GCP…")
            gcp_map, gcp_rows = self._read_gcp(gcp_path)
            self._progress(40, f"GCP: {gcp_rows} linhas → {len(gcp_map)} SKUs únicos válidos")

            self._progress(45, "Lendo Grade de Ativação…")
            skus = self._read_grade(grade_path)
            self._progress(58, f"Grade: {len(skus)} SKUs lidos")

            self._progress(60, f"Cruzando contra janela {l_inf}–{l_sup}…")
            result = self._validate(skus, gcp_map, l_inf, l_sup)
            result.stats["gcp_rows"] = gcp_rows
            result.stats["gcp_unique_skus"] = len(gcp_map)
            result.stats["grade_skus"] = len(skus)

            self._progress(100, "Concluído.")
            return result

        except Exception as exc:  # noqa: BLE001
            return PontuacaoResult(error=str(exc))

    # ── GCP ───────────────────────────────────────────────────────────────

    def _read_gcp(self, path: str) -> tuple[dict[str, list[dict]], int]:
        """Returns (gcp_map, total_rows_read)."""
        ext = Path(path).suffix.lower()
        if ext == ".csv":
            try:
                df = pd.read_csv(path, dtype=str, sep=None, engine="python")
            except UnicodeDecodeError:
                df = pd.read_csv(
                    path, dtype=str, sep=None, engine="python", encoding="cp1252"
                )
        else:
            df = pd.read_excel(path, sheet_name=0, dtype=str, engine="openpyxl")

        # Normalize column names (strip trailing spaces from headers like "ABRANGÊNCIA ")
        df.columns = [str(c).strip() for c in df.columns]

        cols = list(df.columns)
        col_sku = _find_col(
            cols,
            ["CD VENDA PRODUTO", "COD VENDA PRODUTO", "ESTRUTURA VENDAS", "PRODUTO"],
            exclude=["DESCR"],
        )
        # Abrangência: prefer the description column. Avoid "TIPO ESTRUTURA
        # (Abrang. e Vig.)" which is the structure type, not the abrangência text.
        col_abr = _find_col(
            cols,
            ["DESCRIÇÃO ABRANG", "DESCRICAO ABRANG", "ABRANGÊNCIA", "ABRANGENCIA", "ABRANG"],
            exclude=["TIPO", "COD"],
        )
        col_ini = _find_col(
            cols,
            ["CICLO INICIO", "CICLO_INICIO", "DT INICIO", "DT_INICIO"],
            exclude=["FIM", "FINAL", "TERMINO"],
        )
        col_fim = _find_col(
            cols,
            ["CICLO FINAL", "CICLO_FINAL", "DT TERMINO", "DT_TERMINO", "CICLO FIM"],
            exclude=["INICIO"],
        )

        if not col_sku:
            raise ValueError(
                "Coluna de SKU não encontrada no GCP. "
                "Esperado: 'PRODUTO' ou 'ESTRUTURA VENDAS'.\n"
                f"Colunas detectadas: {cols}"
            )

        total_rows = len(df)
        gcp_map: dict[str, list[dict]] = {}
        for _, row in df.iterrows():
            sku = _limpar_sku(row.get(col_sku))
            abr = str(row.get(col_abr, "") or "").upper()

            if not sku:
                continue
            if "BRASIL" not in abr and "BIOSPHERA" not in abr:
                continue

            try:
                ini = int(float(row.get(col_ini) or 0)) if col_ini else 0
            except (ValueError, TypeError):
                ini = 0

            try:
                fim_raw = row.get(col_fim) if col_fim else None
                fim = int(float(fim_raw)) if fim_raw and str(fim_raw).strip() not in ("", "nan") else 0
            except (ValueError, TypeError):
                fim = 0

            is_open = fim == 0
            abrangencia = "RE BIOSPHERA" if "BIOSPHERA" in abr else "BRASIL"

            gcp_map.setdefault(sku, []).append(
                {"ini": ini, "fim": fim, "is_open": is_open, "abrangencia": abrangencia}
            )

        if not gcp_map:
            sample_abr = []
            if col_abr is not None:
                sample_abr = [
                    str(v) for v in df[col_abr].dropna().astype(str).unique()[:8]
                ]
            raise ValueError(
                f"Nenhum registro válido encontrado no GCP "
                f"({total_rows} linhas lidas).\n"
                f"Coluna SKU detectada: '{col_sku}'.\n"
                f"Coluna Abrangência: '{col_abr}'.\n"
                f"Coluna Ciclo Início: '{col_ini}'.\n"
                f"Coluna Ciclo Final: '{col_fim}'.\n"
                f"Amostra de valores em '{col_abr}': {sample_abr}\n"
                f"Verifique se a abrangência das linhas contém 'BRASIL' ou 'BIOSPHERA'."
            )

        return gcp_map, total_rows

    # ── Grade ─────────────────────────────────────────────────────────────

    def _read_grade(self, path: str) -> list[tuple[str, str]]:
        """Return list of (raw_value, cleaned_sku) from the Grade de Ativação."""
        xl = pd.ExcelFile(path, engine="openpyxl")

        # Locate sheet whose name contains "GRADE DE ATIVAÇÃO"
        aba = next(
            (n for n in xl.sheet_names if "GRADE" in n.upper() and "ATIVA" in n.upper()),
            xl.sheet_names[0],
        )

        # Read without header to scan for the SKU header row
        raw = pd.read_excel(xl, sheet_name=aba, header=None, dtype=str)

        header_row_idx = None
        sku_col_idx = None
        for row_idx, row in raw.iterrows():
            for col_idx, cell in enumerate(row):
                if str(cell).strip().upper() == "SKU":
                    header_row_idx = row_idx
                    sku_col_idx = col_idx
                    break
            if header_row_idx is not None:
                break

        if header_row_idx is None:
            raise ValueError("Coluna 'SKU' não encontrada na Grade de Ativação.")

        skus: list[tuple[str, str]] = []
        for _, row in raw.iloc[header_row_idx + 1:].iterrows():
            raw_val = row.iloc[sku_col_idx]
            sku = _limpar_sku(raw_val)
            if sku:
                skus.append((str(raw_val), sku))

        return skus

    # ── Validate ──────────────────────────────────────────────────────────

    def _validate(
        self,
        skus: list[tuple[str, str]],
        gcp_map: dict[str, list[dict]],
        l_inf: int,
        l_sup: int,
    ) -> PontuacaoResult:
        relatorio: list[dict] = []
        carga: list[dict] = []
        stats = {"total": 0, "ok": 0, "fora": 0, "erro": 0}

        total = len(skus)
        for i, (raw_val, sku) in enumerate(skus):
            if i % max(1, total // 20) == 0:
                pct = 60 + int((i / max(1, total)) * 35)
                self._progress(pct, f"Validando SKU {i + 1}/{total}…")

            stats["total"] += 1
            records = gcp_map.get(sku, [])

            if not records:
                status = "NÃO ENCONTRADO"
                motivo = "SKU sem registro válido no GCP"
                abr_detectada = "N/A"
            else:
                abr_detectada = " / ".join(sorted({r["abrangencia"] for r in records}))
                valid = next(
                    (r for r in records if r["ini"] <= l_inf and (r["is_open"] or r["fim"] >= l_sup)),
                    None,
                )
                if valid:
                    status = "OK"
                    motivo = f"Conforme via {valid['abrangencia']} (Ciclo início: {valid['ini']})"
                else:
                    status = "FORA DA REGRA"
                    motivo = (
                        f"Existe em {abr_detectada}, mas ciclos não atendem "
                        f"a janela {l_inf}–{l_sup}"
                    )

            if status == "OK":
                stats["ok"] += 1
            elif status == "FORA DA REGRA":
                stats["fora"] += 1
            else:
                stats["erro"] += 1

            relatorio.append({
                "SKU Original": raw_val,
                "SKU Limpo": sku,
                "Abrangência GCP": abr_detectada,
                "Status": status,
                "Motivo": motivo,
            })

            if status != "OK":
                carga.append({
                    "COD. ABRANGENCIA": "",
                    "COD. VENDA PRODUTO": sku,
                    "DESCRIÇÃO": "",
                    "TIPO ESTRUTURA COMERCIAL": "2 - Região Estratégica",
                    "ESTRUTURA COMERCIAL": "14",
                    "DESCRIÇÃO ABRANGÊNCIA": "RE BIOSPHERA",
                    "CICLO INICIO COMERCIAL": l_inf,
                    "DT INICIO COMERCIAL": "",
                    "CICLO FINAL COMERCIAL": "",
                    "DT FINAL COMERCIAL": "",
                    "EMPORIO": "Não",
                    "STATUS": "",
                })

        return PontuacaoResult(relatorio=relatorio, carga=carga, stats=stats)
