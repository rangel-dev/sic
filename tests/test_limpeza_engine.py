"""
Testes do motor da Limpeza de Campanhas (BRD-015).

Todos os XMLs são inventados — dados reais nunca entram no repositório
(BRD-015, trava 7.4). Os nomes CA-xx remetem aos critérios de aceite.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core import limpeza_engine as le
from src.core.limpeza_engine import (
    AGUARDANDO, DESATIVAR, ELEGIVEL, PROTEGIDO, REVISAR,
    ENT_CAMPAIGNS, ENT_COUPONS, ENT_GROUPS, ENT_PROMOTIONS,
    KIND_COUPONS, KIND_CUSTOMER_GROUPS, KIND_PROMOTIONS,
    LimpezaEngine, LimpezaError, ObservationStore,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _promotions_xml(campaigns=(), promotions=(), assignments=()):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<promotions xmlns="{le.PROMOTIONS_NS}">']
    for c in campaigns:
        out.append(f'<campaign campaign-id="{c["id"]}">')
        out.append(f'<enabled-flag>{"true" if c.get("enabled", True) else "false"}</enabled-flag>')
        out.append('<campaign-scope><applicable-online/></campaign-scope>')
        if "start" in c:
            out.append(f'<start-date>{c["start"]}</start-date>')
        if "end" in c:
            out.append(f'<end-date>{c["end"]}</end-date>')
        groups = c.get("groups", ["Everyone"])
        out.append('<customer-groups match-mode="any">'
                   + "".join(f'<customer-group group-id="{g}"/>' for g in groups) + "</customer-groups>")
        if c.get("coupons"):
            out.append("<coupons>" + "".join(f'<coupon coupon-id="{x}"/>' for x in c["coupons"]) + "</coupons>")
        out.append("</campaign>")
    for p in promotions:
        out.append(f'<promotion promotion-id="{p}"><enabled-flag>true</enabled-flag>'
                   f'<name xml:lang="x-default">{p}</name></promotion>')
    for a in assignments:
        out.append(f'<promotion-campaign-assignment promotion-id="{a["promo"]}" campaign-id="{a["camp"]}">'
                   '<qualifiers match-mode="any"/>')
        if a.get("coupons"):
            out.append("<coupons>" + "".join(f'<coupon coupon-id="{x}"/>' for x in a["coupons"]) + "</coupons>")
        if a.get("groups"):
            out.append('<customer-groups match-mode="any">'
                       + "".join(f'<customer-group group-id="{g}"/>' for g in a["groups"]) + "</customer-groups>")
        out.append("</promotion-campaign-assignment>")
    out.append("</promotions>")
    return "\n".join(out)


def _coupons_xml(coupons=()):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<coupons xmlns="{le.COUPONS_NS}">']
    for c in coupons:
        out.append(f'<coupon coupon-id="{c["id"]}"><description>{c["id"]} desc</description>'
                   f'<enabled-flag>{"true" if c.get("enabled", True) else "false"}</enabled-flag>'
                   '<case-insensitive>true</case-insensitive><redemption-limits/>')
        if c.get("codes"):
            out.append('<multiple-codes><code-prefix>X</code-prefix></multiple-codes>')
        else:
            out.append(f'<single-code>{c["id"].upper()}</single-code>')
        out.append("</coupon>")
    for c in coupons:
        if c.get("codes"):
            out.append(f'<coupon-codes coupon-id="{c["id"]}">'
                       + "".join(f"<code>{c['id']}-{i}</code>" for i in range(c["codes"])) + "</coupon-codes>")
    out.append("</coupons>")
    return "\n".join(out)


def _groups_xml(groups=()):
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<customer-groups xmlns="{le.CUSTOMER_GROUPS_NS}">']
    for g in groups:
        out.append(f'<customer-group group-id="{g["id"]}">')
        if g.get("desc"):
            out.append(f'<description>{g["desc"]}</description>')
        if g.get("dynamic", True):
            out.append("<membership-rule><included-customers/></membership-rule>")
        out.append("<custom-attributes/></customer-group>")
    for g in groups:
        for i in range(g.get("members", 0)):
            out.append(f'<group-assignment group-id="{g["id"]}" customer-no="{i:08d}"/>')
    out.append("</customer-groups>")
    return "\n".join(out)


def _write(tmp_path: Path, promotions="", coupons="", groups="", names=("p.xml", "c.xml", "g.xml")):
    paths = {}
    for kind, content, name in ((KIND_PROMOTIONS, promotions, names[0]),
                                (KIND_COUPONS, coupons, names[1]),
                                (KIND_CUSTOMER_GROUPS, groups, names[2])):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        paths[kind] = str(p)
    return paths


SYSTEM = [{"id": "Everyone"}, {"id": "Registered"}]


def _run(tmp_path, campaigns=(), promotions=(), assignments=(), coupons=(), groups=SYSTEM,
         store=None, now=NOW, loja="natura", record=True, **kw):
    files = _write(tmp_path, _promotions_xml(campaigns, promotions, assignments),
                   _coupons_xml(coupons), _groups_xml(groups))
    eng = LimpezaEngine(files, loja, store=store or ObservationStore(":memory:"), now=now, **kw)
    return eng, eng.simulate(record=record)


def _status(res, entity, item_id):
    return res.items[entity][item_id].status


# ── Reconhecimento dos arquivos ──────────────────────────────────────────────
def test_ca19_reconhece_pelo_namespace_mesmo_com_nomes_trocados(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml(),
                   names=("CUPONS.xml", "PROMOTIONS.xml", "GRUPOS.xml"))
    assert le.detect_kind(files[KIND_PROMOTIONS]) == KIND_PROMOTIONS
    assert le.detect_kind(files[KIND_COUPONS]) == KIND_COUPONS
    sel = le.classify_files(list(files.values()))
    assert sel.complete and sel.paths == files


def test_classificacao_recusa_desconhecido_e_repetido(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    other = tmp_path / "outro_cupons.xml"
    other.write_text(_coupons_xml(), encoding="utf-8")
    junk = tmp_path / "catalogo.xml"
    junk.write_text('<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31"/>', encoding="utf-8")
    sel = le.classify_files([*files.values(), str(other), str(junk)])
    assert sel.complete
    assert {Path(p).name for p, _ in sel.rejected} == {"outro_cupons.xml", "catalogo.xml"}


def test_motor_recusa_arquivo_no_tipo_errado(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    files[KIND_COUPONS], files[KIND_PROMOTIONS] = files[KIND_PROMOTIONS], files[KIND_COUPONS]
    with pytest.raises(LimpezaError):
        LimpezaEngine(files, "natura", store=ObservationStore(":memory:"), now=NOW)


# ── Datas ────────────────────────────────────────────────────────────────────
def test_data_sem_fuso_e_tratada_como_utc_e_ilegivel_sinalizada():
    dt, bad = le.parse_sfcc_date("2026-10-01T10:00:00")
    assert dt.tzinfo is not None and not bad
    assert le.parse_sfcc_date("31/02/2026") == (None, True)
    assert le.parse_sfcc_date("") == (None, False)


# ── Campanhas ────────────────────────────────────────────────────────────────
def test_ca01_vencida_ha_30_dias_ou_mais_e_elegivel_e_menos_e_protegida(tmp_path):
    _, res = _run(tmp_path, campaigns=[
        {"id": "VELHA", "end": _iso(NOW - timedelta(days=30))},
        {"id": "RECENTE", "end": _iso(NOW - timedelta(days=29))},
        {"id": "VIGENTE", "end": _iso(NOW + timedelta(days=5))},
    ])
    assert _status(res, ENT_CAMPAIGNS, "VELHA") == ELEGIVEL
    assert _status(res, ENT_CAMPAIGNS, "RECENTE") == PROTEGIDO
    assert _status(res, ENT_CAMPAIGNS, "VIGENTE") == PROTEGIDO


def test_ca02_perene_habilitada_e_protegida(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "PERENE"}])
    assert _status(res, ENT_CAMPAIGNS, "PERENE") == PROTEGIDO


def test_ca03_perene_desativada_aguarda_carencia_por_observacao(tmp_path):
    store = ObservationStore(":memory:")
    camp = [{"id": "PAUSADA", "enabled": False}]
    _, r1 = _run(tmp_path, campaigns=camp, store=store)
    assert _status(r1, ENT_CAMPAIGNS, "PAUSADA") == AGUARDANDO
    _, r2 = _run(tmp_path, campaigns=camp, store=store, now=NOW + timedelta(days=29))
    assert _status(r2, ENT_CAMPAIGNS, "PAUSADA") == AGUARDANDO
    _, r3 = _run(tmp_path, campaigns=camp, store=store, now=NOW + timedelta(days=30))
    assert _status(r3, ENT_CAMPAIGNS, "PAUSADA") == ELEGIVEL


def test_ca04_data_ilegivel_vai_para_revisar_mesmo_desativada(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "QUEBRADA", "enabled": False, "end": "não-é-data"}])
    assert _status(res, ENT_CAMPAIGNS, "QUEBRADA") == REVISAR


# ── Cascata ──────────────────────────────────────────────────────────────────
def test_ca05_item_ligado_a_campanha_protegida_fica(tmp_path):
    velha = _iso(NOW - timedelta(days=60))
    _, res = _run(
        tmp_path,
        campaigns=[
            {"id": "VELHA", "end": velha, "coupons": ["CUP-COMP"], "groups": ["NAT-RR100"]},
            {"id": "ATIVA", "end": _iso(NOW + timedelta(days=10)), "coupons": ["CUP-COMP"],
             "groups": ["NAT-RR100"]},
        ],
        promotions=["PROMO-COMP"],
        assignments=[{"camp": "VELHA", "promo": "PROMO-COMP"}, {"camp": "ATIVA", "promo": "PROMO-COMP"}],
        coupons=[{"id": "CUP-COMP"}],
        groups=SYSTEM + [{"id": "NAT-RR100"}],
    )
    assert _status(res, ENT_CAMPAIGNS, "VELHA") == ELEGIVEL
    assert _status(res, ENT_PROMOTIONS, "PROMO-COMP") == PROTEGIDO
    assert _status(res, ENT_COUPONS, "CUP-COMP") == PROTEGIDO
    assert _status(res, ENT_GROUPS, "NAT-RR100") == PROTEGIDO


def test_aguardando_carencia_tambem_segura_a_cascata(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "PAUSADA", "enabled": False, "coupons": ["CUP-P"]}],
                  coupons=[{"id": "CUP-P"}])
    assert _status(res, ENT_CAMPAIGNS, "PAUSADA") == AGUARDANDO
    assert _status(res, ENT_COUPONS, "CUP-P") == PROTEGIDO


def test_vinculo_com_campanha_fora_do_arquivo_vai_para_revisar(tmp_path):
    _, res = _run(tmp_path, promotions=["PROMO-X"],
                  assignments=[{"camp": "NAO-EXISTE", "promo": "PROMO-X", "coupons": ["CUP-X"]}],
                  campaigns=[{"id": "QUALQUER"}], coupons=[{"id": "CUP-X"}])
    assert _status(res, ENT_PROMOTIONS, "PROMO-X") == REVISAR
    assert _status(res, ENT_COUPONS, "CUP-X") == REVISAR


# ── Órfãos e carência por observação ────────────────────────────────────────
def test_ca06_orfaos_aguardam_e_depois_ficam_elegiveis(tmp_path):
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "QUALQUER"}], promotions=["PROMO-ORFA"],
              coupons=[{"id": "CUP-ORFAO"}], store=store)
    _, r1 = _run(tmp_path, **kw)
    assert _status(r1, ENT_PROMOTIONS, "PROMO-ORFA") == AGUARDANDO
    assert _status(r1, ENT_COUPONS, "CUP-ORFAO") == AGUARDANDO
    _, r2 = _run(tmp_path, now=NOW + timedelta(days=31), **kw)
    assert _status(r2, ENT_PROMOTIONS, "PROMO-ORFA") == ELEGIVEL
    assert _status(r2, ENT_COUPONS, "CUP-ORFAO") == DESATIVAR   # cupom: 1ª etapa


def test_ca07_contagem_zera_quando_o_item_ganha_campanha(tmp_path):
    store = ObservationStore(":memory:")
    orfa = dict(campaigns=[{"id": "QUALQUER"}], promotions=["PROMO-V"], store=store)
    _run(tmp_path, **orfa)
    _run(tmp_path, assignments=[{"camp": "QUALQUER", "promo": "PROMO-V"}], now=NOW + timedelta(days=10), **orfa)
    _, r = _run(tmp_path, now=NOW + timedelta(days=35), **orfa)
    assert _status(r, ENT_PROMOTIONS, "PROMO-V") == AGUARDANDO   # contou de novo a partir do dia 35


def test_primeira_execucao_nunca_apaga_item_sem_data(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "PAUSADA", "enabled": False}], promotions=["P"],
                  coupons=[{"id": "C"}], groups=SYSTEM + [{"id": "NAT-RR1"}])
    assert res.affected_total == 0


def test_observacao_separada_por_loja(tmp_path):
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "QUALQUER"}], promotions=["PROMO-L"], store=store)
    _run(tmp_path, loja="natura", **kw)
    _, avon = _run(tmp_path, loja="avon", now=NOW + timedelta(days=31), **kw)
    assert _status(avon, ENT_PROMOTIONS, "PROMO-L") == AGUARDANDO


def test_sem_gravar_observacao_nada_sem_data_fica_elegivel(tmp_path):
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "QUALQUER"}], promotions=["PROMO-S"], store=store)
    _run(tmp_path, record=False, **kw)
    _, r = _run(tmp_path, now=NOW + timedelta(days=31), **kw)
    assert _status(r, ENT_PROMOTIONS, "PROMO-S") == AGUARDANDO


# ── Customer groups (N1/N2: só os grupos padrão e DONT_REMOVE são protegidos) ─
def test_ca08_grupos_padrao_e_dont_remove_ficam(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "QUALQUER"}], groups=[
        {"id": "Everyone"}, {"id": "Registered"}, {"id": "Unregistered"},
        {"id": "DONATION_ORDER_DONT_REMOVE"}, {"id": "Grupo X", "desc": "dontremove — usado pelo checkout"},
    ])
    assert all(_status(res, ENT_GROUPS, g) == PROTEGIDO for g in res.items[ENT_GROUPS])


def test_termos_antigos_de_infraestrutura_nao_protegem_mais(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "QUALQUER"}],
                  groups=SYSTEM + [{"id": "System_Team"}, {"id": "productNotFoundLogged"}, {"id": "crm-vip"}])
    for gid in ("System_Team", "productNotFoundLogged", "crm-vip"):
        assert _status(res, ENT_GROUPS, gid) == AGUARDANDO   # seguem as regras normais


def test_lista_protegida_vazia_por_padrao_e_opcional(tmp_path):
    assert le.DEFAULT_PROTECTED_TERMS == ()
    _, res = _run(tmp_path, campaigns=[{"id": "QUALQUER"}], groups=SYSTEM + [{"id": "crm-vip"}],
                  protected_terms=["crm"])
    assert _status(res, ENT_GROUPS, "crm-vip") == PROTEGIDO


def test_ca09_grupo_de_campanha_excluida_e_elegivel_qualquer_que_seja_o_nome(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": _iso(NOW - timedelta(days=40)),
                                        "groups": ["NAT-RR555", "Segunda Compra", "GRUPO_ANTIGO_2019"]}],
                  groups=SYSTEM + [{"id": "NAT-RR555"}, {"id": "Segunda Compra"}, {"id": "GRUPO_ANTIGO_2019"}])
    for gid in ("NAT-RR555", "Segunda Compra", "GRUPO_ANTIGO_2019"):
        assert _status(res, ENT_GROUPS, gid) == ELEGIVEL


def test_ca10_grupo_sem_campanha_aguarda_carencia_e_depois_sai(tmp_path):
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "QUALQUER"}], groups=SYSTEM + [{"id": "Churn geral"}], store=store)
    _, r1 = _run(tmp_path, **kw)
    assert _status(r1, ENT_GROUPS, "Churn geral") == AGUARDANDO
    eng, r2 = _run(tmp_path, now=NOW + timedelta(days=30), **kw)
    assert _status(r2, ENT_GROUPS, "Churn geral") == ELEGIVEL
    out = eng.export(r2, str(tmp_path))
    assert 'group-id="Churn geral"' in Path(out.folder, le.FILE_GROUP_DELETE).read_text(encoding="utf-8")


def test_grupo_ligado_a_campanha_ativa_fica(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "ATIVA", "groups": ["Segunda Compra"]}],
                  groups=SYSTEM + [{"id": "Segunda Compra"}])
    assert _status(res, ENT_GROUPS, "Segunda Compra") == PROTEGIDO


# ── Régua de carência (N3) e lojas LATAM (N6) ────────────────────────────────
def test_regua_de_carencia_ajusta_todas_as_regras(tmp_path):
    camp = [{"id": "VENCIDA-10D", "end": _iso(NOW - timedelta(days=10))}]
    _, r30 = _run(tmp_path, campaigns=camp)
    assert _status(r30, ENT_CAMPAIGNS, "VENCIDA-10D") == PROTEGIDO
    _, r7 = _run(tmp_path, campaigns=camp, grace_days=7)
    assert _status(r7, ENT_CAMPAIGNS, "VENCIDA-10D") == ELEGIVEL
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "QUALQUER"}], promotions=["P-ORFA"], store=store, grace_days=7)
    _run(tmp_path, **kw)
    _, r = _run(tmp_path, now=NOW + timedelta(days=7), **kw)
    assert _status(r, ENT_PROMOTIONS, "P-ORFA") == ELEGIVEL


def test_regua_fora_dos_limites_e_recusada(tmp_path):
    files = _write(tmp_path, _promotions_xml(), _coupons_xml(), _groups_xml())
    for bad in (le.GRACE_MIN_DAYS - 1, le.GRACE_MAX_DAYS + 1):
        with pytest.raises(LimpezaError):
            LimpezaEngine(files, "natura", grace_days=bad, now=NOW)


def test_loja_livre_para_latam(tmp_path):
    assert le.loja_key("Natura Chile") == "natura-chile"
    assert le.loja_key("  Avon   Colômbia ") == le.loja_key("avon colombia") == "avon-colombia"
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": _iso(NOW - timedelta(days=60))}],
                    loja="Natura Chile")
    assert res.loja == "Natura Chile" and res.loja_key == "natura-chile"
    assert Path(eng.export(res, str(tmp_path)).folder).name.startswith("LIMPEZA_NATURA-CHILE_")
    with pytest.raises(LimpezaError):
        _run(tmp_path, loja="   ")


# ── Cupons em duas etapas ────────────────────────────────────────────────────
def test_ca11_cupom_elegivel_primeiro_so_e_desativado(tmp_path):
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": _iso(NOW - timedelta(days=40)),
                                          "coupons": ["CUP-V"]}],
                    coupons=[{"id": "CUP-V", "codes": 3}])
    assert _status(res, ENT_COUPONS, "CUP-V") == DESATIVAR
    out = eng.export(res, str(tmp_path))
    off = ET.parse(Path(out.folder, le.FILE_COUPON_DISABLE)).getroot()
    (coupon,) = list(off)
    assert coupon.findtext("{*}enabled-flag") == "false"
    assert off.find("{*}coupon-codes") is None
    assert "CUP-V" not in Path(out.folder, le.FILE_COUPON_DELETE).read_text(encoding="utf-8")


def test_ca12_cupom_desativado_ha_30_dias_vai_para_exclusao(tmp_path):
    store = ObservationStore(":memory:")
    kw = dict(campaigns=[{"id": "VELHA", "end": _iso(NOW - timedelta(days=40)), "coupons": ["CUP-D"]}],
              coupons=[{"id": "CUP-D", "enabled": False}], store=store)
    _, r1 = _run(tmp_path, **kw)
    assert _status(r1, ENT_COUPONS, "CUP-D") == AGUARDANDO
    _, r2 = _run(tmp_path, now=NOW + timedelta(days=30), **kw)
    assert _status(r2, ENT_COUPONS, "CUP-D") == ELEGIVEL


def test_cupom_desativado_mas_em_uso_fica_e_avisa(tmp_path):
    _, res = _run(tmp_path, campaigns=[{"id": "ATIVA", "coupons": ["CUP-OFF"]}],
                  coupons=[{"id": "CUP-OFF", "enabled": False}])
    item = res.items[ENT_COUPONS]["CUP-OFF"]
    assert item.status == PROTEGIDO and "reative" in item.reason


# ── Exportação e conferência do rollback ─────────────────────────────────────
def _cenario_completo(tmp_path):
    store = ObservationStore(":memory:")
    velha = _iso(NOW - timedelta(days=60))
    kw = dict(
        campaigns=[{"id": "VELHA", "end": velha, "coupons": ["CUP-MULTI"], "groups": ["NAT-RR42"]},
                   {"id": "ATIVA", "coupons": ["CUP-OK"]}],
        promotions=["PROMO-VELHA"],
        assignments=[{"camp": "VELHA", "promo": "PROMO-VELHA"}],
        coupons=[{"id": "CUP-MULTI", "codes": 25, "enabled": False}, {"id": "CUP-OK", "codes": 4}],
        groups=SYSTEM + [{"id": "NAT-RR42", "dynamic": False, "members": 3}],
        store=store,
    )
    _run(tmp_path, **kw)
    return _run(tmp_path, now=NOW + timedelta(days=31), **kw)


def test_ca13_rollback_completo_com_codigos_e_membros(tmp_path):
    eng, res = _cenario_completo(tmp_path)
    assert _status(res, ENT_COUPONS, "CUP-MULTI") == ELEGIVEL
    assert _status(res, ENT_GROUPS, "NAT-RR42") == ELEGIVEL
    out = eng.export(res, str(tmp_path))
    rb = ET.parse(Path(out.folder, le.FILE_COUPON_ROLLBACK)).getroot()
    blocks = rb.findall("{*}coupon-codes")
    assert [b.attrib["coupon-id"] for b in blocks] == ["CUP-MULTI"]
    assert len(blocks[0]) == 25
    tags = [le._local(e.tag) for e in rb]
    assert tags.index("coupon-codes") > tags.index("coupon")   # cupons antes dos códigos
    grb = ET.parse(Path(out.folder, le.FILE_GROUP_ROLLBACK)).getroot()
    assert len(grb.findall("{*}group-assignment")) == 3
    prb = ET.parse(Path(out.folder, le.FILE_PROMO_ROLLBACK)).getroot()
    assert [le._local(e.tag) for e in prb] == ["campaign", "promotion", "promotion-campaign-assignment"]
    assert prb.find("{*}promotion/{*}name").attrib  # xml:lang preservado
    names = {Path(f).name for f in out.files}
    assert {le.FILE_GROUP_ROLLBACK, le.FILE_COUPON_ROLLBACK, le.FILE_PROMO_ROLLBACK,
            "SIMULACAO_LIMPEZA.xlsx"} <= names


def test_ca13_divergencia_na_conferencia_nao_gera_nada(tmp_path):
    eng, res = _cenario_completo(tmp_path)
    eng.coupons["CUP-MULTI"]["codes"] += 1   # simula rollback incompleto
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    with pytest.raises(LimpezaError, match="conferência"):
        eng.export(res, str(out_dir))
    assert list(out_dir.iterdir()) == []


def test_os_3_rollbacks_sao_gerados_mesmo_vazios(tmp_path):
    eng, res = _run(tmp_path, campaigns=[{"id": "VELHA", "end": _iso(NOW - timedelta(days=60))}])
    out = eng.export(res, str(tmp_path))
    for name in (le.FILE_GROUP_ROLLBACK, le.FILE_COUPON_ROLLBACK, le.FILE_PROMO_ROLLBACK):
        assert Path(out.folder, name).exists()
        ET.parse(Path(out.folder, name))   # XML válido


# ── Travas ───────────────────────────────────────────────────────────────────
def test_ca15_arquivos_incoerentes_bloqueiam_e_nao_gravam_observacao(tmp_path):
    store = ObservationStore(":memory:")
    campaigns = [{"id": f"C{i}", "coupons": [f"CUP{i}"]} for i in range(10)]
    eng, res = _run(tmp_path, campaigns=campaigns, promotions=["PROMO-O"],
                    coupons=[{"id": "OUTRA-LOJA-1"}, {"id": "OUTRA-LOJA-2"}], store=store)
    assert not res.coherence_ok and not res.observations_recorded
    with pytest.raises(LimpezaError):
        eng.export(res, str(tmp_path))
    assert store.sync("natura", ENT_PROMOTIONS, le.OBS_ORPHAN, set(), NOW, record=False) == {}


def test_ca16_freio_de_volume(tmp_path):
    velha = _iso(NOW - timedelta(days=60))
    _, res = _run(tmp_path, campaigns=[{"id": "A", "end": velha}, {"id": "B", "end": velha}, {"id": "C"}])
    assert res.volume_alerts and "Campanhas" in res.volume_alerts[0]


def test_planilha_tem_resumo_e_uma_aba_por_entidade(tmp_path):
    _, res = _cenario_completo(tmp_path)
    wb = le.build_workbook(res)
    assert wb.sheetnames == ["Resumo", "Campanhas", "Promoções", "Cupons", "Customer groups"]
