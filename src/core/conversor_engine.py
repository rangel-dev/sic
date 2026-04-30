"""
Conversor Biosphera Engine.
Converte Auditoria (Carga Biosphera) + Revista CF + Grade em arquivos de
Carga GCP e Exceções, seguindo a lógica do JS original.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd


@dataclass
class ConversorResult:
    excecoes: list[dict] = field(default_factory=list)
    carga: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    error: Optional[str] = None


def _calcular_ciclo(ciclo_str: str | int) -> int:
    """Calcula o ciclo base (recuo de 2 ciclos). Usa limite de 18 ciclos por ano (regra JS)."""
    c = int(ciclo_str)
    ano, cic = divmod(c, 100)
    cic -= 2
    if cic <= 0:
        ano -= 1
        cic = 18 + cic
    return ano * 100 + cic


def _limpar(v) -> str:
    """Remove não dígitos e zeros à esquerda."""
    if pd.isna(v) or v is None:
        return ""
    s = str(v).strip()
    s = re.sub(r"\.0+$", "", s)
    s = re.sub(r"\D", "", s)
    s = re.sub(r"^0+", "", s)
    return s


def _clean_num(v) -> float | None:
    """Converte valores monetários ou textos para float."""
    if pd.isna(v) or v is None or str(v).strip() == "":
        return None
    s = str(v).replace("R$", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _norm(s: str) -> str:
    """Remove todos os whitespace (incluindo \xa0, tabs) e converte para maiúsculas."""
    return re.sub(r'\s+', '', str(s).strip()).upper()


def _find_col(df: pd.DataFrame, needles: list[str]) -> dict:
    """Retorna {idx, row} da primeira célula que contenha uma das strings."""
    if df is None or df.empty:
        return {"idx": -1, "row": -1}
    needles_clean = [_norm(n) for n in needles]
    for row_idx in range(min(len(df), 40)):
        for col_idx in range(len(df.columns)):
            cell = df.iat[row_idx, col_idx]
            if pd.notna(cell):
                cell_clean = _norm(cell)
                for n in needles_clean:
                    if n in cell_clean:
                        return {"idx": col_idx, "row": row_idx}
    return {"idx": -1, "row": -1}


def _read_sheet(path: str, aba_names: list[str]) -> pd.DataFrame | None:
    """Lê a aba procurada e retorna o DataFrame cru (sem cabeçalho definido)."""
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", header=None)
        except UnicodeDecodeError:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", encoding="cp1252", header=None)
    else:
        xl = pd.ExcelFile(path, engine="openpyxl")
        targets_norm = [_norm(a) for a in aba_names]
        sheets_norm = {name: _norm(name) for name in xl.sheet_names}

        # Prioridade 1: match exato, respeitando a ordem da lista aba_names
        # (igual ao JS, que tenta ["PAÍS","PAIS"] antes de ["REGIÃO ESTRATÉGICA",...])
        target_sheet = None
        for target in targets_norm:
            for name, norm_name in sheets_norm.items():
                if norm_name == target:
                    target_sheet = name
                    break
            if target_sheet:
                break

        # Prioridade 2: match por substring (fallback para nomes compostos)
        if target_sheet is None:
            for target in targets_norm:
                for name, norm_name in sheets_norm.items():
                    if target in norm_name:
                        target_sheet = name
                        break
                if target_sheet:
                    break

        # Prioridade 3: primeira aba
        if target_sheet is None:
            target_sheet = xl.sheet_names[0]

        return pd.read_excel(xl, sheet_name=target_sheet, dtype=str, header=None)


class ConversorEngine:
    def __init__(self, progress_callback: Optional[Callable[[int, str], None]] = None):
        self._progress = progress_callback or (lambda p, m: None)

    def run(
        self,
        ciclo_base: int,
        aud_path: str,
        rev_path: str,
        grade_path: str,
    ) -> ConversorResult:
        try:
            self._progress(5, "Calculando ciclo…")
            ciclo_calc = _calcular_ciclo(ciclo_base)
            
            self._progress(10, "Lendo Carga Auditoria…")
            df_aud = _read_sheet(aud_path, ["Carga Biosphera", "Planilha1"])
            if df_aud is None:
                return ConversorResult(error="Falha ao ler Auditoria.")
            col_aud = _find_col(df_aud, ["COD. VENDA PRODUTO", "COD VENDA PRODUTO", "SKU"])
            if col_aud["idx"] == -1:
                return ConversorResult(error="Coluna 'COD. VENDA PRODUTO' ou 'SKU' não encontrada na Auditoria.")

            self._progress(30, "Lendo Revista CF…")
            df_rev = _read_sheet(rev_path, ["PAÍS", "PAIS", "REGIÃO ESTRATÉGICA", "REGIAO ESTRATEGICA"])
            if df_rev is None:
                return ConversorResult(error="Falha ao ler Revista CF.")
            
            col_zest = _find_col(df_rev, ["ZEST"])
            col_cv = _find_col(df_rev, ["CV"])
            col_pzest = _find_col(df_rev, ["DE KIT (PREÇO BASE KIT)", "PRECO KIT", "PREÇO KIT"])
            col_pcv = _find_col(df_rev, ["DE (PREÇO BASE UNITÁRIO)", "PRECO UNITARIO", "PREÇO UNITÁRIO"])
            col_pts_g = _find_col(df_rev, ["PONTOS GANHOS (PTS)", "PONTOS GANHOS"])
            col_pts_f = _find_col(df_rev, ["PONTOS FILHOS (PTS)", "PONTOS FILHOS"])

            self._progress(50, "Indexando Revista CF…")
            zest_map = {}
            cv_map = {}
            for i, row in df_rev.iterrows():
                if col_zest["idx"] != -1 and i > col_zest["row"]:
                    z = _limpar(row.iat[col_zest["idx"]])
                    if z: zest_map.setdefault(z, []).append(row)
                
                if col_cv["idx"] != -1 and i > col_cv["row"]:
                    c = _limpar(row.iat[col_cv["idx"]])
                    if c: cv_map.setdefault(c, []).append(row)

            self._progress(65, "Lendo Grade de Backup…")
            grade_map = {}
            col_grade_sku = {"idx": -1, "row": -1}
            col_grade_preco = {"idx": -1, "row": -1}
            if grade_path:
                df_grade = _read_sheet(grade_path, ["GRADE", "PLANILHA1"])
                if df_grade is not None:
                    col_grade_sku = _find_col(df_grade, ["SKU"])
                    col_grade_preco = _find_col(df_grade, ["DE", "PREÇO", "PRECO"])
                    if col_grade_sku["idx"] != -1:
                        for i, row in df_grade.iterrows():
                            if i > col_grade_sku["row"]:
                                s = _limpar(row.iat[col_grade_sku["idx"]])
                                if s: grade_map.setdefault(s, []).append(row)

            self._progress(75, "Cruzando dados…")
            carga = []
            excecoes = []
            stats = {"total": 0, "match": 0, "linhas": 0, "erro": 0}

            total_aud = len(df_aud)
            for i, row in df_aud.iterrows():
                if i <= col_aud["row"]:
                    continue

                if i % max(1, total_aud // 20) == 0:
                    pct = 75 + int((i / max(1, total_aud)) * 20)
                    self._progress(pct, f"Processando linha {i + 1}/{total_aud}…")

                sku_raw = row.iat[col_aud["idx"]]
                sku = _limpar(sku_raw)
                if not sku:
                    continue

                stats["total"] += 1
                encontrado = False

                # 1. KIT (ZEST)
                if sku in zest_map:
                    encontrado = True
                    stats["match"] += 1
                    for m in zest_map[sku]:
                        pzest = _clean_num(m.iat[col_pzest["idx"]]) if col_pzest["idx"] != -1 else None
                        pcv = _clean_num(m.iat[col_pcv["idx"]]) if col_pcv["idx"] != -1 else None
                        ptsg = _clean_num(m.iat[col_pts_g["idx"]]) if col_pts_g["idx"] != -1 else None
                        ptsf = _clean_num(m.iat[col_pts_f["idx"]]) if col_pts_f["idx"] != -1 else 0
                        cv_val = _limpar(m.iat[col_cv["idx"]]) if col_cv["idx"] != -1 else None
                        
                        carga.append(self._build_row(sku, ciclo_calc, pzest, ptsg, pcv, cv_val, ptsf))
                
                # 2. INDIVIDUAL (CV)
                elif sku in cv_map:
                    encontrado = True
                    stats["match"] += 1
                    m = cv_map[sku][0]
                    pcv = _clean_num(m.iat[col_pcv["idx"]]) if col_pcv["idx"] != -1 else None
                    ptsg = _clean_num(m.iat[col_pts_g["idx"]]) if col_pts_g["idx"] != -1 else None
                    
                    carga.append(self._build_row(sku, ciclo_calc, pcv, ptsg, None, None, 0))

                # 3. GRADE (BACKUP)
                elif sku in grade_map:
                    encontrado = True
                    stats["match"] += 1
                    m = grade_map[sku][0]
                    preco = _clean_num(m.iat[col_grade_preco["idx"]]) if col_grade_preco["idx"] != -1 else None
                    
                    carga.append(self._build_row(sku, ciclo_calc, preco, 0, None, None, 0))

                # EXCEÇÃO
                if not encontrado:
                    stats["erro"] += 1
                    excecoes.append({
                        "CODIGO_AUDITORIA": sku_raw,
                        "STATUS": "Não localizado na Revista ou Grade",
                        "ACCAO": "Verificar se o código existe no ciclo ou se está na aba correta"
                    })

            stats["linhas"] = len(carga)
            
            self._progress(100, "Concluído!")
            return ConversorResult(excecoes=excecoes, carga=carga, stats=stats)

        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            return ConversorResult(error=str(exc))

    def _build_row(self, sku, ciclo, preco, pts_ganhos, preco_kit, item_kit, pts_filhos) -> dict:
        row = {
            "COD. VENDA PRODUTO": int(sku) if str(sku).isdigit() else sku,
            "TIPO ESTRUTURA COMERCIAL": "2 - Região Estratégica",
            "ESTRUTURA COMERCIAL": 14,
            "CICLO INICIO COMERCIAL": int(ciclo),
            "DT INICIO COMERCIAL": "",
            "CICLO FINAL COMERCIAL": "",
            "DT FINAL COMERCIAL": "",
            "CANAL": "",
            "SISTEMA": "",
            "MOEDA": "REAL",
            "TIPO ESTRUTURA PREÇO": "2 - Região Estratégica",
            "ESTRUTURA PREÇO": 14,
            "CICLO INICIO PREÇO": int(ciclo),
            "DT INICIO PREÇO": "",
            "CICLO FINAL PREÇO": "",
            "DT FINAL PREÇO": "",
            "MOTIVO": "1 - VENDA",
            "PREÇO  ($)": preco,
            "REDUTOR (%)": 70,
            "PONTOS": pts_ganhos,
            "ITEM KIT": int(item_kit) if item_kit and str(item_kit).isdigit() else None,
            "PREÇO ITEM KIT": preco_kit,
            "PONTOS ": pts_filhos
        }
        
        if row["ITEM KIT"] is None:
            del row["ITEM KIT"]
            
        return row
