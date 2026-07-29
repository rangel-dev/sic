"""
Validação de composição de Kits para o Auditor (BRD-007).

O motor é **dirigido pela Grade de Ativação**: ela lista quais SKUs são kits do
ciclo (coluna TIPO MATERIAL = ZEST) e qual é o Código de Material (CM) vigente de
cada SKU. A grade NÃO relaciona pai↔filho — a composição só existe no catálogo
(bundled-products) e na planilha do BO. Daí o fluxo:

  Grade  → quais kits auditar e qual material está vigente
  Catálogo → a composição publicada no Salesforce (lado auditado)
  BO       → a composição esperada (referência)

O BO é um histórico acumulado: o mesmo SKU reaparece com vários CMs ao longo dos
ciclos. A versão vigente de um kit é selecionada por MATERIAL_PAI == CM da grade,
o que além de isolar a versão certa também desambigua a marca (o BO não tem
coluna de marca, mas o CM é único por material).

Devolve `KitAuditData` (linhas de divergência, KPIs e XML de Correção) para o
painel dedicado do Auditor. Não alimenta o total da auditoria tradicional.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import pandas as pd

_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"

# Subtipos estruturados de divergência (campo "kind" em cada row), usados pela
# UI para gerar cards de filtro dedicados na seção de Validação de Kits (BO).
KIND_KIT_SEM_BUNDLE      = "kit_sem_bundle_no_catalogo"
KIND_AUSENTE_NO_BO       = "ausente_no_bo"
KIND_MATERIAL_PAI_DIV    = "material_pai_divergente"
KIND_MATERIAL_FILHO_DIV  = "material_filho_divergente"
KIND_FILHO_AUSENTE_BO    = "filho_ausente_bo"
KIND_QTD_ERRADA          = "qtd_errada"
KIND_FILHO_FALTANDO_SF   = "filho_faltando_sf"
KIND_FILHO_FORA_DA_GRADE = "filho_fora_da_grade"

# A ordem deste dict define a ordem dos cards na UI.
KIT_ERROR_META: dict[str, dict] = {
    KIND_KIT_SEM_BUNDLE: {
        "title": "Kit sem Composição no SF", "icon": "🧩",
        "impact": "Kit ativo não montado",
        "desc": "A Grade marca o SKU como kit (ZEST), mas ele não tem "
                "bundled-products em nenhum catálogo do Salesforce.",
    },
    KIND_AUSENTE_NO_BO: {
        "title": "Kit Ausente no BO", "icon": "🚫",
        "impact": "Kit não cadastrado no BO",
        "desc": "O kit está ativo na Grade mas não consta na planilha do BO.",
    },
    KIND_MATERIAL_PAI_DIV: {
        "title": "Material do Pai Desatualizado", "icon": "🏷️",
        "impact": "Grade × BO em desacordo",
        "desc": "A Grade diz qual CM (material) está vigente para este kit, e "
                "o BO não tem nenhuma linha com esse CM — só conhece "
                "materiais antigos dele.",
    },
    KIND_MATERIAL_FILHO_DIV: {
        "title": "Material do Filho Desatualizado", "icon": "🔖",
        "impact": "Grade × BO em desacordo",
        "desc": "A Grade diz qual CM (material) está vigente para este "
                "componente, e o BO não tem nenhuma linha com esse CM — só "
                "conhece materiais antigos dele.",
    },
    KIND_FILHO_AUSENTE_BO: {
        "title": "Filho Ausente no BO", "icon": "➖",
        "impact": "Composição incompleta no BO",
        "desc": "O filho está no Salesforce mas não existe registro dele no BO "
                "para este pai.",
    },
    KIND_QTD_ERRADA: {
        "title": "Quantidade Divergente", "icon": "🔢",
        "impact": "Kit com quantidade errada",
        "desc": "A quantidade do filho no Salesforce não bate com a quantidade "
                "cadastrada no BO.",
    },
    KIND_FILHO_FALTANDO_SF: {
        "title": "Filho Faltando no SF", "icon": "➕",
        "impact": "Composição incompleta no SF",
        "desc": "O filho consta no BO mas não foi encontrado no bundle do "
                "Salesforce.",
    },
    KIND_FILHO_FORA_DA_GRADE: {
        "title": "Filho Fora da Grade", "icon": "🚧",
        "impact": "Componente não vigente",
        "desc": "O kit no Salesforce usa um componente que não está na Grade de "
                "Ativação do ciclo.",
    },
}

# Status exibido na tabela (a UI colore "Ausente" em vermelho e "Divergente" em âmbar)
_STATUS_POR_KIND = {
    KIND_KIT_SEM_BUNDLE:      "Ausente no SF",
    KIND_AUSENTE_NO_BO:       "Ausente no BO",
    KIND_MATERIAL_PAI_DIV:    "Material Divergente (Pai)",
    KIND_MATERIAL_FILHO_DIV:  "Material Divergente (Filho)",
    KIND_FILHO_AUSENTE_BO:    "Ausente no BO",
    KIND_QTD_ERRADA:          "Quantidade Divergente",
    KIND_FILHO_FALTANDO_SF:   "Ausente no SF",
    KIND_FILHO_FORA_DA_GRADE: "Ausente na Grade",
}


@dataclass
class GradeIndex:
    """Índice da Grade de Ativação, chaveado por (marca, SKU numérico).

    `cm`   : CM vigente de cada SKU do ciclo (whitelist implícita).
    `kits` : SKUs marcados como kit na grade (TIPO MATERIAL = ZEST).

    `kits` vazio (grade sem a coluna TIPO MATERIAL) faz a validação cair no modo
    antigo, dirigido pelo catálogo — degradação segura para grades legadas.
    """
    cm: dict[tuple[str, str], str] = field(default_factory=dict)
    kits: set[tuple[str, str]] = field(default_factory=set)


@dataclass
class BoIndex:
    """Planilha do BO indexada para consulta por versão de kit."""
    versoes: dict[tuple[str, str], dict[str, dict]] = field(default_factory=dict)
    por_pai: dict[str, dict[str, dict]] = field(default_factory=dict)
    cms_por_sku: dict[str, set] = field(default_factory=dict)


@dataclass
class KitAuditData:
    """Resultado rico da validação de kits, para o painel dedicado no Auditor."""
    # [{sku, pai, brand, status, detail, kind, filho, qtd_sf, qtd_bo, cm_grade, cm_bo}]
    rows: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)   # {total, ok, erro, by_brand:{...}}
    # Um envelope <catalog> por marca (marca -> XML string): cada marca tem seu
    # próprio catalog-id no Salesforce, então não dá pra combinar kits Natura e
    # Avon num único XML com um catalog-id só.
    correction_xmls: dict[str, str] = field(default_factory=dict)


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


def _prefixo(brand: str) -> str:
    """Prefixo de product-id da marca. Sem isto, kits Avon sairiam do XML de
    Correção com ID de Natura."""
    return "AVNBRA-" if brand == "Avon" else "NATBRA-"


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


def _read_bo_excel(path: str) -> BoIndex:
    """Lê a planilha do BO em três índices complementares.

    O BO acumula histórico: o mesmo COD_VENDA reaparece com vários MATERIAL
    (CM) ao longo dos ciclos. Por isso indexamos a composição **por versão**
    ((pai, CM do pai)), guardando também a união de todas as versões (fallback)
    e o conjunto de CMs já vistos para cada SKU (usado para detectar BO
    desatualizado frente à grade).
    """
    df = pd.read_excel(path, sheet_name=0, dtype=str, skiprows=3)
    keys = list(df.columns)

    col_cm_pai   = _find_col(keys, ["MATERIAL_PAI", "MATERIAL_P"],    1)
    col_pai      = _find_col(keys, ["COD_VENDA_PAI"],                 2)
    col_cm_filho = _find_col(keys, ["MATERIAL_FILHO", "MATERIAL_FI"], 5)
    col_filho    = _find_col(keys, ["COD_VENDA_FILHO"],               6)
    col_qtd      = _find_col_ci(keys, "QUANTIDADE",                   8)

    bo = BoIndex()
    for _, row in df.iterrows():
        pai_num   = _so_numeros(row.get(col_pai))
        filho_num = _so_numeros(row.get(col_filho))
        pai_cm    = _so_numeros(row.get(col_cm_pai))
        filho_cm  = _so_numeros(row.get(col_cm_filho))
        try:
            qty = round(float(row.get(col_qtd) or 0))
        except (ValueError, TypeError):
            qty = 0
        if not (pai_num and filho_num):
            continue

        item = {"num": filho_num, "cm": filho_cm, "qty": qty}
        bo.versoes.setdefault((pai_num, pai_cm), {})[filho_num] = item
        bo.por_pai.setdefault(pai_num, {})[filho_num] = item
        if pai_cm:
            bo.cms_por_sku.setdefault(pai_num, set()).add(pai_cm)
        if filho_cm:
            bo.cms_por_sku.setdefault(filho_num, set()).add(filho_cm)
    return bo


def _read_kits_from_xml(paths: list[str]) -> tuple[dict[tuple[str, str], dict], dict[str, str]]:
    """{(marca, sku_num): {raw_pid, filhos:{sku_num: qty}}} — só produtos com bundle.

    Chaveado por marca porque há SKUs numéricos que existem nas duas marcas; sem
    isso um catálogo sobrescreveria o kit do outro. Produtos sem bundle são
    ignorados: o mesmo SKU aparece em vários catálogos (marca + Minha Loja) e o
    espelho sem composição não pode zerar o bundle real.

    Também devolve `catalog_ids: {marca: catalog-id}` — o catalog-id real do
    XML de origem onde um kit daquela marca foi de fato encontrado, usado para
    gerar o XML de Correção com o envelope certo por marca (ver
    `_build_correction_xml`).
    """
    kits: dict[tuple[str, str], dict] = {}
    catalog_ids: dict[str, str] = {}
    for path in paths:
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        cat_id = root.get("catalog-id", "")

        ns = _NS if root.tag.startswith("{") else ""
        tag = lambda t: f"{{{ns}}}{t}" if ns else t  # noqa: E731

        for p in root.iter(tag("product")):
            raw_pid = p.get("product-id", "")
            bundled = p.find(tag("bundled-products"))
            if bundled is None:
                continue

            filhos: dict[str, int] = {}
            for c in bundled.findall(tag("bundled-product")):
                cid_num = _so_numeros(c.get("product-id", ""))
                if not cid_num:
                    continue
                qty_el = c.find(tag("quantity"))
                try:
                    c_qty = round(float(qty_el.text or 0)) if qty_el is not None else 0
                except (ValueError, TypeError):
                    c_qty = 0
                filhos[cid_num] = c_qty

            pid_num = _so_numeros(raw_pid)
            if filhos and pid_num:
                marca = _brand_from_pid(raw_pid)
                chave = (marca, pid_num)
                kits.setdefault(chave, {"raw_pid": raw_pid, "filhos": filhos})
                if cat_id:
                    catalog_ids.setdefault(marca, cat_id)
    return kits, catalog_ids


# Fallback só usado se, por algum motivo, nenhum XML de entrada trouxe um
# catalog-id para a marca (não deveria acontecer: um kit só entra na lista de
# correção se foi lido de algum catálogo — ver validate_kits).
_FALLBACK_CATALOG_ID = {
    "Natura": "natura-br-storefront-catalog",
    "Avon": "avon-br-storefront-catalog",
}


def _build_correction_xml(kits: list[dict], catalog_ids: dict[str, str]) -> dict[str, str]:
    """Gera o XML de Correção (composição do BO) para os kits divergentes, um
    envelope <catalog> por marca — cada marca tem um catalog-id diferente no
    Salesforce, então não é possível combinar Natura e Avon num único XML
    (o import usaria o catalog-id errado para uma das marcas)."""
    por_marca: dict[str, list[dict]] = {}
    for kit in kits:
        por_marca.setdefault(kit.get("marca", "Natura"), []).append(kit)

    xmls: dict[str, str] = {}
    for marca, marca_kits in por_marca.items():
        cat_id = catalog_ids.get(marca) or _FALLBACK_CATALOG_ID.get(marca, _FALLBACK_CATALOG_ID["Natura"])
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<catalog xmlns="{_NS}" catalog-id="{cat_id}">',
        ]
        for kit in marca_kits:
            lines.append(f'  <product product-id="{kit["pid"]}">')
            lines.append("    <bundled-products>")
            for f in kit["filhos"]:
                lines.append(f'      <bundled-product product-id="{f["id"]}">')
                lines.append(f"        <quantity>{f['qty']}</quantity>")
                lines.append("      </bundled-product>")
            lines.append("    </bundled-products>")
            lines.append("  </product>")
        lines.append("</catalog>")
        xmls[marca] = "\n".join(lines)
    return xmls


def _alvos(grade: GradeIndex, kits_cat: dict[tuple[str, str], dict]) -> list[tuple[str, str]]:
    """Universo de kits a auditar.

    Com a grade marcando kits (ZEST) o motor é dirigido pela grade — é o que
    permite flagrar kit ativo sem composição no Salesforce. Sem essa marcação,
    cai no modo antigo (dirigido pelo catálogo), filtrando pela grade quando ela
    existir.
    """
    if grade.kits:
        return sorted(grade.kits)
    if grade.cm:
        return sorted(k for k in kits_cat if k in grade.cm)
    return sorted(kits_cat)


def validate_kits(bo_path: str, cat_paths: list[str],
                  grade: GradeIndex | None = None) -> KitAuditData:
    """
    Audita a composição dos kits do ciclo cruzando Grade × Catálogo × BO.

    Retorna `KitAuditData` com:
      - rows: divergências. `sku`/`brand` alimentam o schema comum; `pai`,
        `status` e `kind` alimentam o painel dedicado; `filho`, `qtd_sf`,
        `qtd_bo`, `cm_grade` e `cm_bo` alimentam o relatório Excel.
      - stats: {total, ok, erro, by_brand: {marca: {total, ok, erro}}}.
      - correction_xmls: composição do BO para os kits divergentes, um XML por
        marca (marca -> XML string).
    """
    grade = grade or GradeIndex()
    bo = _read_bo_excel(bo_path)
    kits_cat, catalog_ids = _read_kits_from_xml(cat_paths)

    rows: list[dict] = []
    kits_para_corrigir: list[dict] = []
    stats = {"total": 0, "ok": 0, "erro": 0, "by_brand": {}}

    for marca, pid in _alvos(grade, kits_cat):
        entry = kits_cat.get((marca, pid))
        raw_pid = entry["raw_pid"] if entry else _prefixo(marca) + pid
        sku = (raw_pid or pid).upper()
        cm_pai = grade.cm.get((marca, pid), "")

        by_brand = stats["by_brand"].setdefault(marca, {"total": 0, "ok": 0, "erro": 0})
        stats["total"] += 1
        by_brand["total"] += 1

        achados: list[dict] = []

        def reportar(kind: str, detail: str, **extra) -> None:
            achados.append({
                "sku": sku, "pai": pid, "brand": marca,
                "status": _STATUS_POR_KIND.get(kind, "Divergente"),
                "detail": detail, "kind": kind,
                "filho": extra.get("filho", ""),
                "qtd_sf": extra.get("qtd_sf", ""),
                "qtd_bo": extra.get("qtd_bo", ""),
                "cm_grade": extra.get("cm_grade", ""),
                "cm_bo": extra.get("cm_bo", ""),
            })

        # 1. Kit ativo na grade que não foi montado como bundle no Salesforce.
        if entry is None:
            cm_txt = f" (CM vigente na Grade: {cm_pai})" if cm_pai else ""
            reportar(KIND_KIT_SEM_BUNDLE,
                     f"A Grade marca este SKU como KIT ativo neste ciclo{cm_txt}, "
                     f"mas ele não foi encontrado com nenhuma composição "
                     f"(bundled-products) em nenhum catálogo do Salesforce — ou "
                     f"seja, o kit está vigente mas ainda não foi montado/publicado.",
                     cm_grade=cm_pai)
            rows.extend(achados)
            stats["erro"] += 1
            by_brand["erro"] += 1
            continue

        filhos_sf: dict[str, int] = entry["filhos"]

        # 2. Composição esperada = versão vigente do kit no BO (MATERIAL_PAI == CM da grade).
        comp = bo.versoes.get((pid, cm_pai)) if cm_pai else None
        if comp is None:
            todas = bo.por_pai.get(pid)
            if not todas:
                reportar(KIND_AUSENTE_NO_BO,
                         "A Grade marca este SKU como KIT ativo neste ciclo e ele "
                         "já está publicado no Salesforce com componentes. Porém, "
                         "não existe nenhuma linha para este pai na planilha do "
                         "BO — sem essa referência, não há como conferir se a "
                         "composição publicada está correta.",
                         cm_grade=cm_pai)
                rows.extend(achados)
                stats["erro"] += 1
                by_brand["erro"] += 1
                continue
            if cm_pai:
                cm_bo_str = ", ".join(sorted(bo.cms_por_sku.get(pid, set()))) or "nenhum"
                reportar(KIND_MATERIAL_PAI_DIV,
                         f"A Grade indica que o material vigente deste kit é o "
                         f"CM {cm_pai}. A planilha do BO não tem nenhuma linha "
                         f"com esse CM para este pai — ela só conhece a(s) "
                         f"versão(ões) {cm_bo_str}. Provável causa: o BO ainda "
                         f"não foi atualizado para o material atual (ou o kit "
                         f"trocou de material recentemente). A composição "
                         f"abaixo foi conferida contra a versão mais recente "
                         f"que o BO conhece.",
                         cm_grade=cm_pai, cm_bo=cm_bo_str)
            comp = todas

        # 3. Catálogo → BO
        for f_sku, q_sf in filhos_sf.items():
            cm_grade_filho = grade.cm.get((marca, f_sku), "")
            if grade.cm and (marca, f_sku) not in grade.cm:
                reportar(KIND_FILHO_FORA_DA_GRADE,
                         f"O componente {f_sku} está publicado no Salesforce "
                         f"dentro deste kit, mas esse SKU não consta na Grade "
                         f"de Ativação do ciclo — ele não deveria estar vigente.",
                         filho=f_sku, qtd_sf=q_sf)
            match = comp.get(f_sku)
            if match is None:
                reportar(KIND_FILHO_AUSENTE_BO,
                         f"O componente {f_sku} (qtd. {q_sf}) está publicado no "
                         f"Salesforce dentro deste kit, mas não existe nenhuma "
                         f"linha no BO ligando esse componente a este pai — nem "
                         f"em versões antigas. O Salesforce publicou algo que o "
                         f"BO desconhece.",
                         filho=f_sku, qtd_sf=q_sf, cm_grade=cm_grade_filho)
            elif match["qty"] != q_sf:
                reportar(KIND_QTD_ERRADA,
                         f"O componente {f_sku} está correto na composição, mas "
                         f"a quantidade diverge: o Salesforce publica {q_sf} "
                         f"unidade(s) e o BO registra {match['qty']} unidade(s) "
                         f"para este mesmo componente.",
                         filho=f_sku, qtd_sf=q_sf, qtd_bo=match["qty"],
                         cm_grade=cm_grade_filho, cm_bo=match["cm"])

        # 4. BO → Catálogo, e material do filho contra a grade
        for f_sku, info in comp.items():
            if f_sku not in filhos_sf:
                reportar(KIND_FILHO_FALTANDO_SF,
                         f"O BO registra o componente {f_sku} ({info['qty']} "
                         f"un.) como parte deste kit, mas ele não foi encontrado "
                         f"entre os componentes publicados no Salesforce. O BO "
                         f"espera esse item no kit, mas o Salesforce não o "
                         f"publicou.",
                         filho=f_sku, qtd_bo=info["qty"], cm_bo=info["cm"],
                         cm_grade=grade.cm.get((marca, f_sku), ""))
                continue
            cm_grade_filho = grade.cm.get((marca, f_sku))
            if cm_grade_filho and cm_grade_filho not in bo.cms_por_sku.get(f_sku, set()):
                cm_bo_str = ", ".join(sorted(bo.cms_por_sku.get(f_sku, set()))) or "nenhum"
                reportar(KIND_MATERIAL_FILHO_DIV,
                         f"A Grade indica que o material vigente do componente "
                         f"{f_sku} é o CM {cm_grade_filho}. O BO não tem "
                         f"nenhuma linha com esse CM para este componente — só "
                         f"conhece a(s) versão(ões) {cm_bo_str}. O componente "
                         f"pode estar certo na composição, mas o BO está "
                         f"referenciando uma versão de material desatualizada.",
                         filho=f_sku, qtd_sf=filhos_sf.get(f_sku, ""),
                         qtd_bo=info["qty"], cm_grade=cm_grade_filho, cm_bo=cm_bo_str)

        if achados:
            rows.extend(achados)
            stats["erro"] += 1
            by_brand["erro"] += 1
            prefixo = _prefixo(marca)
            kits_para_corrigir.append({
                "pid": prefixo + pid,
                "marca": marca,
                "filhos": [{"id": prefixo + f, "qty": i["qty"]} for f, i in comp.items()],
            })
        else:
            stats["ok"] += 1
            by_brand["ok"] += 1

    correction_xmls = _build_correction_xml(kits_para_corrigir, catalog_ids)
    return KitAuditData(rows=rows, stats=stats, correction_xmls=correction_xmls)
